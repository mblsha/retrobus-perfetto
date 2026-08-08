"""Producer schema validation for allocation-free compact traces."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
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


class CompactSchemaError(ValueError):
    """The producer schema is malformed or internally inconsistent."""


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
            value = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CompactSchemaError(f"cannot read compact schema {source}: {error}") from error
        return cls.from_mapping(_require_mapping(value, "schema"))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CompactSchema":
        if value.get("format") != SCHEMA_FORMAT:
            raise CompactSchemaError(
                f"schema format must be {SCHEMA_FORMAT!r}"
            )
        producer = _require_mapping(value.get("producer"), "producer")
        producer_id = _require_int(producer.get("id"), "producer.id", 0xFFFF_FFFF)
        producer_name = _require_text(producer.get("name"), "producer.name")
        version = _require_int(value.get("version"), "version", 0xFFFF_FFFF)
        process_name = _require_text(value.get("process"), "process")

        tracks: dict[int, CompactTrackSchema] = {}
        for index, raw_track in enumerate(_require_sequence(value.get("tracks"), "tracks")):
            track = _require_mapping(raw_track, f"tracks[{index}]")
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
                    if (
                        isinstance(constant_value, bool)
                        or not isinstance(constant_value, (int, float))
                        or not math.isfinite(constant_value)
                    ):
                        raise CompactSchemaError(
                            f"event {event_id} constant {name!r} must be finite numeric"
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
            if kind.startswith("flow_") or kind.startswith("async_"):
                correlation = _require_text(
                    correlation, f"events[{index}].correlation_argument"
                )
                if correlation not in argument_names:
                    raise CompactSchemaError(
                        f"event {event_id} correlation argument {correlation!r} is absent"
                    )
                correlation_schema = next(
                    argument for argument in arguments if argument.name == correlation
                )
                if correlation_schema.type != "uint":
                    raise CompactSchemaError(
                        f"event {event_id} correlation argument must have type 'uint'"
                    )
            elif correlation is not None:
                raise CompactSchemaError(
                    f"event {event_id} does not support correlation_argument"
                )
            events[event_id] = CompactEventSchema(
                id=event_id,
                name=_require_text(event.get("name"), f"events[{index}].name"),
                category=_require_text(
                    event.get("category"), f"events[{index}].category"
                ),
                kind=kind,
                arguments=tuple(arguments),
                correlation_argument=correlation,
                id_argument=id_argument,
                constant_arguments=tuple(constant_arguments),
            )
        if not events:
            raise CompactSchemaError("at least one event is required")

        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return cls(
            producer_id=producer_id,
            producer_name=producer_name,
            version=version,
            process_name=process_name,
            tracks=tracks,
            events=events,
            sha256=hashlib.sha256(canonical).digest(),
            canonical_json=canonical,
        )


def _c_identifier(value: str) -> str:
    identifier = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    if not identifier:
        raise CompactSchemaError("C identifier prefix is empty")
    if identifier[0].isdigit():
        identifier = f"TRACE_{identifier}"
    return identifier


def render_c_schema_header(schema: CompactSchema, prefix: str | None = None) -> str:
    """Render stable IDs and the canonical schema hash for a target producer."""
    symbol = _c_identifier(prefix or schema.producer_name)
    guard = f"{symbol}_COMPACT_TRACE_SCHEMA_H"
    lines = [
        f"#ifndef {guard}",
        f"#define {guard}",
        "",
        "#include <stdint.h>",
        "",
        f"#define {symbol}_TRACE_PRODUCER_ID UINT32_C({schema.producer_id})",
        f"#define {symbol}_TRACE_SCHEMA_VERSION UINT32_C({schema.version})",
    ]
    for track in sorted(schema.tracks.values(), key=lambda item: item.id):
        lines.append(
            f"#define {symbol}_TRACE_TRACK_{_c_identifier(track.name)} "
            f"UINT32_C({track.id})"
        )
    for event in sorted(schema.events.values(), key=lambda item: item.id):
        lines.append(
            f"#define {symbol}_TRACE_EVENT_{_c_identifier(event.name)} "
            f"UINT32_C({event.id})"
        )
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
