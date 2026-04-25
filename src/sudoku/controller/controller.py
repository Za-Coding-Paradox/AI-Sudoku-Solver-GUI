"""Controller — bridges the data model, solver, and GUI via the EventBus.

The Controller:
- Owns the canonical Board state and the undo/redo history.
- Subscribes to user-intent events (CellChanged, UndoRequested, etc.)
- Calls the SolverEngine on solve requests.
- Opens file dialogs for puzzle loading.
- Publishes state-change events back onto the bus for the GUI to consume.

Nothing in this module touches pygame rendering directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

from sudoku.data.board import Board
from sudoku.data.serialiser import BoardSerialiser, PuzzleError
from sudoku.events.bus import EventBus
from sudoku.events.types import (
    CellChanged,
    ErrorRaised,
    PuzzleLoaded,
    PuzzleReset,
    RedoRequested,
    SpeedChanged,
    ThemeChanged,
    UndoRequested,
)
from sudoku.solver.engine import SolverEngine


class Controller:
    """Application controller — owns state, wires events, drives the solver.

    Parameters
    ----------
    bus:     EventBus (defaults to singleton).
    puzzles_dir:
             Default directory for the file picker.
    """

    MAX_HISTORY = 128

    def __init__(
        self,
        bus: EventBus | None = None,
        puzzles_dir: Path | None = None,
    ) -> None:
        self._bus = bus or EventBus.get_instance()
        self._puzzles_dir = puzzles_dir or Path("puzzles")

        self._board: Board = Board.empty()
        self._given_board: Board = Board.empty()   # board at load/new time
        self._undo_stack: list[Board] = []
        self._redo_stack: list[Board] = []

        self._engine = SolverEngine(bus=self._bus)
        self._current_puzzle_name = "Untitled"
        self._current_difficulty = "unknown"

        # Subscribe to user-intent events.
        self._bus.subscribe(CellChanged, self._on_cell_changed)
        self._bus.subscribe(UndoRequested, self._on_undo)
        self._bus.subscribe(RedoRequested, self._on_redo)
        self._bus.subscribe(SpeedChanged, self._on_speed_changed)

    # ------------------------------------------------------------------
    # Public API (called by the App / GUI callbacks)
    # ------------------------------------------------------------------

    def load_puzzle(self, path: Path | None = None) -> None:
        """Open *path* (or show a file picker) and publish PuzzleLoaded."""
        if path is None:
            path = self._pick_puzzle_file()
        if path is None:
            return  # user cancelled

        try:
            schema = BoardSerialiser.load(path)
        except (FileNotFoundError, PuzzleError) as exc:
            self._bus.publish(ErrorRaised(message=str(exc)))
            return

        self._board = schema.board.with_candidates_computed()
        self._given_board = schema.board
        self._current_puzzle_name = schema.name
        self._current_difficulty = schema.difficulty
        self._undo_stack.clear()
        self._redo_stack.clear()

        self._bus.publish(
            PuzzleLoaded(
                board=self._board,
                name=schema.name,
                difficulty=schema.difficulty,
            )
        )

    def new_board(self) -> None:
        """Reset to a completely blank board."""
        self._board = Board.empty()
        self._given_board = Board.empty()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._bus.publish(
            PuzzleLoaded(board=self._board, name="New Puzzle", difficulty="unknown")
        )

    def reset_puzzle(self) -> None:
        """Restore the puzzle to its original given-cell-only state."""
        self._engine.cancel()
        self._board = self._given_board.with_candidates_computed()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._bus.publish(PuzzleReset(board=self._board))

    def solve(self) -> None:
        """Start the solver in a background thread."""
        if self._engine.is_running:
            self._engine.cancel()
            return
        self._engine.start(self._board)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_cell_changed(self, event: CellChanged) -> None:
        if event.by_solver:
            return  # solver-placed cells are managed by the engine
        self._push_undo(self._board)
        self._board = self._board.set_value(event.coord, event.new_value)
        self._redo_stack.clear()

    def _on_undo(self, event: UndoRequested) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._board)
        self._board = self._undo_stack.pop()
        self._bus.publish(PuzzleReset(board=self._board))

    def _on_redo(self, event: RedoRequested) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._board)
        self._board = self._redo_stack.pop()
        self._bus.publish(PuzzleReset(board=self._board))

    def _on_speed_changed(self, event: SpeedChanged) -> None:
        self._engine.set_steps_per_second(event.steps_per_second)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _push_undo(self, board: Board) -> None:
        self._undo_stack.append(board)
        if len(self._undo_stack) > self.MAX_HISTORY:
            self._undo_stack.pop(0)

    def _pick_puzzle_file(self) -> Path | None:
        """Simple puzzle picker — tries tkinter filedialog, falls back to CLI."""
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            filename = filedialog.askopenfilename(
                title="Open Puzzle",
                initialdir=str(self._puzzles_dir),
                filetypes=[("Puzzle JSON", "*.json"), ("All files", "*.*")],
            )
            root.destroy()
            return Path(filename) if filename else None
        except Exception:  # noqa: BLE001
            # Fallback: load first puzzle in the puzzles directory.
            puzzles = sorted(self._puzzles_dir.glob("*.json"))
            return puzzles[0] if puzzles else None
