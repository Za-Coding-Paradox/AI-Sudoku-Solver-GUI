"""ControlPanel — side panel with labelled action buttons and speed slider."""

from __future__ import annotations

from typing import Callable

import pygame

from sudoku.events.bus import EventBus
from sudoku.events.types import (
    RedoRequested,
    SpeedChanged,
    ThemeChanged,
    UndoRequested,
)
from sudoku.gui.theme import Theme, ThemeManager

BUTTON_H       = 38
BUTTON_RADIUS  = 7
PADDING        = 10
SECTION_GAP    = 14
FONT_SIZE      = 15
LABEL_SIZE     = 11
SLIDER_TRACK_H = 5
SLIDER_THUMB_R = 9


class _Button:
    def __init__(self, label: str, rect: pygame.Rect, on_click: Callable[[], None]) -> None:
        self.label    = label
        self.rect     = rect
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
            fired = self._pressed and self.rect.collidepoint(event.pos)
            self._pressed = False
            if fired:
                self.on_click()
                return True
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
        surface.blit(surf, surf.get_rect(center=self.rect.center))


class _Slider:
    def __init__(
        self,
        rect: pygame.Rect,
        min_val: float,
        max_val: float,
        value: float,
        on_change: Callable[[float], None],
    ) -> None:
        self.rect      = rect
        self.min_val   = min_val
        self.max_val   = max_val
        self._value    = value
        self.on_change = on_change
        self._dragging = False

    @property
    def value(self) -> float:
        return self._value

    def _track(self) -> pygame.Rect:
        cy = self.rect.centery
        return pygame.Rect(self.rect.left, cy - SLIDER_TRACK_H // 2, self.rect.width, SLIDER_TRACK_H)

    def _thumb_x(self) -> int:
        span = max(self.max_val - self.min_val, 1)
        t = (self._value - self.min_val) / span
        return int(self.rect.left + t * self.rect.width)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            tx, cy = self._thumb_x(), self.rect.centery
            thumb = pygame.Rect(tx - SLIDER_THUMB_R, cy - SLIDER_THUMB_R, SLIDER_THUMB_R * 2, SLIDER_THUMB_R * 2)
            if thumb.collidepoint(event.pos) or self._track().collidepoint(event.pos):
                self._dragging = True
                self._update(event.pos[0])
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        if event.type == pygame.MOUSEMOTION and self._dragging:
            self._update(event.pos[0])
            return True
        return False

    def _update(self, x: int) -> None:
        t = max(0.0, min(1.0, (x - self.rect.left) / max(self.rect.width, 1)))
        self._value = self.min_val + t * (self.max_val - self.min_val)
        self.on_change(self._value)

    def draw(self, surface: pygame.Surface, theme: Theme, label_font: pygame.font.Font) -> None:
        track = self._track()
        tx    = self._thumb_x()
        cy    = self.rect.centery

        pygame.draw.rect(surface, theme.button_border, track, border_radius=3)
        if tx > track.left:
            pygame.draw.rect(surface, theme.highlight_ring,
                             pygame.Rect(track.left, track.top, tx - track.left, SLIDER_TRACK_H),
                             border_radius=3)
        pygame.draw.circle(surface, theme.highlight_ring, (tx, cy), SLIDER_THUMB_R)
        pygame.draw.circle(surface, theme.button_fg,      (tx, cy), SLIDER_THUMB_R - 3)

        label = "Speed: instant" if self._value <= 0 else f"Speed: {int(self._value)} steps/s"
        lsurf = label_font.render(label, True, theme.status_fg)
        surface.blit(lsurf, (self.rect.left, self.rect.top - lsurf.get_height() - 5))


class ControlPanel:
    """Side panel: buttons, speed slider, keyboard shortcut reference."""

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
        self._rect    = rect
        self._tm      = theme_manager
        self._bus     = bus or EventBus.get_instance()
        self._font:       pygame.font.Font | None = None
        self._label_font: pygame.font.Font | None = None

        self._buttons:  list[_Button]           = []
        self._sections: list[tuple[str, int]]   = []  # (label_text, y)

        x = rect.left + PADDING
        w = rect.width - PADDING * 2
        y = rect.top + PADDING

        def section(title: str) -> None:
            nonlocal y
            self._sections.append((title, y))
            y += LABEL_SIZE + 6

        def button(label: str, cb: Callable[[], None]) -> _Button:
            nonlocal y
            btn = _Button(label, pygame.Rect(x, y, w, BUTTON_H), cb)
            self._buttons.append(btn)
            y += BUTTON_H + PADDING - 2
            return btn

        section("PUZZLE")
        button("▶  Solve",         on_solve)
        button("📂  Load Puzzle",   on_load)
        button("↺  Reset Puzzle",  on_reset)
        button("＋  New Board",    on_new)
        y += SECTION_GAP

        section("EDIT")
        button("← Undo  (Ctrl+Z)", self._undo)
        button("→ Redo  (Ctrl+Y)", self._redo)
        y += SECTION_GAP

        section("VIEW")
        button("🎨  Toggle Theme  (T)", self._cycle_theme)
        y += SECTION_GAP + 22  # room for slider label above track

        self._slider = _Slider(
            rect=pygame.Rect(x, y, w, 24),
            min_val=0, max_val=30, value=10,
            on_change=self._on_speed_change,
        )
        y += 24 + SECTION_GAP + 8

        # Shortcuts reference
        section("SHORTCUTS")
        self._shortcuts_y = y
        self._shortcuts: list[tuple[str, str]] = [
            ("Space",       "Solve"),
            ("Ctrl+Z/Y",    "Undo / Redo"),
            ("Ctrl+O",      "Load puzzle"),
            ("Ctrl+N",      "New board"),
            ("T",           "Toggle theme"),
            ("Arrows",      "Move selection"),
            ("Del / 0",     "Clear cell"),
            ("Esc",         "Quit"),
        ]

    def draw(self) -> None:
        theme = self._tm.active
        self._ensure_fonts()
        assert self._font is not None
        assert self._label_font is not None

        pygame.draw.rect(self._surface, theme.panel_bg, self._rect)
        pygame.draw.line(self._surface, theme.grid_line_thick,
                         self._rect.topleft, self._rect.bottomleft, 2)

        for label, y in self._sections:
            lsurf = self._label_font.render(label, True, theme.status_fg)
            self._surface.blit(lsurf, (self._rect.left + PADDING, y))

        for btn in self._buttons:
            btn.draw(self._surface, theme, self._font)

        self._slider.draw(self._surface, theme, self._label_font)
        self._draw_shortcuts(theme)

    def handle_event(self, event: pygame.event.Event) -> bool:
        for btn in self._buttons:
            if btn.handle_event(event):
                return True
        return self._slider.handle_event(event)

    def _ensure_fonts(self) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont("segoeui,arial,sans-serif", FONT_SIZE)
        if self._label_font is None:
            self._label_font = pygame.font.SysFont("segoeui,arial,sans-serif", LABEL_SIZE, bold=True)

    def _draw_shortcuts(self, theme: Theme) -> None:
        assert self._label_font is not None
        x     = self._rect.left + PADDING
        y     = self._shortcuts_y + LABEL_SIZE + 6
        col2x = x + 90

        for key_str, action in self._shortcuts:
            if y + LABEL_SIZE + 4 > self._rect.bottom - 4:
                break
            ks = self._label_font.render(key_str, True, theme.highlight_ring)
            ac = self._label_font.render(action,  True, theme.status_fg)
            self._surface.blit(ks, (x,     y))
            self._surface.blit(ac, (col2x, y))
            y += LABEL_SIZE + 5

    def _undo(self) -> None:
        self._bus.publish(UndoRequested())

    def _redo(self) -> None:
        self._bus.publish(RedoRequested())

    def _cycle_theme(self) -> None:
        name = self._tm.toggle()
        self._bus.publish(ThemeChanged(theme_name=name))

    def _on_speed_change(self, value: float) -> None:
        self._bus.publish(SpeedChanged(steps_per_second=value))
