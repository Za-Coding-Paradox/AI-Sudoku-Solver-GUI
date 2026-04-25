"""Unit tests for :class:`sudoku.data.validator.Validator`."""

from __future__ import annotations

import pytest

from sudoku.data.board import Board
from sudoku.data.cell import CellCoord
from sudoku.data.validator import Validator

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

# Two 5s in row 0
CONFLICT_STR = (
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


class TestValidatorValidate:
    def test_empty_board_no_conflicts(self) -> None:
        result = Validator.validate(Board.empty())
        assert not result.has_conflicts
        assert not result.is_complete
        assert not result.is_valid
        assert not result.is_solved

    def test_partial_board_no_conflicts(self) -> None:
        result = Validator.validate(Board.from_string(EASY_STR))
        assert not result.has_conflicts

    def test_solved_board_is_valid(self) -> None:
        result = Validator.validate(Board.from_string(SOLUTION_STR))
        assert not result.has_conflicts
        assert result.is_complete
        assert result.is_valid
        assert result.is_solved

    def test_conflict_in_row_detected(self) -> None:
        result = Validator.validate(Board.from_string(CONFLICT_STR))
        assert result.has_conflicts
        # Both 5s in row 0 should be flagged
        conflict_rows = {c.row for c in result.conflict_coords}
        assert 0 in conflict_rows

    def test_conflict_coords_non_empty(self) -> None:
        result = Validator.validate(Board.from_string(CONFLICT_STR))
        assert len(result.conflict_coords) >= 2

    def test_column_conflict_detected(self) -> None:
        # Place two 5s in column 0 (rows 0 and 1)
        b = Board.empty()
        b = b.set_value(CellCoord(0, 0), 5)
        b = b.set_value(CellCoord(1, 0), 5)
        result = Validator.validate(b)
        assert result.has_conflicts
        assert CellCoord(0, 0) in result.conflict_coords
        assert CellCoord(1, 0) in result.conflict_coords

    def test_box_conflict_detected(self) -> None:
        # Place two 5s in the same 3×3 box (rows 0-2, cols 0-2)
        b = Board.empty()
        b = b.set_value(CellCoord(0, 0), 5)
        b = b.set_value(CellCoord(2, 2), 5)
        result = Validator.validate(b)
        assert result.has_conflicts

    def test_no_conflict_same_value_different_group(self) -> None:
        # 5 in (0,0) and 5 in (3,3) — different row, col, and box
        b = Board.empty()
        b = b.set_value(CellCoord(0, 0), 5)
        b = b.set_value(CellCoord(3, 3), 5)
        result = Validator.validate(b)
        assert not result.has_conflicts


class TestValidatorAnnotate:
    def test_annotate_marks_conflict_cells(self) -> None:
        b = Board.from_string(CONFLICT_STR)
        annotated = Validator.annotate(b)
        # At least the first two cells in row 0 (both value=5) should be invalid
        invalid_cells = [
            coord for coord, cell in annotated if not cell.is_valid and cell.is_filled
        ]
        assert len(invalid_cells) >= 2

    def test_annotate_valid_board_unchanged(self) -> None:
        b = Board.from_string(SOLUTION_STR)
        annotated = Validator.annotate(b)
        for _, cell in annotated:
            assert cell.is_valid
