"""Theme — data-driven colour and font definitions for the GUI.

All visual constants live here as plain Python dicts.  The GUI widgets
never hard-code colours; they always look them up via the active Theme.
Switching themes at runtime is a single ThemeManager.set_theme() call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Colour type alias (R, G, B) or (R, G, B, A)
# ---------------------------------------------------------------------------

Colour = tuple[int, int, int] | tuple[int, int, int, int]


# ---------------------------------------------------------------------------
# Theme dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Theme:
    """A complete visual theme.

    All colours are (R, G, B) tuples compatible with pygame.Color.

    Attributes
    ----------
    name:                  Unique key, e.g. "light" or "dark".
    bg:                    Window / board background.
    grid_line_thin:        Colour for the thin lines between cells.
    grid_line_thick:       Colour for the thick lines between 3×3 boxes.
    cell_bg:               Default cell background.
    cell_bg_given:         Background for given (locked) cells.
    cell_bg_selected:      Background for the selected cell.
    cell_bg_peer:          Background for peers of the selected cell.
    cell_bg_same_value:    Background for cells sharing the selected digit.
    cell_bg_error:         Background for cells with a conflict.
    cell_bg_solved:        Background for solver-placed cells.
    digit_given:           Colour for given (locked) digits.
    digit_user:            Colour for user-entered digits.
    digit_solver:          Colour for solver-placed digits.
    digit_error:           Colour for conflicting digits.
    candidate_fg:          Colour for small candidate numbers.
    panel_bg:              Control panel background.
    button_bg:             Normal button background.
    button_bg_hover:       Hovered button background.
    button_bg_active:      Pressed button background.
    button_fg:             Button text colour.
    button_border:         Button border colour.
    status_bg:             Status bar background.
    status_fg:             Status bar text colour.
    highlight_ring:        Colour of the selection ring drawn over a cell.
    """

    name: str

    # Background
    bg: Colour
    panel_bg: Colour
    status_bg: Colour

    # Grid lines
    grid_line_thin: Colour
    grid_line_thick: Colour

    # Cell backgrounds
    cell_bg: Colour
    cell_bg_given: Colour
    cell_bg_selected: Colour
    cell_bg_peer: Colour
    cell_bg_same_value: Colour
    cell_bg_error: Colour
    cell_bg_solved: Colour

    # Digit colours
    digit_given: Colour
    digit_user: Colour
    digit_solver: Colour
    digit_error: Colour

    # Candidate colours
    candidate_fg: Colour

    # Buttons
    button_bg: Colour
    button_bg_hover: Colour
    button_bg_active: Colour
    button_fg: Colour
    button_border: Colour

    # Status bar
    status_fg: Colour

    # Selection ring
    highlight_ring: Colour


# ---------------------------------------------------------------------------
# Built-in themes
# ---------------------------------------------------------------------------

LIGHT_THEME = Theme(
    name="light",
    bg=(245, 245, 245),
    panel_bg=(230, 230, 235),
    status_bg=(215, 215, 220),

    grid_line_thin=(190, 190, 200),
    grid_line_thick=(60, 60, 70),

    cell_bg=(255, 255, 255),
    cell_bg_given=(235, 235, 240),
    cell_bg_selected=(195, 220, 255),
    cell_bg_peer=(225, 235, 248),
    cell_bg_same_value=(210, 240, 210),
    cell_bg_error=(255, 210, 210),
    cell_bg_solved=(220, 245, 220),

    digit_given=(30, 30, 40),
    digit_user=(20, 80, 180),
    digit_solver=(0, 140, 80),
    digit_error=(200, 30, 30),

    candidate_fg=(130, 140, 160),

    button_bg=(200, 205, 215),
    button_bg_hover=(175, 185, 210),
    button_bg_active=(145, 165, 210),
    button_fg=(30, 30, 40),
    button_border=(150, 155, 170),

    status_fg=(60, 60, 70),
    highlight_ring=(70, 130, 230),
)

DARK_THEME = Theme(
    name="dark",
    bg=(28, 28, 35),
    panel_bg=(38, 38, 48),
    status_bg=(22, 22, 30),

    grid_line_thin=(65, 65, 80),
    grid_line_thick=(160, 160, 175),

    cell_bg=(42, 42, 55),
    cell_bg_given=(55, 55, 68),
    cell_bg_selected=(45, 80, 130),
    cell_bg_peer=(42, 58, 80),
    cell_bg_same_value=(38, 80, 55),
    cell_bg_error=(100, 35, 35),
    cell_bg_solved=(35, 75, 50),

    digit_given=(220, 220, 235),
    digit_user=(110, 175, 255),
    digit_solver=(80, 220, 140),
    digit_error=(255, 100, 100),

    candidate_fg=(100, 105, 130),

    button_bg=(58, 58, 72),
    button_bg_hover=(75, 75, 95),
    button_bg_active=(95, 105, 140),
    button_fg=(210, 210, 225),
    button_border=(80, 80, 100),

    status_fg=(170, 170, 185),
    highlight_ring=(80, 155, 255),
)

SOLARIZED_THEME = Theme(
    name="solarized",
    bg=(0, 43, 54),
    panel_bg=(7, 54, 66),
    status_bg=(0, 35, 45),

    grid_line_thin=(42, 79, 91),
    grid_line_thick=(147, 161, 161),

    cell_bg=(7, 54, 66),
    cell_bg_given=(0, 43, 54),
    cell_bg_selected=(38, 139, 210, 80),
    cell_bg_peer=(7, 63, 76),
    cell_bg_same_value=(133, 153, 0, 60),
    cell_bg_error=(220, 50, 47, 80),
    cell_bg_solved=(42, 161, 152, 50),

    digit_given=(147, 161, 161),
    digit_user=(38, 139, 210),
    digit_solver=(42, 161, 152),
    digit_error=(220, 50, 47),

    candidate_fg=(88, 110, 117),

    button_bg=(0, 43, 54),
    button_bg_hover=(7, 54, 66),
    button_bg_active=(38, 139, 210),
    button_fg=(147, 161, 161),
    button_border=(42, 79, 91),

    status_fg=(101, 123, 131),
    highlight_ring=(38, 139, 210),
)


# ---------------------------------------------------------------------------
# ThemeManager
# ---------------------------------------------------------------------------

_BUILTIN_THEMES: dict[str, Theme] = {
    t.name: t for t in (LIGHT_THEME, DARK_THEME, SOLARIZED_THEME)
}


class ThemeManager:
    """Registry + active-theme tracker.

    Usage
    -----
    >>> tm = ThemeManager()
    >>> tm.active.bg
    (245, 245, 245)
    >>> tm.set_theme("dark")
    >>> tm.active.name
    'dark'
    """

    def __init__(self, default: str = "light") -> None:
        self._themes: dict[str, Theme] = dict(_BUILTIN_THEMES)
        if default not in self._themes:
            default = "light"
        self._active_name = default

    @property
    def active(self) -> Theme:
        """Return the currently active :class:`Theme`."""
        return self._themes[self._active_name]

    def set_theme(self, name: str) -> None:
        """Switch to *name*.  Raises KeyError on unknown names."""
        if name not in self._themes:
            raise KeyError(f"Unknown theme {name!r}. Available: {list(self._themes)}")
        self._active_name = name

    def toggle(self) -> str:
        """Cycle through built-in themes in order.  Returns the new name."""
        names = list(self._themes)
        idx = names.index(self._active_name)
        self._active_name = names[(idx + 1) % len(names)]
        return self._active_name

    def register(self, theme: Theme) -> None:
        """Register a custom theme."""
        self._themes[theme.name] = theme

    @property
    def available(self) -> list[str]:
        """Return all registered theme names."""
        return list(self._themes)
