"""Regression tests for source-package bootstrap behavior."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tarfile


def _copy_clean_source(tmp_path: Path) -> Path:
    project_root = Path(__file__).resolve().parents[1]
    checkout_root = tmp_path / "checkout"
    python_root = checkout_root / "py"
    python_root.mkdir(parents=True)
    for filename in ("README.md", "pyproject.toml", "setup.py"):
        shutil.copy2(project_root / filename, python_root)
    shutil.copytree(
        project_root / "retrobus_perfetto",
        python_root / "retrobus_perfetto",
        ignore=shutil.ignore_patterns("*_pb2.py", "*_pb2_grpc.py", "__pycache__"),
    )
    shutil.copytree(project_root.parent / "proto", checkout_root / "proto")
    return python_root


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in tuple(env):
        if name.startswith("COV_CORE_") or name == "COVERAGE_PROCESS_START":
            del env[name]
    return env


def test_setup_loads_without_generated_protobuf(tmp_path: Path) -> None:
    """Setup metadata must load before protobuf bindings have been generated."""
    python_root = _copy_clean_source(tmp_path)

    result = subprocess.run(
        [sys.executable, "setup.py", "--name"],
        cwd=python_root,
        capture_output=True,
        env=_subprocess_env(),
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "retrobus-perfetto"


def test_sdist_bundles_generated_protobuf(tmp_path: Path) -> None:
    """An sdist must contain bindings so its wheel can build without the schema."""
    python_root = _copy_clean_source(tmp_path)
    dist_dir = tmp_path / "dist"

    result = subprocess.run(
        [sys.executable, "setup.py", "sdist", "--dist-dir", str(dist_dir)],
        cwd=python_root,
        capture_output=True,
        env=_subprocess_env(),
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    [sdist_path] = dist_dir.glob("*.tar.gz")
    with tarfile.open(sdist_path, "r:gz") as archive:
        members = archive.getnames()
    assert any(
        name.endswith("/retrobus_perfetto/proto/perfetto_pb2.py") for name in members
    )
