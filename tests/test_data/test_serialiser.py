"""Unit tests for :class:`sudoku.data.serialiser.BoardSerialiser`."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from sudoku.data.serialiser import BoardSerialiser, PuzzleSchema, PuzzleError

VALID_JSON = json.dumps({
    "version": 1,
    "name": "Test Puzzle",
    "difficulty": "easy",
    "grid": [
        [5,3,0, 0,7,0, 0,0,0],
        [6,0,0, 1,9,5, 0,0,0],
        [0,9,8, 0,0,0, 0,6,0],
        [8,0,0, 0,6,0, 0,0,3],
        [4,0,0, 8,0,3, 0,0,1],
        [7,0,0, 0,2,0, 0,0,6],
        [0,6,0, 0,0,0, 2,8,0],
        [0,0,0, 4,1,9, 0,0,5],
        [0,0,0, 0,8,0, 0,7,9],
    ],
})

VALID_JSON_WITH_SOLUTION = json.dumps({
    "version": 1,
    "name": "Test Puzzle With Solution",
    "difficulty": "easy",
    "author": "Test Author",
    "source": "https://example.com",
    "grid": [
        [5,3,0, 0,7,0, 0,0,0],
        [6,0,0, 1,9,5, 0,0,0],
        [0,9,8, 0,0,0, 0,6,0],
        [8,0,0, 0,6,0, 0,0,3],
        [4,0,0, 8,0,3, 0,0,1],
        [7,0,0, 0,2,0, 0,0,6],
        [0,6,0, 0,0,0, 2,8,0],
        [0,0,0, 4,1,9, 0,0,5],
        [0,0,0, 0,8,0, 0,7,9],
    ],
    "solution": [
        [5,3,4, 6,7,8, 9,1,2],
        [6,7,2, 1,9,5, 3,4,8],
        [1,9,8, 3,4,2, 5,6,7],
        [8,5,9, 7,6,1, 4,2,3],
        [4,2,6, 8,5,3, 7,9,1],
        [7,1,3, 9,2,4, 8,5,6],
        [9,6,1, 5,3,7, 2,8,4],
        [2,8,7, 4,1,9, 6,3,5],
        [3,4,5, 2,8,6, 1,7,9],
    ],
})


class TestBoardSerialiserLoadString:
    def test_load_valid_json(self) -> None:
        schema = BoardSerialiser.load_string(VALID_JSON)
        assert isinstance(schema, PuzzleSchema)
        assert schema.name == "Test Puzzle"
        assert schema.difficulty == "easy"

    def test_load_with_solution(self) -> None:
        schema = BoardSerialiser.load_string(VALID_JSON_WITH_SOLUTION)
        assert schema.solution is not None
        assert schema.author == "Test Author"
        assert schema.source == "https://example.com"

    def test_load_grid_values(self) -> None:
        schema = BoardSerialiser.load_string(VALID_JSON)
        assert schema.board[0, 0].value == 5
        assert schema.board[0, 0].is_given
        assert schema.board[0, 2].is_empty

    def test_load_invalid_json_raises(self) -> None:
        with pytest.raises(PuzzleError):
            BoardSerialiser.load_string("{not valid json")

    def test_load_missing_grid_raises(self) -> None:
        data = json.dumps({"version": 1, "name": "x", "difficulty": "easy"})
        with pytest.raises(PuzzleError, match="Missing 'grid'"):
            BoardSerialiser.load_string(data)

    def test_load_wrong_row_count_raises(self) -> None:
        data = json.dumps({
            "version": 1, "name": "x", "difficulty": "easy",
            "grid": [[0]*9]*8,  # only 8 rows
        })
        with pytest.raises(PuzzleError):
            BoardSerialiser.load_string(data)

    def test_load_wrong_col_count_raises(self) -> None:
        grid = [[0]*8] + [[0]*9]*8  # first row has 8 cols
        data = json.dumps({
            "version": 1, "name": "x", "difficulty": "easy",
            "grid": grid,
        })
        with pytest.raises(PuzzleError):
            BoardSerialiser.load_string(data)

    def test_load_invalid_digit_raises(self) -> None:
        grid = [[0]*9 for _ in range(9)]
        grid[0][0] = 10  # invalid
        data = json.dumps({
            "version": 1, "name": "x", "difficulty": "easy",
            "grid": grid,
        })
        with pytest.raises(PuzzleError):
            BoardSerialiser.load_string(data)

    def test_load_unknown_difficulty_raises(self) -> None:
        data = json.dumps({
            "version": 1, "name": "x", "difficulty": "impossible",
            "grid": [[0]*9]*9,
        })
        with pytest.raises(PuzzleError, match="Unknown difficulty"):
            BoardSerialiser.load_string(data)

    def test_load_future_version_raises(self) -> None:
        data = json.dumps({
            "version": 99, "name": "x", "difficulty": "easy",
            "grid": [[0]*9]*9,
        })
        with pytest.raises(PuzzleError, match="Unsupported puzzle schema version"):
            BoardSerialiser.load_string(data)


class TestBoardSerialiserSaveLoad:
    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        schema = BoardSerialiser.load_string(VALID_JSON_WITH_SOLUTION)
        dest = tmp_path / "test_puzzle.json"
        BoardSerialiser.save(schema, dest)
        loaded = BoardSerialiser.load(dest)
        assert loaded.name == schema.name
        assert loaded.board.to_string() == schema.board.to_string()
        assert loaded.solution is not None
        assert loaded.solution.to_string() == schema.solution.to_string()  # type: ignore[union-attr]

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        schema = BoardSerialiser.load_string(VALID_JSON)
        dest = tmp_path / "sub" / "dir" / "puzzle.json"
        BoardSerialiser.save(schema, dest)
        assert dest.exists()

    def test_load_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            BoardSerialiser.load(tmp_path / "nonexistent.json")

    def test_load_real_puzzle_files(self) -> None:
        puzzles_dir = Path(__file__).parent.parent.parent / "puzzles"
        for puzzle_file in puzzles_dir.glob("*.json"):
            schema = BoardSerialiser.load(puzzle_file)
            assert schema.board is not None
            assert not schema.board.is_complete()  # given-cells-only should be partial


class TestFromBoard:
    def test_from_board_wraps_correctly(self) -> None:
        from sudoku.data.board import Board
        board = Board.from_string("5" * 9 + "0" * 72)
        schema = BoardSerialiser.from_board(board, name="Wrap Test", difficulty="hard")
        assert schema.name == "Wrap Test"
        assert schema.difficulty == "hard"
        assert schema.solution is None
