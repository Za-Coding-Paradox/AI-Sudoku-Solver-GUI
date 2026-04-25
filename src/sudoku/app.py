"""app.py — pygame-ce application entry point.

Layout
------
The window is divided into three docked panels:

  ┌──────────────────────────────┬──────────────┐
  │                              │              │
  │        BOARD PANEL           │  SIDE PANEL  │
  │        (resizable)           │  (fixed w)   │
  │                              │              │
  ├──────────────────────────────┴──────────────┤
  │              STATUS BAR                     │
  └─────────────────────────────────────────────┘

The board panel and side panel are separated by a draggable divider.
The window is fully resizable. The board always stays square.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

from sudoku.controller import Controller
from sudoku.events.bus import EventBus
from sudoku.events.types import ThemeChanged
from sudoku.gui.board_widget import BoardWidget, CELL_SIZE
from sudoku.gui.control_panel import ControlPanel
from sudoku.gui.status_bar import StatusBar
from sudoku.gui.theme import ThemeManager

# ---------------------------------------------------------------------------
# Layout defaults
# ---------------------------------------------------------------------------

SIDE_PANEL_W  = 270          # fixed width for the control panel
STATUS_H      = 32
MIN_BOARD_PX  = 288          # 32 px/cell minimum
DIVIDER_W     = 5            # draggable divider thickness
FPS           = 60
WINDOW_TITLE  = "Sudoku Solver"
DEFAULT_GRID  = CELL_SIZE * 9  # 576


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


# ---------------------------------------------------------------------------
# DividerDragger — tracks dragging the panel separator
# ---------------------------------------------------------------------------

class DividerDragger:
    """Tracks dragging of the vertical divider between board and side panel."""

    def __init__(self, x: int) -> None:
        self._x       = x
        self._dragging = False
        self._drag_off = 0

    @property
    def x(self) -> int:
        return self._x

    def rect(self, window_h: int, status_h: int) -> pygame.Rect:
        return pygame.Rect(self._x, 0, DIVIDER_W, window_h - status_h)

    def handle_event(
        self,
        event: pygame.event.Event,
        window_w: int,
        window_h: int,
    ) -> bool:
        divider = self.rect(window_h, STATUS_H)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if divider.collidepoint(event.pos):
                self._dragging = True
                self._drag_off = event.pos[0] - self._x
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        if event.type == pygame.MOUSEMOTION and self._dragging:
            new_x = event.pos[0] - self._drag_off
            self._x = _clamp(new_x, MIN_BOARD_PX, window_w - SIDE_PANEL_W - DIVIDER_W)
            return True
        return False

    def cursor(self, window_h: int) -> bool:
        """Return True if mouse is over the divider (for cursor change)."""
        mx, my = pygame.mouse.get_pos()
        return self.rect(window_h, STATUS_H).collidepoint(mx, my)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    window_w = DEFAULT_GRID + DIVIDER_W + SIDE_PANEL_W
    window_h = DEFAULT_GRID + STATUS_H
    screen = pygame.display.set_mode((window_w, window_h), pygame.RESIZABLE)
    clock  = pygame.time.Clock()

    # Cursor resources
    resize_cursor  = pygame.SYSTEM_CURSOR_SIZEWE
    default_cursor = pygame.SYSTEM_CURSOR_ARROW
    wait_cursor    = pygame.SYSTEM_CURSOR_WAIT

    # Shared state
    bus           = EventBus.get_instance()
    theme_manager = ThemeManager(default="light")
    divider       = DividerDragger(x=DEFAULT_GRID)
    generating    = False  # True while random puzzle is being generated

    # --- Build widgets ---
    def board_rect() -> pygame.Rect:
        grid_px = divider.x
        return pygame.Rect(0, 0, grid_px, grid_px)

    def panel_rect() -> pygame.Rect:
        panel_x = divider.x + DIVIDER_W
        panel_w = screen.get_width() - panel_x
        return pygame.Rect(panel_x, 0, panel_w, screen.get_height() - STATUS_H)

    def status_rect() -> pygame.Rect:
        w, h = screen.get_size()
        return pygame.Rect(0, h - STATUS_H, w, STATUS_H)

    # Controller
    controller = Controller(bus=bus, puzzles_dir=Path("puzzles"))

    # Board widget
    board_widget = BoardWidget(
        surface=screen,
        rect=board_rect(),
        theme_manager=theme_manager,
        bus=bus,
    )

    # Control panel
    control_panel = ControlPanel(
        surface=screen,
        rect=panel_rect(),
        theme_manager=theme_manager,
        on_solve=controller.solve,
        on_load=controller.load_puzzle,
        on_reset=controller.reset_puzzle,
        on_new=controller.new_board,
        bus=bus,
    )

    # Status bar
    status_bar = StatusBar(
        surface=screen,
        rect=status_rect(),
        theme_manager=theme_manager,
        bus=bus,
    )

    # --- Keyboard shortcuts ---
    def handle_global_keys(event: pygame.event.Event) -> bool:
        mods = pygame.key.get_mods()
        if event.type != pygame.KEYDOWN:
            return False

        if mods & pygame.KMOD_CTRL:
            if event.key == pygame.K_z:
                controller._on_undo(None)   # type: ignore[arg-type]
                return True
            if event.key == pygame.K_y:
                controller._on_redo(None)   # type: ignore[arg-type]
                return True
            if event.key == pygame.K_o:
                controller.load_puzzle()
                return True
            if event.key == pygame.K_n:
                controller.new_board()
                return True

        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            controller.solve()
            return True
        if event.key == pygame.K_t:
            name = theme_manager.toggle()
            bus.publish(ThemeChanged(theme_name=name))
            return True
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit(0)

        return False

    # --- Main loop ---
    running = True
    while running:
        w, h = screen.get_size()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            # Divider drag
            if divider.handle_event(event, w, h):
                # Update widget rects after divider moved
                br = board_rect()
                board_widget._rect    = br
                board_widget._cell_w  = br.width  // 9
                board_widget._cell_h  = br.height // 9
                board_widget._digit_font = None
                board_widget._cand_font  = None
                control_panel._rect   = panel_rect()
                control_panel._rebuild_layout()
                status_bar._rect      = status_rect()
                continue

            # Window resize
            if event.type == pygame.VIDEORESIZE:
                new_w, new_h = event.w, event.h
                # Keep divider proportional
                ratio = divider.x / w if w > 0 else 0.68
                new_div_x = _clamp(
                    int(ratio * new_w),
                    MIN_BOARD_PX,
                    new_w - SIDE_PANEL_W - DIVIDER_W,
                )
                divider._x = new_div_x

                br = board_rect()
                board_widget._rect    = br
                board_widget._cell_w  = br.width  // 9
                board_widget._cell_h  = br.height // 9
                board_widget._digit_font = None
                board_widget._cand_font  = None
                control_panel._rect   = panel_rect()
                control_panel._rebuild_layout()
                status_bar._rect      = status_rect()
                continue

            if handle_global_keys(event):
                continue

            # Route to panel first, then board
            if not control_panel.handle_event(event):
                board_widget.handle_event(event)

        # Cursor
        if divider.cursor(h) or divider._dragging:
            pygame.mouse.set_cursor(resize_cursor)
        else:
            pygame.mouse.set_cursor(default_cursor)

        # Draw
        theme = theme_manager.active
        screen.fill(theme.bg)

        board_widget.draw()
        control_panel.draw()
        status_bar.draw()

        # Draw divider
        dv_rect = divider.rect(h, STATUS_H)
        pygame.draw.rect(screen, theme.grid_line_thick, dv_rect)

        # Draw panel border
        px = divider.x + DIVIDER_W
        pygame.draw.line(screen, theme.grid_line_thick, (px, 0), (px, h - STATUS_H), 1)

        pygame.display.flip()
        clock.tick(FPS)

    board_widget.unsubscribe()
    status_bar.unsubscribe()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
