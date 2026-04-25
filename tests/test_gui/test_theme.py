"""Tests for sudoku.gui.theme — Theme dataclass and ThemeManager."""

from __future__ import annotations

import pytest

from sudoku.gui.theme import (
    DARK_THEME,
    LIGHT_THEME,
    SOLARIZED_THEME,
    Theme,
    ThemeManager,
)


# ---------------------------------------------------------------------------
# Theme dataclass
# ---------------------------------------------------------------------------


class TestTheme:
    """Tests for the Theme frozen dataclass."""

    def test_light_theme_name(self) -> None:
        assert LIGHT_THEME.name == "light"

    def test_dark_theme_name(self) -> None:
        assert DARK_THEME.name == "dark"

    def test_solarized_theme_name(self) -> None:
        assert SOLARIZED_THEME.name == "solarized"

    def test_theme_is_frozen(self) -> None:
        with pytest.raises((AttributeError, TypeError)):
            LIGHT_THEME.name = "modified"  # type: ignore[misc]

    def test_all_colour_fields_are_tuples(self) -> None:
        for theme in (LIGHT_THEME, DARK_THEME, SOLARIZED_THEME):
            colour_fields = [
                theme.bg, theme.panel_bg, theme.status_bg,
                theme.grid_line_thin, theme.grid_line_thick,
                theme.cell_bg, theme.cell_bg_given, theme.cell_bg_selected,
                theme.cell_bg_peer, theme.cell_bg_same_value,
                theme.cell_bg_error, theme.cell_bg_solved,
                theme.digit_given, theme.digit_user,
                theme.digit_solver, theme.digit_error,
                theme.candidate_fg, theme.button_bg, theme.button_bg_hover,
                theme.button_bg_active, theme.button_fg, theme.button_border,
                theme.status_fg, theme.highlight_ring,
            ]
            for colour in colour_fields:
                assert isinstance(colour, tuple), (
                    f"{theme.name}: expected tuple, got {type(colour)} for a colour field"
                )

    def test_rgb_components_in_valid_range(self) -> None:
        for theme in (LIGHT_THEME, DARK_THEME, SOLARIZED_THEME):
            for colour in (theme.bg, theme.cell_bg, theme.digit_given):
                for component in colour[:3]:  # ignore optional alpha
                    assert 0 <= component <= 255, (
                        f"{theme.name}: component {component} out of range in {colour}"
                    )

    def test_themes_have_distinct_backgrounds(self) -> None:
        assert LIGHT_THEME.bg != DARK_THEME.bg
        assert DARK_THEME.bg != SOLARIZED_THEME.bg
        assert LIGHT_THEME.bg != SOLARIZED_THEME.bg

    def test_custom_theme_creation(self) -> None:
        custom = Theme(
            name="custom",
            bg=(10, 20, 30),
            panel_bg=(15, 25, 35),
            status_bg=(5, 10, 15),
            grid_line_thin=(50, 50, 50),
            grid_line_thick=(100, 100, 100),
            cell_bg=(200, 200, 200),
            cell_bg_given=(180, 180, 180),
            cell_bg_selected=(150, 200, 255),
            cell_bg_peer=(170, 190, 210),
            cell_bg_same_value=(160, 220, 160),
            cell_bg_error=(255, 160, 160),
            cell_bg_solved=(160, 240, 160),
            digit_given=(20, 20, 20),
            digit_user=(0, 80, 200),
            digit_solver=(0, 150, 80),
            digit_error=(200, 20, 20),
            candidate_fg=(120, 130, 140),
            button_bg=(190, 195, 205),
            button_bg_hover=(170, 180, 205),
            button_bg_active=(140, 160, 205),
            button_fg=(20, 20, 30),
            button_border=(140, 145, 160),
            status_fg=(50, 50, 60),
            highlight_ring=(60, 120, 220),
        )
        assert custom.name == "custom"
        assert custom.bg == (10, 20, 30)


# ---------------------------------------------------------------------------
# ThemeManager
# ---------------------------------------------------------------------------


