"""ControlPanel — Solve, Load, Reset, Undo, Redo buttons + speed slider.

Publishes high-level intent events via the EventBus.
Never calls the solver or touches the board directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import pygame

from sudoku.events.bus import EventBus
from sudoku.events.types import (
    SpeedChanged,
    ThemeChanged,
    UndoRequested,
    RedoRequested,
)
from sudoku.gui.theme import Theme, ThemeManager

BUTTON_HEIGHT = 42
BUTTON_RADIUS = 8
SLIDER_TRACK_H = 6
SLIDER_THUMB_R = 10
PADDING = 10
FONT_SIZE = 16


class _Button:
    """A simple rounded-rectangle clickable button."""

    def __init__(
        self,
        label: str,
        rect: pygame.Rect,
        on_click: Callable[[], None],
    ) -> None:
        self.label = label
        self.rect = rect
        self.on_click = on_click
        self._hovered = False
        self._pressed = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._pressed = True
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._pressed and self.rect.collidepoint(event.pos):
                self._pressed = False
                self.on_click()
                return True
            self._pressed = False
        return False

    def draw(self, surface: pygame.Surface, theme: Theme, font: pygame.font.Font) -> None:
        if self._pressed:
            bg = theme.button_bg_active
        elif self._hovered:
            bg = theme.button_bg_hover
        else:
            bg = theme.button_bg

        pygame.draw.rect(surface, bg, self.rect, border_radius=BUTTON_RADIUS)
        pygame.draw.rect(surface, theme.button_border, self.rect, 1, border_radius=BUTTON_RADIUS)

        surf = font.render(self.label, True, theme.button_fg)
        r = surf.get_rect(center=self.rect.center)
        surface.blit(surf, r)


class _Slider:
    """A horizontal slider for speed control."""

    def __init__(
        self,
        rect: pygame.Rect,
        min_val: float,
        max_val: float,
        value: float,
        on_change: Callable[[float], None],
        label: str = "Speed",
    ) -> None:
        self.rect = rect
        self.min_val = min_val
        self.max_val = max_val
        self._value = value
        self.on_change = on_change
        self.label = label
        self._dragging = False

    @property
    def value(self) -> float:
        return self._value

    def _track_rect(self) -> pygame.Rect:
        cy = self.rect.centery
        return pygame.Rect(
            self.rect.left,
            cy - SLIDER_TRACK_H // 2,
            self.rect.width,
            SLIDER_TRACK_H,
        )

    def _thumb_x(self) -> int:
        t = (self._value - self.min_val) / (self.max_val - self.min_val)
        return int(self.rect.left + t * self.rect.width)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            tx = self._thumb_x()
            cy = self.rect.centery
            thumb = pygame.Rect(tx - SLIDER_THUMB_R, cy - SLIDER_THUMB_R,
                                SLIDER_THUMB_R * 2, SLIDER_THUMB_R * 2)
            if thumb.collidepoint(event.pos) or self._track_rect().collidepoint(event.pos):
                self._dragging = True
                self._update_from_pos(event.pos[0])
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        if event.type == pygame.MOUSEMOTION and self._dragging:
            self._update_from_pos(event.pos[0])
            return True
        return False

    def _update_from_pos(self, x: int) -> None:
        t = (x - self.rect.left) / self.rect.width
        t = max(0.0, min(1.0, t))
        self._value = self.min_val + t * (self.max_val - self.min_val)
        self.on_change(self._value)

    def draw(self, surface: pygame.Surface, theme: Theme, font: pygame.font.Font) -> None:
        track = self._track_rect()
        pygame.draw.rect(surface, theme.button_border, track, border_radius=3)

        # Filled portion
        tx = self._thumb_x()
        filled = pygame.Rect(track.left, track.top, tx - track.left, SLIDER_TRACK_H)
        if filled.width > 0:
            pygame.draw.rect(surface, theme.highlight_ring, filled, border_radius=3)

        # Thumb
        cy = self.rect.centery
        pygame.draw.circle(surface, theme.highlight_ring, (tx, cy), SLIDER_THUMB_R)
        pygame.draw.circle(surface, theme.button_fg, (tx, cy), SLIDER_THUMB_R - 3)

        # Label
        label_text = f"{self.label}: {int(self._value)}/s" if self._value > 0 else f"{self.label}: instant"
        surf = font.render(label_text, True, theme.status_fg)
        surface.blit(surf, (self.rect.left, self.rect.top - surf.get_height() - 4))


class ControlPanel:
    """The side panel containing all action buttons and the speed slider.

    Parameters
    ----------
    surface:    pygame Surface to draw onto.
    rect:       Pixel area this panel occupies.
    theme_manager: Shared ThemeManager.
    on_solve:   Called when "Solve" is clicked.
    on_load:    Called when "Load" is clicked — should open a file dialog.
    on_reset:   Called when "Reset" is clicked.
    on_new:     Called when "New" is clicked (blank board).
    bus:        EventBus (defaults to singleton).
    """

    def __init__(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        theme_manager: ThemeManager,
        on_solve: Callable[[], None],
        on_load: Callable[[], None],
        on_reset: Callable[[], None],
        on_new: Callable[[], None],
        bus: EventBus | None = None,
    ) -> None:
        self._surface = surface
        self._rect = rect
        self._tm = theme_manager
        self._bus = bus or EventBus.get_instance()
        self._font: pygame.font.Font | None = None
        self._label_font: pygame.font.Font | None = None

        x = rect.left + PADDING
        w = rect.width - PADDING * 2
        y = rect.top + PADDING

        def make_button(label: str, callback: Callable[[], None]) -> _Button:
            nonlocal y
            btn = _Button(label, pygame.Rect(x, y, w, BUTTON_HEIGHT), callback)
            y += BUTTON_HEIGHT + PADDING
            return btn

        self._btn_solve = make_button("▶  Solve", on_solve)
        self._btn_load = make_button("📂  Load Puzzle", on_load)
        self._btn_reset = make_button("↺  Reset", on_reset)
        self._btn_new = make_button("＋  New", on_new)
        self._btn_undo = make_button("← Undo", self._undo)
        self._btn_redo = make_button("→ Redo", self._redo)
        self._btn_theme = make_button("🎨  Theme", self._cycle_theme)

        y += PADDING  # extra gap before slider
        slider_rect = pygame.Rect(x, y + 24, w, 24)
        self._slider = _Slider(
            rect=slider_rect,
            min_val=0,
            max_val=30,
            value=10,
            on_change=self._on_speed_change,
            label="Speed",
        )

        self._buttons = [
            self._btn_solve, self._btn_load, self._btn_reset,
            self._btn_new, self._btn_undo, self._btn_redo, self._btn_theme,
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draw(self) -> None:
        theme = self._tm.active
        self._ensure_fonts()
        assert self._font is not None

        pygame.draw.rect(self._surface, theme.panel_bg, self._rect)

        for btn in self._buttons:
            btn.draw(self._surface, theme, self._font)

        self._slider.draw(self._surface, theme, self._font)

    def handle_event(self, event: pygame.event.Event) -> bool:
        for btn in self._buttons:
            if btn.handle_event(event):
                return True
        return self._slider.handle_event(event)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont("segoeui,arial,sans-serif", FONT_SIZE)

    def _undo(self) -> None:
        self._bus.publish(UndoRequested())

    def _redo(self) -> None:
        self._bus.publish(RedoRequested())

    def _cycle_theme(self) -> None:
        name = self._tm.toggle()
        self._bus.publish(ThemeChanged(theme_name=name))

    def _on_speed_change(self, value: float) -> None:
        self._bus.publish(SpeedChanged(steps_per_second=value))
