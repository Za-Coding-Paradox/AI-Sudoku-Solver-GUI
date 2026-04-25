"""Board — the 9×9 Sudoku grid.

The Board is an immutable value object.  Every mutation returns a *new*
Board, making it trivial to implement undo/redo by storing Board snapshots.

All constraint helpers (peers, row_values, col_values, box_values) operate
purely on the data without touching any GUI or I/O layer.
"""

from __future__ import annotations

import copy
from typing import Iterator, Sequence

from sudoku.data.cell import Cell, CellCoord

# A raw grid is a 9×9 list of ints (0 = empty, 1-9 = digit).
RawGrid = list[list[int]]

# 81-character string representation (row-major, '.' for empty).
GridString = str


class Board:
    """Immutable 9×9 grid of :class:`Cell` objects.

    Internally the grid is stored as a tuple-of-tuples so that Board
    instances are naturally hashable and can be used as dict keys or
    placed in sets (useful for the solver's visited-state detection).

    Usage
    -----
    >>> b = Board.from_string("5.....3.." + "." * 72)
    >>> b[0, 0].value
    5
    >>> b2 = b.set_cell(CellCoord(0, 1), b[0, 1].with_value(7))
    >>> b2[0, 1].value
    7
    >>> b[0, 1].value   # original unchanged
    0
    """

    SIZE: int = 9
    BOX_SIZE: int = 3

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, grid: tuple[tuple[Cell, ...], ...]) -> None:
        if len(grid) != self.SIZE or any(len(row) != self.SIZE for row in grid):
            raise ValueError("Board grid must be exactly 9×9.")
        self._grid = grid

    @classmethod
    def empty(cls) -> "Board":
        """Return a completely blank, all-candidates board."""
        row = tuple(Cell.empty() for _ in range(cls.SIZE))
        return cls(tuple(row for _ in range(cls.SIZE)))

    @classmethod
    def from_raw(cls, raw: RawGrid, *, given_mask: list[list[bool]] | None = None) -> "Board":
        """Build a Board from a 9×9 list-of-lists of ints.

        Parameters
        ----------
        raw:
            9×9 grid.  0 or None means empty.  1-9 are digits.
        given_mask:
            Optional explicit mask.  When None, any non-zero cell is
            treated as a given clue.
        """
        rows: list[tuple[Cell, ...]] = []
        for r in range(cls.SIZE):
            cells: list[Cell] = []
            for c in range(cls.SIZE):
                digit = int(raw[r][c])
                if given_mask is not None:
                    is_given = bool(given_mask[r][c])
                else:
                    is_given = digit != 0
                if digit == 0:
                    cells.append(Cell.empty())
                else:
                    cells.append(Cell.given(digit) if is_given else Cell.empty().with_value(digit))
            rows.append(tuple(cells))
        return cls(tuple(rows))

    @classmethod
    def from_string(cls, s: str) -> "Board":
        """Parse an 81-character string ('.' or '0' = empty, '1'-'9' = digit).

        Whitespace is ignored, so multi-line strings work fine.
        """
        digits = [ch for ch in s if ch in "0123456789."]
        if len(digits) != 81:
            raise ValueError(f"Expected 81 cells, got {len(digits)} from {s!r}")
        raw: RawGrid = []
        for r in range(cls.SIZE):
            row: list[int] = []
            for c in range(cls.SIZE):
                ch = digits[r * cls.SIZE + c]
                row.append(0 if ch in ".0" else int(ch))
            raw.append(row)
        return cls.from_raw(raw)

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def __getitem__(self, coord: tuple[int, int] | CellCoord) -> Cell:
        r, c = coord
        return self._grid[r][c]

    def __iter__(self) -> Iterator[tuple[CellCoord, Cell]]:
        """Yield (CellCoord, Cell) pairs in row-major order."""
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                yield CellCoord(r, c), self._grid[r][c]

    def rows(self) -> Iterator[tuple[Cell, ...]]:
        """Yield each row as a tuple of Cells."""
        yield from self._grid

    def empty_coords(self) -> list[CellCoord]:
        """Return all coordinates with no digit placed, in row-major order."""
        return [coord for coord, cell in self if cell.is_empty]

    def is_complete(self) -> bool:
        """True when every cell has a digit placed."""
        return all(cell.is_filled for _, cell in self)

    # ------------------------------------------------------------------
    # Mutation (returns new Board)
    # ------------------------------------------------------------------

    def set_cell(self, coord: CellCoord, cell: Cell) -> "Board":
        """Return a new Board with *cell* placed at *coord*."""
        rows = list(list(row) for row in self._grid)
        rows[coord.row][coord.col] = cell
        return Board(tuple(tuple(row) for row in rows))

    def set_value(self, coord: CellCoord, digit: int) -> "Board":
        """Shorthand: place *digit* at *coord* without changing other flags."""
        new_cell = self[coord].with_value(digit)
        return self.set_cell(coord, new_cell)

    # ------------------------------------------------------------------
    # Constraint helpers
    # ------------------------------------------------------------------

    def row_values(self, row: int) -> frozenset[int]:
        """Return all non-zero digits placed in *row*."""
        return frozenset(cell.value for cell in self._grid[row] if cell.is_filled)

    def col_values(self, col: int) -> frozenset[int]:
        """Return all non-zero digits placed in column *col*."""
        return frozenset(self._grid[r][col].value for r in range(self.SIZE) if self._grid[r][col].is_filled)

    def box_values(self, box: int) -> frozenset[int]:
        """Return all non-zero digits placed in 3×3 box *box* (0-8, row-major)."""
        br, bc = divmod(box, self.BOX_SIZE)
        values: set[int] = set()
        for r in range(br * 3, br * 3 + 3):
            for c in range(bc * 3, bc * 3 + 3):
                cell = self._grid[r][c]
                if cell.is_filled:
                    values.add(cell.value)
        return frozenset(values)

    def peers(self, coord: CellCoord) -> frozenset[CellCoord]:
        """Return all 20 peer coordinates (same row, col, or box)."""
        r, c = coord
        box = coord.box
        br, bc = divmod(box, self.BOX_SIZE)
        result: set[CellCoord] = set()
        for i in range(self.SIZE):
            result.add(CellCoord(r, i))  # same row
            result.add(CellCoord(i, c))  # same col
        for dr in range(3):
            for dc in range(3):
                result.add(CellCoord(br * 3 + dr, bc * 3 + dc))  # same box
        result.discard(coord)
        return frozenset(result)

    def candidates_for(self, coord: CellCoord) -> frozenset[int]:
        """Compute legal candidates for *coord* from the current board state."""
        if self[coord].is_filled:
            return frozenset()
        used = self.row_values(coord.row) | self.col_values(coord.col) | self.box_values(coord.box)
        return frozenset(range(1, 10)) - used

    def with_candidates_computed(self) -> "Board":
        """Return a new Board with every empty cell's candidate set refreshed."""
        rows = [list(row) for row in self._grid]
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                coord = CellCoord(r, c)
                cell = self._grid[r][c]
                if cell.is_empty:
                    rows[r][c] = cell.with_candidates(self.candidates_for(coord))
        return Board(tuple(tuple(row) for row in rows))

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_raw(self) -> RawGrid:
        """Return the board as a 9×9 list-of-lists of ints."""
        return [[self._grid[r][c].value for c in range(self.SIZE)] for r in range(self.SIZE)]

    def to_string(self) -> GridString:
        """Return the board as an 81-character string ('.' for empty)."""
        chars: list[str] = []
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                v = self._grid[r][c].value
                chars.append("0" if v == 0 else str(v))
        return "".join(chars)

    def given_mask(self) -> list[list[bool]]:
        """Return a 9×9 bool grid — True where is_given."""
        return [[self._grid[r][c].is_given for c in range(self.SIZE)] for r in range(self.SIZE)]

    # ------------------------------------------------------------------
    # Copy / hash
    # ------------------------------------------------------------------

    def copy(self) -> "Board":
        return Board(copy.deepcopy(self._grid))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Board):
            return NotImplemented
        return self._grid == other._grid

    def __hash__(self) -> int:
        return hash(self._grid)

    # ------------------------------------------------------------------
    # Pretty-print
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Board({self.to_string()!r})"

    def __str__(self) -> str:
        lines: list[str] = []
        for r in range(self.SIZE):
            if r % 3 == 0 and r != 0:
                lines.append("------+-------+------")
            row_parts: list[str] = []
            for c in range(self.SIZE):
                if c % 3 == 0 and c != 0:
                    row_parts.append("|")
                row_parts.append(str(self._grid[r][c]))
            lines.append(" ".join(row_parts))
        return "\n".join(lines)
