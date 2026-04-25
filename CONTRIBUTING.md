# Contributing to Sudoku Solver

Thank you for taking the time to contribute! This document explains the
process, conventions, and expectations so that your contribution can be
reviewed and merged as smoothly as possible.

---

## Table of contents

1. [Getting started](#getting-started)
2. [Development workflow](#development-workflow)
3. [Code style](#code-style)
4. [Commit messages](#commit-messages)
5. [Pull request process](#pull-request-process)
6. [Architecture rules](#architecture-rules)
7. [Adding a new puzzle](#adding-a-new-puzzle)
8. [Adding a new theme](#adding-a-new-theme)
9. [Adding a new solving strategy](#adding-a-new-solving-strategy)

---

## Getting started

```bash
git clone https://github.com/yourname/sudoku-solver.git
cd sudoku-solver
./setup.sh          # Linux/macOS
# or
setup.bat           # Windows

source .venv/bin/activate
make test           # all tests should pass before you start
```

---

## Development workflow

```bash
git checkout -b feature/my-feature    # branch off main
# ... make changes ...
make lint                             # ruff check
make typecheck                        # mypy --strict
make test                             # pytest with coverage
git commit -m "feat: describe change"
git push origin feature/my-feature
# open a PR on GitHub
```

---

## Code style

- **Formatter**: `ruff format` (Black-compatible, line length 100).
- **Linter**: `ruff check` — all rules in `pyproject.toml` must pass.
- **Types**: `mypy --strict` — all public functions must have type annotations.
- **Docstrings**: Google style for modules and classes; NumPy style for
  parameter tables.
- **Imports**: stdlib → third-party → internal, separated by blank lines.
  Ruff `isort` enforces this automatically.

Run everything in one command:

```bash
make format && make lint && make typecheck && make test
```

---

## Commit messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) spec:

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`.

Examples:
```
feat(solver): add hidden singles strategy
fix(board): candidates_for returns empty set for filled cells
docs(readme): add screenshot
test(bus): cover wildcard subscription dedup
```

---

## Pull request process

1. Ensure all CI checks pass (lint, typecheck, tests on all OS/Python combos).
2. Add or update tests — new code should maintain ≥ 90% coverage.
3. Update `CHANGELOG.md` under `[Unreleased]`.
4. Keep PRs focused — one feature or fix per PR.
5. Request a review from a maintainer.

---

## Architecture rules

The project enforces strict layer separation. **Violating these rules will
cause a PR to be rejected.**

| Layer | May import | Must NOT import |
|---|---|---|
| `sudoku.data` | stdlib only | `events`, `solver`, `gui`, `pygame` |
| `sudoku.events` | stdlib only | `data`, `solver`, `gui`, `pygame` |
| `sudoku.solver` | `data`, `events`, stdlib | `gui`, `pygame` |
| `sudoku.gui` | `data`, `events`, `pygame` | `solver` directly |
| `sudoku.controller` | `data`, `events`, `solver` | `pygame` rendering |
| `sudoku.app` | everything | — |

All cross-layer communication **must** go through the EventBus.

---

## Adding a new puzzle

1. Create `puzzles/<name>.json` following the schema in `README.md`.
2. Run `pytest tests/test_data/test_serialiser.py` — the
   `test_load_real_puzzle_files` test will automatically pick it up.
3. Verify the puzzle is not already solved (given-cells-only grid must be partial).

---

## Adding a new theme

1. Open `src/sudoku/gui/theme.py`.
2. Create a new `Theme(...)` instance following the same structure as
   `LIGHT_THEME` and `DARK_THEME`.
3. Add it to `_BUILTIN_THEMES` dict at the bottom of the file.
4. The theme will automatically appear in the `T`-key cycle.

---

## Adding a new solving strategy

1. Create a class in `src/sudoku/solver/strategies.py` with a classmethod
   `apply(cls, board: Board) -> Generator[tuple[Board, SolveStep], None, ...]`.
2. Yield `(new_board, SolveStep(...))` for every digit placed.
3. Register it in `SolverEngine._run()` in `engine.py` at the appropriate
   position in the pipeline.
4. Add tests in `tests/test_solver/test_strategies.py`.
