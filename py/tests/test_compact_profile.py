"""Corpus replay and byte-attribution tests for compact density models."""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
import subprocess
import sys

from retrobus_perfetto import (
    CompactCodecProfile,
    CompactSchema,
    render_c_codec_profile,
)
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
import retrobus_perfetto.compact_codec as compact_codec_module

from .test_compact import _rbct_image, _schema_mapping, _v3_payload_image


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
    v4 = model_compact_trace(trace, 4)

    assert schema.v3_event_opcodes[250] == 251
    assert 251 not in schema.v3_event_opcodes
    assert v3["special_opcode_hits"]["extended"] == 3
    assert v3["varint_width_histograms"]["timestamp_delta"] == {1: 3, 2: 1, 3: 1}
    assert v3["varint_width_histograms"]["duration"] == {2: 1}
    assert v3["varint_width_histograms"]["arguments"][8] == 1
    assert v3["per_event"]["3"]["attribution"]["track_controls"] == 3
    assert v4["varint_width_histograms"]["timestamp_delta"] == {
        1: 3,
        2: 1,
        3: 1,
    }
    assert v4["varint_width_histograms"]["duration"] == {2: 1}
    assert v4["varint_width_histograms"]["arguments"][8] == 1


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
    v4 = model_compact_trace(trace, 4)

    expected_widths = {1: 3, 2: 1, 3: 1}
    assert v3["varint_width_histograms"]["timestamp_delta"] == expected_widths
    assert v3["varint_width_histograms"]["duration"] == expected_widths
    assert v3["varint_width_histograms"]["arguments"] == {1: 10}
    assert v3["per_event"]["0"]["attribution"].get("arguments", 0) == 0
    assert v3["per_event"]["4"]["attribution"]["arguments"] == 4
    assert v4["varint_width_histograms"]["timestamp_delta"] == expected_widths
    assert v4["varint_width_histograms"]["duration"] == expected_widths
    assert v4["varint_width_histograms"]["arguments"] == {1: 10}


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


def test_v4_profile_training_is_deterministic_and_improves_density() -> None:
    schema = CompactSchema.from_mapping(
        {
            "format": "retrobus-compact-schema-v1",
            "producer": {"id": 11, "name": "profile-training"},
            "version": 1,
            "process": "Profile training",
            "tracks": [{"id": 0, "name": "main", "kind": "thread"}],
            "events": [
                {
                    "id": event_id,
                    "name": f"slice {event_id}",
                    "category": "matrix",
                    "kind": "slice",
                    "arguments": [],
                }
                for event_id in range(3)
            ],
        }
    )
    records = tuple(
        CompactRecord(
            schema.events[0 if index % 20 else 1],
            0,
            0,
            index + 1,
            1,
            (),
            index,
        )
        for index in range(1000)
    )
    trace = CompactTrace(
        _header(schema, records=1000, events=2000), schema, records, ()
    )

    profile = CompactCodecProfile.train(
        [trace], schema, entry_limit=128, state_events=(1, 2)
    )
    repeated = CompactCodecProfile.train(
        [trace], schema, entry_limit=128, state_events=(1, 2)
    )
    v3 = model_compact_trace(trace, 3)
    v4 = model_compact_trace(trace, 4, codec_profile=profile)

    assert profile.canonical_json == repeated.canonical_json
    assert profile.sha256 == repeated.sha256
    assert profile.entry_limit == 128
    assert len(profile.entries) >= 2
    assert v4["special_opcode_hits"]["profile_hit"] > 990
    assert v4["payload_bits"] < v3["payload_bytes"] * 8 // 10
    rendered = render_c_codec_profile(profile, "training")
    assert "TRAINING_PROFILE" in rendered
    assert f"UINT16_C({profile.entry_limit})" in rendered


