"""Unit tests for SolverEngine (sync path — no pygame needed)."""

from __future__ import annotations

import pytest

from sudoku.data.board import Board
from sudoku.data.cell import CellCoord
from sudoku.events.bus import EventBus
from sudoku.events.types import SolveComplete, SolveFailed, SolveStarted, SolveStep
from sudoku.solver.engine import SolverEngine
from sudoku.solver.strategies import SolveResult

EASY = (
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

HARD = (
    "000000000"
    "000003085"
    "001020000"
    "000507000"
    "004000100"
    "090000000"
    "500000073"
    "002010000"
    "000040009"
)

# Already-solved board
SOLVED = (
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
# Synchronous solve_sync() — no events, no threads
# ---------------------------------------------------------------------------


class TestSolverEngineSyncEasy:
    def test_solves_easy_puzzle(self) -> None:
        engine = SolverEngine()
        result = engine.solve_sync(Board.from_string(EASY))
        assert result.solved
        assert result.board.is_complete()
        assert not result.failed

    def test_solution_matches_known(self) -> None:
        engine = SolverEngine()
        result = engine.solve_sync(Board.from_string(EASY))
        assert result.board.to_string() == SOLVED

    def test_steps_recorded(self) -> None:
        engine = SolverEngine()
        result = engine.solve_sync(Board.from_string(EASY))
        assert len(result.steps) > 0

    def test_steps_are_valid_placements(self) -> None:
        engine = SolverEngine()
        result = engine.solve_sync(Board.from_string(EASY))
        for step in result.steps:
            assert 1 <= step.value <= 9
            assert 0 <= step.coord.row < 9
            assert 0 <= step.coord.col < 9


class TestSolverEngineSyncHard:
    def test_solves_hard_puzzle(self) -> None:
        engine = SolverEngine()
        result = engine.solve_sync(Board.from_string(HARD))
        assert result.solved
        assert result.board.is_complete()

    def test_hard_result_valid(self) -> None:
        from sudoku.data.validator import Validator
        engine = SolverEngine()
        result = engine.solve_sync(Board.from_string(HARD))
        validation = Validator.validate(result.board)
        assert not validation.has_conflicts
        assert validation.is_complete


class TestSolverEngineSyncEdgeCases:
    def test_already_solved_board(self) -> None:
        engine = SolverEngine()
        result = engine.solve_sync(Board.from_string(SOLVED))
        assert result.solved
        assert len(result.steps) == 0

    def test_empty_board_produces_a_solution(self) -> None:
        engine = SolverEngine()
        result = engine.solve_sync(Board.empty())
        assert result.solved
        assert result.board.is_complete()

    def test_impossible_board_fails(self) -> None:
        # Two 5s in row 0 — no solution possible
        board = Board.empty()
        board = board.set_value(CellCoord(0, 0), 5)
        board = board.set_value(CellCoord(0, 1), 5)
        engine = SolverEngine()
        result = engine.solve_sync(board)
        assert result.failed

    def test_solve_result_fields(self) -> None:
        engine = SolverEngine()
        result = engine.solve_sync(Board.from_string(EASY))
        assert isinstance(result, SolveResult)
        assert isinstance(result.board, Board)
        assert isinstance(result.steps, list)


# ---------------------------------------------------------------------------
# Event emission via async start() — uses the real EventBus
# ---------------------------------------------------------------------------


class TestSolverEngineEvents:
    def test_emits_solve_started(self, bus: EventBus) -> None:
        started: list[SolveStarted] = []
        bus.subscribe(SolveStarted, started.append)

        engine = SolverEngine(bus=bus)
        engine.start(Board.from_string(EASY))
        engine.cancel()  # wait for thread to finish
        assert len(started) == 1

    def test_emits_solve_steps(self, bus: EventBus) -> None:
        steps: list[SolveStep] = []
        bus.subscribe(SolveStep, steps.append)

        engine = SolverEngine(bus=bus)
        engine.start(Board.from_string(EASY))
        engine.cancel()
        assert len(steps) > 0

    def test_emits_solve_complete(self, bus: EventBus) -> None:
        import time
        completed: list[SolveComplete] = []
        bus.subscribe(SolveComplete, completed.append)

        engine = SolverEngine(bus=bus)
        engine.start(Board.from_string(EASY))

        # Wait for solve to finish (max 5 s)
        deadline = time.time() + 5
        while time.time() < deadline and engine.is_running:
            time.sleep(0.05)
        engine.cancel()

        assert len(completed) == 1
        assert completed[0].board.is_complete()

    def test_emits_solve_failed_on_impossible(self, bus: EventBus) -> None:
        import time
        failures: list[SolveFailed] = []
        bus.subscribe(SolveFailed, failures.append)

        board = Board.empty()
        board = board.set_value(CellCoord(0, 0), 5)
        board = board.set_value(CellCoord(0, 1), 5)

        engine = SolverEngine(bus=bus)
        engine.start(board)

        deadline = time.time() + 5
        while time.time() < deadline and engine.is_running:
            time.sleep(0.05)
        engine.cancel()

        assert len(failures) >= 1

    def test_step_indices_are_monotonic(self, bus: EventBus) -> None:
        import time
        steps: list[SolveStep] = []
        bus.subscribe(SolveStep, steps.append)

        engine = SolverEngine(bus=bus)
        engine.start(Board.from_string(EASY))

        deadline = time.time() + 5
        while time.time() < deadline and engine.is_running:
            time.sleep(0.05)
        engine.cancel()

        for i, step in enumerate(steps):
            assert step.step_index == i


# ---------------------------------------------------------------------------
# Control — pause / resume / cancel / speed
# ---------------------------------------------------------------------------


class TestSolverEngineControl:
    def test_cancel_stops_engine(self) -> None:
        engine = SolverEngine()
        board = Board.from_string(HARD)
        engine.set_delay(10.0)  # very slow — won't finish
        engine.start(board)
        assert engine.is_running
        engine.cancel()
        assert not engine.is_running

    def test_set_delay(self) -> None:
        engine = SolverEngine()
        engine.set_delay(0.1)
        assert engine._delay == pytest.approx(0.1)

    def test_set_steps_per_second(self) -> None:
        engine = SolverEngine()
        engine.set_steps_per_second(10)
        assert engine._delay == pytest.approx(0.1)

    def test_set_steps_per_second_zero_gives_instant(self) -> None:
        engine = SolverEngine()
        engine.set_steps_per_second(0)
        assert engine._delay == 0.0

    def test_is_running_false_before_start(self) -> None:
        engine = SolverEngine()
        assert not engine.is_running

    def test_starting_twice_cancels_first(self) -> None:
        import time
        engine = SolverEngine()
        engine.set_delay(10.0)
        engine.start(Board.from_string(HARD))
        assert engine.is_running
        engine.start(Board.from_string(EASY))  # should cancel first
        time.sleep(0.1)
        engine.cancel()
        assert not engine.is_running
