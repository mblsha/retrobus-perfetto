#!/usr/bin/env python3
"""Regenerate the pinned official Perfetto descriptor used by compatibility tests."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tempfile
import urllib.request
from pathlib import Path


PERFETTO_REVISION = "ec5d16b14b743ba6063d720956d6d6af6610fd72"
SOURCE_SHA256 = "c43d1658360a80a144a2d7a0a6e58a70795b0051f4e333db9d17834eab4a7a1a"
SOURCE_URL = (
    "https://raw.githubusercontent.com/google/perfetto/"
    f"{PERFETTO_REVISION}/protos/perfetto/trace/perfetto_trace.proto"
)
DEFAULT_OUTPUT = (
    Path(__file__).parents[1]
    / "py"
    / "tests"
    / "fixtures"
    / "perfetto-official-ec5d16b1.desc"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with urllib.request.urlopen(SOURCE_URL) as response:
        source = response.read()
    digest = hashlib.sha256(source).hexdigest()
    if digest != SOURCE_SHA256:
        raise RuntimeError(
            f"official Perfetto source hash changed: {digest} != {SOURCE_SHA256}"
        )

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="retrobus-perfetto-proto-") as temp:
        source_path = Path(temp) / "perfetto_trace.proto"
        source_path.write_bytes(source)
        subprocess.run(
            [
                "protoc",
                f"--proto_path={temp}",
                f"--descriptor_set_out={output}",
                source_path.name,
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
