"""Static context-codec profiles for the compact v4 target writer."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import heapq
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, cast, Iterable, Mapping, Sequence, TYPE_CHECKING

from .compact_schema import CompactSchema

if TYPE_CHECKING:
    from .compact import CompactClockSync, CompactRecord, CompactTrace


CODEC_PROFILE_FORMAT = "retrobus-compact-codec-profile-v1"
CODEC_PROFILE_ENTRY_LIMITS = frozenset((128, 247))
CODEC_PROFILE_MAX_CODE_BITS = 12
CODEC_PROFILE_INITIAL_STATE = 2
CODEC_PROFILE_STATE_CANDIDATES = 12


class CompactCodecProfileError(ValueError):
    """A v4 codec profile is malformed or does not match its schema."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CompactCodecProfileError(
                f"codec profile contains duplicate JSON key {key!r}"
            )
        result[key] = value
    return result


def _reverse_bits(value: int, width: int) -> int:
    result = 0
    for _ in range(width):
        result = (result << 1) | (value & 1)
        value >>= 1
    return result


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _require_int(value: Any, field: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CompactCodecProfileError(f"{field} must be an integer")
    if not 0 <= value <= maximum:
        raise CompactCodecProfileError(f"{field} is outside 0..{maximum}")
    return value


@dataclass(frozen=True, order=True)
class CompactCodecEntry:
    state: int
    event_id: int
    delta: int
    duration: int
    code: int
    code_length: int
    training_count: int = 0

    @property
    def key(self) -> int:
        return (
            (self.state << 24)
            | (self.event_id << 16)
            | (self.delta << 8)
            | self.duration
        )

    @property
    def code_info(self) -> int:
        return (self.code_length << 12) | self.code


@dataclass(frozen=True)
class CompactCodecHash:
    multiplier1: int
    multiplier2: int
    displacements: bytes
    keys: tuple[int, ...]
    code_info: tuple[int, ...]


def _hash_index(key: int, multiplier: int, size: int) -> int:
    shift = 32 - (size.bit_length() - 1)
    return ((key * multiplier) & 0xFFFF_FFFF) >> shift


def _build_perfect_hash(
    entries: Sequence[CompactCodecEntry], entry_limit: int
) -> CompactCodecHash:
    bucket_count = 64 if entry_limit == 128 else 128
    slot_count = 128 if entry_limit == 128 else 256
    mask = slot_count - 1
    seed = int.from_bytes(
        hashlib.sha256(
            b"".join(entry.key.to_bytes(4, "little") for entry in entries)
        ).digest()[:8],
        "little",
    )
    for attempt in range(20_000):
        first = (0x9E37_79B1 + 2 * ((seed + attempt * 0x85EB_CA6B) & 0x7FFF_FFFF)) & 0xFFFF_FFFF
        second = (0xC2B2_AE35 + 2 * ((seed >> 17) + attempt * 0x27D4_EB2D)) & 0xFFFF_FFFF
        first |= 1
        second |= 1
        buckets: list[list[CompactCodecEntry]] = [
            [] for _ in range(bucket_count)
        ]
        for entry in entries:
            buckets[_hash_index(entry.key, first, bucket_count)].append(entry)
        order = sorted(range(bucket_count), key=lambda index: -len(buckets[index]))
        occupied = [False] * slot_count
        slots: list[CompactCodecEntry | None] = [None] * slot_count
        displacement = [0] * bucket_count
        failed = False
        for bucket in order:
            values = buckets[bucket]
            if len(values) <= 1:
                continue
            for candidate in range(slot_count):
                indexes = [
                    (_hash_index(entry.key, second, slot_count) + candidate) & mask
                    for entry in values
                ]
                if len(set(indexes)) == len(indexes) and not any(
                    occupied[index] for index in indexes
                ):
                    displacement[bucket] = candidate
                    for index, entry in zip(indexes, values):
                        occupied[index] = True
                        slots[index] = entry
                    break
            else:
                failed = True
                break
        if failed:
            continue
        free = iter(index for index, value in enumerate(occupied) if not value)
        for bucket in order:
            values = buckets[bucket]
            if len(values) != 1:
                continue
            entry = values[0]
            index = next(free)
            displacement[bucket] = (
                index - _hash_index(entry.key, second, slot_count)
            ) & mask
            occupied[index] = True
            slots[index] = entry
        return CompactCodecHash(
            first,
            second,
            bytes(displacement),
            tuple(entry.key if entry is not None else 0 for entry in slots),
            tuple(entry.code_info if entry is not None else 0 for entry in slots),
        )
    raise CompactCodecProfileError("could not construct compact perfect hash")


def _limited_huffman_lengths(
    frequencies: Mapping[object, int], maximum_bits: int
) -> Mapping[object, int]:
    symbols = sorted(frequencies, key=repr)
    if len(symbols) == 1:
        return {symbols[0]: 1}
    heap: list[tuple[int, int, object]] = [
        (max(1, frequencies[symbol]), index, symbol)
        for index, symbol in enumerate(symbols)
    ]
    heapq.heapify(heap)
    serial = len(heap)
    while len(heap) > 1:
        left_weight, _, left = heapq.heappop(heap)
        right_weight, _, right = heapq.heappop(heap)
        heapq.heappush(
            heap,
            (left_weight + right_weight, serial, (left, right)),
        )
        serial += 1
    raw_lengths: dict[object, int] = {}

    def visit(node: object, depth: int) -> None:
        if node in frequencies:
            raw_lengths[node] = max(1, depth)
        else:
            left, right = cast(tuple[object, object], node)
            visit(left, depth + 1)
            visit(right, depth + 1)

    visit(heap[0][2], 0)
    counts = [0] * (maximum_bits + 1)
    overflow = 0
    for length in raw_lengths.values():
        if length > maximum_bits:
            length = maximum_bits
            overflow += 1
        counts[length] += 1
    while overflow > 0:
        bits = maximum_bits - 1
        while bits > 0 and counts[bits] == 0:
            bits -= 1
        if bits == 0 or counts[maximum_bits] == 0:
            raise CompactCodecProfileError("cannot length-limit Huffman profile")
        counts[bits] -= 1
        counts[bits + 1] += 2
        counts[maximum_bits] -= 1
        overflow -= 2
    by_frequency = sorted(symbols, key=lambda symbol: (frequencies[symbol], repr(symbol)))
    result: dict[object, int] = {}
    index = 0
    for bits in range(maximum_bits, 0, -1):
        for _ in range(counts[bits]):
            result[by_frequency[index]] = bits
            index += 1
    if index != len(symbols):
        raise CompactCodecProfileError("invalid length-limited Huffman profile")
    return result


def _canonical_codes(lengths: Mapping[object, int]) -> Mapping[object, tuple[int, int]]:
    counts = Counter(lengths.values())
    next_code: dict[int, int] = {}
    code = 0
    for bits in range(1, max(counts, default=0) + 1):
        code = (code + counts.get(bits - 1, 0)) << 1
        next_code[bits] = code
    result: dict[object, tuple[int, int]] = {}
    for symbol in sorted(lengths, key=lambda item: (lengths[item], repr(item))):
        width = lengths[symbol]
        canonical = next_code[width]
        next_code[width] += 1
        result[symbol] = (_reverse_bits(canonical, width), width)
    return result


def _profile_state(previous_event_id: int | None, state_events: tuple[int, int]) -> int:
    if previous_event_id == state_events[0]:
        return 0
    if previous_event_id == state_events[1]:
        return 1
    return CODEC_PROFILE_INITIAL_STATE


def _estimated_profile_bits(
    frequencies: Counter[tuple[int, int, int, int]],
    state_totals: Counter[int],
    entry_limit: int,
) -> int:
    selected = dict(frequencies.most_common(entry_limit))
    result = 0
    for state in range(3):
        symbols = {
            key: count for key, count in selected.items() if key[0] == state
        }
        escape = ("escape", state)
        escaped = max(1, state_totals[state] - sum(symbols.values()))
        weighted: dict[object, int] = {
            cast(object, key): count for key, count in symbols.items()
        }
        weighted[escape] = escaped
        lengths = _limited_huffman_lengths(
            weighted, CODEC_PROFILE_MAX_CODE_BITS
        )
        result += sum(weighted[symbol] * width for symbol, width in lengths.items())
    return result


def _training_frequencies(
    trace: "CompactTrace", state_events: tuple[int, int]
) -> tuple[Counter[tuple[int, int, int, int]], Counter[int]]:
    from .compact import CompactClockSync

    items: list[CompactRecord | CompactClockSync] = [
        *trace.records,
        *trace.clock_syncs,
    ]
    items.sort(key=lambda item: item.order)
    mask = (1 << trace.header.clock_width_bits) - 1
    timestamp = 0
    track = trace.header.default_track
    generation: int | None = None
    previous_event: int | None = None
    frequencies: Counter[tuple[int, int, int, int]] = Counter()
    state_totals: Counter[int] = Counter()
    for item in items:
        if generation != item.generation:
            generation = item.generation
            timestamp = (
                item.counter_before
                if isinstance(item, CompactClockSync)
                else item.raw_timestamp
            )
            track = trace.header.default_track
            previous_event = None
        if isinstance(item, CompactClockSync):
            timestamp = (
                item.counter_before + ((item.counter_after - item.counter_before) & mask) // 2
            ) & mask
            continue
        state = _profile_state(previous_event, state_events)
        state_totals[state] += 1
        delta = (item.raw_timestamp - timestamp) & mask
        if (
            item.event.kind == "slice"
            and not item.event.arguments
            and item.track_id == track
            and item.event.id <= 0xFF
            and delta <= 0xFF
            and item.duration_ticks is not None
            and item.duration_ticks <= 0xFF
        ):
            frequencies[(state, item.event.id, delta, item.duration_ticks)] += 1
        timestamp = item.raw_timestamp
        track = item.track_id
        previous_event = item.event.id
    return frequencies, state_totals


@dataclass(frozen=True)
class CompactCodecProfile:
    schema_sha256: bytes
    state_events: tuple[int, int]
    entry_limit: int
    entries: tuple[CompactCodecEntry, ...]
    escape_codes: tuple[tuple[int, int], tuple[int, int], tuple[int, int]]
    sha256: bytes
    canonical_json: bytes
    perfect_hash: CompactCodecHash
    _decode_tables: tuple[Mapping[tuple[int, int], CompactCodecEntry | None], ...]

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        schema: CompactSchema | None = None,
    ) -> "CompactCodecProfile":
        if not isinstance(value, dict):
            raise CompactCodecProfileError("codec profile must be an object")
        allowed = {
            "format",
            "schema_sha256",
            "state_events",
            "entry_limit",
            "entries",
            "escape_codes",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise CompactCodecProfileError(
                f"codec profile contains unsupported field {unknown[0]!r}"
            )
        if value.get("format") != CODEC_PROFILE_FORMAT:
            raise CompactCodecProfileError(
                f"codec profile format must be {CODEC_PROFILE_FORMAT!r}"
            )
        raw_hash = value.get("schema_sha256")
        if not isinstance(raw_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", raw_hash):
            raise CompactCodecProfileError("schema_sha256 must be lowercase hexadecimal")
        schema_hash = bytes.fromhex(raw_hash)
        if schema is not None and schema_hash != schema.sha256:
            raise CompactCodecProfileError("codec profile schema SHA-256 mismatch")
        raw_states = value.get("state_events")
        if not isinstance(raw_states, list) or len(raw_states) != 2:
            raise CompactCodecProfileError("state_events must contain two event IDs")
        state_events = tuple(
            _require_int(item, f"state_events[{index}]", 0xFFFF_FFFF)
            for index, item in enumerate(raw_states)
        )
        if state_events[0] == state_events[1]:
            raise CompactCodecProfileError("state event IDs must be distinct")
        if schema is not None and any(item not in schema.events for item in state_events):
            raise CompactCodecProfileError("codec state event is absent from schema")
        entry_limit = _require_int(value.get("entry_limit"), "entry_limit", 247)
        if entry_limit not in CODEC_PROFILE_ENTRY_LIMITS:
            raise CompactCodecProfileError("entry_limit must be 128 or 247")
        raw_entries = value.get("entries")
        if not isinstance(raw_entries, list) or not raw_entries:
            raise CompactCodecProfileError("entries must be a non-empty array")
        entries: list[CompactCodecEntry] = []
        seen_keys: set[int] = set()
        for index, raw_entry in enumerate(raw_entries):
            if not isinstance(raw_entry, dict) or set(raw_entry) != {
                "state",
                "event_id",
                "delta",
                "duration",
                "code",
                "code_length",
                "training_count",
            }:
                raise CompactCodecProfileError(f"entries[{index}] has invalid fields")
            entry = CompactCodecEntry(
                _require_int(raw_entry["state"], f"entries[{index}].state", 2),
                _require_int(raw_entry["event_id"], f"entries[{index}].event_id", 0xFF),
                _require_int(raw_entry["delta"], f"entries[{index}].delta", 0xFF),
                _require_int(raw_entry["duration"], f"entries[{index}].duration", 0xFF),
                _require_int(raw_entry["code"], f"entries[{index}].code", 0xFFF),
                _require_int(
                    raw_entry["code_length"],
                    f"entries[{index}].code_length",
                    CODEC_PROFILE_MAX_CODE_BITS,
                ),
                _require_int(
                    raw_entry["training_count"],
                    f"entries[{index}].training_count",
                    0xFFFF_FFFF_FFFF_FFFF,
                ),
            )
            if entry.code_length == 0 or entry.code >= 1 << entry.code_length:
                raise CompactCodecProfileError(f"entries[{index}] has invalid code")
            if entry.key in seen_keys:
                raise CompactCodecProfileError(f"entries[{index}] duplicates a tuple")
            if schema is not None:
                event = schema.events.get(entry.event_id)
                if event is None or event.kind != "slice" or event.arguments:
                    raise CompactCodecProfileError(
                        f"entries[{index}] is not a zero-argument schema slice"
                    )
            seen_keys.add(entry.key)
            entries.append(entry)
        if len(entries) > entry_limit:
            raise CompactCodecProfileError("profile exceeds its entry_limit")
        if entries != sorted(entries, key=lambda entry: entry.key):
            raise CompactCodecProfileError("profile entries are not canonically sorted")
        raw_escapes = value.get("escape_codes")
        if not isinstance(raw_escapes, list) or len(raw_escapes) != 3:
            raise CompactCodecProfileError("escape_codes must contain three codes")
        escapes: list[tuple[int, int]] = []
        decode_tables: list[dict[tuple[int, int], CompactCodecEntry | None]] = [
            {}, {}, {}
        ]
        for state, raw_escape in enumerate(raw_escapes):
            if not isinstance(raw_escape, dict) or set(raw_escape) != {
                "code",
                "code_length",
            }:
                raise CompactCodecProfileError(f"escape_codes[{state}] has invalid fields")
            code = _require_int(raw_escape["code"], f"escape_codes[{state}].code", 0xFFF)
            width = _require_int(
                raw_escape["code_length"],
                f"escape_codes[{state}].code_length",
                CODEC_PROFILE_MAX_CODE_BITS,
            )
            if width == 0 or code >= 1 << width:
                raise CompactCodecProfileError(f"escape_codes[{state}] has invalid code")
            escapes.append((code, width))
            decode_tables[state][(code, width)] = None
        for entry in entries:
            table = decode_tables[entry.state]
            if (entry.code, entry.code_length) in table:
                raise CompactCodecProfileError("codec profile contains a duplicate code")
            table[(entry.code, entry.code_length)] = entry
        for state, table in enumerate(decode_tables):
            codes = list(table)
            for left_index, (left_code, left_width) in enumerate(codes):
                for right_code, right_width in codes[left_index + 1 :]:
                    width = min(left_width, right_width)
                    if (left_code & ((1 << width) - 1)) == (
                        right_code & ((1 << width) - 1)
                    ):
                        raise CompactCodecProfileError(
                            f"state {state} codec is not prefix-free"
                        )
        canonical = _canonical_json(value)
        profile_hash = hashlib.sha256(canonical).digest()
        perfect_hash = _build_perfect_hash(entries, entry_limit)
        return cls(
            schema_hash,
            (state_events[0], state_events[1]),
            entry_limit,
            tuple(entries),
            (escapes[0], escapes[1], escapes[2]),
            profile_hash,
            canonical,
            perfect_hash,
            tuple(MappingProxyType(table) for table in decode_tables),
        )

    @classmethod
    def load(
        cls, path: Path | str, schema: CompactSchema | None = None
    ) -> "CompactCodecProfile":
        source = Path(path)
        try:
            value = json.loads(
                source.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise CompactCodecProfileError(
                f"cannot read compact codec profile {source}: {error}"
            ) from error
        return cls.from_mapping(value, schema)

    @classmethod
    def train(
        cls,
        traces: Iterable["CompactTrace"],
        schema: CompactSchema,
        *,
        entry_limit: int = 247,
        state_events: tuple[int, int] | None = None,
    ) -> "CompactCodecProfile":
        if entry_limit not in CODEC_PROFILE_ENTRY_LIMITS:
            raise CompactCodecProfileError("entry_limit must be 128 or 247")
        corpus = list(traces)
        if not corpus:
            raise CompactCodecProfileError("codec training corpus is empty")
        if any(trace.schema.sha256 != schema.sha256 for trace in corpus):
            raise CompactCodecProfileError("codec training corpus mixes schemas")
        if state_events is None:
            prior = Counter(
                record.event.id
                for trace in corpus
                for record in trace.records
            )
            candidates = sorted(prior, key=lambda event_id: (-prior[event_id], event_id))[
                :CODEC_PROFILE_STATE_CANDIDATES
            ]
            if len(candidates) < 2:
                raise CompactCodecProfileError("training needs at least two event IDs")
            best: tuple[int, int] | None = None
            best_score: int | None = None
            for left_index, left in enumerate(candidates):
                for right in candidates[left_index + 1 :]:
                    combined: Counter[tuple[int, int, int, int]] = Counter()
                    totals: Counter[int] = Counter()
                    for trace in corpus:
                        candidate_frequencies, candidate_totals = _training_frequencies(
                            trace, (left, right)
                        )
                        combined.update(candidate_frequencies)
                        totals.update(candidate_totals)
                    score = _estimated_profile_bits(combined, totals, entry_limit)
                    if best_score is None or score < best_score:
                        best = (left, right)
                        best_score = score
            assert best is not None
            state_events = best
        if state_events[0] == state_events[1] or any(
            event_id not in schema.events for event_id in state_events
        ):
            raise CompactCodecProfileError("invalid codec state event IDs")
        frequencies: Counter[tuple[int, int, int, int]] = Counter()
        state_totals: Counter[int] = Counter()
        for trace in corpus:
            trace_frequencies, trace_totals = _training_frequencies(trace, state_events)
            frequencies.update(trace_frequencies)
            state_totals.update(trace_totals)
        selected = dict(frequencies.most_common(entry_limit))
        if not selected:
            raise CompactCodecProfileError("training corpus has no eligible slice tuples")
        entries: list[CompactCodecEntry] = []
        escapes: list[tuple[int, int]] = []
        for state in range(3):
            symbols = {
                key: count for key, count in selected.items() if key[0] == state
            }
            escape_symbol = ("escape", state)
            escaped = max(1, state_totals[state] - sum(symbols.values()))
            weighted: dict[object, int] = {
                cast(object, key): count for key, count in symbols.items()
            }
            weighted[escape_symbol] = escaped
            codes = _canonical_codes(
                _limited_huffman_lengths(weighted, CODEC_PROFILE_MAX_CODE_BITS)
            )
            escapes.append(codes[escape_symbol])
            for key, count in symbols.items():
                code, width = codes[key]
                entries.append(
                    CompactCodecEntry(*key, code, width, training_count=count)
                )
        entries.sort(key=lambda entry: entry.key)
        value: dict[str, Any] = {
            "format": CODEC_PROFILE_FORMAT,
            "schema_sha256": schema.sha256.hex(),
            "state_events": list(state_events),
            "entry_limit": entry_limit,
            "entries": [
                {
                    "state": entry.state,
                    "event_id": entry.event_id,
                    "delta": entry.delta,
                    "duration": entry.duration,
                    "code": entry.code,
                    "code_length": entry.code_length,
                    "training_count": entry.training_count,
                }
                for entry in entries
            ],
            "escape_codes": [
                {"code": code, "code_length": width}
                for code, width in escapes
            ],
        }
        return cls.from_mapping(value, schema)

    def to_mapping(self) -> Mapping[str, Any]:
        return json.loads(self.canonical_json)

    def decode_symbol(
        self, state: int, code: int, width: int
    ) -> object:
        key = (code, width)
        if key in self._decode_tables[state]:
            return self._decode_tables[state][key]
        return ...


def render_c_codec_profile(
    profile: CompactCodecProfile, prefix: str = "RBCT_CODEC"
) -> str:
    """Render a profile as const C tables consumed directly from target ROM."""
    symbol = re.sub(r"[^A-Za-z0-9]+", "_", prefix).strip("_").upper()
    if not symbol or symbol[0].isdigit():
        raise CompactCodecProfileError("C profile prefix is not an identifier")
    guard = f"{symbol}_PROFILE_H"
    hashed = profile.perfect_hash

    def rows(values: Sequence[int], formatter: Any, width: int = 8) -> list[str]:
        return [
            "    " + ", ".join(formatter(value) for value in values[index : index + width]) + ","
            for index in range(0, len(values), width)
        ]

    lines = [
        f"#ifndef {guard}",
        f"#define {guard}",
        "",
        "#include <retrobus/compact_trace.h>",
        "",
        f"static const uint8_t {symbol}_DISPLACEMENTS[{len(hashed.displacements)}] = {{",
        *rows(hashed.displacements, lambda value: f"UINT8_C({value})", 12),
        "};",
        f"static const uint32_t {symbol}_KEYS[{len(hashed.keys)}] = {{",
        *rows(hashed.keys, lambda value: f"UINT32_C(0x{value:08x})", 6),
        "};",
        f"static const uint16_t {symbol}_CODES[{len(hashed.code_info)}] = {{",
        *rows(hashed.code_info, lambda value: f"UINT16_C(0x{value:04x})", 8),
        "};",
        f"static const rbct_codec_profile_t {symbol}_PROFILE = {{",
        "    {" + ", ".join(f"0x{byte:02x}" for byte in profile.sha256) + "},",
        "    {" + ", ".join(f"0x{byte:02x}" for byte in profile.schema_sha256) + "},",
        f"    {{UINT32_C({profile.state_events[0]}), UINT32_C({profile.state_events[1]})}},",
        f"    UINT16_C({profile.entry_limit}),",
        f"    UINT32_C(0x{hashed.multiplier1:08x}),",
        f"    UINT32_C(0x{hashed.multiplier2:08x}),",
        f"    {symbol}_DISPLACEMENTS,",
        f"    {symbol}_KEYS,",
        f"    {symbol}_CODES,",
        "    {" + ", ".join(
            f"UINT16_C(0x{((width << 12) | code):04x})"
            for code, width in profile.escape_codes
        ) + "}",
        "};",
        "",
        f"#endif  /* {guard} */",
        "",
    ]
    return "\n".join(lines)