def test_v4_automatic_state_search_exhausts_its_bounded_candidate_pairs(
    monkeypatch,
) -> None:
    schema = CompactSchema.from_mapping(
        {
            "format": "retrobus-compact-schema-v1",
            "producer": {"id": 14, "name": "state-search"},
            "version": 1,
            "process": "State search",
            "tracks": [{"id": 0, "name": "main", "kind": "thread"}],
            "events": [
                {
                    "id": event_id,
                    "name": f"slice {event_id}",
                    "category": "matrix",
                    "kind": "slice",
                    "arguments": [],
                }
                for event_id in range(13)
            ],
        }
    )
    event_ids = [
        event_id for event_id in range(13) for _ in range(13 - event_id)
    ]
    timestamp = 0
    records = []
    for order, event_id in enumerate(event_ids):
        timestamp += 1
        records.append(
            CompactRecord(schema.events[event_id], 0, 0, timestamp, 1, (), order)
        )
    trace = CompactTrace(
        _header(schema, records=len(records), events=2 * len(records)),
        schema,
        tuple(records),
        (),
    )
    original = compact_codec_module._training_frequencies
    searched: list[tuple[int, int]] = []

    def recording_frequencies(
        candidate_trace: CompactTrace, state_events: tuple[int, int]
    ):
        searched.append(state_events)
        return original(candidate_trace, state_events)

    monkeypatch.setattr(
        compact_codec_module, "_training_frequencies", recording_frequencies
    )
    profile = CompactCodecProfile.train([trace], schema, entry_limit=128)

    expected_pairs = list(combinations(range(12), 2))
    assert searched[: len(expected_pairs)] == expected_pairs
    assert len(searched) == len(expected_pairs) + 1
    assert set(profile.state_events) <= set(range(12))

    searched.clear()
    repeated = CompactCodecProfile.train([trace], schema, entry_limit=128)
    assert repeated.canonical_json == profile.canonical_json
    assert searched[: len(expected_pairs)] == expected_pairs


def test_v4_model_accounts_exact_hit_miss_bits_and_byte_rounding() -> None:
    schema = CompactSchema.from_mapping(
        {
            "format": "retrobus-compact-schema-v1",
            "producer": {"id": 15, "name": "exact-v4-model"},
            "version": 1,
            "process": "Exact v4 model",
            "tracks": [{"id": 0, "name": "main", "kind": "thread"}],
            "events": [
                {
                    "id": event_id,
                    "name": f"slice {event_id}",
                    "category": "matrix",
                    "kind": "slice",
                    "arguments": [],
                }
                for event_id in range(3)
            ],
        }
    )
    profile = CompactCodecProfile.from_mapping(
        {
            "format": "retrobus-compact-codec-profile-v1",
            "schema_sha256": schema.sha256.hex(),
            "state_events": [1, 2],
            "entry_limit": 128,
            "entries": [
                {
                    "state": 2,
                    "event_id": 0,
                    "delta": 0,
                    "duration": 1,
                    "code": 0,
                    "code_length": 1,
                    "training_count": 1,
                }
            ],
            "escape_codes": [
                {"code": 0, "code_length": 1},
                {"code": 0, "code_length": 1},
                {"code": 1, "code_length": 1},
            ],
        },
        schema,
    )
    trace = CompactTrace(
        _header(schema, records=2, events=4),
        schema,
        (
            CompactRecord(schema.events[0], 0, 0, 10, 1, (), 0),
            CompactRecord(schema.events[1], 0, 0, 11, 1, (), 1),
        ),
        (),
    )

    model = model_compact_trace(trace, 4, codec_profile=profile)

    assert model["payload_bits"] == 28
    assert model["payload_bytes"] == 4
    assert model["container_bytes"] == 4_288
    assert model["chunk_used_bits"] == [28]
    assert model["chunk_used_lengths"] == [4]
    assert model["special_opcode_hits"] == {"profile_hit": 1, "profile_miss": 1}
    assert model["bit_attribution"] == {
        "profile_code": 1,
        "profile_prefix": 1,
        "literal_kind": 2,
        "event_identity": 8,
        "timestamp_delta": 8,
        "duration": 8,
        "arguments": 0,
        "track_controls": 0,
    }
    assert model["attribution"] == {
        "file_header": 192,
        "chunk_headers": 48,
        "payload": 4,
        "chunk_slack": 4_044,
        "unused_chunk_capacity": 0,
    }
    assert sum(model["attribution"].values()) == model["container_bytes"]


