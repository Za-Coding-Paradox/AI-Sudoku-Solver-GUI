"""Event bus layer — typed events and the singleton EventBus.

All inter-module communication goes through this layer.  The solver emits
events; the GUI subscribes to them.  Neither layer imports the other.
"""

from sudoku.events.types import (
    Event,
    CellChanged,
    CandidatesChanged,
    SolveStarted,
    SolveStep,
    SolveComplete,
    SolveFailed,
    PuzzleLoaded,
    PuzzleReset,
    UndoRequested,
    RedoRequested,
    SelectionChanged,
    ErrorRaised,
    ThemeChanged,
    SpeedChanged,
)
from sudoku.events.bus import EventBus

__all__ = [
    # Bus
    "EventBus",
    # Event types
    "Event",
    "CellChanged",
    "CandidatesChanged",
    "SolveStarted",
    "SolveStep",
    "SolveComplete",
    "SolveFailed",
    "PuzzleLoaded",
    "PuzzleReset",
    "UndoRequested",
    "RedoRequested",
    "SelectionChanged",
    "ErrorRaised",
    "ThemeChanged",
    "SpeedChanged",
]
