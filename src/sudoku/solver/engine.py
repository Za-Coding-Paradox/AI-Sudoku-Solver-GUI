"""SolverEngine — orchestrates strategies and runs in a background thread.

The engine:
  1. Runs NakedSingles → AC-3 → Backtracking in sequence.
  2. Emits EventBus events for every step (SolveStep, SolveComplete, SolveFailed).
  3. Runs in a daemon thread so the pygame main loop stays responsive.
  4. Supports pause / resume / cancel via threading.Event flags.
  5. Respects a configurable inter-step delay so the GUI can animate.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from sudoku.data.board import Board
from sudoku.data.validator import Validator
from sudoku.events.bus import EventBus
from sudoku.events.types import (
    SolveComplete,
    SolveFailed,
    SolveStarted,
    SolveStep as SolveStepEvent,
)
from sudoku.solver.strategies import (
    AC3,
    Backtracker,
    NakedSingles,
    SolveResult,
    SolveStep,
)


class SolverEngine:
    """Orchestrates solving strategies and emits EventBus events.

    Usage
    -----
    >>> engine = SolverEngine()
    >>> engine.start(board)          # non-blocking, spawns a daemon thread
    >>> engine.cancel()              # request early stop
    >>> engine.set_delay(0.05)       # 50 ms between steps (~20 steps/sec)

    Events emitted (all via EventBus)
    ----------------------------------
    SolveStarted    — immediately when start() is called
    SolveStep       — for every digit placed by any strategy
    SolveComplete   — when the board is fully solved
    SolveFailed     — when no solution exists or solve was cancelled
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus or EventBus.get_instance()
        self._thread: threading.Thread | None = None
        self._cancel_flag = threading.Event()
        self._pause_flag = threading.Event()
        self._pause_flag.set()  # not paused by default
        self._delay: float = 0.0  # seconds between steps; 0 = instant
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public control API
    # ------------------------------------------------------------------

    def start(self, board: Board) -> None:
        """Start solving *board* in a background daemon thread.

        If a solve is already running it is cancelled first.
        """
        self.cancel()
        with self._lock:
            self._cancel_flag.clear()
            self._pause_flag.set()
            self._thread = threading.Thread(
                target=self._run,
                args=(board,),
                daemon=True,
                name="SolverEngine",
            )
            self._thread.start()

    def cancel(self) -> None:
        """Request the running solve to stop as soon as possible."""
        self._cancel_flag.set()
        self._pause_flag.set()  # unblock if paused
        with self._lock:
            if self._thread is not None:
                self._thread.join(timeout=2.0)
                self._thread = None

    def pause(self) -> None:
        """Pause step emission (the thread keeps running but waits)."""
        self._pause_flag.clear()

    def resume(self) -> None:
        """Resume after a pause."""
        self._pause_flag.set()

    def set_delay(self, seconds: float) -> None:
        """Set the inter-step delay.  0 = instant (no animation)."""
        self._delay = max(0.0, seconds)

    def set_steps_per_second(self, sps: float) -> None:
        """Convenience: set delay from a steps-per-second value."""
        self._delay = 0.0 if sps <= 0 else 1.0 / sps

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Internal solve loop
    # ------------------------------------------------------------------

    def _run(self, board: Board) -> None:
        """Main solver loop — runs in the daemon thread."""
        start_time = time.perf_counter()
        self._bus.publish(SolveStarted(board_snapshot=board))

        steps_taken: list[SolveStep] = []
        current_board = board.with_candidates_computed()

        # --- Strategy 1: Naked Singles ---
        for current_board, step in NakedSingles.apply(current_board):
            if self._cancel_flag.is_set():
                self._emit_failed("Solve cancelled.", steps_taken)
                return
            steps_taken.append(step)
            self._emit_step(step, len(steps_taken) - 1)
            self._pace()

        # --- Strategy 2: AC-3 ---
        for current_board, step in AC3.apply(current_board):
            if self._cancel_flag.is_set():
                self._emit_failed("Solve cancelled.", steps_taken)
                return
            steps_taken.append(step)
            self._emit_step(step, len(steps_taken) - 1)
            self._pace()

        # Check if already solved after the cheap strategies.
        if current_board.is_complete():
            self._emit_complete(current_board, steps_taken, start_time)
            return

        # Verify there are no dead-end cells before backtracking.
        if not AC3.is_consistent(current_board):
            self._emit_failed("No solution exists (AC-3 found empty domain).", steps_taken)
            return

        # --- Strategy 3: Backtracking ---
        gen = Backtracker.apply(current_board)
        solved_board: Board | None = None

        try:
            while True:
                if self._cancel_flag.is_set():
                    self._emit_failed("Solve cancelled.", steps_taken)
                    return

                try:
                    new_board, step = next(gen)  # type: ignore[misc]
                except StopIteration as exc:
                    solved_board = exc.value  # type: ignore[assignment]
                    break

                current_board = new_board
                steps_taken.append(step)
                self._emit_step(step, len(steps_taken) - 1)
                self._pace()

        except Exception as exc:  # noqa: BLE001
            self._emit_failed(f"Solver error: {exc}", steps_taken)
            return

        if solved_board is not None and solved_board.is_complete():
            self._emit_complete(solved_board, steps_taken, start_time)
        else:
            self._emit_failed("No solution exists for this puzzle.", steps_taken)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pace(self) -> None:
        """Honour pause + inter-step delay."""
        self._pause_flag.wait()  # blocks if paused
        if self._delay > 0:
            time.sleep(self._delay)

    def _emit_step(self, step: SolveStep, index: int) -> None:
        self._bus.publish(
            SolveStepEvent(
                coord=step.coord,
                value=step.value,
                strategy=step.strategy,
                step_index=index,
            )
        )

    def _emit_complete(
        self, board: Board, steps: list[SolveStep], start_time: float
    ) -> None:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._bus.publish(
            SolveComplete(
                board=board,
                steps_taken=len(steps),
                elapsed_ms=elapsed_ms,
            )
        )

    def _emit_failed(self, reason: str, steps: list[SolveStep]) -> None:
        self._bus.publish(SolveFailed(reason=reason))

    # ------------------------------------------------------------------
    # Synchronous solve (for tests / non-GUI use)
    # ------------------------------------------------------------------

    def solve_sync(self, board: Board) -> SolveResult:
        """Solve *board* synchronously (blocking).  Does NOT emit events.

        Returns a :class:`SolveResult` with the outcome and all steps.
        Useful for unit tests and non-GUI contexts.
        """
        steps: list[SolveStep] = []
        current = board.with_candidates_computed()

        for current, step in NakedSingles.apply(current):
            steps.append(step)

        for current, step in AC3.apply(current):
            steps.append(step)

        if current.is_complete():
            return SolveResult(solved=True, board=current, steps=steps)

        if not AC3.is_consistent(current):
            return SolveResult(
                solved=False, board=current, steps=steps,
                failed=True, fail_reason="No solution (AC-3 domain wipe-out).",
            )

        gen = Backtracker.apply(current)
        solved_board: Board | None = None
        try:
            while True:
                try:
                    new_board, step = next(gen)  # type: ignore[misc]
                    current = new_board
                    steps.append(step)
                except StopIteration as exc:
                    solved_board = exc.value  # type: ignore[assignment]
                    break
        except Exception as exc:  # noqa: BLE001
            return SolveResult(
                solved=False, board=current, steps=steps,
                failed=True, fail_reason=str(exc),
            )

        if solved_board is not None and solved_board.is_complete():
            return SolveResult(solved=True, board=solved_board, steps=steps)
        return SolveResult(
            solved=False, board=current, steps=steps,
            failed=True, fail_reason="No solution exists.",
        )
