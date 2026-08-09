"""Producer schema validation for allocation-free compact traces."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence


SCHEMA_FORMAT = "retrobus-compact-schema-v1"
ARGUMENT_TYPES = frozenset(("uint", "sint", "bool", "fixed64", "float64"))
EVENT_KINDS = frozenset(
    (
        "slice",
        "instant",
        "counter",
        "flow_start",
        "flow_step",
        "flow_end",
        "async_begin",
        "async_end",
    )
)
TRACK_KINDS = frozenset(("thread", "counter"))
V3_FIRST_EVENT_OPCODE = 0x01
V3_LAST_EVENT_OPCODE = 0xFB
V3_EXTENDED_EVENT_OPCODE = 0xFF


class CompactSchemaError(ValueError):
    """The producer schema is malformed or internally inconsistent."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in pairs:
        if key in result:
            raise CompactSchemaError(f"schema contains duplicate JSON key {key!r}")
        result[key] = item
    return result


def _reject_nonfinite_json(value: str) -> None:
    raise CompactSchemaError(f"schema contains non-finite JSON number {value}")


def _validate_json_value(value: Any, field: str = "schema") -> None:
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CompactSchemaError(f"{field} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{field}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CompactSchemaError(f"{field} contains a non-string object key")
            _validate_json_value(item, f"{field}.{key}")
        return
    raise CompactSchemaError(f"{field} contains a value that JSON cannot represent")


def _reject_unknown_fields(
    value: Mapping[str, Any], allowed: frozenset[str], field: str
) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise CompactSchemaError(
            f"{field} contains unsupported field {unknown[0]!r}"
        )


def _require_int(value: Any, field: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CompactSchemaError(f"{field} must be an integer")
    if not 0 <= value <= maximum:
        raise CompactSchemaError(f"{field} is outside 0..{maximum}")
    return value


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CompactSchemaError(f"{field} must be a non-empty string")
    return value


def _require_sequence(value: Any, field: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise CompactSchemaError(f"{field} must be an array")
    return value


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CompactSchemaError(f"{field} must be an object")
    return value


@dataclass(frozen=True)
class CompactArgumentSchema:
    name: str
    type: str


@dataclass(frozen=True)
class CompactConstantArgumentSchema:
    name: str
    type: str
    value: bool | int | float


@dataclass(frozen=True)
class CompactTrackSchema:
    id: int
    name: str
    kind: str
    unit: str = ""


@dataclass(frozen=True)
class CompactEventSchema:
    id: int
    name: str
    category: str
    kind: str
    arguments: tuple[CompactArgumentSchema, ...]
    correlation_argument: str | None = None
    series: str | None = None
    id_argument: str | None = None
    constant_arguments: tuple[CompactConstantArgumentSchema, ...] = ()


@dataclass(frozen=True)
class CompactSchema:
    producer_id: int
    producer_name: str
    version: int
    process_name: str
    tracks: Mapping[int, CompactTrackSchema]
    events: Mapping[int, CompactEventSchema]
    sha256: bytes
    canonical_json: bytes

    @classmethod
    def load(cls, path: Path | str) -> "CompactSchema":
        source = Path(path)
        try:
            value = json.loads(
                source.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite_json,
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise CompactSchemaError(f"cannot read compact schema {source}: {error}") from error
        return cls.from_mapping(_require_mapping(value, "schema"))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CompactSchema":
        _validate_json_value(value)
        value = dict(value)
        _reject_unknown_fields(
            value,
            frozenset(("format", "producer", "version", "process", "tracks", "events")),
            "schema",
        )
        if value.get("format") != SCHEMA_FORMAT:
            raise CompactSchemaError(
                f"schema format must be {SCHEMA_FORMAT!r}"
            )
        producer = _require_mapping(value.get("producer"), "producer")
        _reject_unknown_fields(producer, frozenset(("id", "name")), "producer")
        producer_id = _require_int(producer.get("id"), "producer.id", 0xFFFF_FFFF)
        producer_name = _require_text(producer.get("name"), "producer.name")
        version = _require_int(value.get("version"), "version", 0xFFFF_FFFF)
        process_name = _require_text(value.get("process"), "process")

        tracks: dict[int, CompactTrackSchema] = {}
        for index, raw_track in enumerate(_require_sequence(value.get("tracks"), "tracks")):
            track = _require_mapping(raw_track, f"tracks[{index}]")
            _reject_unknown_fields(
                track, frozenset(("id", "name", "kind", "unit")), f"tracks[{index}]"
            )
            track_id = _require_int(track.get("id"), f"tracks[{index}].id", 0xFFFF_FFFF)
            if track_id in tracks:
                raise CompactSchemaError(f"duplicate track ID {track_id}")
            kind = _require_text(track.get("kind"), f"tracks[{index}].kind")
            if kind not in TRACK_KINDS:
                raise CompactSchemaError(f"unsupported track kind {kind!r}")
            unit = track.get("unit", "")
            if not isinstance(unit, str):
                raise CompactSchemaError(f"tracks[{index}].unit must be a string")
            tracks[track_id] = CompactTrackSchema(
                id=track_id,
                name=_require_text(track.get("name"), f"tracks[{index}].name"),
                kind=kind,
                unit=unit,
            )
        if not tracks:
            raise CompactSchemaError("at least one track is required")

        events: dict[int, CompactEventSchema] = {}
        for index, raw_event in enumerate(_require_sequence(value.get("events"), "events")):
            event = _require_mapping(raw_event, f"events[{index}]")
            _reject_unknown_fields(
                event,
                frozenset(
                    (
                        "id",
                        "name",
                        "category",
                        "kind",
                        "arguments",
                        "correlation_argument",
                        "series",
                        "id_argument",
                        "constant_arguments",
                    )
                ),
                f"events[{index}]",
            )
            event_id = _require_int(event.get("id"), f"events[{index}].id", 0xFFFF_FFFF)
            if event_id in events:
                raise CompactSchemaError(f"duplicate event ID {event_id}")
            kind = _require_text(event.get("kind"), f"events[{index}].kind")
            if kind not in EVENT_KINDS:
                raise CompactSchemaError(f"unsupported event kind {kind!r}")
            arguments: list[CompactArgumentSchema] = []
            argument_names: set[str] = set()
            for argument_index, raw_argument in enumerate(
                _require_sequence(event.get("arguments", []), f"events[{index}].arguments")
            ):
                argument = _require_mapping(
                    raw_argument, f"events[{index}].arguments[{argument_index}]"
                )
                _reject_unknown_fields(
                    argument,
                    frozenset(("name", "type")),
                    f"events[{index}].arguments[{argument_index}]",
                )
                name = _require_text(
                    argument.get("name"),
                    f"events[{index}].arguments[{argument_index}].name",
                )
                if name in argument_names:
                    raise CompactSchemaError(
                        f"event {event_id} has duplicate argument {name!r}"
                    )
                argument_type = _require_text(
                    argument.get("type"),
                    f"events[{index}].arguments[{argument_index}].type",
                )
                if argument_type not in ARGUMENT_TYPES:
                    raise CompactSchemaError(
                        f"event {event_id} has unsupported argument type {argument_type!r}"
                    )
                argument_names.add(name)
                arguments.append(CompactArgumentSchema(name=name, type=argument_type))
            if len(arguments) > 4:
                raise CompactSchemaError(f"event {event_id} exceeds four arguments")

            id_argument = event.get("id_argument")
            if id_argument is not None:
                id_argument = _require_text(
                    id_argument, f"events[{index}].id_argument"
                )
                if id_argument in argument_names:
                    raise CompactSchemaError(
                        f"event {event_id} derived argument {id_argument!r} collides "
                        "with a stored argument"
                    )
                argument_names.add(id_argument)

            constant_arguments: list[CompactConstantArgumentSchema] = []
            for constant_index, raw_constant in enumerate(
                _require_sequence(
                    event.get("constant_arguments", []),
                    f"events[{index}].constant_arguments",
                )
            ):
                constant = _require_mapping(
                    raw_constant,
                    f"events[{index}].constant_arguments[{constant_index}]",
                )
                _reject_unknown_fields(
                    constant,
                    frozenset(("name", "type", "value")),
                    f"events[{index}].constant_arguments[{constant_index}]",
                )
                name = _require_text(
                    constant.get("name"),
                    f"events[{index}].constant_arguments[{constant_index}].name",
                )
                if name in argument_names:
                    raise CompactSchemaError(
                        f"event {event_id} has duplicate or colliding argument {name!r}"
                    )
                argument_type = _require_text(
                    constant.get("type"),
                    f"events[{index}].constant_arguments[{constant_index}].type",
                )
                if argument_type not in ARGUMENT_TYPES:
                    raise CompactSchemaError(
                        f"event {event_id} has unsupported constant argument type "
                        f"{argument_type!r}"
                    )
                constant_value = constant.get("value")
                if argument_type == "bool":
                    if not isinstance(constant_value, bool):
                        raise CompactSchemaError(
                            f"event {event_id} constant {name!r} must be boolean"
                        )
                elif argument_type == "float64":
                    finite_float = False
                    if not isinstance(constant_value, bool) and isinstance(
                        constant_value, (int, float)
                    ):
                        try:
                            finite_float = math.isfinite(constant_value)
                        except OverflowError:
                            pass
                    if not finite_float:
                        raise CompactSchemaError(
                            f"event {event_id} constant {name!r} must be finite numeric"
                        )
                    assert not isinstance(constant_value, bool) and isinstance(
                        constant_value, (int, float)
                    )
                    constant_value = float(constant_value)
                elif isinstance(constant_value, bool) or not isinstance(
                    constant_value, int
                ):
                    raise CompactSchemaError(
                        f"event {event_id} constant {name!r} must be an integer"
                    )
                elif argument_type in {"uint", "fixed64"} and not (
                    0 <= constant_value <= 0xFFFF_FFFF_FFFF_FFFF
                ):
                    raise CompactSchemaError(
                        f"event {event_id} constant {name!r} is outside unsigned 64-bit"
                    )
                elif argument_type == "sint" and not (
                    -(1 << 63) <= constant_value < (1 << 63)
                ):
                    raise CompactSchemaError(
                        f"event {event_id} constant {name!r} is outside signed 64-bit"
                    )
                argument_names.add(name)
                constant_arguments.append(
                    CompactConstantArgumentSchema(name, argument_type, constant_value)
                )
            if kind == "counter" and len(arguments) != 1:
                raise CompactSchemaError(
                    f"counter event {event_id} must have exactly one value argument"
                )
            if kind == "counter" and arguments[0].type not in {
                "uint",
                "sint",
                "float64",
            }:
                raise CompactSchemaError(
                    f"counter event {event_id} has unsupported value type "
                    f"{arguments[0].type!r}"
                )
            correlation = event.get("correlation_argument")
            series: str | None = None
            if kind.startswith("flow_") or kind.startswith("async_"):
                correlation = _require_text(
                    correlation, f"events[{index}].correlation_argument"
                )
                stored_arguments = {
                    argument.name: argument for argument in arguments
                }
                if correlation not in stored_arguments:
                    raise CompactSchemaError(
                        f"event {event_id} correlation argument {correlation!r} "
                        "must name a stored argument"
                    )
                correlation_schema = stored_arguments[correlation]
                if correlation_schema.type != "uint":
                    raise CompactSchemaError(
                        f"event {event_id} correlation argument must have type 'uint'"
                    )
                series = event.get("series", event.get("name"))
                series = _require_text(series, f"events[{index}].series")
            elif correlation is not None:
                raise CompactSchemaError(
                    f"event {event_id} does not support correlation_argument"
                )
            elif event.get("series") is not None:
                raise CompactSchemaError(f"event {event_id} does not support series")
            events[event_id] = CompactEventSchema(
                id=event_id,
                name=_require_text(event.get("name"), f"events[{index}].name"),
                category=_require_text(
                    event.get("category"), f"events[{index}].category"
                ),
                kind=kind,
                arguments=tuple(arguments),
                correlation_argument=correlation,
                series=series,
                id_argument=id_argument,
                constant_arguments=tuple(constant_arguments),
            )
        if not events:
            raise CompactSchemaError("at least one event is required")

        lifecycle_kinds: dict[tuple[str, str], set[str]] = {}
        for schema_event in events.values():
            if schema_event.series is None:
                continue
            family = (
                "async" if schema_event.kind.startswith("async_") else "flow"
            )
            lifecycle_kinds.setdefault((family, schema_event.series), set()).add(
                schema_event.kind
            )
        for (family, series_name), kinds in lifecycle_kinds.items():
            required = (
                {"async_begin", "async_end"}
                if family == "async"
                else {"flow_start", "flow_end"}
            )
            if not required.issubset(kinds):
                missing = sorted(required - kinds)[0]
                raise CompactSchemaError(
                    f"{family} series {series_name!r} is missing {missing}"
                )

        try:
            canonical = json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        except (TypeError, UnicodeError, ValueError) as error:
            raise CompactSchemaError(f"schema cannot be canonically encoded: {error}") from error
        return cls(
            producer_id=producer_id,
            producer_name=producer_name,
            version=version,
            process_name=process_name,
            tracks=MappingProxyType(tracks),
            events=MappingProxyType(events),
            sha256=hashlib.sha256(canonical).digest(),
            canonical_json=canonical,
        )

    @property
    def v3_event_opcodes(self) -> Mapping[int, int]:
        """Return the deterministic v3 ordinary opcode for each direct event."""
        direct_events = sorted(self.events)[:V3_LAST_EVENT_OPCODE]
        return MappingProxyType(
            {
                event_id: V3_FIRST_EVENT_OPCODE + index
                for index, event_id in enumerate(direct_events)
            }
        )

    @property
    def v3_inline_opcodes(self) -> Mapping[int, tuple[int, int]]:
        """Return schema-derived delta-zero/one opcodes for minimal instants."""
        direct_count = min(len(self.events), V3_LAST_EVENT_OPCODE)
        available = iter(range(V3_FIRST_EVENT_OPCODE + direct_count, 0xFC))
        result: dict[int, tuple[int, int]] = {}
        for event in sorted(self.events.values(), key=lambda item: item.id):
            if event.kind != "instant" or event.arguments:
                continue
            try:
                delta_zero = next(available)
                delta_one = next(available)
            except StopIteration:
                break
            result[event.id] = (delta_zero, delta_one)
        return MappingProxyType(result)


def _c_identifier(value: str, fallback: str | None = None) -> str:
    identifier = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    if not identifier:
        if fallback is None:
            raise CompactSchemaError("C identifier prefix is empty")
        identifier = fallback
    if identifier[0].isdigit():
        identifier = f"TRACE_{identifier}"
    return identifier


def _unique_c_symbols(
    values: Sequence[CompactTrackSchema | CompactEventSchema],
) -> dict[int, str]:
    bases = [_c_identifier(value.name, f"ID_{value.id}") for value in values]
    counts = Counter(bases)
    symbols: dict[int, str] = {}
    used: set[str] = set()
    for value, base in zip(values, bases):
        candidate = base if counts[base] == 1 else f"{base}_{value.id}"
        if candidate in used:
            root = f"{base}_{value.id}"
            candidate = root
            disambiguator = 2
            while candidate in used:
                candidate = f"{root}_{disambiguator}"
                disambiguator += 1
        used.add(candidate)
        symbols[value.id] = candidate
    return symbols


def _c_argument_parameter(
    specification: CompactArgumentSchema, index: int
) -> tuple[str, str, str]:
    suffix = re.sub(r"[^A-Za-z0-9]+", "_", specification.name).strip("_").lower()
    parameter = f"argument_{index}_{suffix or 'value'}"
    if specification.type == "sint":
        return f"int64_t {parameter}", f"rbct_argument_i64({parameter})", parameter
    if specification.type == "bool":
        return (
            f"int {parameter}",
            f"rbct_argument_u64({parameter} != 0)",
            parameter,
        )
    if specification.type in {"fixed64", "float64"}:
        bits_parameter = f"{parameter}_bits"
        return (
            f"uint64_t {bits_parameter}",
            f"rbct_argument_fixed64({bits_parameter})",
            bits_parameter,
        )
    return f"uint64_t {parameter}", f"rbct_argument_u64({parameter})", parameter


def render_c_schema_header(schema: CompactSchema, prefix: str | None = None) -> str:
    """Render stable IDs, typed emitters, and the schema hash for a producer."""
    if prefix is None:
        producer_symbol = _c_identifier(schema.producer_name, "PRODUCER")
        symbol = f"{producer_symbol}_{schema.producer_id}_V{schema.version}"
    else:
        symbol = _c_identifier(prefix, f"PRODUCER_{schema.producer_id}")
    guard = f"{symbol}_COMPACT_TRACE_SCHEMA_H"
    lines = [
        f"#ifndef {guard}",
        f"#define {guard}",
        "",
        "#include <stdint.h>",
        "#include <retrobus/compact_trace.h>",
        "",
        f"#define {symbol}_TRACE_PRODUCER_ID UINT32_C({schema.producer_id})",
        f"#define {symbol}_TRACE_SCHEMA_VERSION UINT32_C({schema.version})",
    ]
    tracks = sorted(schema.tracks.values(), key=lambda item: item.id)
    track_symbols = _unique_c_symbols(tracks)
    for track in tracks:
        track_symbol = track_symbols[track.id]
        lines.append(
            f"#define {symbol}_TRACE_TRACK_{track_symbol} "
            f"UINT32_C({track.id})"
        )
    lines.extend(("", f"static inline int {symbol}_TRACE_TRACK_KIND(uint32_t track_id) {{"))
    lines.append("  switch (track_id) {")
    for track in tracks:
        track_symbol = track_symbols[track.id]
        kind_value = 1 if track.kind == "counter" else 0
        lines.append(f"    case {symbol}_TRACE_TRACK_{track_symbol}:")
        lines.append(f"      return {kind_value};")
    lines.extend(("    default:", "      return -1;", "  }", "}"))
    events = sorted(schema.events.values(), key=lambda item: item.id)
    event_symbols = _unique_c_symbols(events)
    event_opcodes = schema.v3_event_opcodes
    inline_opcodes = schema.v3_inline_opcodes
    for event in events:
        event_symbol = event_symbols[event.id]
        lines.append(
            f"#define {symbol}_TRACE_EVENT_{event_symbol} "
            f"UINT32_C({event.id})"
        )
        opcode = event_opcodes.get(event.id, V3_EXTENDED_EVENT_OPCODE)
        lines.append(
            f"#define {symbol}_TRACE_OPCODE_{event_symbol} "
            f"UINT8_C({opcode})"
        )
        inline = inline_opcodes.get(event.id)
        if inline is not None:
            lines.append(
                f"#define {symbol}_TRACE_OPCODE_{event_symbol}_DELTA_ZERO "
                f"UINT8_C({inline[0]})"
            )
            lines.append(
                f"#define {symbol}_TRACE_OPCODE_{event_symbol}_DELTA_ONE "
                f"UINT8_C({inline[1]})"
            )
    for event in events:
        event_symbol = event_symbols[event.id]
        operation = "BEGIN" if event.kind == "slice" else "EMIT"
        function = f"{symbol}_TRACE_{operation}_{event_symbol}"
        parameters = [
            "rbct_writer_t* writer",
            "uint64_t timestamp",
            "uint32_t track_id",
        ]
        initializers: list[str] = []
        parameter_names: list[str] = []
        for index, argument in enumerate(event.arguments):
            parameter, initializer, parameter_name = _c_argument_parameter(argument, index)
            parameters.append(parameter)
            initializers.append(initializer)
            parameter_names.append(parameter_name)
        lines.extend(("", f"static inline rbct_status_t {function}("))
        for index, parameter in enumerate(parameters):
            if index + 1 < len(parameters):
                lines.append(f"    {parameter},")
            else:
                lines.append(f"    {parameter}) {{")
        lines.extend(
            (
                "  if (!rbct_writer_enabled(writer)) {",
                "    return RBCT_INVALID_STATE;",
                "  }",
            )
        )
        expected_track_kind = 1 if event.kind == "counter" else 0
        lines.append(
            f"  if ({symbol}_TRACE_TRACK_KIND(track_id) != {expected_track_kind}) {{"
        )
        lines.extend(
            (
                "    ++writer->dropped_records;",
                "    return RBCT_INVALID_ARGUMENT;",
                "  }",
            )
        )
        if (
            event.kind == "counter"
            and event.arguments
            and event.arguments[0].type == "uint"
        ):
            lines.append(
                f"  if ({parameter_names[0]} > UINT64_C(0x7fffffffffffffff)) {{"
            )
            lines.extend(
                (
                    "    ++writer->dropped_records;",
                    "    return RBCT_INVALID_ARGUMENT;",
                    "  }",
                )
            )
        if (
            event.kind == "counter"
            and event.arguments
            and event.arguments[0].type == "float64"
        ):
            lines.append(
                f"  if (({parameter_names[0]} & UINT64_C(0x7ff0000000000000)) "
                "== UINT64_C(0x7ff0000000000000)) {"
            )
            lines.extend(
                (
                    "    ++writer->dropped_records;",
                    "    return RBCT_INVALID_ARGUMENT;",
                    "  }",
                )
            )
        if initializers:
            lines.append(
                f"  const rbct_argument_t arguments[{len(initializers)}] = {{"
            )
            lines.append(f"      {', '.join(initializers)}}};")
            call_arguments = f"arguments, {len(initializers)}u"
        else:
            call_arguments = "NULL, 0u"
        writer_function = (
            "rbct_writer_begin_opcode"
            if event.kind == "slice"
            else "rbct_writer_emit_opcode"
        )
        lines.append(
            f"  return {writer_function}("
        )
        lines.append(
            f"      writer, timestamp, track_id, {symbol}_TRACE_EVENT_{event_symbol},"
        )
        lines.append(f"      {symbol}_TRACE_OPCODE_{event_symbol},")
        if event.kind != "slice":
            inline = inline_opcodes.get(event.id)
            if inline is None:
                lines.append("      UINT8_C(0), UINT8_C(0),")
            else:
                lines.append(
                    f"      {symbol}_TRACE_OPCODE_{event_symbol}_DELTA_ZERO,"
                )
                lines.append(
                    f"      {symbol}_TRACE_OPCODE_{event_symbol}_DELTA_ONE,"
                )
        lines.append(f"      {call_arguments});")
        lines.append("}")
    hash_bytes = ", ".join(f"0x{byte:02x}" for byte in schema.sha256)
    lines.extend(
        (
            "",
            f"static const uint8_t {symbol}_TRACE_SCHEMA_SHA256[32] = {{",
            f"    {hash_bytes}",
            "};",
            "",
            f"#endif  /* {guard} */",
            "",
        )
    )
    return "\n".join(lines)
