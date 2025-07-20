"""Setup script for retrobus-perfetto."""

from setuptools import setup

from retrobus_perfetto._build import BuildPyCommand, DevelopCommand

setup(
    cmdclass={
        'build_py': BuildPyCommand,
        'develop': DevelopCommand,
    }
)