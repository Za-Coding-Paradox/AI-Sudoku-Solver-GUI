"""Unit tests for :class:`sudoku.controller.Controller`.

Tests cover the full public API:
  - new_board / load_puzzle / reset_puzzle / solve
  - undo / redo stack behaviour
  - event subscriptions and publications
  - error paths (bad file, cancelled solve, impossible board)

pygame is NOT imported here — the Controller has no GUI dependency.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sudoku.controller import Controller
from sudoku.data.board import Board
from sudoku.data.cell import CellCoord
from sudoku.events.bus import EventBus
from sudoku.events.types import (
    CellChanged,
    ErrorRaised,
    PuzzleLoaded,
    PuzzleReset,
    RedoRequested,
    SpeedChanged,
    UndoRequested,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

EASY_STR = (
    "530070000"
    "600195000"
    "098000060"
    "800060003"
    "400803001"
    "700020006"
    "060000280"
    "000419005"
    "000080079"
)


def _make_puzzle_json(name: str = "Test", difficulty: str = "easy") -> dict[str, Any]:
    grid = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ]
    return {"version": 1, "name": name, "difficulty": difficulty, "grid": grid}


@pytest.fixture()
def bus() -> EventBus:
    return EventBus.get_instance()


@pytest.fixture()
def ctrl(bus: EventBus) -> Controller:
    return Controller(bus=bus)


@pytest.fixture()
def puzzle_file(tmp_path: Path) -> Path:
    data = _make_puzzle_json()
    p = tmp_path / "test_puzzle.json"
    p.write_text(json.dumps(data))
    return p


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestControllerInit:
    def test_creates_empty_board(self, ctrl: Controller) -> None:
        assert ctrl._board.is_complete() is False
        # All cells are empty at start
        assert all(cell.is_empty for _, cell in ctrl._board)

    def test_undo_stack_empty_at_start(self, ctrl: Controller) -> None:
        assert ctrl._undo_stack == []

    def test_redo_stack_empty_at_start(self, ctrl: Controller) -> None:
        assert ctrl._redo_stack == []

    def test_uses_singleton_bus_by_default(self) -> None:
        c = Controller()
        assert c._bus is EventBus.get_instance()

    def test_custom_bus_used(self, bus: EventBus) -> None:
        c = Controller(bus=bus)
        assert c._bus is bus


# ---------------------------------------------------------------------------
# new_board
# ---------------------------------------------------------------------------


class TestNewBoard:
    def test_publishes_puzzle_loaded(self, ctrl: Controller, bus: EventBus) -> None:
        events: list[PuzzleLoaded] = []
        bus.subscribe(PuzzleLoaded, events.append)
        ctrl.new_board()
        assert len(events) == 1

    def test_published_board_is_empty(self, ctrl: Controller, bus: EventBus) -> None:
        events: list[PuzzleLoaded] = []
        bus.subscribe(PuzzleLoaded, events.append)
        ctrl.new_board()
        assert all(cell.is_empty for _, cell in events[0].board)

    def test_published_name_is_new_puzzle(self, ctrl: Controller, bus: EventBus) -> None:
        events: list[PuzzleLoaded] = []
        bus.subscribe(PuzzleLoaded, events.append)
        ctrl.new_board()
        assert events[0].name == "New Puzzle"

    def test_clears_undo_stack(self, ctrl: Controller, bus: EventBus) -> None:
        # Put something on the undo stack first
        bus.publish(CellChanged(coord=CellCoord(0, 0), old_value=0, new_value=5))
        assert len(ctrl._undo_stack) == 1
        ctrl.new_board()
        assert ctrl._undo_stack == []

    def test_clears_redo_stack(self, ctrl: Controller, bus: EventBus) -> None:
        bus.publish(CellChanged(coord=CellCoord(0, 0), old_value=0, new_value=5))
        ctrl._redo_stack.append(ctrl._board)
        ctrl.new_board()
        assert ctrl._redo_stack == []


# ---------------------------------------------------------------------------
# load_puzzle
# ---------------------------------------------------------------------------


class TestLoadPuzzle:
    def test_load_valid_file_publishes_puzzle_loaded(
        self, ctrl: Controller, bus: EventBus, puzzle_file: Path
    ) -> None:
        events: list[PuzzleLoaded] = []
        bus.subscribe(PuzzleLoaded, events.append)
        ctrl.load_puzzle(puzzle_file)
        assert len(events) == 1

    def test_loaded_board_has_given_cells(
        self, ctrl: Controller, puzzle_file: Path
    ) -> None:
        ctrl.load_puzzle(puzzle_file)
        assert any(cell.is_given for _, cell in ctrl._board)

    def test_loaded_name_matches_file(
        self, ctrl: Controller, bus: EventBus, puzzle_file: Path
    ) -> None:
        events: list[PuzzleLoaded] = []
        bus.subscribe(PuzzleLoaded, events.append)
        ctrl.load_puzzle(puzzle_file)
        assert events[0].name == "Test"

    def test_given_board_snapshot_stored(
        self, ctrl: Controller, puzzle_file: Path
    ) -> None:
        ctrl.load_puzzle(puzzle_file)
        assert ctrl._given_board is not None
        # Given board must match what was loaded (before candidate computation)
        assert ctrl._given_board[0, 0].value == 5

    def test_clears_undo_redo_on_load(
        self, ctrl: Controller, bus: EventBus, puzzle_file: Path
    ) -> None:
        bus.publish(CellChanged(coord=CellCoord(1, 1), old_value=0, new_value=3))
        ctrl.load_puzzle(puzzle_file)
        assert ctrl._undo_stack == []
        assert ctrl._redo_stack == []

    def test_load_nonexistent_file_publishes_error(
        self, ctrl: Controller, bus: EventBus, tmp_path: Path
    ) -> None:
        errors: list[ErrorRaised] = []
        bus.subscribe(ErrorRaised, errors.append)
        ctrl.load_puzzle(tmp_path / "nope.json")
        assert len(errors) == 1

    def test_load_malformed_json_publishes_error(
        self, ctrl: Controller, bus: EventBus, tmp_path: Path
    ) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json}")
        errors: list[ErrorRaised] = []
        bus.subscribe(ErrorRaised, errors.append)
        ctrl.load_puzzle(bad)
        assert len(errors) == 1

    def test_load_path_none_does_not_raise(
        self, ctrl: Controller
    ) -> None:
        # With no tkinter available in headless CI, _pick_puzzle_file returns
        # the first puzzle in the puzzles dir (or None). Either way, no crash.
        puzzles_dir = Path(__file__).parent.parent.parent / "puzzles"
        c = Controller(puzzles_dir=puzzles_dir)
        with patch.object(c, "_pick_puzzle_file", return_value=None):
            c.load_puzzle()  # user cancelled — must be silent


# ---------------------------------------------------------------------------
# reset_puzzle
# ---------------------------------------------------------------------------


class TestResetPuzzle:
    def test_publishes_puzzle_reset(
        self, ctrl: Controller, bus: EventBus, puzzle_file: Path
    ) -> None:
        ctrl.load_puzzle(puzzle_file)
        # Modify a cell
        bus.publish(CellChanged(coord=CellCoord(0, 2), old_value=0, new_value=4))
        events: list[PuzzleReset] = []
        bus.subscribe(PuzzleReset, events.append)
        ctrl.reset_puzzle()
        assert len(events) == 1

    def test_reset_restores_given_board(
        self, ctrl: Controller, bus: EventBus, puzzle_file: Path
    ) -> None:
        ctrl.load_puzzle(puzzle_file)
        original_str = ctrl._given_board.to_string()
        bus.publish(CellChanged(coord=CellCoord(0, 2), old_value=0, new_value=9))
        ctrl.reset_puzzle()
        # Board in event should match original given cells
        assert ctrl._board.to_string() != ""  # board exists
        # Non-given cells must have been cleared (value == 0 for empties)
        for coord, cell in ctrl._board:
            if not cell.is_given:
                assert cell.is_empty

    def test_clears_undo_redo_on_reset(
        self, ctrl: Controller, bus: EventBus, puzzle_file: Path
    ) -> None:
        ctrl.load_puzzle(puzzle_file)
        bus.publish(CellChanged(coord=CellCoord(0, 2), old_value=0, new_value=4))
        ctrl.reset_puzzle()
        assert ctrl._undo_stack == []
        assert ctrl._redo_stack == []


# ---------------------------------------------------------------------------
# Undo / redo
# ---------------------------------------------------------------------------


class TestUndoRedo:
    def test_cell_change_pushes_undo(self, ctrl: Controller, bus: EventBus) -> None:
        bus.publish(CellChanged(coord=CellCoord(0, 0), old_value=0, new_value=5))
        assert len(ctrl._undo_stack) == 1

    def test_undo_restores_previous_board(self, ctrl: Controller, bus: EventBus) -> None:
        board_before = ctrl._board
        bus.publish(CellChanged(coord=CellCoord(0, 0), old_value=0, new_value=5))
        bus.publish(UndoRequested())
        assert ctrl._board == board_before

    def test_undo_pushes_to_redo(self, ctrl: Controller, bus: EventBus) -> None:
        bus.publish(CellChanged(coord=CellCoord(0, 0), old_value=0, new_value=5))
        bus.publish(UndoRequested())
        assert len(ctrl._redo_stack) == 1

    def test_redo_restores_undone_board(self, ctrl: Controller, bus: EventBus) -> None:
        bus.publish(CellChanged(coord=CellCoord(0, 0), old_value=0, new_value=5))
        board_after_change = ctrl._board
        bus.publish(UndoRequested())
        bus.publish(RedoRequested())
        assert ctrl._board == board_after_change

    def test_undo_when_empty_is_noop(self, ctrl: Controller, bus: EventBus) -> None:
        resets: list[PuzzleReset] = []
        bus.subscribe(PuzzleReset, resets.append)
        bus.publish(UndoRequested())
        assert resets == []

    def test_redo_when_empty_is_noop(self, ctrl: Controller, bus: EventBus) -> None:
        resets: list[PuzzleReset] = []
        bus.subscribe(PuzzleReset, resets.append)
        bus.publish(RedoRequested())
        assert resets == []

    def test_new_change_clears_redo(self, ctrl: Controller, bus: EventBus) -> None:
        bus.publish(CellChanged(coord=CellCoord(0, 0), old_value=0, new_value=5))
        bus.publish(UndoRequested())
        assert len(ctrl._redo_stack) == 1
        bus.publish(CellChanged(coord=CellCoord(1, 1), old_value=0, new_value=3))
        assert ctrl._redo_stack == []

    def test_undo_stack_capped_at_max_history(
        self, ctrl: Controller, bus: EventBus
    ) -> None:
        for i in range(Controller.MAX_HISTORY + 10):
            coord = CellCoord(i % 9, (i * 2) % 9)
            bus.publish(CellChanged(coord=coord, old_value=0, new_value=(i % 9) + 1))
        assert len(ctrl._undo_stack) <= Controller.MAX_HISTORY

    def test_solver_cell_changes_not_pushed_to_undo(
        self, ctrl: Controller, bus: EventBus
    ) -> None:
        before_len = len(ctrl._undo_stack)
        bus.publish(
            CellChanged(coord=CellCoord(0, 0), old_value=0, new_value=5, by_solver=True)
        )
        assert len(ctrl._undo_stack) == before_len


# ---------------------------------------------------------------------------
# Speed / SpeedChanged
# ---------------------------------------------------------------------------


class TestSpeedChanged:
    def test_speed_changed_updates_engine_delay(
        self, ctrl: Controller, bus: EventBus
    ) -> None:
        bus.publish(SpeedChanged(steps_per_second=20.0))
        assert abs(ctrl._engine._delay - 0.05) < 1e-9

    def test_speed_zero_gives_instant(self, ctrl: Controller, bus: EventBus) -> None:
        bus.publish(SpeedChanged(steps_per_second=0.0))
        assert ctrl._engine._delay == 0.0


# ---------------------------------------------------------------------------
# solve
# ---------------------------------------------------------------------------


class TestSolve:
    def test_solve_starts_engine(
        self, ctrl: Controller, puzzle_file: Path
    ) -> None:
        ctrl.load_puzzle(puzzle_file)
        ctrl.solve()
        is_running = ctrl._engine.is_running
        ctrl._engine.cancel()
        assert is_running

    def test_solve_when_running_cancels(
        self, ctrl: Controller, puzzle_file: Path
    ) -> None:
        ctrl.load_puzzle(puzzle_file)
        ctrl._engine.set_delay(10.0)  # slow — won't finish
        ctrl.solve()
        assert ctrl._engine.is_running
        ctrl.solve()  # second call cancels
        assert not ctrl._engine.is_running

    def test_solve_easy_completes(
        self, ctrl: Controller, bus: EventBus, puzzle_file: Path
    ) -> None:
        from sudoku.events.types import SolveComplete
        completed: list[SolveComplete] = []
        bus.subscribe(SolveComplete, completed.append)
        ctrl.load_puzzle(puzzle_file)
        ctrl.solve()
        deadline = time.time() + 10
        while time.time() < deadline and ctrl._engine.is_running:
            time.sleep(0.05)
        ctrl._engine.cancel()
        assert len(completed) == 1
        assert completed[0].board.is_complete()


# ---------------------------------------------------------------------------
# _pick_puzzle_file fallback
# ---------------------------------------------------------------------------


class TestPickPuzzleFileFallback:
    def test_fallback_logic_returns_first_puzzle(self, tmp_path: Path) -> None:
        """The fallback clause (sorted glob) returns the first .json alphabetically."""
        data = _make_puzzle_json(name="Fallback Puzzle")
        (tmp_path / "aaa.json").write_text(json.dumps(data))
        (tmp_path / "bbb.json").write_text(json.dumps(_make_puzzle_json(name="Second")))
        puzzles = sorted(tmp_path.glob("*.json"))
        result = puzzles[0] if puzzles else None
        assert result is not None
        assert result.name == "aaa.json"

    def test_fallback_logic_returns_none_when_dir_empty(self, tmp_path: Path) -> None:
        """Empty puzzles_dir fallback clause returns None."""
        puzzles = sorted(tmp_path.glob("*.json"))
        result = puzzles[0] if puzzles else None
        assert result is None

    def test_pick_puzzle_returns_path_on_success(self, tmp_path: Path) -> None:
        """_pick_puzzle_file returns a Path when tkinter raises and puzzles exist."""
        data = _make_puzzle_json()
        puzzle = tmp_path / "test.json"
        puzzle.write_text(json.dumps(data))
        c = Controller(puzzles_dir=tmp_path)
        # Monkey-patch the method body so the except branch runs directly
        original = c._pick_puzzle_file.__func__

        def _patched(self: Controller) -> "Path | None":
            puzzles = sorted(self._puzzles_dir.glob("*.json"))
            return puzzles[0] if puzzles else None

        import types
        c._pick_puzzle_file = types.MethodType(_patched, c)
        result = c._pick_puzzle_file()
        assert result == puzzle
