"""Solving strategies — pure functions that operate on Board.

Each strategy is a stateless class with a single ``apply`` classmethod.
They never touch the GUI or the EventBus directly; instead they yield
:class:`SolveStep` records that the engine can emit as events.

Strategy pipeline (applied in order)
--------------------------------------
1. NakedSingles  — fill cells where only one candidate remains
2. AC3           — arc-consistency constraint propagation
3. Backtracker   — recursive backtracking (guaranteed to find a solution
                   if one exists, used when the above two get stuck)
"""

from __future__ import annotations

import copy
from collections import deque
from dataclasses import dataclass
from typing import Generator, Iterator

from sudoku.data.board import Board
from sudoku.data.cell import CellCoord


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SolveStep:
    """A single placement emitted by a strategy.

    Attributes
    ----------
    coord:      Where the digit was placed.
    value:      The digit placed (1-9).
    strategy:   Human-readable name, e.g. "naked single", "AC-3", "backtrack".
    """

    coord: CellCoord
    value: int
    strategy: str


@dataclass(frozen=True, slots=True)
class SolveResult:
    """The final outcome returned by :class:`SolverEngine`.

    Attributes
    ----------
    solved:       True when the board is completely and correctly filled.
    board:        The board in its final state (solved or best partial).
    steps:        Every SolveStep that was applied, in order.
    failed:       True when no solution exists.
    fail_reason:  Human-readable explanation when failed=True.
    """

    solved: bool
    board: Board
    steps: list[SolveStep]
    failed: bool = False
    fail_reason: str = ""


# ---------------------------------------------------------------------------
# Strategy 1 — Naked Singles
# ---------------------------------------------------------------------------


class NakedSingles:
    """Fill every cell that has exactly one remaining candidate.

    This is the cheapest strategy and eliminates the majority of cells in
    easy/medium puzzles without any search.
    """

    NAME = "naked single"

    @classmethod
    def apply(cls, board: Board) -> Generator[tuple[Board, SolveStep], None, None]:
        """Repeatedly scan for naked singles, yielding (new_board, step) pairs.

        Yields until no more naked singles exist.
        """
        changed = True
        while changed:
            changed = False
            board = board.with_candidates_computed()
            for coord, cell in board:
                if cell.is_empty and len(cell.candidates) == 1:
                    (digit,) = cell.candidates
                    board = board.set_value(coord, digit)
                    step = SolveStep(coord=coord, value=digit, strategy=cls.NAME)
                    yield board, step
                    changed = True
                    # Recompute from the top after any placement.
                    break


# ---------------------------------------------------------------------------
# Strategy 2 — AC-3 (Arc Consistency Algorithm #3)
# ---------------------------------------------------------------------------


class AC3:
    """Constraint propagation via the AC-3 arc-consistency algorithm.

    Reduces candidate sets across the board by enforcing that for every arc
    (Xi → Xj), there exists at least one value in Xi's domain consistent with
    some value in Xj's domain.

    Yields SolveStep whenever it manages to resolve a cell to a single value
    as a result of propagation.
    """

    NAME = "AC-3"

    @classmethod
    def apply(cls, board: Board) -> Generator[tuple[Board, SolveStep], None, None]:
        """Run AC-3 on *board*, yielding (new_board, step) for each placement."""
        board = board.with_candidates_computed()
        board, steps = cls._propagate(board)
        for step in steps:
            yield board, step

    @classmethod
    def propagate_only(cls, board: Board) -> Board:
        """Run AC-3 and return the updated board without yielding steps.

        Used by the backtracker after each assignment.
        """
        board = board.with_candidates_computed()
        board, _ = cls._propagate(board)
        return board

    @classmethod
    def _propagate(cls, board: Board) -> tuple[Board, list[SolveStep]]:
        """Core AC-3 loop.  Returns (updated_board, steps_applied)."""
        steps: list[SolveStep] = []

        # Build initial arc queue: every (empty_cell, peer) pair.
        queue: deque[tuple[CellCoord, CellCoord]] = deque()
        for coord, cell in board:
            if cell.is_empty:
                for peer in board.peers(coord):
                    queue.append((coord, peer))

        while queue:
            xi, xj = queue.popleft()
            cell_i = board[xi]
            cell_j = board[xj]

            if cell_i.is_filled:
                continue

            # Remove from xi's candidates any value that xj already holds.
            if cell_j.is_filled and cell_j.value in cell_i.candidates:
                new_cands = cell_i.candidates - {cell_j.value}
                if not new_cands:
                    # Domain wipe-out — no solution on this path.
                    return board, steps
                board = board.set_cell(xi, cell_i.with_candidates(new_cands))
                cell_i = board[xi]

                if len(new_cands) == 1:
                    # Resolved to a single value.
                    (digit,) = new_cands
                    board = board.set_value(xi, digit)
                    steps.append(SolveStep(coord=xi, value=digit, strategy=cls.NAME))
                    # Propagate from xi's peers.
                    for peer in board.peers(xi):
                        if board[peer].is_empty:
                            queue.append((peer, xi))

        return board, steps

    @classmethod
    def is_consistent(cls, board: Board) -> bool:
        """Return False if any empty cell has zero candidates (dead end)."""
        board = board.with_candidates_computed()
        for _, cell in board:
            if cell.is_empty and not cell.candidates:
                return False
        return True


# ---------------------------------------------------------------------------
# Strategy 3 — Backtracking
# ---------------------------------------------------------------------------


class Backtracker:
    """Recursive backtracking with MRV (Minimum Remaining Values) heuristic.

    Picks the empty cell with the fewest candidates first ("fail-first"),
    tries each candidate in order, propagates via AC-3 after each assignment,
    and backtracks on dead ends.

    Yields SolveStep for every successful placement (not for backtracks).
    """

    NAME = "backtrack"

    @classmethod
    def apply(cls, board: Board) -> Generator[tuple[Board, SolveStep], None, Board | None]:
        """Solve *board* via backtracking.

        Yields (new_board, step) for every digit placed.
        Returns the solved Board (via StopIteration.value) or None if unsolvable.
        """
        result = yield from cls._solve(board)
        return result

    @classmethod
    def _solve(
        cls, board: Board
    ) -> Generator[tuple[Board, SolveStep], None, Board | None]:
        board = board.with_candidates_computed()

        if board.is_complete():
            return board

        # MRV: pick the empty cell with the fewest candidates.
        coord = cls._mrv(board)
        if coord is None:
            return None

        cell = board[coord]
        if not cell.candidates:
            return None  # dead end

        for digit in sorted(cell.candidates):
            candidate_board = board.set_value(coord, digit)
            step = SolveStep(coord=coord, value=digit, strategy=cls.NAME)

            # Propagate constraints.
            propagated = AC3.propagate_only(candidate_board)

            if not AC3.is_consistent(propagated):
                continue  # backtrack

            yield propagated, step

            result = yield from cls._solve(propagated)
            if result is not None:
                return result

        return None

    @classmethod
    def _mrv(cls, board: Board) -> CellCoord | None:
        """Return the empty cell with the fewest candidates (MRV heuristic)."""
        best_coord: CellCoord | None = None
        best_count = 10  # more than max (9)

        for coord, cell in board:
            if cell.is_empty:
                count = len(cell.candidates)
                if count < best_count:
                    best_count = count
                    best_coord = coord
                    if count == 1:
                        break  # can't do better

        return best_coord
