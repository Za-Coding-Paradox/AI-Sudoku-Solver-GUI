"""Solver layer — strategies and engine that run in a background thread."""

from sudoku.solver.strategies import NakedSingles, AC3, Backtracker, SolveResult
from sudoku.solver.engine import SolverEngine

__all__ = [
    "NakedSingles",
    "AC3",
    "Backtracker",
    "SolveResult",
    "SolverEngine",
]
