"""BoardWidget — renders the 9×9 Sudoku grid using pygame-ce.

Responsibilities
----------------
- Draw the grid, cells, digits, and candidate numbers.
- Highlight selected cell, peers, same-value cells, errors.
- Handle mouse clicks and keyboard digit/arrow input.
- Publish SelectionChanged and CellChanged events via the EventBus.
- Subscribe to CellChanged, SolveStep, SolveComplete, PuzzleLoaded,
  PuzzleReset, ThemeChanged to keep itself in sync.
"""

from __future__ import annotations

import pygame

from sudoku.data.board import Board
from sudoku.data.cell import CellCoord
from sudoku.data.validator import Validator
from sudoku.events.bus import EventBus
from sudoku.events.types import (
    CellChanged,
    PuzzleLoaded,
    PuzzleReset,
    SelectionChanged,
    SolveComplete,
    SolveStep,
    ThemeChanged,
)
from sudoku.gui.theme import Theme, ThemeManager

# Grid geometry constants (in pixels, for a SIZE×SIZE widget).
CELL_SIZE = 64
GRID_SIZE = CELL_SIZE * 9          # 576
THIN_LINE = 1
THICK_LINE = 3
CANDIDATE_FONT_RATIO = 0.28        # fraction of CELL_SIZE
DIGIT_FONT_RATIO = 0.58