def test_v4_model_reencodes_at_wrap_and_reports_each_bit_cursor() -> None:
    schema = CompactSchema.from_mapping(
        {
            "format": "retrobus-compact-schema-v1",
            "producer": {"id": 16, "name": "exact-v4-wrap"},
            "version": 1,
            "process": "Exact v4 wrap",
            "tracks": [{"id": 0, "name": "main", "kind": "thread"}],
            "events": [
                {
                    "id": event_id,
                    "name": f"slice {event_id}",
                    "category": "matrix",
                    "kind": "slice",
                    "arguments": [],
                }
                for event_id in range(3)
            ],
        }
    )
    profile = CompactCodecProfile.from_mapping(
        {
            "format": "retrobus-compact-codec-profile-v1",
            "schema_sha256": schema.sha256.hex(),
            "state_events": [1, 2],
            "entry_limit": 128,
            "entries": [
                {
                    "state": 2,
                    "event_id": 0,
                    "delta": 0,
                    "duration": 1,
                    "code": 1,
                    "code_length": 2,
                    "training_count": 1,
                },
                {
                    "state": 2,
                    "event_id": 0,
                    "delta": 1,
                    "duration": 1,
                    "code": 0,
                    "code_length": 1,
                    "training_count": 32_383,
                },
            ],
            "escape_codes": [
                {"code": 0, "code_length": 1},
                {"code": 0, "code_length": 1},
                {"code": 3, "code_length": 2},
            ],
        },
        schema,
    )
    records = tuple(
        CompactRecord(schema.events[0], 0, 0, index, 1, (), index)
        for index in range(32_384)
    )
    trace = CompactTrace(
        _header(schema, records=len(records), events=2 * len(records)),
        schema,
        records,
        (),
    )

    model = model_compact_trace(trace, 4, chunk_count=2, codec_profile=profile)

    assert model["chunk_used_bits"] == [32_384, 2]
    assert model["chunk_used_lengths"] == [4_048, 1]
    assert model["payload_bits"] == 32_386
    assert model["payload_bytes"] == 4_049
    assert model["container_bytes"] == 8_384
    assert model["special_opcode_hits"] == {"profile_hit": 32_384}


