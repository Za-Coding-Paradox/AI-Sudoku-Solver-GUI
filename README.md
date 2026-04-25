# Sudoku Solver

A **data-driven, event-bus-powered** GUI Sudoku Solver built with Python and [pygame-ce](https://pyga.me/).

The solver animates its solving process in real time — you can watch constraint propagation and backtracking work step by step, control the animation speed, and edit cells manually between runs.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Solving Strategies](#solving-strategies)
- [Keyboard & Mouse Controls](#keyboard--mouse-controls)
- [Puzzle Format](#puzzle-format)
- [Development](#development)
- [Running Tests](#running-tests)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Feature | Details |
|---|---|
| **Interactive pygame-ce GUI** | Crisp grid rendering, cell selection, keyboard + mouse input |
| **Event Bus architecture** | Solver, data model, and GUI communicate via typed events — no direct cross-layer imports |
| **Immutable data model** | Pure Python dataclasses for `Cell` and `Board`; every mutation returns a new object |
| **Three solving strategies** | Naked Singles → Constraint Propagation (AC-3) → Backtracking |
| **Step-by-step animation** | Adjustable speed from instant to 1 step per second |
| **Puzzle JSON schema** | Load and save puzzles from plain JSON files; bundled easy, medium, and hard puzzles included |
| **Light & dark themes** | Switchable at runtime with a single key |
| **Full keyboard navigation** | Arrow keys, digit entry, Ctrl+Z / Ctrl+Y undo/redo |
| **Typed event system** | Thread-safe pub/sub `EventBus` singleton with fully typed event dataclasses |

---

## Requirements

- **Python 3.11 or newer** (tested up to 3.14)
- **pygame-ce 2.4+** (installed automatically by the setup script)

---

## Quick Start

### Linux / macOS

```bash
git clone https://github.com/yourname/sudoku-solver.git
cd sudoku-solver

chmod +x setup.sh
./setup.sh

source .venv/bin/activate
make run
```

### Windows

```bat
git clone https://github.com/yourname/sudoku-solver.git
cd sudoku-solver

setup.bat

.venv\Scripts\activate.bat
python -m sudoku.app
```

### Setup script options

Both `setup.sh` and `setup.bat` accept the same flags:

| Flag | Effect |
|---|---|
| *(none)* | Install venv + dependencies |
| `--test` | Install everything, then run the full test suite |
| `--test-only` | Run tests only (venv must already exist) |
| `--help` / `-h` | Show usage |

```bash
# Example — install and immediately verify everything works:
./setup.sh --test
```

---

## Project Structure

```
sudoku-solver/
├── src/sudoku/
│   ├── app.py                  ← Entry point (pygame init, main loop)
│   ├── controller/
│   │   └── controller.py       ← Input handler — translates pygame events to domain events
│   ├── data/
│   │   ├── cell.py             ← Cell dataclass (immutable value object)
│   │   ├── board.py            ← Board — 9×9 grid, candidate computation, constraint helpers
│   │   ├── validator.py        ← Sudoku rules engine (conflict detection, completeness check)
│   │   └── serialiser.py       ← JSON puzzle load / save
│   ├── events/
│   │   ├── bus.py              ← EventBus singleton (thread-safe pub/sub)
│   │   └── types.py            ← All typed event dataclasses
│   ├── solver/
│   │   ├── engine.py           ← SolverEngine — runs strategies in a background thread
│   │   └── strategies.py       ← NakedSingles, AC3, Backtracker implementations
│   └── gui/
│       ├── board_widget.py     ← pygame canvas — draws the 9×9 grid and candidates
│       ├── control_panel.py    ← Solve / Load / Reset / Speed buttons
│       ├── status_bar.py       ← Status line + elapsed solve timer
│       └── theme.py            ← Light / dark theme colour data
├── tests/
│   ├── conftest.py             ← Shared pytest fixtures
│   ├── test_app/               ← App-level integration tests
│   ├── test_controller/        ← Controller unit tests
│   ├── test_data/              ← Cell, Board, Validator, Serialiser tests
│   ├── test_events/            ← EventBus and event type tests
│   ├── test_gui/               ← Widget and theme tests
│   └── test_strategies/        ← Solver strategy and engine tests
├── puzzles/
│   ├── easy_001.json
│   ├── medium_001.json
│   └── hard_001.json
├── pyproject.toml              ← PEP 517/518 project config (build, lint, type check, test)
├── Makefile                    ← Developer task runner
├── setup.sh                    ← Linux / macOS bootstrap script
├── setup.bat                   ← Windows bootstrap script
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                      EventBus                        │
│         (singleton — all layers subscribe here)      │
└──────────┬───────────────────────────┬───────────────┘
           │ publishes                 │ publishes
    ┌──────▼──────┐             ┌──────▼──────┐
    │   Solver    │             │  Controller │ ← pygame input events
    │  (thread)   │             │             │
    └─────────────┘             └──────┬──────┘
                                       │ mutates
                                ┌──────▼──────┐
                                │  Data Model │
                                │ Board/Cell  │
                                └──────┬──────┘
                                       │ change events
                                ┌──────▼──────┐
                                │     GUI     │
                                │  (pygame)   │
                                └─────────────┘
```

**Key design principles:**

- The **GUI layer never imports the solver**, and the **solver never imports the GUI**. All coordination flows through the `EventBus` via strongly typed events.
- The **data model is immutable** — every operation on `Board` or `Cell` returns a new object, making undo/redo trivial and eliminating shared mutable state bugs.
- The **solver runs in a background thread**, publishing `SolverStepEvent` objects at a configurable rate so the GUI stays responsive during solving.

---

## Solving Strategies

The engine applies three strategies in order, escalating only when the current strategy is exhausted:

### 1. Naked Singles
If a cell has only one candidate remaining, that value is the only possibility. This pass repeats until no new assignments can be made.

### 2. Constraint Propagation (AC-3)
Enforces arc consistency across all peers (row, column, and 3×3 box). When a value is assigned, it is eliminated from all peers' candidate sets. This cascade often solves medium-difficulty puzzles without guessing.

### 3. Backtracking
A depth-first search with constraint checking. An empty cell is chosen, a candidate value is tried, and the solver recurses. On contradiction the solver backtracks and tries the next candidate. This guarantees a solution for any valid puzzle.

> **Note:** The backtracking solver does not currently use MRV (minimum remaining values) or degree heuristics, so very hard puzzles may take a few seconds. Contributions to add heuristics are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Keyboard & Mouse Controls

| Input | Action |
|---|---|
| **Click** a cell | Select it |
| **Arrow keys** | Move selection |
| **1 – 9** | Enter a digit into the selected cell |
| **Delete / Backspace** | Clear the selected cell |
| **Ctrl+Z** | Undo last change |
| **Ctrl+Y** | Redo |
| **T** | Toggle light / dark theme |
| **Escape** | Deselect / cancel solving |

---

## Puzzle Format

Puzzles are plain JSON files stored in `puzzles/`. The schema:

```json
{
  "version": 1,
  "name": "Easy #001",
  "difficulty": "easy",
  "author": "optional",
  "source": "optional URL",
  "grid": [
    [5, 3, 0,  0, 7, 0,  0, 0, 0],
    [6, 0, 0,  1, 9, 5,  0, 0, 0],
    [0, 9, 8,  0, 0, 0,  0, 6, 0],

    [8, 0, 0,  0, 6, 0,  0, 0, 3],
    [4, 0, 0,  8, 0, 3,  0, 0, 1],
    [7, 0, 0,  0, 2, 0,  0, 0, 6],

    [0, 6, 0,  0, 0, 0,  2, 8, 0],
    [0, 0, 0,  4, 1, 9,  0, 0, 5],
    [0, 0, 0,  0, 8, 0,  0, 7, 9]
  ],
  "solution": [
    [5, 3, 4,  6, 7, 8,  9, 1, 2],
    ...
  ]
}
```

`0` represents an empty cell. The `solution` key is optional and is used by the validator in tests.

---

## Development

All common tasks are available via `make`. Run `make help` for a full list.

```bash
make run            # Launch the GUI
make test           # Full test suite with coverage report
make test-fast      # Tests without coverage (faster)
make lint           # ruff linter (check only)
make format         # ruff auto-format + auto-fix
make typecheck      # mypy strict mode
make check          # lint + format-check + typecheck (CI gate)
make clean          # Remove build artefacts and caches
make reset          # Remove venv entirely — full fresh start
```

**Run a single test file:**
```bash
make test-file FILE=tests/test_data/test_board.py
# or directly:
pytest tests/test_data/test_board.py -v
```

**Run tests matching a pattern:**
```bash
make test-k K=test_toggle
# or directly:
pytest -k "test_toggle" -v
```

**Generate an HTML coverage report:**
```bash
make coverage-html
# opens htmlcov/index.html
```

---

## Running Tests

```bash
# All tests with coverage
pytest

# Specific module
pytest tests/test_strategies/ -v

# Stop on first failure
pytest -x

# Show print output
pytest -s
```

Coverage is reported automatically. The configuration lives in `pyproject.toml` under `[tool.pytest.ini_options]` and `[tool.coverage.*]`.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on branching, commit style, code quality requirements, and how to add new puzzle files or solver strategies.

---

## License

[MIT](LICENSE)
