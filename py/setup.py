"""Setup script for retrobus-perfetto."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from setuptools import setup


# Load build hooks without importing retrobus_perfetto. The package imports generated
# protobuf bindings that do not exist yet in a clean source checkout.
_build_path = Path(__file__).parent / "retrobus_perfetto" / "_build.py"
_build_spec = spec_from_file_location("_retrobus_perfetto_build", _build_path)
if _build_spec is None or _build_spec.loader is None:
    raise ImportError(f"Unable to load build hooks from {_build_path}")
_build_module = module_from_spec(_build_spec)
_build_spec.loader.exec_module(_build_module)

BuildPyCommand = _build_module.BuildPyCommand
DevelopCommand = _build_module.DevelopCommand
SdistCommand = _build_module.SdistCommand

setup(
    cmdclass={
        "build_py": BuildPyCommand,
        "develop": DevelopCommand,
        "sdist": SdistCommand,
    }
)
