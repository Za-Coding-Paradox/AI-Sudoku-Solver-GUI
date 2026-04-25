"""Unit tests for :class:`sudoku.data.board.Board`."""

from __future__ import annotations

import pytest

from sudoku.data.board import Board
from sudoku.data.cell import Cell, CellCoord


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

SOLUTION_STR = (
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
# Construction
# ---------------------------------------------------------------------------


class TestBoardConstruction:
    def test_empty_board_all_zero(self) -> None:
        b = Board.empty()
        for _, cell in b:
            assert cell.value == 0

    def test_from_string_length_81(self) -> None:
        b = Board.from_string(EASY_STR)
        count = sum(1 for _ in b)
        assert count == 81

    def test_from_string_parses_givens(self) -> None:
        b = Board.from_string(EASY_STR)
        assert b[0, 0].value == 5
        assert b[0, 0].is_given

    def test_from_string_parses_empty(self) -> None:
        b = Board.from_string(EASY_STR)
        assert b[0, 2].value == 0  # position 2 in "530..." is 0
        assert b[0, 2].is_empty

    def test_from_string_dot_notation(self) -> None:
        s = "." * 81
        b = Board.from_string(s)
        assert all(cell.is_empty for _, cell in b)

    def test_from_string_whitespace_ignored(self) -> None:
        multiline = "\n".join(EASY_STR[i * 9:(i + 1) * 9] for i in range(9))
        b = Board.from_string(multiline)
        assert b[0, 0].value == 5

    def test_from_string_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError):
            Board.from_string("123")

    def test_from_raw(self) -> None:
        raw = [[0] * 9 for _ in range(9)]
        raw[0][0] = 5
        b = Board.from_raw(raw)
        assert b[0, 0].value == 5
        assert b[0, 0].is_given  # non-zero → given by default

    def test_invalid_size_raises(self) -> None:
        with pytest.raises(ValueError):
            Board(tuple())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Access
# ---------------------------------------------------------------------------


class TestBoardAccess:
    def test_getitem_tuple(self) -> None:
        b = Board.from_string(EASY_STR)
        cell = b[0, 0]
        assert isinstance(cell, Cell)

    def test_getitem_coord(self) -> None:
        b = Board.from_string(EASY_STR)
        cell = b[CellCoord(0, 0)]
        assert cell.value == 5

    def test_iteration_yields_81_pairs(self) -> None:
        b = Board.empty()
        pairs = list(b)
        assert len(pairs) == 81
        assert all(isinstance(coord, CellCoord) for coord, _ in pairs)

    def test_rows_yields_9_rows(self) -> None:
        b = Board.empty()
        rows = list(b.rows())
        assert len(rows) == 9

    def test_empty_coords(self) -> None:
        b = Board.from_string(EASY_STR)
        empty = b.empty_coords()
        assert all(b[c].is_empty for c in empty)

    def test_is_complete_false_for_partial(self) -> None:
        b = Board.from_string(EASY_STR)
        assert not b.is_complete()

    def test_is_complete_true_for_solution(self) -> None:
        b = Board.from_string(SOLUTION_STR)
        assert b.is_complete()


# ---------------------------------------------------------------------------
# Mutation (immutable style)
# ---------------------------------------------------------------------------


class TestBoardMutation:
    def test_set_value_returns_new_board(self) -> None:
        b = Board.empty()
        b2 = b.set_value(CellCoord(0, 0), 5)
        assert b2[0, 0].value == 5
        assert b[0, 0].value == 0  # original unchanged

    def test_set_cell_returns_new_board(self) -> None:
        b = Board.empty()
        new_cell = Cell.given(9)
        b2 = b.set_cell(CellCoord(4, 4), new_cell)
        assert b2[4, 4].is_given
        assert not b[4, 4].is_given

    def test_chain_mutations(self) -> None:
        b = Board.empty()
        b2 = b.set_value(CellCoord(0, 0), 1).set_value(CellCoord(0, 1), 2)
        assert b2[0, 0].value == 1
        assert b2[0, 1].value == 2


# ---------------------------------------------------------------------------
# Constraint helpers
# ---------------------------------------------------------------------------


class TestConstraintHelpers:
    def test_row_values(self) -> None:
        b = Board.from_string(EASY_STR)
        # Row 0: "530070000" → values 5,3,7
        vals = b.row_values(0)
        assert 5 in vals and 3 in vals and 7 in vals
        assert 0 not in vals

    def test_col_values(self) -> None:
        b = Board.from_string(EASY_STR)
        vals = b.col_values(0)
        assert 5 in vals  # row 0, col 0 = 5

    def test_box_values(self) -> None:
        b = Board.from_string(EASY_STR)
        # Box 0 (top-left 3×3): 5,3,0,6,0,0,0,9,8 → {5,3,6,9,8}
        vals = b.box_values(0)
        assert vals == {5, 3, 6, 9, 8}

    def test_peers_count(self) -> None:
        b = Board.empty()
        peers = b.peers(CellCoord(0, 0))
        assert len(peers) == 20  # 8 row + 8 col + 8 box - overlaps = 20

    def test_peers_do_not_include_self(self) -> None:
        coord = CellCoord(4, 4)
        b = Board.empty()
        assert coord not in b.peers(coord)

    def test_candidates_for_empty_cell(self) -> None:
        b = Board.from_string(EASY_STR)
        # Cell (0, 2) is empty; row 0 has 5,3,7 → candidates exclude those
        cands = b.candidates_for(CellCoord(0, 2))
        assert 5 not in cands
        assert 3 not in cands
        assert 7 not in cands
        assert all(1 <= v <= 9 for v in cands)

    def test_candidates_for_filled_cell_is_empty(self) -> None:
        b = Board.from_string(EASY_STR)
        assert b.candidates_for(CellCoord(0, 0)) == frozenset()

    def test_with_candidates_computed(self) -> None:
        b = Board.from_string(EASY_STR).with_candidates_computed()
        for coord, cell in b:
            if cell.is_empty:
                assert cell.candidates  # at least one candidate
            else:
                assert cell.candidates == frozenset()


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------


class TestBoardSerialisation:
    def test_to_string_round_trip(self) -> None:
        b = Board.from_string(EASY_STR)
        assert b.to_string() == EASY_STR

    def test_to_raw_shape(self) -> None:
        b = Board.from_string(EASY_STR)
        raw = b.to_raw()
        assert len(raw) == 9
        assert all(len(row) == 9 for row in raw)

    def test_given_mask_correct(self) -> None:
        b = Board.from_string(EASY_STR)
        mask = b.given_mask()
        assert mask[0][0] is True   # 5 is a given
        assert mask[0][2] is False  # 0 is empty, not given

    def test_repr_contains_string(self) -> None:
        b = Board.from_string(EASY_STR)
        assert EASY_STR in repr(b)


# ---------------------------------------------------------------------------
# Equality / hash
# ---------------------------------------------------------------------------


class TestBoardEquality:
    def test_equal_boards(self) -> None:
        b1 = Board.from_string(EASY_STR)
        b2 = Board.from_string(EASY_STR)
        assert b1 == b2

    def test_different_boards_not_equal(self) -> None:
        b1 = Board.from_string(EASY_STR)
        b2 = Board.empty()
        assert b1 != b2

    def test_boards_hashable_for_sets(self) -> None:
        b1 = Board.from_string(EASY_STR)
        b2 = Board.from_string(EASY_STR)
        b3 = Board.empty()
        s = {b1, b2, b3}
        assert len(s) == 2