class TestThemeManager:
    """Tests for ThemeManager — registry and active-theme tracking."""

    def test_default_is_light(self) -> None:
        tm = ThemeManager()
        assert tm.active.name == "light"

    def test_explicit_default_dark(self) -> None:
        tm = ThemeManager(default="dark")
        assert tm.active.name == "dark"

    def test_unknown_default_falls_back_to_light(self) -> None:
        tm = ThemeManager(default="nonexistent")
        assert tm.active.name == "light"

    def test_set_theme_changes_active(self) -> None:
        tm = ThemeManager()
        tm.set_theme("dark")
        assert tm.active.name == "dark"

    def test_set_theme_unknown_raises_key_error(self) -> None:
        tm = ThemeManager()
        with pytest.raises(KeyError):
            tm.set_theme("invalid_theme")

    def test_toggle_cycles_through_themes(self) -> None:
        tm = ThemeManager()
        first = tm.active.name
        second = tm.toggle()
        assert second != first
        third = tm.toggle()
        assert third != second
        # After cycling through all 3 built-ins, wraps back to first
        fourth = tm.toggle()
        assert fourth == first

    def test_toggle_returns_new_name(self) -> None:
        tm = ThemeManager()
        returned = tm.toggle()
        assert returned == tm.active.name

    def test_available_contains_all_builtins(self) -> None:
        tm = ThemeManager()
        assert "light" in tm.available
        assert "dark" in tm.available
        assert "solarized" in tm.available

    def test_register_custom_theme(self) -> None:
        tm = ThemeManager()
        custom = Theme(
            name="my_theme",
            bg=(1, 2, 3), panel_bg=(1, 2, 3), status_bg=(1, 2, 3),
            grid_line_thin=(1, 2, 3), grid_line_thick=(1, 2, 3),
            cell_bg=(1, 2, 3), cell_bg_given=(1, 2, 3),
            cell_bg_selected=(1, 2, 3), cell_bg_peer=(1, 2, 3),
            cell_bg_same_value=(1, 2, 3), cell_bg_error=(1, 2, 3),
            cell_bg_solved=(1, 2, 3), digit_given=(1, 2, 3),
            digit_user=(1, 2, 3), digit_solver=(1, 2, 3),
            digit_error=(1, 2, 3), candidate_fg=(1, 2, 3),
            button_bg=(1, 2, 3), button_bg_hover=(1, 2, 3),
            button_bg_active=(1, 2, 3), button_fg=(1, 2, 3),
            button_border=(1, 2, 3), status_fg=(1, 2, 3),
            highlight_ring=(1, 2, 3),
        )
        tm.register(custom)
        assert "my_theme" in tm.available
        tm.set_theme("my_theme")
        assert tm.active.name == "my_theme"

    def test_register_overwrites_existing_name(self) -> None:
        tm = ThemeManager()
        replacement = Theme(
            name="light",
            bg=(99, 99, 99), panel_bg=(1, 2, 3), status_bg=(1, 2, 3),
            grid_line_thin=(1, 2, 3), grid_line_thick=(1, 2, 3),
            cell_bg=(1, 2, 3), cell_bg_given=(1, 2, 3),
            cell_bg_selected=(1, 2, 3), cell_bg_peer=(1, 2, 3),
            cell_bg_same_value=(1, 2, 3), cell_bg_error=(1, 2, 3),
            cell_bg_solved=(1, 2, 3), digit_given=(1, 2, 3),
            digit_user=(1, 2, 3), digit_solver=(1, 2, 3),
            digit_error=(1, 2, 3), candidate_fg=(1, 2, 3),
            button_bg=(1, 2, 3), button_bg_hover=(1, 2, 3),
            button_bg_active=(1, 2, 3), button_fg=(1, 2, 3),
            button_border=(1, 2, 3), status_fg=(1, 2, 3),
            highlight_ring=(1, 2, 3),
        )
        tm.register(replacement)
        tm.set_theme("light")
        assert tm.active.bg == (99, 99, 99)

    def test_available_count_default(self) -> None:
        tm = ThemeManager()
        assert len(tm.available) == 3

    def test_active_returns_theme_instance(self) -> None:
        tm = ThemeManager()
        assert isinstance(tm.active, Theme)

    def test_independent_instances_do_not_share_state(self) -> None:
        tm1 = ThemeManager(default="light")
        tm2 = ThemeManager(default="dark")
        assert tm1.active.name == "light"
        assert tm2.active.name == "dark"
        tm1.toggle()
        assert tm2.active.name == "dark"  # tm2 unaffected
