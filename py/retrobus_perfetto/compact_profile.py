"""Replay compact logical records through v1/v2/v3 density models."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .compact import (
    CHUNK_BYTES,
    CHUNK_HEADER_BYTES,
    FILE_HEADER_BYTES,
    CompactClockSync,
    CompactRecord,
    CompactTrace,
    CompactTraceReader,
)
from .compact_schema import CompactArgumentSchema, CompactSchema


PAYLOAD_BYTES = CHUNK_BYTES - CHUNK_HEADER_BYTES


def _varint_width(value: int) -> int:
    return max(1, (value.bit_length() + 6) // 7)


def _zigzag(value: int) -> int:
    return (value << 1) ^ (value >> 63)


def _argument_width(specification: CompactArgumentSchema, value: Any) -> int:
    if specification.type in {"fixed64", "float64"}:
        return 8
    if specification.type == "sint":
        return _varint_width(_zigzag(int(value)))
    return _varint_width(int(value))


def _midpoint(before: int, after: int, mask: int) -> int:
    return (before + ((after - before) & mask) // 2) & mask


@dataclass
class _Cost:
    publication_framing: int = 0
    event_identity: int = 0
    timestamp_delta: int = 0
    duration: int = 0
    arguments: int = 0
    track_controls: int = 0
    clock_sync_controls: int = 0
    other_controls: int = 0
    delta_width: int | None = None
    duration_width: int | None = None
    argument_widths: tuple[int, ...] = ()
    hit: str = ""

    @property
    def payload_bytes(self) -> int:
        return (
            self.publication_framing
            + self.event_identity
            + self.timestamp_delta
            + self.duration
            + self.arguments
            + self.track_controls
            + self.clock_sync_controls
            + self.other_controls
        )


@dataclass
class _ChunkModel:
    generation: int
    base_timestamp: int
    used: int = 0
    records: int = 0
    events: int = 0
    syncs: int = 0


@dataclass
class _EventAccumulator:
    count: int = 0
    expanded_events: int = 0
    total_bytes: int = 0
    minimum_bytes: int = 1 << 30
    maximum_bytes: int = 0
    attribution: Counter[str] = field(default_factory=Counter)

    def add(self, cost: _Cost, expanded_events: int) -> None:
        size = cost.payload_bytes
        self.count += 1
        self.expanded_events += expanded_events
        self.total_bytes += size
        self.minimum_bytes = min(self.minimum_bytes, size)
        self.maximum_bytes = max(self.maximum_bytes, size)
        for name in (
            "publication_framing",
            "event_identity",
            "timestamp_delta",
            "duration",
            "arguments",
            "track_controls",
            "clock_sync_controls",
            "other_controls",
        ):
            self.attribution[name] += int(getattr(cost, name))


class _EncodingModel:
    def __init__(self, trace: CompactTrace, version: int, chunk_count: int) -> None:
        self.trace = trace
        self.version = version
        self.chunk_count = chunk_count
        self.mask = (1 << trace.header.clock_width_bits) - 1
        self.current_generation = trace.header.initial_generation
        self.current_timestamp = 0
        self.current_track = trace.header.default_track
        self.v3_event_opcodes = trace.schema.v3_event_opcodes
        self.v3_inline_opcodes = trace.schema.v3_inline_opcodes
        self.chunks: list[_ChunkModel] = []
        self.attribution: Counter[str] = Counter()
        self.hits: Counter[str] = Counter()
        self.delta_widths: Counter[int] = Counter()
        self.duration_widths: Counter[int] = Counter()
        self.argument_widths: Counter[int] = Counter()
        self.per_event: dict[int, _EventAccumulator] = {}

    @property
    def chunk(self) -> _ChunkModel:
        return self.chunks[-1]

    def _start_chunk(self, item: CompactRecord | CompactClockSync) -> None:
        base = (
            item.counter_before
            if isinstance(item, CompactClockSync)
            else item.raw_timestamp
        )
        self.current_generation = item.generation
        self.current_timestamp = base
        self.current_track = self.trace.header.default_track
        self.chunks.append(_ChunkModel(item.generation, base))

    def _event_cost(self, record: CompactRecord) -> _Cost:
        delta = (record.raw_timestamp - self.current_timestamp) & self.mask
        delta_width = _varint_width(delta)
        duration_width = (
            _varint_width(record.duration_ticks)
            if record.duration_ticks is not None
            else 0
        )
        argument_widths = tuple(
            _argument_width(specification, value)
            for specification, value in zip(
                record.event.arguments, record.arguments
            )
        )
        track_width = (
            1 + _varint_width(record.track_id)
            if record.track_id != self.current_track
            else 0
        )
        if self.version in (1, 2):
            identity_width = (
                1
                if record.event.id <= 251
                else 1 + _varint_width(record.event.id)
            )
        else:
            identity_width = (
                1
                if record.event.id in self.v3_event_opcodes
                else 1 + _varint_width(record.event.id)
            )

        if self.version == 1:
            return _Cost(
                event_identity=identity_width,
                timestamp_delta=delta_width,
                duration=duration_width,
                arguments=sum(argument_widths),
                track_controls=track_width,
                delta_width=delta_width,
                duration_width=duration_width or None,
                argument_widths=argument_widths,
                hit="ordinary",
            )

        if self.version == 2:
            v2_inline = (
                record.track_id == self.current_track
                and record.event.id <= 21
                and record.event.kind == "instant"
                and not record.event.arguments
                and delta <= 1
            )
            if v2_inline:
                return _Cost(
                    event_identity=1,
                    delta_width=delta_width,
                    hit=f"inline_delta_{delta}",
                )
            implicit = delta <= 1
            return _Cost(
                publication_framing=1,
                event_identity=identity_width,
                timestamp_delta=0 if implicit else delta_width,
                duration=duration_width,
                arguments=sum(argument_widths),
                track_controls=track_width,
                delta_width=delta_width,
                duration_width=duration_width or None,
                argument_widths=argument_widths,
                hit=f"implicit_delta_{delta}" if implicit else "explicit_delta",
            )

        inline_opcodes = self.v3_inline_opcodes.get(record.event.id)
        special = bool(
            inline_opcodes is not None
            and record.event.kind == "instant"
            and not record.event.arguments
            and delta <= 1
        )
        return _Cost(
            event_identity=1 if special else identity_width,
            timestamp_delta=0 if special else delta_width,
            duration=duration_width,
            arguments=sum(argument_widths),
            track_controls=track_width,
            delta_width=delta_width,
            duration_width=duration_width or None,
            argument_widths=argument_widths,
            hit=(
                f"special_delta_{delta}"
                if special
                else (
                    "ordinary"
                    if record.event.id in self.v3_event_opcodes
                    else "extended"
                )
            ),
        )

    def _sync_cost(self, sync: CompactClockSync) -> _Cost:
        body = sum(
            _varint_width(value)
            for value in (
                sync.generation,
                sync.counter_before,
                sync.counter_after,
                sync.reference_timestamp_ns,
                sync.uncertainty_ns,
            )
        )
        return _Cost(
            publication_framing=1 if self.version == 2 else 0,
            clock_sync_controls=1 + body,
            hit="clock_sync",
        )

    def _cost(self, item: CompactRecord | CompactClockSync) -> _Cost:
        return (
            self._sync_cost(item)
            if isinstance(item, CompactClockSync)
            else self._event_cost(item)
        )

    def _account(self, item: CompactRecord | CompactClockSync, cost: _Cost) -> None:
        for name in (
            "publication_framing",
            "event_identity",
            "timestamp_delta",
            "duration",
            "arguments",
            "track_controls",
            "clock_sync_controls",
            "other_controls",
        ):
            self.attribution[name] += int(getattr(cost, name))
        self.hits[cost.hit] += 1
        if cost.delta_width is not None:
            self.delta_widths[cost.delta_width] += 1
        if cost.duration_width is not None:
            self.duration_widths[cost.duration_width] += 1
        self.argument_widths.update(cost.argument_widths)
        self.chunk.used += cost.payload_bytes
        if isinstance(item, CompactClockSync):
            self.chunk.syncs += 1
            self.current_timestamp = (
                item.counter_before
                if self.version == 1
                else _midpoint(item.counter_before, item.counter_after, self.mask)
            )
        else:
            expanded = 2 if item.event.kind == "slice" else 1
            self.chunk.records += 1
            self.chunk.events += expanded
            self.current_timestamp = item.raw_timestamp
            self.current_track = item.track_id
            accumulator = self.per_event.setdefault(item.event.id, _EventAccumulator())
            accumulator.add(cost, expanded)

    def run(self, items: Iterable[CompactRecord | CompactClockSync]) -> Mapping[str, Any]:
        for item in items:
            if not self.chunks or item.generation != self.current_generation:
                self._start_chunk(item)
            cost = self._cost(item)
            if cost.payload_bytes > PAYLOAD_BYTES - self.chunk.used:
                self._start_chunk(item)
                cost = self._cost(item)
            if cost.payload_bytes > PAYLOAD_BYTES:
                raise ValueError("compact logical record exceeds one chunk payload")
            self._account(item, cost)

        payload_bytes = sum(chunk.used for chunk in self.chunks)
        records = sum(chunk.records for chunk in self.chunks)
        events = sum(chunk.events for chunk in self.chunks)
        syncs = sum(chunk.syncs for chunk in self.chunks)
        chunk_slack = len(self.chunks) * PAYLOAD_BYTES - payload_bytes
        overwritten_chunks = max(0, len(self.chunks) - self.chunk_count)
        overwritten_records = sum(
            chunk.records for chunk in self.chunks[:overwritten_chunks]
        )
        overwritten_events = sum(
            chunk.events for chunk in self.chunks[:overwritten_chunks]
        )
        attributions = dict(self.attribution)
        attributions.update(
            {
                "file_header": FILE_HEADER_BYTES,
                "chunk_headers": len(self.chunks) * CHUNK_HEADER_BYTES,
                "chunk_slack": chunk_slack,
                "unused_chunk_capacity": 0,
            }
        )
        per_event = {
            str(event_id): {
                "name": self.trace.schema.events[event_id].name,
                "count": value.count,
                "expanded_events": value.expanded_events,
                "total_bytes": value.total_bytes,
                "mean_bytes": value.total_bytes / value.count,
                "minimum_bytes": value.minimum_bytes,
                "maximum_bytes": value.maximum_bytes,
                "payload_share": value.total_bytes / payload_bytes
                if payload_bytes
                else 0.0,
                "attribution": dict(value.attribution),
            }
            for event_id, value in sorted(self.per_event.items())
        }
        return {
            "format_version": self.version,
            "records": records,
            "expanded_events": events,
            "clock_syncs": syncs,
            "payload_bytes": payload_bytes,
            "bytes_per_record": payload_bytes / records if records else 0.0,
            "records_per_payload_kib": records * 1024 / payload_bytes
            if payload_bytes
            else 0.0,
            "events_per_payload_kib": events * 1024 / payload_bytes
            if payload_bytes
            else 0.0,
            "chunks_started": len(self.chunks),
            "chunk_wraps": overwritten_chunks,
            "model_overwritten_records": overwritten_records,
            "model_overwritten_events": overwritten_events,
            "chunk_used_lengths": [chunk.used for chunk in self.chunks],
            "chunk_slack_bytes": chunk_slack,
            "attribution": attributions,
            "varint_width_histograms": {
                "timestamp_delta": dict(sorted(self.delta_widths.items())),
                "duration": dict(sorted(self.duration_widths.items())),
                "arguments": dict(sorted(self.argument_widths.items())),
            },
            "special_opcode_hits": dict(sorted(self.hits.items())),
            "per_event": per_event,
        }


def model_compact_trace(
    trace: CompactTrace, version: int, *, chunk_count: int | None = None
) -> Mapping[str, Any]:
    """Model one logical capture using a selected compact wire version."""
    if version not in (1, 2, 3):
        raise ValueError("compact model version must be 1, 2, or 3")
    count = (
        (trace.header.buffer_bytes - FILE_HEADER_BYTES) // CHUNK_BYTES
        if chunk_count is None
        else chunk_count
    )
    if count <= 0:
        raise ValueError("compact model needs at least one chunk")
    items: list[CompactRecord | CompactClockSync] = [
        *trace.records,
        *trace.clock_syncs,
    ]
    items.sort(key=lambda item: item.order)
    return _EncodingModel(trace, version, count).run(items)


def profile_compact_trace(
    path: Path | str,
    schema: CompactSchema | Path | str,
    *,
    allow_unfinalized: bool = False,
) -> Mapping[str, Any]:
    """Read one capture, replay all versions, and verify actual v2 chunk use."""
    producer_schema = (
        schema if isinstance(schema, CompactSchema) else CompactSchema.load(schema)
    )
    reader = CompactTraceReader(
        path, producer_schema, allow_unfinalized=allow_unfinalized
    )
    trace = reader.read()
    models = {
        f"v{version}": model_compact_trace(trace, version)
        for version in (1, 2, 3)
    }
    actual_used = [chunk.used for chunk in reader._chunks]
    physical_chunk_count = (
        trace.header.buffer_bytes - FILE_HEADER_BYTES
    ) // CHUNK_BYTES
    actual_chunks = [
        {
            "sequence": chunk.sequence,
            "physical_index": chunk.physical_index,
            "used": chunk.used,
            "slack": PAYLOAD_BYTES - chunk.used,
            "records": chunk.records,
            "expanded_events": chunk.events,
            "clock_syncs": chunk.syncs,
        }
        for chunk in reader._chunks
    ]
    chunks_started = reader._chunks[-1].sequence + 1 if reader._chunks else 0
    v2_prediction: bool | None = None
    if trace.header.format_version == 2 and not trace.header.ring_wrapped:
        v2_prediction = models["v2"]["chunk_used_lengths"] == actual_used
    actual_payload = sum(actual_used)
    return {
        "capture": str(Path(path)),
        "schema": {
            "producer_id": producer_schema.producer_id,
            "version": producer_schema.version,
            "sha256": producer_schema.sha256.hex(),
            "events": len(producer_schema.events),
        },
        "actual": {
            "format_version": trace.header.format_version,
            "finalized": trace.header.finalized,
            "ring_wrapped": trace.header.ring_wrapped,
            "buffer_bytes": trace.header.buffer_bytes,
            "chunks": actual_chunks,
            "chunk_used_lengths": actual_used,
            "chunk_header_bytes": len(reader._chunks) * CHUNK_HEADER_BYTES,
            "chunk_slack_bytes": sum(PAYLOAD_BYTES - value for value in actual_used),
            "unused_chunks": physical_chunk_count - len(reader._chunks),
            "unused_chunk_bytes": (
                physical_chunk_count - len(reader._chunks)
            )
            * CHUNK_BYTES,
            "chunks_started": chunks_started,
            "chunk_wraps": max(0, chunks_started - physical_chunk_count),
            "payload_bytes": actual_payload,
            "records": trace.header.retained_records,
            "expanded_events": trace.header.retained_events,
            "overwritten_records": trace.header.overwritten_records,
            "overwritten_events": trace.header.overwritten_events,
            "dropped_records": trace.header.dropped_records,
            "corpus_completeness": (
                "retained_only" if trace.header.ring_wrapped else "complete"
            ),
        },
        "v2_prediction_matches_actual": v2_prediction,
        "models": models,
    }


def _sum_integer_mapping(
    destination: Counter[str], source: Mapping[Any, Any]
) -> None:
    for key, value in source.items():
        destination[str(key)] += int(value)


def aggregate_density_reports(
    reports: Iterable[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Aggregate capture reports without hiding retained-only corpus inputs."""
    captures = list(reports)
    models: dict[str, Any] = {}
    for version_name in ("v1", "v2", "v3"):
        totals: Counter[str] = Counter()
        attribution: Counter[str] = Counter()
        hits: Counter[str] = Counter()
        histograms = {
            "timestamp_delta": Counter[str](),
            "duration": Counter[str](),
            "arguments": Counter[str](),
        }
        per_event: dict[str, dict[str, Any]] = {}
        chunk_used_lengths: list[int] = []
        for report in captures:
            model = report["models"][version_name]
            for key in (
                "records",
                "expanded_events",
                "clock_syncs",
                "payload_bytes",
                "chunks_started",
                "chunk_wraps",
                "model_overwritten_records",
                "model_overwritten_events",
                "chunk_slack_bytes",
            ):
                totals[key] += int(model[key])
            chunk_used_lengths.extend(int(value) for value in model["chunk_used_lengths"])
            _sum_integer_mapping(attribution, model["attribution"])
            _sum_integer_mapping(hits, model["special_opcode_hits"])
            for field_name, values in model["varint_width_histograms"].items():
                _sum_integer_mapping(histograms[field_name], values)
            for event_id, event in model["per_event"].items():
                target = per_event.setdefault(
                    event_id,
                    {
                        "name": event["name"],
                        "count": 0,
                        "expanded_events": 0,
                        "total_bytes": 0,
                        "minimum_bytes": 1 << 30,
                        "maximum_bytes": 0,
                        "attribution": Counter[str](),
                    },
                )
                target["count"] += int(event["count"])
                target["expanded_events"] += int(event["expanded_events"])
                target["total_bytes"] += int(event["total_bytes"])
                target["minimum_bytes"] = min(
                    target["minimum_bytes"], int(event["minimum_bytes"])
                )
                target["maximum_bytes"] = max(
                    target["maximum_bytes"], int(event["maximum_bytes"])
                )
                _sum_integer_mapping(target["attribution"], event["attribution"])
        payload = totals["payload_bytes"]
        records = totals["records"]
        expanded_events = totals["expanded_events"]
        normalized_events = {}
        for event_id, event in per_event.items():
            count = event["count"]
            normalized_events[event_id] = {
                **event,
                "mean_bytes": event["total_bytes"] / count,
                "payload_share": event["total_bytes"] / payload if payload else 0.0,
                "attribution": dict(event["attribution"]),
            }
        models[version_name] = {
            **dict(totals),
            "bytes_per_record": payload / records if records else 0.0,
            "records_per_payload_kib": records * 1024 / payload
            if payload
            else 0.0,
            "events_per_payload_kib": expanded_events * 1024 / payload
            if payload
            else 0.0,
            "chunk_used_lengths": chunk_used_lengths,
            "attribution": dict(attribution),
            "varint_width_histograms": {
                key: dict(sorted(values.items(), key=lambda item: int(item[0])))
                for key, values in histograms.items()
            },
            "special_opcode_hits": dict(hits),
            "per_event": normalized_events,
        }
    verified = [
        report["v2_prediction_matches_actual"]
        for report in captures
        if report["v2_prediction_matches_actual"] is not None
    ]
    return {
        "captures": len(captures),
        "retained_only_captures": sum(
            report["actual"]["corpus_completeness"] == "retained_only"
            for report in captures
        ),
        "v2_predictions_verified": len(verified),
        "v2_predictions_all_match": all(verified) if verified else None,
        "models": models,
    }


def profile_compact_corpus(
    paths: Iterable[Path | str],
    schema: CompactSchema | Path | str,
    *,
    allow_unfinalized: bool = False,
) -> Mapping[str, Any]:
    """Profile several captures and return individual plus aggregate results."""
    producer_schema = (
        schema if isinstance(schema, CompactSchema) else CompactSchema.load(schema)
    )
    reports = [
        profile_compact_trace(
            path, producer_schema, allow_unfinalized=allow_unfinalized
        )
        for path in paths
    ]
    return {"captures": reports, "aggregate": aggregate_density_reports(reports)}
