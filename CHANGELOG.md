# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Puzzle generator (create new puzzles of specified difficulty)
- Hint mode (reveal one cell at a time with explanation)
- Timer display on the board
- Export solved puzzle as PNG image

---

## [0.1.0] — 2026-04-25

### Added
- **Data model layer** — immutable `Cell` and `Board` dataclasses with full
  constraint helpers (`peers`, `row_values`, `col_values`, `box_values`,
  `candidates_for`, `with_candidates_computed`).
- **JSON puzzle schema** (version 1) — `BoardSerialiser` for load/save.
  Bundled puzzles: `easy_001`, `medium_001`, `hard_001`.
- **Validator** — pure stateless Sudoku rule checker; annotates conflicting cells.
- **EventBus** — thread-safe singleton pub/sub with typed event dataclasses,
  wildcard subscriptions, error isolation, and no-infinite-loop guard.
- **Typed events** — `CellChanged`, `CandidatesChanged`, `SolveStarted`,
  `SolveStep`, `SolveComplete`, `SolveFailed`, `PuzzleLoaded`, `PuzzleReset`,
  `UndoRequested`, `RedoRequested`, `SelectionChanged`, `ErrorRaised`,
  `ThemeChanged`, `SpeedChanged`.
- **Solver engine** — three strategies in a pipeline:
  - `NakedSingles` — fills cells with exactly one candidate.
  - `AC-3` — arc-consistency constraint propagation.
  - `Backtracker` — recursive backtracking with MRV heuristic.
  - All run in a daemon thread; emit `SolveStep` events for animation.
  - `solve_sync()` for non-GUI / test use.
- **pygame-ce GUI** — `BoardWidget`, `ControlPanel`, `StatusBar`.
  - Cell selection via mouse and arrow keys.
  - Digit entry, peer/same-value highlighting, conflict highlighting.
  - Candidate number display.
  - Adjustable solve speed slider (0–30 steps/second).
  - Pause / Resume via the Solve button (click again to cancel).
- **Theme system** — `ThemeManager` with three built-in themes:
  `light`, `dark`, `solarized`. Switchable at runtime via `T` key.
- **Controller** — undo/redo stack (128 steps), puzzle load/reset, file picker.
- **Project tooling** — `pyproject.toml` (hatchling), ruff, mypy strict,
  pytest + pytest-cov, pre-commit hooks, GitHub Actions CI matrix.
- **Bootstrap scripts** — `setup.sh` (Linux/macOS) and `setup.bat` (Windows).
- **Makefile** — `make run/test/lint/format/typecheck/clean`.

### Test coverage
- 140 unit tests across `test_cell`, `test_board`, `test_validator`,
  `test_serialiser`, `test_types`, `test_bus` — 96% overall coverage.

---

[Unreleased]: https://github.com/yourname/sudoku-solver/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourname/sudoku-solver/releases/tag/v0.1.0
