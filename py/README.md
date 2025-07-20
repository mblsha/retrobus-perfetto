# retrobus-perfetto Python Implementation

This directory contains the Python implementation of retrobus-perfetto.

## Installation

From the `py/` directory:

```bash
# For development
pip install -e ".[dev]"

# For regular use
pip install .
```

## Development

### Running Tests
```bash
pytest
```

### Running Linter
```bash
pylint $(git ls-files '*.py' | grep "^py/")
```

### Running Type Checker
```bash
mypy retrobus_perfetto --config-file mypy.ini
```

### Building Package
```bash
python -m build
```

## Project Structure

- `retrobus_perfetto/` - Main package source code
  - `builder.py` - Main trace builder class
  - `annotations.py` - Annotation helper classes
  - `proto/` - Generated protobuf files (created during build)
- `tests/` - Unit tests
- `example.py` - Example usage
- `pyproject.toml` - Package configuration