"""Unit tests for :class:`sudoku.data.cell.Cell` and :class:`CellCoord`."""

from __future__ import annotations

import pytest

from sudoku.data.cell import Cell, CellCoord


# ---------------------------------------------------------------------------
# CellCoord
# ---------------------------------------------------------------------------


class TestCellCoord:
    def test_row_col_accessible(self) -> None:
        c = CellCoord(3, 7)
        assert c.row == 3
        assert c.col == 7

    @pytest.mark.parametrize(
        "row, col, expected_box",
        [
            (0, 0, 0), (0, 3, 1), (0, 6, 2),
            (3, 0, 3), (3, 3, 4), (3, 6, 5),
            (6, 0, 6), (6, 3, 7), (6, 6, 8),
            (2, 2, 0), (4, 5, 4), (8, 8, 8),
        ],
    )
    def test_box_index(self, row: int, col: int, expected_box: int) -> None:
        assert CellCoord(row, col).box == expected_box

    def test_namedtuple_unpacking(self) -> None:
        r, c = CellCoord(1, 2)
        assert r == 1 and c == 2

    def test_repr(self) -> None:
        assert "row=1" in repr(CellCoord(1, 2))
        assert "col=2" in repr(CellCoord(1, 2))

    def test_equality(self) -> None:
        assert CellCoord(4, 4) == CellCoord(4, 4)
        assert CellCoord(0, 0) != CellCoord(0, 1)

    def test_hashable(self) -> None:
        s = {CellCoord(0, 0), CellCoord(0, 0), CellCoord(1, 1)}
        assert len(s) == 2


# ---------------------------------------------------------------------------
# Cell construction
# ---------------------------------------------------------------------------


class TestCellConstruction:
    def test_empty_cell_defaults(self) -> None:
        cell = Cell.empty()
        assert cell.value == 0
        assert cell.is_given is False
        assert cell.is_valid is True
        assert cell.is_highlighted is False
        assert cell.candidates == frozenset(range(1, 10))

    def test_given_cell_valid_digits(self) -> None:
        for digit in range(1, 10):
            cell = Cell.given(digit)
            assert cell.value == digit
            assert cell.is_given is True
            assert cell.is_valid is True
            assert cell.candidates == frozenset()

    def test_given_cell_invalid_digit_raises(self) -> None:
        with pytest.raises(ValueError):
            Cell.given(0)
        with pytest.raises(ValueError):
            Cell.given(10)

    def test_default_cell_is_empty(self) -> None:
        cell = Cell()
        assert cell.is_empty
        assert not cell.is_filled


# ---------------------------------------------------------------------------
# Cell properties
# ---------------------------------------------------------------------------


class TestCellProperties:
    def test_is_empty_true_for_zero(self) -> None:
        assert Cell.empty().is_empty

    def test_is_empty_false_for_nonzero(self) -> None:
        assert not Cell.given(5).is_empty

    def test_is_filled_inverse_of_is_empty(self) -> None:
        empty = Cell.empty()
        filled = Cell.given(3)
        assert empty.is_filled is not empty.is_empty
        assert filled.is_filled is not filled.is_empty


# ---------------------------------------------------------------------------
# Cell mutation helpers (immutable style)
# ---------------------------------------------------------------------------


class TestCellMutation:
    def test_with_value_places_digit(self) -> None:
        cell = Cell.empty()
        new = cell.with_value(7)
        assert new.value == 7
        assert cell.value == 0  # original unchanged

    def test_with_value_zero_clears(self) -> None:
        cell = Cell.given(5)
        # Given cells are frozen=True dataclasses — with_value returns a copy
        new = cell.with_value(0)
        assert new.value == 0

    def test_with_value_invalid_raises(self) -> None:
        cell = Cell.empty()
        with pytest.raises(ValueError):
            cell.with_value(-1)
        with pytest.raises(ValueError):
            cell.with_value(10)

    def test_with_value_zero_allowed(self) -> None:
        cell = Cell.empty()
        new = cell.with_value(0)
        assert new.value == 0

    def test_with_candidates_updates_set(self) -> None:
        cell = Cell.empty()
        new = cell.with_candidates(frozenset({1, 3, 5}))
        assert new.candidates == frozenset({1, 3, 5})

    def test_with_validity_sets_flag(self) -> None:
        cell = Cell.empty()
        invalid = cell.with_validity(False)
        assert invalid.is_valid is False
        valid = invalid.with_validity(True)
        assert valid.is_valid is True

    def test_with_highlight_sets_flag(self) -> None:
        cell = Cell.empty()
        highlighted = cell.with_highlight(True)
        assert highlighted.is_highlighted is True

    def test_mutations_are_independent(self) -> None:
        original = Cell.empty()
        a = original.with_value(3)
        b = original.with_highlight(True)
        assert a.value == 3 and a.is_highlighted is False
        assert b.value == 0 and b.is_highlighted is True

    def test_frozen_cell_cannot_be_mutated_directly(self) -> None:
        cell = Cell.empty()
        with pytest.raises((AttributeError, TypeError)):
            cell.value = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Cell __str__
# ---------------------------------------------------------------------------


class TestCellStr:
    def test_empty_cell_str(self) -> None:
        assert str(Cell.empty()) == "."

    def test_given_cell_str_has_star(self) -> None:
        s = str(Cell.given(5))
        assert "5" in s
        assert "*" in s

    def test_invalid_cell_str_has_exclamation(self) -> None:
        cell = Cell.empty().with_value(3).with_validity(False)
        s = str(cell)
        assert "3" in s
        assert "!" in s
