"""Tests for sudoku.app — entry-point constants and layout logic."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch
import pytest
import pygame

# Stub the empty controller __init__ before importing app
from sudoku.controller import controller as _ctrl_mod
import sudoku.controller as _ctrl_pkg
if not hasattr(_ctrl_pkg, "Controller"):
    _ctrl_pkg.Controller = _ctrl_mod.Controller  # type: ignore[attr-defined]

from sudoku.app import (  # noqa: E402
    FPS,
    PANEL_W,
    STATUS_H,
    WINDOW_H,
    WINDOW_TITLE,
    WINDOW_W,
)
from sudoku.gui.board_widget import GRID_SIZE


# ---------------------------------------------------------------------------
# Window / layout constants
# ---------------------------------------------------------------------------


class TestLayoutConstants:
    def test_status_height(self) -> None:
        assert STATUS_H == 32

    def test_panel_width(self) -> None:
        assert PANEL_W == 220

    def test_window_width_equals_grid_plus_panel(self) -> None:
        assert WINDOW_W == GRID_SIZE + PANEL_W

    def test_window_height_equals_grid_plus_status(self) -> None:
        assert WINDOW_H == GRID_SIZE + STATUS_H

    def test_fps_is_positive(self) -> None:
        assert FPS > 0

    def test_window_title_is_string(self) -> None:
        assert isinstance(WINDOW_TITLE, str)
        assert len(WINDOW_TITLE) > 0

    def test_grid_size_is_576(self) -> None:
        assert GRID_SIZE == 576

    def test_window_width_numerical(self) -> None:
        assert WINDOW_W == 796  # 576 + 220

    def test_window_height_numerical(self) -> None:
        assert WINDOW_H == 608  # 576 + 32


# ---------------------------------------------------------------------------
# Layout rect calculations (derived from constants)
# ---------------------------------------------------------------------------


class TestLayoutRects:
    def test_board_rect_covers_grid(self) -> None:
        board_rect = pygame.Rect(0, 0, GRID_SIZE, GRID_SIZE)
        assert board_rect.width == GRID_SIZE
        assert board_rect.height == GRID_SIZE

    def test_panel_rect_starts_at_grid_right_edge(self) -> None:
        panel_rect = pygame.Rect(GRID_SIZE, 0, WINDOW_W - GRID_SIZE, GRID_SIZE)
        assert panel_rect.left == GRID_SIZE
        assert panel_rect.width == PANEL_W

    def test_status_rect_starts_below_grid(self) -> None:
        status_rect = pygame.Rect(0, GRID_SIZE, WINDOW_W, STATUS_H)
        assert status_rect.top == GRID_SIZE
        assert status_rect.height == STATUS_H
        assert status_rect.width == WINDOW_W

    def test_board_and_panel_share_top_edge(self) -> None:
        board_rect = pygame.Rect(0, 0, GRID_SIZE, GRID_SIZE)
        panel_rect = pygame.Rect(GRID_SIZE, 0, WINDOW_W - GRID_SIZE, GRID_SIZE)
        assert board_rect.top == panel_rect.top

    def test_board_and_panel_share_height(self) -> None:
        board_rect = pygame.Rect(0, 0, GRID_SIZE, GRID_SIZE)
        panel_rect = pygame.Rect(GRID_SIZE, 0, WINDOW_W - GRID_SIZE, GRID_SIZE)
        assert board_rect.height == panel_rect.height

    def test_no_gap_between_board_and_panel(self) -> None:
        board_rect = pygame.Rect(0, 0, GRID_SIZE, GRID_SIZE)
        panel_rect = pygame.Rect(GRID_SIZE, 0, WINDOW_W - GRID_SIZE, GRID_SIZE)
        assert board_rect.right == panel_rect.left

    def test_no_gap_between_grid_and_status(self) -> None:
        board_rect = pygame.Rect(0, 0, GRID_SIZE, GRID_SIZE)
        status_rect = pygame.Rect(0, GRID_SIZE, WINDOW_W, STATUS_H)
        assert board_rect.bottom == status_rect.top

    def test_total_height_equals_window_height(self) -> None:
        assert GRID_SIZE + STATUS_H == WINDOW_H

    def test_total_width_equals_window_width(self) -> None:
        assert GRID_SIZE + PANEL_W == WINDOW_W


# ---------------------------------------------------------------------------
# Resize logic (extracted from main's VIDEORESIZE handler)
# ---------------------------------------------------------------------------


class TestResizeLogic:
    def _compute_resize(
        self, w: int, h: int, panel_w: int = PANEL_W, status_h: int = STATUS_H
    ) -> int:
        new_grid = min(w - panel_w, h - status_h)
        new_grid = max(new_grid, 288)
        return new_grid

    def test_resize_standard_window(self) -> None:
        new_grid = self._compute_resize(WINDOW_W, WINDOW_H)
        assert new_grid == GRID_SIZE

    def test_resize_enforces_minimum(self) -> None:
        new_grid = self._compute_resize(100, 100)
        assert new_grid == 288

    def test_resize_width_constrained(self) -> None:
        new_grid = self._compute_resize(1200, 400)
        assert new_grid == 400 - STATUS_H

    def test_resize_height_constrained(self) -> None:
        new_grid = self._compute_resize(500, 1200)
        assert new_grid == 288  # 500 - 220 = 280 < 288 minimum, so clamped

    def test_resize_never_below_minimum(self) -> None:
        for w, h in [(0, 0), (10, 10), (300, 300), (PANEL_W, STATUS_H)]:
            new_grid = self._compute_resize(w, h)
            assert new_grid >= 288


# ---------------------------------------------------------------------------
# main() — smoke test (mocked pygame, no display required)
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_quits_on_quit_event(self) -> None:
        with (
            patch("sudoku.app.pygame.init"),
            patch("sudoku.app.pygame.display.set_caption"),
            patch("sudoku.app.pygame.display.set_mode") as mock_mode,
            patch("sudoku.app.pygame.time.Clock") as mock_clock,
            patch("sudoku.app.pygame.event.get") as mock_get,
            patch("sudoku.app.pygame.display.flip"),
            patch("sudoku.app.pygame.quit"),
            patch("sudoku.app.sys.exit", side_effect=SystemExit),
            patch("sudoku.app.Controller"),
            patch("sudoku.app.BoardWidget") as mock_bw,
            patch("sudoku.app.ControlPanel") as mock_cp,
            patch("sudoku.app.StatusBar") as mock_sb,
        ):
            surface = MagicMock()
            mock_mode.return_value = surface

            clock = MagicMock()
            mock_clock.return_value = clock

            quit_event = MagicMock()
            quit_event.type = pygame.QUIT
            mock_get.return_value = [quit_event]

            board_widget = MagicMock()
            control_panel = MagicMock()
            status_bar = MagicMock()
            mock_bw.return_value = board_widget
            mock_cp.return_value = control_panel
            mock_sb.return_value = status_bar

            from sudoku.app import main
            with pytest.raises(SystemExit):
                main()

        board_widget.unsubscribe.assert_called_once()
        status_bar.unsubscribe.assert_called_once()
