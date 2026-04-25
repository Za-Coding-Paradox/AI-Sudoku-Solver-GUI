"""Unit tests for all event type dataclasses."""

from __future__ import annotations

import pytest

from sudoku.data.board import Board
from sudoku.data.cell import CellCoord
from sudoku.events.types import (
    CellChanged,
    CandidatesChanged,
    SolveStarted,
    SolveStep,
    SolveComplete,
    SolveFailed,
    PuzzleLoaded,
    PuzzleReset,
    UndoRequested,
    RedoRequested,
    SelectionChanged,
    ErrorRaised,
    ThemeChanged,
    SpeedChanged,
    Event,
)

COORD = CellCoord(0, 0)


class TestEventDataclasses:
    def test_cell_changed_fields(self) -> None:
        e = CellChanged(coord=COORD, old_value=0, new_value=5)
        assert e.coord == COORD
        assert e.old_value == 0
        assert e.new_value == 5
        assert e.by_solver is False

    def test_cell_changed_by_solver(self) -> None:
        e = CellChanged(coord=COORD, old_value=0, new_value=3, by_solver=True)
        assert e.by_solver is True

    def test_candidates_changed_fields(self) -> None:
        cands = frozenset({1, 2, 3})
        e = CandidatesChanged(coord=COORD, candidates=cands)
        assert e.candidates == cands

    def test_solve_step_fields(self) -> None:
        e = SolveStep(coord=COORD, value=7, strategy="naked single", step_index=42)
        assert e.value == 7
        assert e.strategy == "naked single"
        assert e.step_index == 42

    def test_solve_complete_fields(self) -> None:
        board = Board.empty()
        e = SolveComplete(board=board, steps_taken=100, elapsed_ms=12.5)
        assert e.steps_taken == 100
        assert e.elapsed_ms == pytest.approx(12.5)

    def test_solve_failed_reason(self) -> None:
        e = SolveFailed(reason="no candidates")
        assert "no candidates" in e.reason

    def test_puzzle_loaded_fields(self) -> None:
        board = Board.empty()
        e = PuzzleLoaded(board=board, name="Easy #001", difficulty="easy")
        assert e.name == "Easy #001"
        assert e.difficulty == "easy"

    def test_puzzle_reset_fields(self) -> None:
        board = Board.empty()
        e = PuzzleReset(board=board)
        assert e.board is board

    def test_selection_changed_with_coord(self) -> None:
        e = SelectionChanged(coord=COORD)
        assert e.coord == COORD

    def test_selection_changed_none(self) -> None:
        e = SelectionChanged(coord=None)
        assert e.coord is None

    def test_error_raised_defaults(self) -> None:
        e = ErrorRaised(message="oops")
        assert e.message == "oops"
        assert e.detail == ""

    def test_error_raised_with_detail(self) -> None:
        e = ErrorRaised(message="oops", detail="traceback here")
        assert "traceback" in e.detail

    def test_theme_changed(self) -> None:
        e = ThemeChanged(theme_name="dark")
        assert e.theme_name == "dark"

    def test_speed_changed(self) -> None:
        e = SpeedChanged(steps_per_second=10.0)
        assert e.steps_per_second == pytest.approx(10.0)

    def test_speed_changed_zero_means_instant(self) -> None:
        e = SpeedChanged(steps_per_second=0.0)
        assert e.steps_per_second == 0.0

    def test_undo_requested_is_event(self) -> None:
        assert isinstance(UndoRequested(), Event)

    def test_redo_requested_is_event(self) -> None:
        assert isinstance(RedoRequested(), Event)


class TestEventImmutability:
    def test_cell_changed_is_frozen(self) -> None:
        e = CellChanged(coord=COORD, old_value=0, new_value=5)
        with pytest.raises((AttributeError, TypeError)):
            e.new_value = 9  # type: ignore[misc]

    def test_solve_step_is_frozen(self) -> None:
        e = SolveStep(coord=COORD, value=1, strategy="backtrack", step_index=0)
        with pytest.raises((AttributeError, TypeError)):
            e.value = 2  # type: ignore[misc]


class TestEventIsBaseClass:
    def test_all_events_inherit_from_event(self) -> None:
        events = [
            CellChanged(coord=COORD, old_value=0, new_value=1),
            CandidatesChanged(coord=COORD, candidates=frozenset()),
            SolveStep(coord=COORD, value=1, strategy="x", step_index=0),
            SolveFailed(reason="x"),
            PuzzleLoaded(board=Board.empty(), name="x", difficulty="easy"),
            PuzzleReset(board=Board.empty()),
            UndoRequested(),
            RedoRequested(),
            SelectionChanged(coord=None),
            ErrorRaised(message="x"),
            ThemeChanged(theme_name="light"),
            SpeedChanged(steps_per_second=5.0),
        ]
        for e in events:
            assert isinstance(e, Event), f"{type(e)} is not a subclass of Event"
