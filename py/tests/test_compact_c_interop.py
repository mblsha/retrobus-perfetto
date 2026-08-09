"""Compile the C producer and decode its exact output with the Python host."""

from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from retrobus_perfetto import (
    CompactCodecProfile,
    CompactSchema,
    compact_trace_to_builder,
    profile_compact_trace,
    read_compact_trace,
    render_c_schema_header,
    render_c_codec_profile,
)
from retrobus_perfetto.compact import FLAG_CHUNK_HEADER_CRC


UINT32_MAX = (1 << 32) - 1
UINT64_MAX = (1 << 64) - 1


def _compile_producer(
    compiler: str,
    repository: Path,
    tmp_path: Path,
    source_name: str,
) -> tuple[CompactSchema, Path]:
    compact = repository / "compact"
    schema = CompactSchema.load(compact / "tests" / "interop-schema.json")
    generated = tmp_path / "interop_schema.h"
    generated.write_text(render_c_schema_header(schema, "interop"), encoding="utf-8")
    executable = tmp_path / Path(source_name).stem
    subprocess.run(
        [
            compiler,
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{compact / 'include'}",
            f"-I{tmp_path}",
            str(compact / "src" / "compact_trace.c"),
            str(compact / "tests" / source_name),
            "-o",
            str(executable),
        ],
        check=True,
    )
    return schema, executable


def test_c_writer_python_decoder_interoperability(tmp_path: Path) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    schema, executable = _compile_producer(
        compiler, repository, tmp_path, "write_interop_trace.c"
    )
    capture = tmp_path / "interop.rbct"
    subprocess.run([executable, capture], check=True)

    image = capture.read_bytes()
    payload_offset = 192 + 48
    assert image[:8] == b"RBCTRC4\0"
    assert image[160:192] == b"\0" * 32
    assert struct.unpack_from("<H", image, 192 + 28)[0] > 0
    assert image[payload_offset] != 0

    trace = read_compact_trace(capture, schema)
    assert trace.header.flags & FLAG_CHUNK_HEADER_CRC
    assert trace.header.total_records == 5
    assert trace.header.total_events == 6
    assert trace.header.dropped_records == 3
    assert [record.event.id for record in trace.records] == [21, 2, 1, 3, 300]
    assert trace.records[0].arguments == ()
    assert trace.records[1].arguments == (-7,)
    assert trace.records[2].duration_ticks == 40
    assert trace.records[3].track_id == 1
    assert trace.records[4].arguments == (0xDEAD_BEEF_1234_5678,)


def test_profiled_c_writer_python_decoder_interoperability(tmp_path: Path) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    schema = CompactSchema.load(repository / "compact/tests/interop-schema.json")
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
                    "training_count": 999,
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
    (tmp_path / "interop_codec.h").write_text(
        render_c_codec_profile(profile, "interop_codec"), encoding="utf-8"
    )
    _, executable = _compile_producer(
        compiler, repository, tmp_path, "write_profile_interop_trace.c"
    )
    capture = tmp_path / "profiled.rbct"
    subprocess.run([executable, capture], check=True)

    image = capture.read_bytes()
    assert image[:8] == b"RBCTRC4\0"
    assert image[160:192] == profile.sha256
    assert struct.unpack_from("<H", image, 192 + 28)[0] == 1001
    trace = read_compact_trace(capture, schema, codec_profile=profile)
    assert len(trace.records) == 1000
    assert all(record.event.id == 0 for record in trace.records)
    assert all(record.duration_ticks == 1 for record in trace.records)
    with pytest.raises(ValueError, match="requires its external codec profile"):
        read_compact_trace(capture, schema)

    literal_capture = tmp_path / "literal-v4.rbct"
    subprocess.run([executable, literal_capture, "literal"], check=True)
    literal_trace = read_compact_trace(literal_capture, schema)
    assert trace.records == literal_trace.records
    assert compact_trace_to_builder(trace).serialize() == compact_trace_to_builder(
        literal_trace
    ).serialize()
    report = profile_compact_trace(capture, schema, codec_profile=profile)
    assert report["v4_prediction_matches_actual"] is True
    assert report["models"]["v4"]["payload_bits"] == 1001
    assert report["models"]["v4"]["payload_bytes"] == 126
    assert report["models"]["v4"]["chunk_used_bits"] == [1001]
    assert report["models"]["v4"]["chunk_used_lengths"] == [126]
    assert report["models"]["v4"]["special_opcode_hits"] == {
        "profile_hit": 1000
    }
    assert sum(report["models"]["v4"]["bit_attribution"].values()) == 1001

    corrupt = bytearray(image)
    corrupt[192 + 48] ^= 1
    corrupt_path = tmp_path / "profiled-corrupt.rbct"
    corrupt_path.write_bytes(corrupt)
    with pytest.raises(ValueError, match="CRC mismatch"):
        read_compact_trace(corrupt_path, schema, codec_profile=profile)

    finalized = literal_capture.read_bytes()
    payload_offset = 192 + 48
    first_record = finalized[payload_offset : payload_offset + 4]
    for stored_bytes in range(5):
        interrupted = bytearray(finalized)
        struct.pack_into("<H", interrupted, 38, 0)
        interrupted[192 + 28 : 192 + 32] = b"\0" * 4
        interrupted[192 + 40 : 192 + 48] = b"\0" * 8
        interrupted[payload_offset : payload_offset + 4048] = b"\0" * 4048
        interrupted[payload_offset : payload_offset + stored_bytes] = first_record[
            :stored_bytes
        ]
        snapshot = tmp_path / f"interrupted-byte-{stored_bytes}.rbct"
        snapshot.write_bytes(interrupted)
        assert not read_compact_trace(
            snapshot, schema, allow_unfinalized=True
        ).records

    published = bytearray(interrupted)
    published[payload_offset : payload_offset + 4] = first_record
    struct.pack_into("<HH", published, 192 + 28, 27, 1)
    published_path = tmp_path / "published-first-record.rbct"
    published_path.write_bytes(published)
    recovered = read_compact_trace(
        published_path, schema, allow_unfinalized=True
    )
    assert len(recovered.records) == 1
    assert recovered.records[0].event.id == 0


