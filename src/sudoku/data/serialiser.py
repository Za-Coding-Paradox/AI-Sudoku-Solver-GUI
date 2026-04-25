"""Serialiser — load and save puzzle files.

Puzzle JSON schema
------------------
{
    "version": 1,
    "name":    "Easy #001",
    "author":  "optional",
    "source":  "optional URL",
    "difficulty": "easy",          // easy | medium | hard | expert | evil
    "grid": [
        [5,3,0, 0,7,0, 0,0,0],     // 0 = empty
        ...                         // 9 rows × 9 columns
    ],
    "solution": [                   // optional
        [5,3,4, 6,7,8, 9,1,2],
        ...
    ]
}

The serialiser validates the schema on load and raises :class:`PuzzleError`
on any structural violation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sudoku.data.board import Board, RawGrid

# Schema version this serialiser understands.
CURRENT_VERSION: int = 1

VALID_DIFFICULTIES = frozenset({"easy", "medium", "hard", "expert", "evil", "unknown"})


class PuzzleError(Exception):
    """Raised when a puzzle file is malformed or fails validation."""


@dataclass(frozen=True, slots=True)
class PuzzleSchema:
    """Parsed representation of a puzzle JSON file.

    All fields that are optional in the file are given sensible defaults.
    """

    name: str
    difficulty: str
    board: Board
    solution: Board | None = None
    author: str = ""
    source: str = ""
    version: int = CURRENT_VERSION


class BoardSerialiser:
    """Load and save :class:`PuzzleSchema` objects to/from JSON files."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str) -> PuzzleSchema:
        """Load a puzzle from a JSON file at *path*.

        Raises
        ------
        PuzzleError
            On any structural or semantic problem with the file.
        FileNotFoundError
            When the file does not exist.
        """
        path = Path(path)
        try:
            raw_text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(f"Puzzle file not found: {path}") from None

        try:
            data: dict[str, Any] = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise PuzzleError(f"Invalid JSON in {path}: {exc}") from exc

        return cls._parse(data, path)

    @classmethod
    def load_string(cls, json_str: str, *, name: str = "inline") -> PuzzleSchema:
        """Parse a JSON *string* directly (useful for tests and embedded puzzles)."""
        try:
            data: dict[str, Any] = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise PuzzleError(f"Invalid JSON: {exc}") from exc
        return cls._parse(data, Path(name))

    @classmethod
    def save(cls, schema: PuzzleSchema, path: Path | str) -> None:
        """Write *schema* to a JSON file at *path*."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = cls._serialise(schema)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def from_board(
        cls,
        board: Board,
        *,
        name: str = "Untitled",
        difficulty: str = "unknown",
    ) -> PuzzleSchema:
        """Wrap an existing :class:`Board` in a minimal schema."""
        return PuzzleSchema(
            name=name,
            difficulty=difficulty,
            board=board,
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @classmethod
    def _parse(cls, data: dict[str, Any], source: Path) -> PuzzleSchema:
        version = data.get("version", 1)
        if not isinstance(version, int) or version > CURRENT_VERSION:
            raise PuzzleError(
                f"Unsupported puzzle schema version {version!r} in {source}. "
                f"Maximum supported version is {CURRENT_VERSION}."
            )

        name = str(data.get("name", "Untitled"))
        author = str(data.get("author", ""))
        src_url = str(data.get("source", ""))
        difficulty = str(data.get("difficulty", "unknown")).lower()

        if difficulty not in VALID_DIFFICULTIES:
            raise PuzzleError(
                f"Unknown difficulty {difficulty!r} in {source}. "
                f"Valid values: {sorted(VALID_DIFFICULTIES)}"
            )

        raw_grid = data.get("grid")
        if raw_grid is None:
            raise PuzzleError(f"Missing 'grid' key in {source}.")

        board = cls._parse_grid(raw_grid, source, key="grid")

        raw_solution = data.get("solution")
        solution: Board | None = None
        if raw_solution is not None:
            solution = cls._parse_grid(raw_solution, source, key="solution")

        return PuzzleSchema(
            version=version,
            name=name,
            author=author,
            source=src_url,
            difficulty=difficulty,
            board=board,
            solution=solution,
        )

    @classmethod
    def _parse_grid(cls, raw: Any, source: Path, key: str) -> Board:
        if not isinstance(raw, list) or len(raw) != 9:
            raise PuzzleError(
                f"'{key}' in {source} must be a list of exactly 9 rows."
            )
        parsed: RawGrid = []
        for r, row in enumerate(raw):
            if not isinstance(row, list) or len(row) != 9:
                raise PuzzleError(
                    f"'{key}[{r}]' in {source} must be a list of exactly 9 integers."
                )
            cells: list[int] = []
            for c, val in enumerate(row):
                if not isinstance(val, int) or not (0 <= val <= 9):
                    raise PuzzleError(
                        f"'{key}[{r}][{c}]' in {source} must be an integer 0-9, got {val!r}."
                    )
                cells.append(val)
            parsed.append(cells)
        return Board.from_raw(parsed)

    # ------------------------------------------------------------------
    # Serialising
    # ------------------------------------------------------------------

    @classmethod
    def _serialise(cls, schema: PuzzleSchema) -> dict[str, Any]:
        data: dict[str, Any] = {
            "version": schema.version,
            "name": schema.name,
            "difficulty": schema.difficulty,
            "grid": schema.board.to_raw(),
        }
        if schema.author:
            data["author"] = schema.author
        if schema.source:
            data["source"] = schema.source
        if schema.solution is not None:
            data["solution"] = schema.solution.to_raw()
        return data
