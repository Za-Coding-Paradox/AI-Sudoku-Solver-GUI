"""app.py — pygame-ce application entry point.

Initialises pygame, builds the layout, wires the Controller, runs the loop.

Layout (default 900×640 window)
---------------------------------
┌──────────────────┬────────────┐
│                  │            │
│   BoardWidget    │  Control   │
│   576 × 576      │  Panel     │
│                  │  324 × 576 │
├──────────────────┴────────────┤
│         StatusBar  900 × 32   │
└───────────────────────────────┘
"""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

from sudoku.controller import Controller
from sudoku.events.bus import EventBus
from sudoku.events.types import ThemeChanged
from sudoku.gui.board_widget import BoardWidget, GRID_SIZE
from sudoku.gui.control_panel import ControlPanel
from sudoku.gui.status_bar import StatusBar
from sudoku.gui.theme import ThemeManager

# ---------------------------------------------------------------------------
# Window constants
# ---------------------------------------------------------------------------

STATUS_H = 32
PANEL_W = 220
WINDOW_W = GRID_SIZE + PANEL_W          # 576 + 220 = 796
WINDOW_H = GRID_SIZE + STATUS_H         # 576 + 32  = 608
FPS = 60
WINDOW_TITLE = "Sudoku Solver — pygame-ce"


def main() -> None:
    """Application entry point."""
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    # --- Shared objects ---
    bus = EventBus.get_instance()
    theme_manager = ThemeManager(default="light")

    # --- Layout rects ---
    board_rect = pygame.Rect(0, 0, GRID_SIZE, GRID_SIZE)
    panel_rect = pygame.Rect(GRID_SIZE, 0, WINDOW_W - GRID_SIZE, GRID_SIZE)
    status_rect = pygame.Rect(0, GRID_SIZE, WINDOW_W, STATUS_H)

    # --- Controller ---
    controller = Controller(bus=bus, puzzles_dir=Path("puzzles"))

    # --- GUI widgets ---
    board_widget = BoardWidget(
        surface=screen,
        rect=board_rect,
        theme_manager=theme_manager,
        bus=bus,
    )
    control_panel = ControlPanel(
        surface=screen,
        rect=panel_rect,
        theme_manager=theme_manager,
        on_solve=controller.solve,
        on_load=controller.load_puzzle,
        on_reset=controller.reset_puzzle,
        on_new=controller.new_board,
        bus=bus,
    )
    status_bar = StatusBar(
        surface=screen,
        rect=status_rect,
        theme_manager=theme_manager,
        bus=bus,
    )

    # --- Keyboard shortcuts ---
    def handle_global_keys(event: pygame.event.Event) -> bool:
        mods = pygame.key.get_mods()
        if event.type == pygame.KEYDOWN:
            if mods & pygame.KMOD_CTRL:
                if event.key == pygame.K_z:
                    controller._on_undo(None)  # type: ignore[arg-type]
                    return True
                if event.key == pygame.K_y:
                    controller._on_redo(None)  # type: ignore[arg-type]
                    return True
                if event.key == pygame.K_o:
                    controller.load_puzzle()
                    return True
                if event.key == pygame.K_n:
                    controller.new_board()
                    return True
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if handle_global_keys(event):
                continue

            if event.type == pygame.VIDEORESIZE:
                # Recalculate layout on resize.
                w, h = event.w, event.h
                new_grid = min(w - PANEL_W, h - STATUS_H)
                new_grid = max(new_grid, 288)  # minimum 288 px (32 px/cell)
                board_widget._rect = pygame.Rect(0, 0, new_grid, new_grid)
                board_widget._cell_w = new_grid // 9
                board_widget._cell_h = new_grid // 9
                board_widget._digit_font = None
                board_widget._cand_font = None
                panel_rect = pygame.Rect(new_grid, 0, w - new_grid, new_grid)
                control_panel._rect = panel_rect
                status_rect = pygame.Rect(0, new_grid, w, STATUS_H)
                status_bar._rect = status_rect
                continue

            # Route events: panel first, then board.
            if not control_panel.handle_event(event):
                board_widget.handle_event(event)

        # Draw
        screen.fill(theme_manager.active.bg)
        board_widget.draw()
        control_panel.draw()
        status_bar.draw()
        pygame.display.flip()
        clock.tick(FPS)

    board_widget.unsubscribe()
    status_bar.unsubscribe()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
