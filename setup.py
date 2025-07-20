"""Setup script for retrobus-perfetto package."""

import subprocess
import sys
from pathlib import Path

from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop


class BuildProtoCommand:
    """Mixin for building protobuf files."""

    def run_protoc(self):
        """Compile .proto files to Python modules."""
        proto_dir = Path("retrobus_perfetto/proto")
        proto_file = proto_dir / "perfetto.proto"

        if not proto_file.exists():
            print(f"Warning: {proto_file} not found, skipping protobuf compilation")
            return

        print(f"Compiling {proto_file}...")

        try:
            # Run protoc
            result = subprocess.run([
                sys.executable, "-m", "grpc_tools.protoc",
                f"--proto_path={proto_dir}",
                f"--python_out={proto_dir}",
                str(proto_file)
            ], capture_output=True, text=True, check=False)

            if result.returncode != 0:
                print(f"protoc failed: {result.stderr}")
                # Try alternative protoc command
                result = subprocess.run([
                    "protoc",
                    f"--proto_path={proto_dir}",
                    f"--python_out={proto_dir}",
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


# Read long description from README
readme_path = Path(__file__).parent / "README.md"
if readme_path.exists():
    long_description = readme_path.read_text()
else:
    long_description = "A minimal Perfetto trace generation library for retrocomputer emulators."


setup(
    name="retrobus-perfetto",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A minimal Perfetto trace generation library for retrocomputer emulators",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/retrobus-perfetto",
    packages=find_packages(),
    package_data={
        "retrobus_perfetto": ["proto/*.proto", "py.typed", "proto/*.pyi"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Debuggers",
        "Topic :: System :: Emulators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "protobuf>=3.20.0,<5.0.0",
    ],
    extras_require={
        "dev": [
            "grpcio-tools>=1.48.0",  # For protoc compilation
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
        ],
    },
    cmdclass={
        "build_py": BuildPyCommand,
        "develop": DevelopCommand,
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/retrobus-perfetto/issues",
        "Source": "https://github.com/yourusername/retrobus-perfetto",
    },
)