class BoardWidget:
    """Renders and handles interaction for the 9×9 board.

    Parameters
    ----------
    surface:
        The pygame Surface to draw onto.
    rect:
        The pixel rect this widget occupies on *surface*.
    theme_manager:
        Shared ThemeManager; widget reads theme.active on every draw.
    bus:
        The application EventBus (defaults to singleton).
    """

    SIZE = 9

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

        self._board: Board = Board.empty()
        self._selected: CellCoord | None = None
        self._solving = False

        # Fonts (initialised lazily after pygame.init())
        self._digit_font: pygame.font.Font | None = None
        self._cand_font: pygame.font.Font | None = None

        self._cell_w = rect.width // self.SIZE
        self._cell_h = rect.height // self.SIZE

        # Subscribe to events.
        self._bus.subscribe(CellChanged, self._on_cell_changed)
        self._bus.subscribe(SolveStep, self._on_solve_step)
        self._bus.subscribe(SolveComplete, self._on_solve_complete)
        self._bus.subscribe(PuzzleLoaded, self._on_puzzle_loaded)
        self._bus.subscribe(PuzzleReset, self._on_puzzle_reset)
        self._bus.subscribe(ThemeChanged, self._on_theme_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_board(self, board: Board) -> None:
        self._board = board
        self._selected = None

    @property
    def board(self) -> Board:
        return self._board

    def draw(self) -> None:
        """Draw the complete board widget onto self._surface."""
        theme = self._tm.active
        self._ensure_fonts()

        # Background
        pygame.draw.rect(self._surface, theme.bg, self._rect)

        # Cell backgrounds
        self._draw_cell_backgrounds(theme)

        # Grid lines
        self._draw_grid_lines(theme)

        # Digits / candidates
        self._draw_digits(theme)

        # Selection ring
        if self._selected is not None:
            self._draw_selection_ring(self._selected, theme)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process a pygame event.  Returns True if the event was consumed."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos)
        if event.type == pygame.KEYDOWN:
            return self._handle_key(event)
        return False

    def unsubscribe(self) -> None:
        """Remove all event subscriptions (call before destroying widget)."""
        self._bus.unsubscribe(CellChanged, self._on_cell_changed)
        self._bus.unsubscribe(SolveStep, self._on_solve_step)
        self._bus.unsubscribe(SolveComplete, self._on_solve_complete)
        self._bus.unsubscribe(PuzzleLoaded, self._on_puzzle_loaded)
        self._bus.unsubscribe(PuzzleReset, self._on_puzzle_reset)
        self._bus.unsubscribe(ThemeChanged, self._on_theme_changed)

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._digit_font is None:
            size = int(self._cell_h * DIGIT_FONT_RATIO)
            self._digit_font = pygame.font.SysFont("segoeui,arial,sans-serif", size, bold=True)
        if self._cand_font is None:
            size = int(self._cell_h * CANDIDATE_FONT_RATIO)
            self._cand_font = pygame.font.SysFont("segoeui,arial,sans-serif", size)

    def _coord_to_rect(self, coord: CellCoord) -> pygame.Rect:
        x = self._rect.left + coord.col * self._cell_w
        y = self._rect.top + coord.row * self._cell_h
        return pygame.Rect(x, y, self._cell_w, self._cell_h)

    def _pos_to_coord(self, pos: tuple[int, int]) -> CellCoord | None:
        mx, my = pos
        if not self._rect.collidepoint(mx, my):
            return None
        col = (mx - self._rect.left) // self._cell_w
        row = (my - self._rect.top) // self._cell_h
        if 0 <= row < self.SIZE and 0 <= col < self.SIZE:
            return CellCoord(row, col)
        return None

    def _draw_cell_backgrounds(self, theme: Theme) -> None:
        selected = self._selected
        peers: frozenset[CellCoord] = frozenset()
        selected_value = 0

        if selected is not None:
            peers = self._board.peers(selected)
            selected_value = self._board[selected].value

        # Get conflict coords
        validation = Validator.validate(self._board)
        conflicts = validation.conflict_coords

        for coord, cell in self._board:
            rect = self._coord_to_rect(coord)

            if coord in conflicts and cell.is_filled:
                colour = theme.cell_bg_error
            elif coord == selected:
                colour = theme.cell_bg_selected
            elif selected is not None and coord in peers:
                colour = theme.cell_bg_peer
            elif selected_value and cell.is_filled and cell.value == selected_value:
                colour = theme.cell_bg_same_value
            elif cell.is_given:
                colour = theme.cell_bg_given
            else:
                colour = theme.cell_bg

            pygame.draw.rect(self._surface, colour, rect)

    def _draw_grid_lines(self, theme: Theme) -> None:
        left = self._rect.left
        top = self._rect.top
        right = self._rect.right
        bottom = self._rect.bottom

        for i in range(self.SIZE + 1):
            thick = (i % 3 == 0)
            lw = THICK_LINE if thick else THIN_LINE
            colour = theme.grid_line_thick if thick else theme.grid_line_thin

            # Horizontal
            y = top + i * self._cell_h
            pygame.draw.line(self._surface, colour, (left, y), (right, y), lw)

            # Vertical
            x = left + i * self._cell_w
            pygame.draw.line(self._surface, colour, (x, top), (x, bottom), lw)

    def _draw_digits(self, theme: Theme) -> None:
        assert self._digit_font is not None
        assert self._cand_font is not None

        validation = Validator.validate(self._board)
        conflicts = validation.conflict_coords

        for coord, cell in self._board:
            rect = self._coord_to_rect(coord)

            if cell.is_filled:
                if coord in conflicts:
                    colour = theme.digit_error
                elif cell.is_given:
                    colour = theme.digit_given
                else:
                    colour = theme.digit_solver if cell.is_highlighted else theme.digit_user

                surf = self._digit_font.render(str(cell.value), True, colour)
                r = surf.get_rect(center=rect.center)
                self._surface.blit(surf, r)

            elif cell.candidates:
                self._draw_candidates(coord, cell.candidates, rect, theme)

    def _draw_candidates(
        self,
        coord: CellCoord,
        candidates: frozenset[int],
        rect: pygame.Rect,
        theme: Theme,
    ) -> None:
        assert self._cand_font is not None
        sub_w = self._cell_w // 3
        sub_h = self._cell_h // 3

        for digit in range(1, 10):
            if digit not in candidates:
                continue
            sub_row = (digit - 1) // 3
            sub_col = (digit - 1) % 3
            cx = rect.left + sub_col * sub_w + sub_w // 2
            cy = rect.top + sub_row * sub_h + sub_h // 2
            surf = self._cand_font.render(str(digit), True, theme.candidate_fg)
            r = surf.get_rect(center=(cx, cy))
            self._surface.blit(surf, r)

    def _draw_selection_ring(self, coord: CellCoord, theme: Theme) -> None:
        rect = self._coord_to_rect(coord)
        pygame.draw.rect(self._surface, theme.highlight_ring, rect, 3)

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def _handle_click(self, pos: tuple[int, int]) -> bool:
        coord = self._pos_to_coord(pos)
        if coord is None:
            return False
        self._selected = coord
        self._bus.publish(SelectionChanged(coord=coord))
        return True

    def _handle_key(self, event: pygame.event.Event) -> bool:
        key = event.key
        # Arrow navigation first — prevents any accidental digit fallthrough
        if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
            return self._move_selection(key)
        # Clear cell
        if key in (pygame.K_0, pygame.K_KP0, pygame.K_BACKSPACE, pygame.K_DELETE):
            return self._place_digit(0)
        # Top-row digits 1-9 (explicit map, no arithmetic)
        row_map = {
            pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3,
            pygame.K_4: 4, pygame.K_5: 5, pygame.K_6: 6,
            pygame.K_7: 7, pygame.K_8: 8, pygame.K_9: 9,
        }
        if key in row_map:
            return self._place_digit(row_map[key])
        # Numpad digits 1-9 (explicit map, no arithmetic)
        kp_map = {
            pygame.K_KP1: 1, pygame.K_KP2: 2, pygame.K_KP3: 3,
            pygame.K_KP4: 4, pygame.K_KP5: 5, pygame.K_KP6: 6,
            pygame.K_KP7: 7, pygame.K_KP8: 8, pygame.K_KP9: 9,
        }
        if key in kp_map:
            return self._place_digit(kp_map[key])
        return False

    def _place_digit(self, digit: int) -> bool:
        if self._selected is None or self._solving:
            return False
        cell = self._board[self._selected]
        if cell.is_given:
            return False
        old_value = cell.value
        if old_value == digit:
            return True  # no change
        self._board = self._board.set_value(self._selected, digit)
        self._bus.publish(
            CellChanged(
                coord=self._selected,
                old_value=old_value,
                new_value=digit,
                by_solver=False,
            )
        )
        return True

    def _move_selection(self, key: int) -> bool:
        if self._selected is None:
            self._selected = CellCoord(0, 0)
            self._bus.publish(SelectionChanged(coord=self._selected))
            return True

        r, c = self._selected
        delta = {
            pygame.K_UP: (-1, 0),
            pygame.K_DOWN: (1, 0),
            pygame.K_LEFT: (0, -1),
            pygame.K_RIGHT: (0, 1),
        }[key]
        new_r = max(0, min(8, r + delta[0]))
        new_c = max(0, min(8, c + delta[1]))
        self._selected = CellCoord(new_r, new_c)
        self._bus.publish(SelectionChanged(coord=self._selected))
        return True

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_cell_changed(self, event: CellChanged) -> None:
        self._board = self._board.set_value(event.coord, event.new_value)

    def _on_solve_step(self, event: SolveStep) -> None:
        self._solving = True
        cell = self._board[event.coord].with_value(event.value).with_highlight(True)
        self._board = self._board.set_cell(event.coord, cell)

    def _on_solve_complete(self, event: SolveComplete) -> None:
        self._solving = False
        self._board = event.board

    def _on_puzzle_loaded(self, event: PuzzleLoaded) -> None:
        self._board = event.board
        self._selected = None
        self._solving = False

    def _on_puzzle_reset(self, event: PuzzleReset) -> None:
        self._board = event.board
        self._selected = None
        self._solving = False

    def _on_theme_changed(self, event: ThemeChanged) -> None:
        pass  # ThemeManager.active is read on every draw(); nothing to cache.
