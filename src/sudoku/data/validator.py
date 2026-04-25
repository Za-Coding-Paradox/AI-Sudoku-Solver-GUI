"""Validator — pure Sudoku rule checker.

Runs three checks: row uniqueness, column uniqueness, and box uniqueness.
Returns a :class:`ValidationResult` that annotates every conflicting cell,
so the GUI can highlight them in red without doing any rule logic itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sudoku.data.board import Board
from sudoku.data.cell import CellCoord


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """The outcome of running :meth:`Validator.validate` on a Board.

    Attributes
    ----------
    is_valid:
        True only when the board has no conflicts AND is complete.
    has_conflicts:
        True when at least one cell conflicts with a peer.
    is_complete:
        True when every cell has a digit (independent of validity).
    conflict_coords:
        Set of coordinates whose values conflict with a peer.
    """

    is_valid: bool
    has_conflicts: bool
    is_complete: bool
    conflict_coords: frozenset[CellCoord] = field(default_factory=frozenset)

    @property
    def is_solved(self) -> bool:
        """True when complete AND conflict-free."""
        return self.is_complete and not self.has_conflicts


class Validator:
    """Stateless Sudoku rules engine."""

    SIZE: int = 9

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def validate(cls, board: Board) -> ValidationResult:
        """Run all constraint checks on *board* and return a result."""
        conflicts: set[CellCoord] = set()

        for group in cls._all_groups():
            cls._find_conflicts_in_group(board, group, conflicts)

        is_complete = board.is_complete()
        has_conflicts = bool(conflicts)
        is_valid = is_complete and not has_conflicts

        return ValidationResult(
            is_valid=is_valid,
            has_conflicts=has_conflicts,
            is_complete=is_complete,
            conflict_coords=frozenset(conflicts),
        )

    @classmethod
    def annotate(cls, board: Board) -> Board:
        """Return a new Board where every conflicting cell has is_valid=False."""
        result = cls.validate(board)
        updated = board
        for coord, cell in board:
            is_valid = coord not in result.conflict_coords
            if cell.is_valid != is_valid:
                updated = updated.set_cell(coord, cell.with_validity(is_valid))
        return updated

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    def _all_groups(cls) -> list[list[CellCoord]]:
        """Yield lists of 9 CellCoords — one per row, col, and box."""
        groups: list[list[CellCoord]] = []

        # Rows
        for r in range(cls.SIZE):
            groups.append([CellCoord(r, c) for c in range(cls.SIZE)])

        # Columns
        for c in range(cls.SIZE):
            groups.append([CellCoord(r, c) for r in range(cls.SIZE)])

        # 3×3 Boxes
        for br in range(3):
            for bc in range(3):
                groups.append(
                    [
                        CellCoord(br * 3 + dr, bc * 3 + dc)
                        for dr in range(3)
                        for dc in range(3)
                    ]
                )

        return groups

    @classmethod
    def _find_conflicts_in_group(
        cls,
        board: Board,
        group: list[CellCoord],
        conflicts: set[CellCoord],
    ) -> None:
        """Add any conflicting coordinates from *group* into *conflicts*."""
        seen: dict[int, CellCoord] = {}
        for coord in group:
            cell = board[coord]
            if cell.is_empty:
                continue
            if cell.value in seen:
                # Both the first occurrence and the current one conflict.
                conflicts.add(seen[cell.value])
                conflicts.add(coord)
            else:
                seen[cell.value] = coord
