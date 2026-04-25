"""Shared pytest fixtures for the Sudoku Solver test suite."""

from __future__ import annotations

import pytest

from sudoku.data.board import Board
from sudoku.data.cell import Cell, CellCoord
from sudoku.events.bus import EventBus

# ---------------------------------------------------------------------------
# Canonical puzzle strings used across multiple test modules
# ---------------------------------------------------------------------------

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

EMPTY_GRID_STR = "0" * 81

# A board with a deliberate row conflict (two 5s in row 0)
CONFLICT_GRID_STR = (
    "550070000"
    "600195000"
    "098000060"
    "800060003"
    "400803001"
    "700020006"
    "060000280"
    "000419005"
    "000080079"
)


# ---------------------------------------------------------------------------
# Board fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_board() -> Board:
    """A completely blank 9×9 board."""
    return Board.empty()


@pytest.fixture()
def easy_board() -> Board:
    """The well-known 'Easy #001' puzzle board (given cells only)."""
    return Board.from_string(EASY_GRID_STR)


@pytest.fixture()
def easy_solution() -> Board:
    """The solved form of the Easy #001 puzzle."""
    return Board.from_string(EASY_SOLUTION_STR)


@pytest.fixture()
def conflict_board() -> Board:
    """A board that contains a deliberate row conflict (two 5s in row 0)."""
    return Board.from_string(CONFLICT_GRID_STR)


@pytest.fixture()
def solved_board() -> Board:
    """A completely filled, valid board (used to test is_complete / validate)."""
    return Board.from_string(EASY_SOLUTION_STR)


# ---------------------------------------------------------------------------
# EventBus fixture — reset singleton between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_event_bus() -> None:  # type: ignore[return]
    """Ensure every test starts with a fresh EventBus singleton."""
    EventBus.reset()
    yield
    EventBus.reset()


@pytest.fixture()
def bus() -> EventBus:
    """A fresh EventBus instance for the current test."""
    return EventBus.get_instance()


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def origin() -> CellCoord:
    return CellCoord(0, 0)


@pytest.fixture()
def center() -> CellCoord:
    return CellCoord(4, 4)
