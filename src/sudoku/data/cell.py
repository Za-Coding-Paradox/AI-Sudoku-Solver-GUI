"""Cell — the atomic unit of a Sudoku board.

A Cell is a pure value object: it holds a digit (1-9, or 0 for empty),
flags that describe its state, and a frozenset of candidate digits computed
by constraint propagation.  No GUI, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import NamedTuple


class CellCoord(NamedTuple):
    """Zero-based (row, col) coordinate on a 9×9 board."""

    row: int
    col: int

    @property
    def box(self) -> int:
        """Return the 0-based 3×3 box index (row-major, 0-8)."""
        return (self.row // 3) * 3 + (self.col // 3)

    def __repr__(self) -> str:
        return f"CellCoord(row={self.row}, col={self.col})"


@dataclass(frozen=True, slots=True)
class Cell:
    """Immutable value object representing a single Sudoku cell.

    Attributes
    ----------
    value:
        The digit placed in the cell. 0 means the cell is empty.
    is_given:
        True when this cell was part of the original puzzle clue and must
        not be modified by the solver or the user.
    is_valid:
        False when the cell's value conflicts with another cell in the same
        row, column, or 3×3 box.  Always True for empty cells.
    is_highlighted:
        Transient UI flag — set by the GUI when the cell should be visually
        emphasised (e.g. selected, hinted, or currently being solved).
    candidates:
        The set of digits (1-9) that could legally occupy this cell given
        the current board state.  Empty when `value` is non-zero.
    """

    value: int = 0
    is_given: bool = False
    is_valid: bool = True
    is_highlighted: bool = False
    candidates: frozenset[int] = field(default_factory=frozenset)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def empty(cls) -> "Cell":
        """Return a blank, mutable, fully-candidated cell."""
        return cls(
            value=0,
            is_given=False,
            is_valid=True,
            is_highlighted=False,
            candidates=frozenset(range(1, 10)),
        )

    @classmethod
    def given(cls, digit: int) -> "Cell":
        """Return a pre-filled, locked clue cell."""
        if not (1 <= digit <= 9):
            raise ValueError(f"Clue digit must be 1-9, got {digit!r}")
        return cls(
            value=digit,
            is_given=True,
            is_valid=True,
            is_highlighted=False,
            candidates=frozenset(),
        )

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        """True when no digit has been placed."""
        return self.value == 0

    @property
    def is_filled(self) -> bool:
        """True when a digit has been placed."""
        return self.value != 0

    # ------------------------------------------------------------------
    # Mutation helpers (return new Cell — immutable style)
    # ------------------------------------------------------------------

    def with_value(self, digit: int) -> "Cell":
        """Return a copy of this cell with *digit* placed (0 = clear)."""
        if digit != 0 and not (1 <= digit <= 9):
            raise ValueError(f"Digit must be 0-9, got {digit!r}")
        return replace(self, value=digit, candidates=frozenset() if digit else self.candidates)

    def with_candidates(self, candidates: frozenset[int]) -> "Cell":
        """Return a copy with an updated candidate set."""
        return replace(self, candidates=candidates)

    def with_validity(self, valid: bool) -> "Cell":
        """Return a copy with `is_valid` set."""
        return replace(self, is_valid=valid)

    def with_highlight(self, highlighted: bool) -> "Cell":
        """Return a copy with `is_highlighted` set."""
        return replace(self, is_highlighted=highlighted)

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        if self.is_empty:
            return "."
        marker = "!" if not self.is_valid else ("*" if self.is_given else "")
        return f"{self.value}{marker}"