def test_v4_large_profile_builds_247_entry_hash_layout() -> None:
    schema = CompactSchema.from_mapping(
        {
            "format": "retrobus-compact-schema-v1",
            "producer": {"id": 12, "name": "large-profile"},
            "version": 1,
            "process": "Large profile",
            "tracks": [{"id": 0, "name": "main", "kind": "thread"}],
            "events": [
                {
                    "id": event_id,
                    "name": f"slice {event_id}",
                    "category": "matrix",
                    "kind": "slice",
                    "arguments": [],
                }
                for event_id in range(12)
            ],
        }
    )
    timestamp = 0
    records = []
    for order in range(300):
        delta = order % 25 + 1
        timestamp += delta
        records.append(
            CompactRecord(
                schema.events[(order // 25) % 12],
                0,
                0,
                timestamp,
                order // 25 + 1,
                (),
                order,
            )
        )
    trace = CompactTrace(
        _header(schema, records=300, events=600), schema, tuple(records), ()
    )

    profile = CompactCodecProfile.train(
        [trace], schema, entry_limit=247, state_events=(10, 11)
    )

    assert profile.entry_limit == 247
    assert len(profile.entries) > 128
    assert len(profile.perfect_hash.displacements) == 128
    assert len(profile.perfect_hash.keys) == 256
    assert len(profile.perfect_hash.code_info) == 256


def test_codec_profile_cli_trains_json_and_c_header(tmp_path: Path) -> None:
    schema = CompactSchema.from_mapping(
        {
            "format": "retrobus-compact-schema-v1",
            "producer": {"id": 13, "name": "profile-cli"},
            "version": 1,
            "process": "Profile CLI",
            "tracks": [{"id": 0, "name": "main", "kind": "thread"}],
            "events": [
                {
                    "id": event_id,
                    "name": f"slice {event_id}",
                    "category": "matrix",
                    "kind": "slice",
                    "arguments": [],
                }
                for event_id in range(3)
            ],
        }
    )
    schema_path = tmp_path / "schema.json"
    schema_path.write_bytes(schema.canonical_json)
    capture = tmp_path / "training.rbct"
    capture.write_bytes(
        _v3_payload_image(
            schema,
            bytes([1, 1, 1]) * 100,
            records=100,
            events=200,
        )
    )
    profile_path = tmp_path / "codec.json"
    header_path = tmp_path / "codec.h"
    repository = Path(__file__).resolve().parents[2]

    completed = subprocess.run(
        [
            sys.executable,
            str(repository / "tools/compact_codec_profile.py"),
            str(capture),
            "--schema",
            str(schema_path),
            "--state-events",
            "1",
            "2",
            "--entry-limit",
            "128",
            "--output",
            str(profile_path),
            "--c-header",
            str(header_path),
            "--c-prefix",
            "profile_cli",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    profile = CompactCodecProfile.load(profile_path, schema)
    assert len(profile.entries) == 2
    assert "entries=2" in completed.stdout
    assert "PROFILE_CLI_PROFILE" in header_path.read_text(encoding="utf-8")


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

    assert result["format"] == "retrobus-compact-density-profile-v2"
    assert result["captures"][0]["provenance"] == {
        "device": "synthetic",
        "scenario": "v2 replay",
    }
    assert result["aggregate"]["v2_predictions_all_match"] is True


def test_preserved_historical_v4_audit_totals_and_checksums() -> None:
    repository = Path(__file__).resolve().parents[2]
    audit = repository / "compact/audit/v4-redux-historical"
    for line in (audit / "ARTIFACTS.sha256").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        assert hashlib.sha256((audit / name).read_bytes()).hexdigest() == expected

    results = json.loads((audit / "results.json").read_text(encoding="utf-8"))
    expected = {
        ("zire31-cold-boot", "v3"): (348_157, None, None),
        ("t3-cold-boot", "v3"): (808_513, None, None),
        ("zire31-cold-boot", "v4_profile_128"): (82_864, 662_835, 7_619),
        ("t3-cold-boot", "v4_profile_128"): (186_086, 1_488_568, 16_779),
        ("zire31-cold-boot", "v4_profile_247"): (73_656, 589_210, 3_647),
        ("t3-cold-boot", "v4_profile_247"): (168_074, 1_344_502, 8_976),
    }
    for (capture_id, model_name), (payload_bytes, payload_bits, misses) in expected.items():
        model = results["captures"][capture_id][model_name]
        assert model["payload_bytes"] == payload_bytes
        assert len(model["chunk_used_lengths"]) == model["chunks"]
        assert model["container_bytes"] == model["file_header_bytes"] + 4096 * model[
            "chunks"
        ]
        if payload_bits is None:
            assert sum(model["chunk_used_lengths"]) == payload_bytes
            continue
        assert model["payload_bits"] == payload_bits
        assert model["profile_misses"] == misses
        assert model["bit_attribution"]["literal_kind"] == 2 * misses
        assert sum(model["bit_attribution"].values()) == payload_bits
        assert sum(model["chunk_used_bits"]) == payload_bits
        assert sum((cursor + 7) // 8 for cursor in model["chunk_used_bits"]) == payload_bytes
        assert model["chunk_used_lengths"] == [
            (cursor + 7) // 8 for cursor in model["chunk_used_bits"]
        ]

    for entry_limit, profile in results["profiles"].items():
        canonical = (audit / profile["path"]).read_bytes().rstrip(b"\n")
        assert hashlib.sha256(canonical).hexdigest() == profile["sha256"]
        assert int(entry_limit) == profile["entries"]
