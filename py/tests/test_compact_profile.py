"""Corpus replay and byte-attribution tests for compact density models."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from retrobus_perfetto import CompactSchema
from retrobus_perfetto.compact import (
    CompactClockSync,
    CompactRecord,
    CompactTrace,
    CompactTraceHeader,
)
from retrobus_perfetto.compact_profile import (
    aggregate_density_reports,
    model_compact_trace,
    profile_compact_trace,
)

from .test_compact import _rbct_image, _schema_mapping


def _header(schema: CompactSchema, *, records: int, events: int) -> CompactTraceHeader:
    return CompactTraceHeader(
        "retrobus-compact-v3",
        1,
        1_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"\0" * 16,
        records,
        0,
        0,
        events,
        0,
        160 + 4096,
        0,
        0,
    )


def test_v2_replay_matches_actual_chunk_used_length(
    tmp_path: Path,
) -> None:
    schema = CompactSchema.from_mapping(_schema_mapping())
    capture = tmp_path / "actual-v2.rbct"
    capture.write_bytes(_rbct_image(schema, version=2))

    report = profile_compact_trace(capture, schema)

    assert report["v2_prediction_matches_actual"] is True
    assert report["models"]["v2"]["chunk_used_lengths"] == report["actual"][
        "chunk_used_lengths"
    ]
    assert sum(report["models"]["v2"]["attribution"].values()) == 4256


def test_redux_like_slice_and_screen_mutation_density() -> None:
    events = [
        {
            "id": event_id,
            "name": f"slice {event_id}",
            "category": "dal",
            "kind": "slice",
        }
        for event_id in range(227)
    ]
    events.extend(
        {
            "id": event_id,
            "name": "screen mutation" if event_id == 229 else f"instant {event_id}",
            "category": "runtime",
            "kind": "instant",
            "arguments": []
            if event_id == 229
            else [{"name": "value", "type": "uint"}],
        }
        for event_id in range(227, 237)
    )
    schema = CompactSchema.from_mapping(
        {
            "format": "retrobus-compact-schema-v1",
            "producer": {"id": 7, "name": "redux-density"},
            "version": 1,
            "process": "Redux density",
            "tracks": [{"id": 0, "name": "main", "kind": "thread"}],
            "events": events,
        }
    )
    sync = CompactClockSync(0, 0, 0, 0, 0, 0)
    slice_record = CompactRecord(schema.events[0], 0, 0, 2, 1, (), 1)
    mutation = CompactRecord(schema.events[229], 0, 0, 3, None, (), 2)
    trace = CompactTrace(
        _header(schema, records=2, events=3),
        schema,
        (slice_record, mutation),
        (sync,),
    )

    profiles = {version: model_compact_trace(trace, version) for version in (1, 2, 3)}

    assert schema.v3_event_opcodes[236] == 237
    assert schema.v3_inline_opcodes[229] == (238, 239)
    assert profiles[1]["per_event"]["0"]["total_bytes"] == 3
    assert profiles[2]["per_event"]["0"]["total_bytes"] == 4
    assert profiles[3]["per_event"]["0"]["total_bytes"] == 3
    assert profiles[1]["per_event"]["229"]["total_bytes"] == 2
    assert profiles[2]["per_event"]["229"]["total_bytes"] == 2
    assert profiles[3]["per_event"]["229"]["total_bytes"] == 1
    assert profiles[3]["special_opcode_hits"]["special_delta_1"] == 1


def test_synthetic_width_track_argument_and_extended_event_matrix() -> None:
    events = [
        {
            "id": event_id,
            "name": f"event {event_id}",
            "category": "matrix",
            "kind": "instant",
            "arguments": [{"name": "value", "type": "uint"}],
        }
        for event_id in range(253)
    ]
    events[3] = {
        "id": 3,
        "name": "wide slice",
        "category": "matrix",
        "kind": "slice",
        "arguments": [
            {"name": "fixed", "type": "fixed64"},
            {"name": "unsigned", "type": "uint"},
            {"name": "signed", "type": "sint"},
            {"name": "flag", "type": "bool"},
        ],
    }
    schema = CompactSchema.from_mapping(
        {
            "format": "retrobus-compact-schema-v1",
            "producer": {"id": 8, "name": "matrix"},
            "version": 1,
            "process": "Matrix",
            "tracks": [
                {"id": 0, "name": "main", "kind": "thread"},
                {"id": 128, "name": "other", "kind": "thread"},
            ],
            "events": events,
        }
    )
    deltas = (0, 1, 127, 128, 16_384)
    timestamp = 0
    records = []
    for order, delta in enumerate(deltas):
        timestamp += delta
        event = schema.events[3] if order == 3 else schema.events[250 + order % 3]
        arguments = (
            (0xDEAD_BEEF_1234_5678, 128, -65, True)
            if event.id == 3
            else (128,)
        )
        records.append(
            CompactRecord(
                event,
                0,
                128 if order == 3 else 0,
                timestamp,
                128 if event.kind == "slice" else None,
                arguments,
                order,
            )
        )
    trace = CompactTrace(
        _header(schema, records=len(records), events=len(records) + 1),
        schema,
        tuple(records),
        (),
    )

    v3 = model_compact_trace(trace, 3)

    assert schema.v3_event_opcodes[250] == 251
    assert 251 not in schema.v3_event_opcodes
    assert v3["special_opcode_hits"]["extended"] == 3
    assert v3["varint_width_histograms"]["timestamp_delta"] == {1: 3, 2: 1, 3: 1}
    assert v3["varint_width_histograms"]["duration"] == {2: 1}
    assert v3["varint_width_histograms"]["arguments"][8] == 1
    assert v3["per_event"]["3"]["attribution"]["track_controls"] == 3


def test_synthetic_zero_to_four_argument_and_duration_width_matrix() -> None:
    schema = CompactSchema.from_mapping(
        {
            "format": "retrobus-compact-schema-v1",
            "producer": {"id": 9, "name": "shape-matrix"},
            "version": 1,
            "process": "Shape matrix",
            "tracks": [{"id": 0, "name": "main", "kind": "thread"}],
            "events": [
                {
                    "id": count,
                    "name": f"slice with {count} arguments",
                    "category": "matrix",
                    "kind": "slice",
                    "arguments": [
                        {"name": f"value_{index}", "type": "uint"}
                        for index in range(count)
                    ],
                }
                for count in range(5)
            ],
        }
    )
    widths = (0, 1, 127, 128, 16_384)
    timestamp = 0
    records = []
    for order, (event, width) in enumerate(zip(schema.events.values(), widths)):
        timestamp += width
        records.append(
            CompactRecord(
                event,
                0,
                0,
                timestamp,
                width,
                (1,) * len(event.arguments),
                order,
            )
        )
    trace = CompactTrace(
        _header(schema, records=5, events=10),
        schema,
        tuple(records),
        (),
    )

    v3 = model_compact_trace(trace, 3)

    expected_widths = {1: 3, 2: 1, 3: 1}
    assert v3["varint_width_histograms"]["timestamp_delta"] == expected_widths
    assert v3["varint_width_histograms"]["duration"] == expected_widths
    assert v3["varint_width_histograms"]["arguments"] == {1: 10}
    assert v3["per_event"]["0"]["attribution"].get("arguments", 0) == 0
    assert v3["per_event"]["4"]["attribution"]["arguments"] == 4


def test_v3_model_reports_exact_wrap_and_overwritten_records() -> None:
    schema = CompactSchema.from_mapping(
        {
            "format": "retrobus-compact-schema-v1",
            "producer": {"id": 10, "name": "wrap-matrix"},
            "version": 1,
            "process": "Wrap matrix",
            "tracks": [{"id": 0, "name": "main", "kind": "thread"}],
            "events": [
                {
                    "id": 7,
                    "name": "minimal",
                    "category": "matrix",
                    "kind": "instant",
                    "arguments": [],
                }
            ],
        }
    )
    records = tuple(
        CompactRecord(schema.events[7], 0, 0, 0, None, (), order)
        for order in range(4050)
    )
    trace = CompactTrace(_header(schema, records=4050, events=4050), schema, records, ())

    v3 = model_compact_trace(trace, 3, chunk_count=1)

    assert v3["chunk_used_lengths"] == [4048, 2]
    assert v3["chunks_started"] == 2
    assert v3["chunk_wraps"] == 1
    assert v3["model_overwritten_records"] == 4048
    assert v3["model_overwritten_events"] == 4048


def test_corpus_aggregate_preserves_attribution_and_density(
    tmp_path: Path,
) -> None:
    schema = CompactSchema.from_mapping(_schema_mapping())
    reports = []
    for index, version in enumerate((2, 3)):
        path = tmp_path / f"capture-{index}.rbct"
        path.write_bytes(_rbct_image(schema, version=version))
        reports.append(profile_compact_trace(path, schema))

    aggregate = aggregate_density_reports(reports)

    assert aggregate["captures"] == 2
    assert aggregate["v2_predictions_verified"] == 1
    assert aggregate["v2_predictions_all_match"] is True
    assert aggregate["models"]["v3"]["records"] == 16
    assert sum(aggregate["models"]["v3"]["attribution"].values()) == 8512


def test_profile_cli_manifest_preserves_provenance_and_checks_v2(
    tmp_path: Path,
) -> None:
    schema = CompactSchema.from_mapping(_schema_mapping())
    schema_path = tmp_path / "schema.json"
    schema_path.write_bytes(schema.canonical_json)
    capture = tmp_path / "capture.rbct"
    capture.write_bytes(_rbct_image(schema, version=2))
    manifest = tmp_path / "corpus.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": schema_path.name,
                "captures": [
                    {
                        "path": capture.name,
                        "device": "synthetic",
                        "scenario": "v2 replay",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    repository = Path(__file__).resolve().parents[2]

    completed = subprocess.run(
        [
            sys.executable,
            str(repository / "tools" / "compact_trace_profile.py"),
            "--manifest",
            str(manifest),
            "--fail-on-v2-mismatch",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["format"] == "retrobus-compact-density-profile-v1"
    assert result["captures"][0]["provenance"] == {
        "device": "synthetic",
        "scenario": "v2 replay",
    }
    assert result["aggregate"]["v2_predictions_all_match"] is True
