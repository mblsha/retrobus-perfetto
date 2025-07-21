"""Setup script for retrobus-perfetto."""

from setuptools import setup
import sys
import os

# Add the current directory to the path to import the build module
sys.path.insert(0, os.path.dirname(__file__))

from retrobus_perfetto._build import BuildPyCommand, DevelopCommand

setup(
    cmdclass={
        'build_py': BuildPyCommand,
        'develop': DevelopCommand,
    }
)