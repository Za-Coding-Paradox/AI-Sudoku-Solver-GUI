# Sudoku Solver

A **data-driven, event-bus-powered** GUI Sudoku Solver built with Python and [pygame-ce](https://pyga.me/).

The solver animates its solving process in real time — you can watch constraint propagation and backtracking work step by step, control the animation speed, and edit cells manually between runs.

---

## Features

- **Interactive pygame-ce GUI** — crisp grid rendering, cell selection, keyboard + mouse input
- **Event Bus architecture** — solver, data model, and GUI communicate via typed events; no direct imports between layers
- **Data-driven design** — pure Python dataclasses for `Cell` and `Board`; every mutation returns a new object (immutable style, trivial undo/redo)
- **Three solving strategies** — Naked Singles → Constraint Propagation (AC-3) → Backtracking
- **Step-by-step animation** — adjustable speed from instant to 1 step/second
- **Puzzle JSON schema** — load/save puzzles from plain JSON files; bundled easy/medium/hard puzzles included
- **Light & dark themes** — switchable at runtime
- **Full keyboard navigation** — arrow keys, digit entry, Ctrl+Z / Ctrl+Y

---

## Requirements

- Python **3.11+**
- pygame-ce **2.4+**

---

## Quick start

### Linux / macOS

```bash
git clone https://github.com/yourname/sudoku-solver.git
cd sudoku-solver
chmod +x setup.sh && ./setup.sh
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

---

## Project structure

```
sudoku-solver/
├── src/sudoku/
│   ├── app.py              ← entry point (pygame init, main loop)
│   ├── data/
│   │   ├── cell.py         ← Cell dataclass (immutable value object)
│   │   ├── board.py        ← Board — 9×9 grid, constraint helpers
│   │   ├── validator.py    ← Sudoku rules engine
│   │   └── serialiser.py   ← JSON puzzle load/save
│   ├── events/
│   │   ├── bus.py          ← EventBus singleton (thread-safe pub/sub)
│   │   └── types.py        ← All typed event dataclasses
│   ├── solver/
│   │   ├── engine.py       ← Solver strategies (runs in background thread)
│   │   └── strategies.py   ← Naked singles, AC-3, backtracking
│   └── gui/
│       ├── board_widget.py ← pygame Canvas — draws the 9×9 grid
│       ├── control_panel.py← Solve / Load / Reset buttons
│       ├── status_bar.py   ← Status line + solve timer
│       └── theme.py        ← Light/dark theme data
├── tests/
│   ├── test_data/          ← Cell, Board, Validator, Serialiser tests
│   └── test_events/        ← EventBus and event type tests
├── puzzles/                ← Bundled puzzle JSON files
├── pyproject.toml          ← PEP 517/518 project config
├── Makefile                ← make run / test / lint / typecheck
├── setup.sh                ← Linux/macOS bootstrap
└── setup.bat               ← Windows bootstrap
```

---

## Architecture overview

```
┌─────────────────────────────────────────────┐
│                  EventBus                   │
│    (singleton — all modules subscribe here) │
└──────────┬───────────────────┬──────────────┘
           │ publishes         │ publishes
    ┌──────▼──────┐     ┌──────▼──────┐
    │   Solver    │     │  Controller │ ← user input
    │  (thread)   │     │             │
    └─────────────┘     └──────┬──────┘
                               │ updates
                        ┌──────▼──────┐
                        │  Data Model │
                        │ Board/Cell  │
                        └──────┬──────┘
                               │ events
                        ┌──────▼──────┐
                        │     GUI     │
                        │  (pygame)   │
                        └─────────────┘
```

The **GUI layer never imports the solver** and the **solver never imports the GUI**. All coordination goes through the EventBus via typed events.

---

## Development

```bash
make test       # run pytest with coverage
make lint       # ruff linter
make format     # ruff auto-format
make typecheck  # mypy strict mode
```

### Running a single test file

```bash
pytest tests/test_data/test_board.py -v
```

---

## Puzzle format

Puzzles are plain JSON files stored in `puzzles/`:

```json
{
  "version": 1,
  "name": "Easy #001",
  "difficulty": "easy",
  "author": "optional",
  "source": "optional URL",
  "grid": [
    [5,3,0, 0,7,0, 0,0,0],
    ...
  ],
  "solution": [...]
}
```

`0` means an empty cell.  The `solution` key is optional.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[MIT](LICENSE)