def test_wrapped_c_writer_remains_decodable_after_anchor_loss(
    tmp_path: Path,
) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    schema, executable = _compile_producer(
        compiler, repository, tmp_path, "write_ring_interop_trace.c"
    )
    capture = tmp_path / "wrapped.rbct"

    subprocess.run([executable, capture], check=True)
    trace = read_compact_trace(capture, schema)

    assert trace.header.ring_wrapped
    assert trace.header.total_records == 672
    assert trace.header.overwritten_records == 389
    assert len(trace.records) == 283
    assert {record.generation for record in trace.records} == {7}
    assert {sync.generation for sync in trace.clock_syncs} == {8}
    assert trace.uncorrelated_generations == (7,)
    assert trace.timestamp_ns(7, trace.records[-1].extended_tick) == 2000
    assert trace.timestamp_ns(8, trace.clock_syncs[0].extended_tick) == 2000


def test_live_wrapped_c_writer_recovers_after_anchor_loss(tmp_path: Path) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    schema, executable = _compile_producer(
        compiler, repository, tmp_path, "write_ring_interop_trace.c"
    )
    capture = tmp_path / "live-wrapped.rbct"

    subprocess.run([executable, capture, "live"], check=True)
    trace = read_compact_trace(capture, schema, allow_unfinalized=True)

    assert not trace.header.finalized
    assert trace.header.ring_wrapped
    assert len(trace.records) == 283
    assert trace.uncorrelated_generations == (7,)

    legacy_image = bytearray(capture.read_bytes())
    struct.pack_into("<H", legacy_image, 38, 0)
    legacy_capture = tmp_path / "live-wrapped-without-flag.rbct"
    legacy_capture.write_bytes(legacy_image)
    inferred = read_compact_trace(legacy_capture, schema, allow_unfinalized=True)
    assert inferred.header.ring_wrapped
    assert inferred.uncorrelated_generations == (7,)


def test_wrapped_c_writer_can_retain_later_clock_generations(
    tmp_path: Path,
) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    schema, executable = _compile_producer(
        compiler, repository, tmp_path, "write_generation_ring_interop_trace.c"
    )
    capture = tmp_path / "later-generations.rbct"

    subprocess.run([executable, capture], check=True)
    trace = read_compact_trace(capture, schema)

    assert trace.header.ring_wrapped
    assert [sync.generation for sync in trace.clock_syncs] == [9, 10]


def test_maximum_v4_literal_is_hidden_for_each_reconstructed_body_prefix(
    tmp_path: Path,
) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    schema, executable = _compile_producer(
        compiler, repository, tmp_path, "write_max_literal_trace.c"
    )
    capture = tmp_path / "maximum-literal.rbct"
    subprocess.run([executable, capture], check=True)
    finalized = capture.read_bytes()
    payload_offset = 192 + 48

    complete = read_compact_trace(capture, schema)
    assert [record.event.id for record in complete.records] == [21, UINT32_MAX]
    assert complete.records[1].track_id == UINT32_MAX
    assert complete.records[1].duration_ticks == (1 << 63) - 1
    assert complete.records[1].arguments == (UINT64_MAX,) * 4
    assert struct.unpack_from("<H", finalized, 192 + 28)[0] == 582

    for stored_bytes in range(71):
        interrupted = bytearray(finalized)
        struct.pack_into("<H", interrupted, 38, 0)
        struct.pack_into("<HH", interrupted, 192 + 28, 27, 1)
        interrupted[192 + 40 : 192 + 48] = b"\0" * 8
        interrupted[payload_offset : payload_offset + 4048] = b"\0" * 4048
        interrupted[payload_offset : payload_offset + 3] = finalized[
            payload_offset : payload_offset + 3
        ]
        interrupted[payload_offset + 3] = finalized[payload_offset + 3] & 0x07
        if stored_bytes:
            interrupted[
                payload_offset + 3 : payload_offset + 3 + stored_bytes
            ] = finalized[
                payload_offset + 3 : payload_offset + 3 + stored_bytes
            ]
        snapshot = tmp_path / f"maximum-interrupted-{stored_bytes}.rbct"
        snapshot.write_bytes(interrupted)
        recovered = read_compact_trace(
            snapshot, schema, allow_unfinalized=True
        )
        assert [record.event.id for record in recovered.records] == [21]

    published = bytearray(interrupted)
    published[payload_offset : payload_offset + 73] = finalized[
        payload_offset : payload_offset + 73
    ]
    struct.pack_into("<HH", published, 192 + 28, 582, 2)
    published_path = tmp_path / "maximum-published.rbct"
    published_path.write_bytes(published)
    assert len(
        read_compact_trace(
            published_path, schema, allow_unfinalized=True
        ).records
    ) == 2
