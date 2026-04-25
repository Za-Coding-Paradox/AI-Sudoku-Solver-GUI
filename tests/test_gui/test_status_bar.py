"""Tests for sudoku.gui.status_bar — StatusBar event-driven message logic."""

from __future__ import annotations

import time
from unittest.mock import patch

import pygame
import pytest

from sudoku.data.board import Board
from sudoku.data.cell import CellCoord
from sudoku.events.bus import EventBus
from sudoku.events.types import (
    ErrorRaised,
    PuzzleLoaded,
    PuzzleReset,
    SelectionChanged,
    SolveComplete,
    SolveFailed,
    SolveStarted,
    SolveStep,
)
from sudoku.gui.status_bar import StatusBar
from sudoku.gui.theme import ThemeManager

EASY_GRID_STR = (
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

EASY_SOLUTION_STR = (
    "534678912"
    "672195348"
    "198342567"
    "859761423"
    "426853791"
    "713924856"
    "961537284"
    "287419635"
    "345286179"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def pygame_init() -> None:  # type: ignore[return]
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture()
def surface() -> pygame.Surface:
    return pygame.Surface((900, 32))


@pytest.fixture()
def status_rect() -> pygame.Rect:
    return pygame.Rect(0, 0, 900, 32)


@pytest.fixture()
def theme_manager() -> ThemeManager:
    return ThemeManager(default="light")


@pytest.fixture()
def bus() -> EventBus:
    return EventBus.get_instance()


@pytest.fixture()
def bar(
    surface: pygame.Surface,
    status_rect: pygame.Rect,
    theme_manager: ThemeManager,
    bus: EventBus,
) -> StatusBar:
    return StatusBar(
        surface=surface,
        rect=status_rect,
        theme_manager=theme_manager,
        bus=bus,
    )


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestStatusBarInit:
    def test_default_message_set(self, bar: StatusBar) -> None:
        assert "Load" in bar._message or "start" in bar._message

    def test_right_message_empty_on_init(self, bar: StatusBar) -> None:
        assert bar._right_message == ""

    def test_step_count_zero_on_init(self, bar: StatusBar) -> None:
        assert bar._step_count == 0


# ---------------------------------------------------------------------------
# PuzzleLoaded
# ---------------------------------------------------------------------------


class TestOnPuzzleLoaded:
    def test_message_contains_name(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_GRID_STR)
        event = PuzzleLoaded(board=board, name="Easy #001", difficulty="easy")
        bar._on_puzzle_loaded(event)
        assert "Easy #001" in bar._message

    def test_message_contains_difficulty(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_GRID_STR)
        event = PuzzleLoaded(board=board, name="Easy #001", difficulty="easy")
        bar._on_puzzle_loaded(event)
        assert "easy" in bar._message

    def test_right_message_cleared(self, bar: StatusBar) -> None:
        bar._right_message = "100 ms"
        board = Board.from_string(EASY_GRID_STR)
        event = PuzzleLoaded(board=board, name="Hard #005", difficulty="hard")
        bar._on_puzzle_loaded(event)
        assert bar._right_message == ""


# ---------------------------------------------------------------------------
# PuzzleReset
# ---------------------------------------------------------------------------


class TestOnPuzzleReset:
    def test_message_indicates_reset(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_GRID_STR)
        event = PuzzleReset(board=board)
        bar._on_puzzle_reset(event)
        assert "reset" in bar._message.lower()

    def test_right_message_cleared(self, bar: StatusBar) -> None:
        bar._right_message = "42 ms"
        board = Board.from_string(EASY_GRID_STR)
        event = PuzzleReset(board=board)
        bar._on_puzzle_reset(event)
        assert bar._right_message == ""


# ---------------------------------------------------------------------------
# SolveStarted
# ---------------------------------------------------------------------------


class TestOnSolveStarted:
    def test_message_indicates_solving(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_GRID_STR)
        event = SolveStarted(board_snapshot=board)
        bar._on_solve_started(event)
        assert "Solving" in bar._message or "solving" in bar._message.lower()

    def test_step_count_reset_to_zero(self, bar: StatusBar) -> None:
        bar._step_count = 50
        board = Board.from_string(EASY_GRID_STR)
        event = SolveStarted(board_snapshot=board)
        bar._on_solve_started(event)
        assert bar._step_count == 0

    def test_right_message_cleared(self, bar: StatusBar) -> None:
        bar._right_message = "old value"
        board = Board.from_string(EASY_GRID_STR)
        event = SolveStarted(board_snapshot=board)
        bar._on_solve_started(event)
        assert bar._right_message == ""


# ---------------------------------------------------------------------------
# SolveStep
# ---------------------------------------------------------------------------


class TestOnSolveStep:
    def test_step_count_increments(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_GRID_STR)
        bar._on_solve_started(SolveStarted(board_snapshot=board))
        for i in range(5):
            event = SolveStep(coord=CellCoord(0, i), value=i + 1,
                              strategy="naked single", step_index=i)
            bar._on_solve_step(event)
        assert bar._step_count == 5

    def test_message_contains_strategy(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_GRID_STR)
        bar._on_solve_started(SolveStarted(board_snapshot=board))
        event = SolveStep(coord=CellCoord(0, 0), value=1,
                          strategy="hidden single", step_index=0)
        bar._on_solve_step(event)
        assert "hidden single" in bar._message

    def test_right_message_shows_elapsed(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_GRID_STR)
        bar._on_solve_started(SolveStarted(board_snapshot=board))
        event = SolveStep(coord=CellCoord(0, 0), value=1,
                          strategy="naked single", step_index=0)
        bar._on_solve_step(event)
        assert "ms" in bar._right_message

    def test_message_contains_step_number(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_GRID_STR)
        bar._on_solve_started(SolveStarted(board_snapshot=board))
        event = SolveStep(coord=CellCoord(0, 0), value=1,
                          strategy="naked single", step_index=2)
        bar._on_solve_step(event)
        assert "3" in bar._message  # step_index + 1


# ---------------------------------------------------------------------------
# SolveComplete
# ---------------------------------------------------------------------------


class TestOnSolveComplete:
    def test_message_indicates_solved(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_SOLUTION_STR)
        event = SolveComplete(board=board, steps_taken=42, elapsed_ms=12.5)
        bar._on_solve_complete(event)
        assert "Solved" in bar._message or "solved" in bar._message.lower()

    def test_message_contains_steps_taken(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_SOLUTION_STR)
        event = SolveComplete(board=board, steps_taken=42, elapsed_ms=12.5)
        bar._on_solve_complete(event)
        assert "42" in bar._message

    def test_message_contains_elapsed(self, bar: StatusBar) -> None:
        board = Board.from_string(EASY_SOLUTION_STR)
        event = SolveComplete(board=board, steps_taken=10, elapsed_ms=8.3)
        bar._on_solve_complete(event)
        assert "8.3" in bar._message

    def test_right_message_cleared(self, bar: StatusBar) -> None:
        bar._right_message = "leftover"
        board = Board.from_string(EASY_SOLUTION_STR)
        event = SolveComplete(board=board, steps_taken=5, elapsed_ms=1.0)
        bar._on_solve_complete(event)
        assert bar._right_message == ""


# ---------------------------------------------------------------------------
# SolveFailed
# ---------------------------------------------------------------------------


class TestOnSolveFailed:
    def test_message_contains_reason(self, bar: StatusBar) -> None:
        event = SolveFailed(reason="no candidates remain for (3, 7)")
        bar._on_solve_failed(event)
        assert "no candidates remain for (3, 7)" in bar._message

    def test_right_message_cleared(self, bar: StatusBar) -> None:
        bar._right_message = "something"
        event = SolveFailed(reason="contradiction")
        bar._on_solve_failed(event)
        assert bar._right_message == ""

    def test_message_shows_failure_indicator(self, bar: StatusBar) -> None:
        event = SolveFailed(reason="unsolvable")
        bar._on_solve_failed(event)
        # The handler prepends "✗" or similar indicator
        assert "✗" in bar._message or "unsolvable" in bar._message


# ---------------------------------------------------------------------------
# SelectionChanged
# ---------------------------------------------------------------------------


class TestOnSelectionChanged:
    def test_message_shows_row_and_col(self, bar: StatusBar) -> None:
        event = SelectionChanged(coord=CellCoord(2, 4))
        bar._on_selection_changed(event)
        # Row 3, col 5 (1-based)
        assert "3" in bar._message
        assert "5" in bar._message

    def test_message_for_origin_cell(self, bar: StatusBar) -> None:
        event = SelectionChanged(coord=CellCoord(0, 0))
        bar._on_selection_changed(event)
        assert "1" in bar._message

    def test_none_coord_does_not_crash(self, bar: StatusBar) -> None:
        # SelectionChanged with None coord should be handled gracefully
        event = SelectionChanged(coord=None)
        # Should not raise
        bar._on_selection_changed(event)


# ---------------------------------------------------------------------------
# ErrorRaised
# ---------------------------------------------------------------------------


class TestOnErrorRaised:
    def test_message_contains_error_text(self, bar: StatusBar) -> None:
        event = ErrorRaised(message="File not found")
        bar._on_error_raised(event)
        assert "File not found" in bar._message

    def test_message_has_warning_indicator(self, bar: StatusBar) -> None:
        event = ErrorRaised(message="Something went wrong")
        bar._on_error_raised(event)
        assert "⚠" in bar._message or "Something went wrong" in bar._message


# ---------------------------------------------------------------------------
# Bus integration — events published on bus reach bar
# ---------------------------------------------------------------------------


class TestBusIntegration:
    def test_puzzle_loaded_via_bus_updates_message(
        self, bar: StatusBar, bus: EventBus
    ) -> None:
        board = Board.from_string(EASY_GRID_STR)
        bus.publish(PuzzleLoaded(board=board, name="Medium #002", difficulty="medium"))
        assert "Medium #002" in bar._message

    def test_solve_failed_via_bus_updates_message(
        self, bar: StatusBar, bus: EventBus
    ) -> None:
        bus.publish(SolveFailed(reason="no solution found"))
        assert "no solution found" in bar._message

    def test_error_raised_via_bus_updates_message(
        self, bar: StatusBar, bus: EventBus
    ) -> None:
        bus.publish(ErrorRaised(message="Disk full"))
        assert "Disk full" in bar._message


# ---------------------------------------------------------------------------
# Unsubscribe
# ---------------------------------------------------------------------------


class TestUnsubscribe:
    def test_unsubscribe_stops_updates(self, bar: StatusBar, bus: EventBus) -> None:
        bar.unsubscribe()
        original_message = bar._message
        board = Board.from_string(EASY_GRID_STR)
        bus.publish(PuzzleLoaded(board=board, name="Should Not Appear", difficulty="easy"))
        assert bar._message == original_message
