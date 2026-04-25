"""Tests for sudoku.gui.board_widget — BoardWidget logic (no display)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pygame
import pytest

from sudoku.data.board import Board
from sudoku.data.cell import CellCoord
from sudoku.events.bus import EventBus
from sudoku.events.types import (
    CellChanged,
    PuzzleLoaded,
    PuzzleReset,
    SelectionChanged,
    SolveComplete,
    SolveStep,
    ThemeChanged,
)
from sudoku.gui.board_widget import CELL_SIZE, GRID_SIZE, BoardWidget
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
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def pygame_init() -> None:  # type: ignore[return]
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture()
def surface() -> pygame.Surface:
    return pygame.Surface((GRID_SIZE, GRID_SIZE))


@pytest.fixture()
def rect() -> pygame.Rect:
    return pygame.Rect(0, 0, GRID_SIZE, GRID_SIZE)


@pytest.fixture()
def theme_manager() -> ThemeManager:
    return ThemeManager(default="light")


@pytest.fixture()
def bus() -> EventBus:
    return EventBus.get_instance()


@pytest.fixture()
def widget(surface: pygame.Surface, rect: pygame.Rect,
           theme_manager: ThemeManager, bus: EventBus) -> BoardWidget:
    return BoardWidget(surface=surface, rect=rect,
                       theme_manager=theme_manager, bus=bus)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_cell_size(self) -> None:
        assert CELL_SIZE == 64

    def test_grid_size(self) -> None:
        assert GRID_SIZE == CELL_SIZE * 9


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestInit:
    def test_board_is_empty_on_init(self, widget: BoardWidget) -> None:
        for _, cell in widget.board:
            assert not cell.is_filled

    def test_no_selection_on_init(self, widget: BoardWidget) -> None:
        assert widget._selected is None

    def test_solving_flag_false_on_init(self, widget: BoardWidget) -> None:
        assert not widget._solving

    def test_cell_dimensions_match_rect(self, widget: BoardWidget, rect: pygame.Rect) -> None:
        assert widget._cell_w == rect.width // 9
        assert widget._cell_h == rect.height // 9


# ---------------------------------------------------------------------------
# set_board / board property
# ---------------------------------------------------------------------------


class TestSetBoard:
    def test_set_board_updates_board(self, widget: BoardWidget) -> None:
        board = Board.from_string(EASY_GRID_STR)
        widget.set_board(board)
        assert widget.board is board

    def test_set_board_clears_selection(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(3, 3)
        widget.set_board(Board.empty())
        assert widget._selected is None


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------


class TestCoordHelpers:
    def test_pos_to_coord_inside_grid(self, widget: BoardWidget) -> None:
        coord = widget._pos_to_coord((0, 0))
        assert coord == CellCoord(0, 0)

    def test_pos_to_coord_center_cell(self, widget: BoardWidget) -> None:
        cx = CELL_SIZE * 4 + CELL_SIZE // 2
        cy = CELL_SIZE * 4 + CELL_SIZE // 2
        coord = widget._pos_to_coord((cx, cy))
        assert coord == CellCoord(4, 4)

    def test_pos_to_coord_outside_returns_none(self, widget: BoardWidget) -> None:
        coord = widget._pos_to_coord((-1, -1))
        assert coord is None

    def test_pos_to_coord_bottom_right_cell(self, widget: BoardWidget) -> None:
        cx = CELL_SIZE * 8 + CELL_SIZE // 2
        cy = CELL_SIZE * 8 + CELL_SIZE // 2
        coord = widget._pos_to_coord((cx, cy))
        assert coord == CellCoord(8, 8)

    def test_coord_to_rect_origin(self, widget: BoardWidget) -> None:
        r = widget._coord_to_rect(CellCoord(0, 0))
        assert r.left == 0
        assert r.top == 0
        assert r.width == widget._cell_w
        assert r.height == widget._cell_h

    def test_coord_to_rect_bottom_right(self, widget: BoardWidget) -> None:
        r = widget._coord_to_rect(CellCoord(8, 8))
        assert r.left == 8 * widget._cell_w
        assert r.top == 8 * widget._cell_h


# ---------------------------------------------------------------------------
# Mouse click handling
# ---------------------------------------------------------------------------


class TestHandleClick:
    def test_click_inside_selects_cell(self, widget: BoardWidget, bus: EventBus) -> None:
        received: list[SelectionChanged] = []
        bus.subscribe(SelectionChanged, received.append)

        cx = CELL_SIZE // 2
        cy = CELL_SIZE // 2
        consumed = widget._handle_click((cx, cy))

        assert consumed is True
        assert widget._selected == CellCoord(0, 0)
        assert len(received) == 1
        assert received[0].coord == CellCoord(0, 0)

    def test_click_outside_returns_false(self, widget: BoardWidget) -> None:
        consumed = widget._handle_click((-10, -10))
        assert consumed is False
        assert widget._selected is None

    def test_click_publishes_selection_changed(self, widget: BoardWidget, bus: EventBus) -> None:
        events: list[SelectionChanged] = []
        bus.subscribe(SelectionChanged, events.append)
        widget._handle_click((CELL_SIZE * 2 + 5, CELL_SIZE * 3 + 5))
        assert len(events) == 1
        assert events[0].coord == CellCoord(3, 2)


# ---------------------------------------------------------------------------
# Keyboard: digit input
# ---------------------------------------------------------------------------


class TestPlaceDigit:
    def test_place_digit_without_selection_returns_false(self, widget: BoardWidget) -> None:
        assert widget._place_digit(5) is False

    def test_place_digit_on_selected_empty_cell(self, widget: BoardWidget, bus: EventBus) -> None:
        widget._selected = CellCoord(0, 0)
        events: list[CellChanged] = []
        bus.subscribe(CellChanged, events.append)

        result = widget._place_digit(7)

        assert result is True
        assert widget.board[CellCoord(0, 0)].value == 7
        assert len(events) == 1
        assert events[0].new_value == 7
        assert events[0].by_solver is False

    def test_place_digit_zero_clears_cell(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(0, 0)
        widget._place_digit(5)
        widget._place_digit(0)
        assert widget.board[CellCoord(0, 0)].value == 0

    def test_place_same_digit_returns_true_no_event(self, widget: BoardWidget, bus: EventBus) -> None:
        widget._selected = CellCoord(0, 0)
        widget._place_digit(5)

        events: list[CellChanged] = []
        bus.subscribe(CellChanged, events.append)
        result = widget._place_digit(5)  # same value again

        assert result is True
        assert len(events) == 0

    def test_cannot_place_digit_on_given_cell(self, widget: BoardWidget) -> None:
        board = Board.from_string(EASY_GRID_STR)
        widget.set_board(board)
        widget._selected = CellCoord(0, 0)  # cell with given value 5
        result = widget._place_digit(9)
        assert result is False

    def test_cannot_place_digit_while_solving(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(0, 0)
        widget._solving = True
        assert widget._place_digit(5) is False


# ---------------------------------------------------------------------------
# Keyboard: arrow navigation
# ---------------------------------------------------------------------------


class TestMoveSelection:
    def test_no_selection_initialises_to_origin(self, widget: BoardWidget) -> None:
        widget._move_selection(pygame.K_UP)
        assert widget._selected == CellCoord(0, 0)

    def test_move_down(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(0, 0)
        widget._move_selection(pygame.K_DOWN)
        assert widget._selected == CellCoord(1, 0)

    def test_move_right(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(0, 0)
        widget._move_selection(pygame.K_RIGHT)
        assert widget._selected == CellCoord(0, 1)

    def test_move_up(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(4, 4)
        widget._move_selection(pygame.K_UP)
        assert widget._selected == CellCoord(3, 4)

    def test_move_left(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(4, 4)
        widget._move_selection(pygame.K_LEFT)
        assert widget._selected == CellCoord(4, 3)

    def test_clamp_at_top_edge(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(0, 0)
        widget._move_selection(pygame.K_UP)
        assert widget._selected == CellCoord(0, 0)

    def test_clamp_at_bottom_edge(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(8, 8)
        widget._move_selection(pygame.K_DOWN)
        assert widget._selected == CellCoord(8, 8)

    def test_clamp_at_left_edge(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(4, 0)
        widget._move_selection(pygame.K_LEFT)
        assert widget._selected == CellCoord(4, 0)

    def test_clamp_at_right_edge(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(4, 8)
        widget._move_selection(pygame.K_RIGHT)
        assert widget._selected == CellCoord(4, 8)

    def test_move_publishes_selection_changed(self, widget: BoardWidget, bus: EventBus) -> None:
        widget._selected = CellCoord(2, 2)
        events: list[SelectionChanged] = []
        bus.subscribe(SelectionChanged, events.append)
        widget._move_selection(pygame.K_DOWN)
        assert len(events) == 1
        assert events[0].coord == CellCoord(3, 2)


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


class TestEventHandlers:
    def test_on_cell_changed_updates_board(self, widget: BoardWidget) -> None:
        event = CellChanged(coord=CellCoord(1, 1), old_value=0, new_value=3)
        widget._on_cell_changed(event)
        assert widget.board[CellCoord(1, 1)].value == 3

    def test_on_solve_step_sets_solving_flag(self, widget: BoardWidget) -> None:
        board = Board.from_string(EASY_GRID_STR)
        widget.set_board(board)
        event = SolveStep(coord=CellCoord(0, 2), value=4, strategy="naked single", step_index=0)
        widget._on_solve_step(event)
        assert widget._solving is True

    def test_on_solve_step_updates_cell_value(self, widget: BoardWidget) -> None:
        board = Board.from_string(EASY_GRID_STR)
        widget.set_board(board)
        event = SolveStep(coord=CellCoord(0, 2), value=4, strategy="naked single", step_index=0)
        widget._on_solve_step(event)
        assert widget.board[CellCoord(0, 2)].value == 4

    def test_on_solve_complete_clears_solving_flag(self, widget: BoardWidget) -> None:
        widget._solving = True
        solved_board = Board.from_string(EASY_SOLUTION_STR)
        event = SolveComplete(board=solved_board, steps_taken=10, elapsed_ms=5.0)
        widget._on_solve_complete(event)
        assert widget._solving is False

    def test_on_solve_complete_updates_board(self, widget: BoardWidget) -> None:
        solved_board = Board.from_string(EASY_SOLUTION_STR)
        event = SolveComplete(board=solved_board, steps_taken=10, elapsed_ms=5.0)
        widget._on_solve_complete(event)
        assert widget.board is solved_board

    def test_on_puzzle_loaded_sets_board_and_clears_selection(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(2, 2)
        board = Board.from_string(EASY_GRID_STR)
        event = PuzzleLoaded(board=board, name="Easy #001", difficulty="easy")
        widget._on_puzzle_loaded(event)
        assert widget.board is board
        assert widget._selected is None
        assert widget._solving is False

    def test_on_puzzle_reset_sets_board_and_clears_state(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(5, 5)
        widget._solving = True
        board = Board.from_string(EASY_GRID_STR)
        event = PuzzleReset(board=board)
        widget._on_puzzle_reset(event)
        assert widget.board is board
        assert widget._selected is None
        assert widget._solving is False

    def test_on_theme_changed_is_no_op(self, widget: BoardWidget) -> None:
        # ThemeManager.active is read on every draw(); handler should be silent.
        event = ThemeChanged(theme_name="dark")
        widget._on_theme_changed(event)  # must not raise


# ---------------------------------------------------------------------------
# handle_event routing
# ---------------------------------------------------------------------------


class TestHandleEvent:
    def test_mouse_button_down_left_click_consumed(self, widget: BoardWidget) -> None:
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10))
        assert widget.handle_event(event) is True

    def test_mouse_button_right_click_not_consumed(self, widget: BoardWidget) -> None:
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(10, 10))
        assert widget.handle_event(event) is False

    def test_keydown_digit_consumed_when_cell_selected(self, widget: BoardWidget) -> None:
        widget._selected = CellCoord(0, 0)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_5, mod=0, unicode="5")
        assert widget.handle_event(event) is True

    def test_unrelated_event_not_consumed(self, widget: BoardWidget) -> None:
        event = pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0), rel=(0, 0), buttons=(0, 0, 0))
        assert widget.handle_event(event) is False


# ---------------------------------------------------------------------------
# Subscription / unsubscribe
# ---------------------------------------------------------------------------


class TestUnsubscribe:
    def test_unsubscribe_removes_handlers(self, widget: BoardWidget, bus: EventBus) -> None:
        widget.unsubscribe()
        # After unsubscribing, publishing CellChanged should NOT update the board.
        original_board = widget.board
        event = CellChanged(coord=CellCoord(0, 0), old_value=0, new_value=9)
        bus.publish(event)
        assert widget.board is original_board
