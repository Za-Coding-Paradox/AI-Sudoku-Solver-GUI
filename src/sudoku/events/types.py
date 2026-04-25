"""Typed event definitions for the Sudoku Solver event bus.

Every event is a frozen dataclass.  Using dataclasses (rather than plain
dicts or strings) gives us:
  - IDE auto-complete on payload fields
  - mypy type-checking at call sites
  - Immutability (frozen=True) so handlers cannot mutate events

Naming convention
-----------------
Events are named in the past or present tense to describe *what happened*,
not *what should happen next*:
    CellChanged      ← value was changed
    SolveStep        ← solver placed a digit during solving
    SolveComplete    ← puzzle reached a solved state

This separates intent (user pressed Solve) from fact (solver finished).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sudoku.data.board import Board
    from sudoku.data.cell import CellCoord


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Event:
    """Base class for all events.  Never published directly."""


# ---------------------------------------------------------------------------
# Board / cell events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CellChanged(Event):
    """A digit was placed in or cleared from a cell.

    Attributes
    ----------
    coord:
        The (row, col) of the changed cell.
    old_value:
        The digit that was there before (0 = empty).
    new_value:
        The digit placed (0 = cleared).
    by_solver:
        True when the change came from the solver engine, False when it
        came from the user editing manually.
    """

    coord: "CellCoord"
    old_value: int
    new_value: int
    by_solver: bool = False


@dataclass(frozen=True, slots=True)
class CandidatesChanged(Event):
    """The candidate set for a cell was updated (e.g. after constraint propagation).

    Attributes
    ----------
    coord:
        The (row, col) of the affected cell.
    candidates:
        The new candidate set (empty when a digit is placed).
    """

    coord: "CellCoord"
    candidates: frozenset[int]


# ---------------------------------------------------------------------------
# Solver lifecycle events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SolveStarted(Event):
    """The solver has begun working on the current board."""

    board_snapshot: "Board"


@dataclass(frozen=True, slots=True)
class SolveStep(Event):
    """The solver placed a single digit as part of its solve sequence.

    The GUI can listen to these to animate the solve process step-by-step.

    Attributes
    ----------
    coord:
        Where the digit was placed.
    value:
        The digit placed (1-9).
    strategy:
        Human-readable name of the strategy used, e.g. "naked single",
        "backtrack", "AC-3".
    step_index:
        Monotonically increasing step counter (0-based).
    """

    coord: "CellCoord"
    value: int
    strategy: str
    step_index: int


@dataclass(frozen=True, slots=True)
class SolveComplete(Event):
    """The solver found a complete, valid solution.

    Attributes
    ----------
    board:
        The fully solved Board.
    steps_taken:
        Total number of :class:`SolveStep` events emitted.
    elapsed_ms:
        Wall-clock milliseconds taken to solve.
    """

    board: "Board"
    steps_taken: int
    elapsed_ms: float


@dataclass(frozen=True, slots=True)
class SolveFailed(Event):
    """The solver determined the puzzle has no solution.

    Attributes
    ----------
    reason:
        A short human-readable explanation (e.g. "no candidates remain for (3, 7)").
    """

    reason: str


# ---------------------------------------------------------------------------
# Puzzle lifecycle events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PuzzleLoaded(Event):
    """A new puzzle was loaded into the app.

    Attributes
    ----------
    board:
        The freshly-loaded Board (given cells only, solver cells cleared).
    name:
        Display name for the puzzle (e.g. "Easy #001").
    difficulty:
        Difficulty string from the puzzle schema.
    """

    board: "Board"
    name: str
    difficulty: str


@dataclass(frozen=True, slots=True)
class PuzzleReset(Event):
    """The puzzle was reset to its original given-cells-only state.

    Attributes
    ----------
    board:
        The reset Board.
    """

    board: "Board"


# ---------------------------------------------------------------------------
# UI interaction events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UndoRequested(Event):
    """The user requested an undo action."""


@dataclass(frozen=True, slots=True)
class RedoRequested(Event):
    """The user requested a redo action."""


@dataclass(frozen=True, slots=True)
class SelectionChanged(Event):
    """The user moved the selection cursor to a different cell.

    Attributes
    ----------
    coord:
        The newly-selected cell, or None when nothing is selected.
    """

    coord: "CellCoord | None"


@dataclass(frozen=True, slots=True)
class ErrorRaised(Event):
    """A non-fatal error occurred that should be displayed to the user.

    Attributes
    ----------
    message:
        Short, human-readable error message.
    detail:
        Optional longer explanation (e.g. exception traceback) for the log.
    """

    message: str
    detail: str = ""


# ---------------------------------------------------------------------------
# Settings events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ThemeChanged(Event):
    """The user switched the visual theme.

    Attributes
    ----------
    theme_name:
        One of the keys registered in the ThemeManager ("light", "dark", …).
    """

    theme_name: str


@dataclass(frozen=True, slots=True)
class SpeedChanged(Event):
    """The user adjusted the solve animation speed.

    Attributes
    ----------
    steps_per_second:
        How many :class:`SolveStep` events the GUI should apply per second.
        A value of 0 means "instant" (no animation).
    """

    steps_per_second: float
