"""Custom build commands for protobuf compilation."""

import subprocess
import sys
from pathlib import Path

from setuptools.command.build_py import build_py
from setuptools.command.develop import develop


class BuildProtoCommand:
    """Mixin for building protobuf files."""

    def run_protoc(self):
        """Compile .proto files to Python modules."""
        # Get paths from pyproject.toml or use defaults
        project_root = Path(__file__).parent.parent
        proto_path = project_root.parent / "proto"
        proto_out = project_root / "retrobus_perfetto" / "proto"

        # Create output directory
        proto_out.mkdir(parents=True, exist_ok=True)

        # Create __init__.py in proto directory
        (proto_out / "__init__.py").write_text("")
        proto_file = proto_path / "perfetto.proto"

        if not proto_file.exists():
            print(f"Warning: {proto_file} not found, skipping protobuf compilation")
            return

        print(f"Compiling {proto_file}...")

        try:
            # Run protoc
            result = subprocess.run([
                sys.executable, "-m", "grpc_tools.protoc",
                f"--proto_path={proto_path}",
                f"--python_out={proto_out}",
                str(proto_file)
            ], capture_output=True, text=True, check=False)

            if result.returncode != 0:
                print(f"protoc failed: {result.stderr}")
                # Try alternative protoc command
                result = subprocess.run([
                    "protoc",
                    f"--proto_path={proto_path}",
                    f"--python_out={proto_out}",
                    str(proto_file)
                ], capture_output=True, text=True, check=False)

                if result.returncode != 0:
                    print(f"Alternative protoc also failed: {result.stderr}")
                    print("Please install protobuf compiler (protoc) or grpcio-tools")
                    sys.exit(1)

            print("Protobuf compilation successful")

        except FileNotFoundError:
            print("protoc not found. Please install protobuf compiler or grpcio-tools")
            sys.exit(1)


class BuildPyCommand(build_py, BuildProtoCommand):
    """Custom build command that compiles protos."""

    def run(self):
        self.run_protoc()
        super().run()


class DevelopCommand(develop, BuildProtoCommand):
    """Custom develop command that compiles protos."""

    def run(self):
        self.run_protoc()
        super().run()
