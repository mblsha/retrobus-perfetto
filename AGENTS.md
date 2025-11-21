# Repository Guidelines

## Project Structure & Module Organization
- `py/` Python implementation and packaging; `cpp/` header-only C++ library with `examples/` and `tests/`; `proto/` shared Perfetto schema; `tools/` Python trace-analysis scripts; see `perfetto-trace-generation-guide.md` for trace notes.
- Generated protobuf code lands in `py/retrobus_perfetto/proto/` during Python builds and `cpp/build/proto/` during CMake builds—keep schema changes synchronized.

## Build, Test, and Development Commands
- Python setup: `cd py && pip install -e ".[dev]"`; build wheel/sdist with `python -m build`.
- Python checks: `cd py && pytest`; `ruff check .`; `mypy retrobus_perfetto --config-file mypy.ini`.
- C++: `cmake -S cpp -B cpp/build` then `cmake --build cpp/build`; run tests via `ctest --test-dir cpp/build`; execute examples from `cpp/build/examples/basic_example` or `cpu_emulator_example`.
- Tools: run helpers directly, e.g., `python tools/perfetto_pc_analyzer.py trace.perfetto-trace`.

## Coding Style & Naming Conventions
- Python: 4-space indents, type hints, docstrings where behavior is non-obvious, `snake_case` for functions/variables, `PascalCase` for classes (`PerfettoTraceBuilder`). Keep lint clean with Ruff and maintain mypy compatibility (see `py/mypy.ini`).
- C++: C++17, header-only APIs in `include/retrobus`; prefer `snake_case` methods and `CamelCase` types, keep includes ordered (STL, protobuf, local), avoid `using namespace`. Preserve existing atomic/thread-safety patterns in builders.
- Proto evolution: maintain backward compatibility across languages; regenerate bindings when `proto/perfetto.proto` changes and document impacts.

## Testing Guidelines
- Python tests live in `py/tests/test_*.py`; mirror new functionality with unit tests. For coverage checks, run `pytest --cov retrobus_perfetto`.
- C++ tests use Catch2 (fetched automatically); add cases in `cpp/tests/` and rerun `ctest`.
- Prefer deterministic fixtures; when adding trace outputs, keep sample `.perfetto-trace` files minimal or build them in-test.

## Commit & Pull Request Guidelines
- Commit messages are short, present-tense summaries (e.g., `Refactor packet creation helper`, `Update snapshots for dict entry ordering`); group related changes per commit.
- PRs should describe intent, list commands/tests run, flag API or protobuf schema changes, and attach sample traces or screenshots when observable output shifts.
- Keep diffs focused and update relevant READMEs when introducing workflows, options, or new build flags.
