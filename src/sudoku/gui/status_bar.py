"""StatusBar — one-line info strip at the bottom of the window.

Subscribes to bus events and formats them into human-readable messages.
"""

from __future__ import annotations

import time

import pygame

from sudoku.events.bus import EventBus
from sudoku.events.types import (
    ErrorRaised,
    PuzzleLoaded,
    PuzzleReset,
    SelectionChanged,
    SolveComplete,
    SolveFailed,
    SolveStarted,
    SolveStep,
)
from sudoku.gui.theme import ThemeManager

FONT_SIZE = 15
PADDING_X = 12
PADDING_Y = 6


class StatusBar:
    """Thin horizontal strip that shows contextual messages.

    Parameters
    ----------
    surface:         pygame Surface to draw onto.
    rect:            Pixel area for the status bar.
    theme_manager:   Shared ThemeManager.
    bus:             EventBus (defaults to singleton).
    """

    def __init__(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        theme_manager: ThemeManager,
        bus: EventBus | None = None,
    ) -> None:
        self._surface = surface
        self._rect = rect
        self._tm = theme_manager
        self._bus = bus or EventBus.get_instance()
        self._font: pygame.font.Font | None = None

        self._message = "Load a puzzle or click a cell to start."
        self._right_message = ""
        self._step_count = 0
        self._solve_start: float = 0.0

        self._bus.subscribe(PuzzleLoaded, self._on_puzzle_loaded)
        self._bus.subscribe(PuzzleReset, self._on_puzzle_reset)
        self._bus.subscribe(SolveStarted, self._on_solve_started)
        self._bus.subscribe(SolveStep, self._on_solve_step)
        self._bus.subscribe(SolveComplete, self._on_solve_complete)
        self._bus.subscribe(SolveFailed, self._on_solve_failed)
        self._bus.subscribe(SelectionChanged, self._on_selection_changed)
        self._bus.subscribe(ErrorRaised, self._on_error_raised)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self) -> None:
        theme = self._tm.active
        self._ensure_font()
        assert self._font is not None

        pygame.draw.rect(self._surface, theme.status_bg, self._rect)
        # Top border
        pygame.draw.line(
            self._surface, theme.grid_line_thick,
            self._rect.topleft, self._rect.topright, 1,
        )

        # Left message
        surf = self._font.render(self._message, True, theme.status_fg)
        self._surface.blit(surf, (self._rect.left + PADDING_X, self._rect.top + PADDING_Y))

        # Right message (elapsed / step count)
        if self._right_message:
            rsurf = self._font.render(self._right_message, True, theme.status_fg)
            rx = self._rect.right - rsurf.get_width() - PADDING_X
            self._surface.blit(rsurf, (rx, self._rect.top + PADDING_Y))

    def unsubscribe(self) -> None:
        self._bus.unsubscribe(PuzzleLoaded, self._on_puzzle_loaded)
        self._bus.unsubscribe(PuzzleReset, self._on_puzzle_reset)
        self._bus.unsubscribe(SolveStarted, self._on_solve_started)
        self._bus.unsubscribe(SolveStep, self._on_solve_step)
        self._bus.unsubscribe(SolveComplete, self._on_solve_complete)
        self._bus.unsubscribe(SolveFailed, self._on_solve_failed)
        self._bus.unsubscribe(SelectionChanged, self._on_selection_changed)
        self._bus.unsubscribe(ErrorRaised, self._on_error_raised)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _ensure_font(self) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont("segoeui,arial,sans-serif", FONT_SIZE)

    def _on_puzzle_loaded(self, event: PuzzleLoaded) -> None:
        self._message = f"Loaded: {event.name}  [{event.difficulty}]"
        self._right_message = ""

    def _on_puzzle_reset(self, event: PuzzleReset) -> None:
        self._message = "Puzzle reset to original state."
        self._right_message = ""

    def _on_solve_started(self, event: SolveStarted) -> None:
        self._message = "Solving…"
        self._step_count = 0
        self._solve_start = time.perf_counter()
        self._right_message = ""

    def _on_solve_step(self, event: SolveStep) -> None:
        self._step_count += 1
        self._message = f"Solving… ({event.strategy})  step {event.step_index + 1}"
        elapsed = (time.perf_counter() - self._solve_start) * 1000
        self._right_message = f"{elapsed:.0f} ms"

    def _on_solve_complete(self, event: SolveComplete) -> None:
        self._message = (
            f"✓  Solved in {event.steps_taken} steps  "
            f"({event.elapsed_ms:.1f} ms)"
        )
        self._right_message = ""

    def _on_solve_failed(self, event: SolveFailed) -> None:
        self._message = f"✗  {event.reason}"
        self._right_message = ""

    def _on_selection_changed(self, event: SelectionChanged) -> None:
        if event.coord is not None:
            r, c = event.coord
            self._message = f"Selected: row {r + 1}, col {c + 1}"

    def _on_error_raised(self, event: ErrorRaised) -> None:
        self._message = f"⚠  {event.message}"
