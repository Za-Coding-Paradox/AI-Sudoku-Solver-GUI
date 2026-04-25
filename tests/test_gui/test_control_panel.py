"""Tests for sudoku.gui.control_panel — ControlPanel, _Button, _Slider."""

from __future__ import annotations

from unittest.mock import MagicMock

import pygame
import pytest

from sudoku.events.bus import EventBus
from sudoku.events.types import RedoRequested, SpeedChanged, ThemeChanged, UndoRequested
from sudoku.gui.control_panel import (
    BUTTON_HEIGHT,
    PADDING,
    ControlPanel,
    _Button,
    _Slider,
)
from sudoku.gui.theme import ThemeManager

PANEL_W = 220
PANEL_H = 576


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def pygame_init() -> None:  # type: ignore[return]
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture()
def surface() -> pygame.Surface:
    return pygame.Surface((PANEL_W, PANEL_H))


@pytest.fixture()
def panel_rect() -> pygame.Rect:
    return pygame.Rect(0, 0, PANEL_W, PANEL_H)


@pytest.fixture()
def theme_manager() -> ThemeManager:
    return ThemeManager(default="light")


@pytest.fixture()
def bus() -> EventBus:
    return EventBus.get_instance()


@pytest.fixture()
def callbacks() -> dict[str, MagicMock]:
    return {
        "on_solve": MagicMock(),
        "on_load": MagicMock(),
        "on_reset": MagicMock(),
        "on_new": MagicMock(),
    }


@pytest.fixture()
def panel(
    surface: pygame.Surface,
    panel_rect: pygame.Rect,
    theme_manager: ThemeManager,
    callbacks: dict[str, MagicMock],
    bus: EventBus,
) -> ControlPanel:
    return ControlPanel(
        surface=surface,
        rect=panel_rect,
        theme_manager=theme_manager,
        on_solve=callbacks["on_solve"],
        on_load=callbacks["on_load"],
        on_reset=callbacks["on_reset"],
        on_new=callbacks["on_new"],
        bus=bus,
    )


# ---------------------------------------------------------------------------
# _Button
# ---------------------------------------------------------------------------


class TestButton:
    def _make_button(self, label: str = "Test", callback: MagicMock | None = None) -> _Button:
        cb = callback or MagicMock()
        return _Button(label=label, rect=pygame.Rect(10, 10, 100, 40), on_click=cb)

    def test_label_stored(self) -> None:
        btn = self._make_button("Click Me")
        assert btn.label == "Click Me"

    def test_not_hovered_initially(self) -> None:
        btn = self._make_button()
        assert btn._hovered is False

    def test_not_pressed_initially(self) -> None:
        btn = self._make_button()
        assert btn._pressed is False

    def test_mouse_motion_sets_hovered_when_inside(self) -> None:
        btn = self._make_button()
        event = pygame.event.Event(pygame.MOUSEMOTION, pos=(50, 30), rel=(1, 0), buttons=(0, 0, 0))
        btn.handle_event(event)
        assert btn._hovered is True

    def test_mouse_motion_clears_hovered_when_outside(self) -> None:
        btn = self._make_button()
        btn._hovered = True
        event = pygame.event.Event(pygame.MOUSEMOTION, pos=(200, 200), rel=(1, 0), buttons=(0, 0, 0))
        btn.handle_event(event)
        assert btn._hovered is False

    def test_click_inside_calls_callback(self) -> None:
        cb = MagicMock()
        btn = self._make_button(callback=cb)
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 30))
        btn.handle_event(down)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(50, 30))
        btn.handle_event(up)
        cb.assert_called_once()

    def test_click_outside_does_not_call_callback(self) -> None:
        cb = MagicMock()
        btn = self._make_button(callback=cb)
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(200, 200))
        btn.handle_event(down)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(200, 200))
        btn.handle_event(up)
        cb.assert_not_called()

    def test_mousedown_inside_sets_pressed(self) -> None:
        btn = self._make_button()
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 30))
        btn.handle_event(down)
        assert btn._pressed is True

    def test_mouseup_outside_clears_pressed_without_calling_callback(self) -> None:
        cb = MagicMock()
        btn = self._make_button(callback=cb)
        btn._pressed = True
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(200, 200))
        btn.handle_event(up)
        assert btn._pressed is False
        cb.assert_not_called()

    def test_right_click_does_not_trigger(self) -> None:
        cb = MagicMock()
        btn = self._make_button(callback=cb)
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(50, 30))
        btn.handle_event(down)
        cb.assert_not_called()


# ---------------------------------------------------------------------------
# _Slider
# ---------------------------------------------------------------------------


class TestSlider:
    def _make_slider(self, on_change: MagicMock | None = None) -> _Slider:
        cb = on_change or MagicMock()
        return _Slider(
            rect=pygame.Rect(10, 100, 180, 24),
            min_val=0,
            max_val=30,
            value=10,
            on_change=cb,
        )

    def test_initial_value(self) -> None:
        slider = self._make_slider()
        assert slider.value == 10

    def test_value_clamps_on_drag_left_edge(self) -> None:
        cb = MagicMock()
        slider = self._make_slider(on_change=cb)
        slider._dragging = True
        motion = pygame.event.Event(
            pygame.MOUSEMOTION, pos=(slider.rect.left - 50, slider.rect.centery),
            rel=(0, 0), buttons=(1, 0, 0),
        )
        slider.handle_event(motion)
        assert slider.value == slider.min_val

    def test_value_clamps_on_drag_right_edge(self) -> None:
        cb = MagicMock()
        slider = self._make_slider(on_change=cb)
        slider._dragging = True
        motion = pygame.event.Event(
            pygame.MOUSEMOTION, pos=(slider.rect.right + 100, slider.rect.centery),
            rel=(0, 0), buttons=(1, 0, 0),
        )
        slider.handle_event(motion)
        assert slider.value == slider.max_val

    def test_drag_calls_on_change(self) -> None:
        cb = MagicMock()
        slider = self._make_slider(on_change=cb)
        slider._dragging = True
        cx = slider.rect.left + slider.rect.width // 2
        motion = pygame.event.Event(
            pygame.MOUSEMOTION, pos=(cx, slider.rect.centery),
            rel=(0, 0), buttons=(1, 0, 0),
        )
        slider.handle_event(motion)
        cb.assert_called_once()

    def test_mouseup_clears_dragging(self) -> None:
        slider = self._make_slider()
        slider._dragging = True
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(50, 112))
        slider.handle_event(up)
        assert slider._dragging is False

    def test_motion_without_dragging_does_not_call_on_change(self) -> None:
        cb = MagicMock()
        slider = self._make_slider(on_change=cb)
        motion = pygame.event.Event(
            pygame.MOUSEMOTION, pos=(50, 112),
            rel=(0, 0), buttons=(0, 0, 0),
        )
        slider.handle_event(motion)
        cb.assert_not_called()

    def test_thumb_x_at_min(self) -> None:
        slider = self._make_slider()
        slider._value = slider.min_val
        assert slider._thumb_x() == slider.rect.left

    def test_thumb_x_at_max(self) -> None:
        slider = self._make_slider()
        slider._value = slider.max_val
        assert slider._thumb_x() == slider.rect.left + slider.rect.width


# ---------------------------------------------------------------------------
# ControlPanel initialisation
# ---------------------------------------------------------------------------


class TestControlPanelInit:
    def test_seven_buttons_created(self, panel: ControlPanel) -> None:
        assert len(panel._buttons) == 7

    def test_slider_initial_value(self, panel: ControlPanel) -> None:
        assert panel._slider.value == 10

    def test_buttons_within_panel_rect(self, panel: ControlPanel, panel_rect: pygame.Rect) -> None:
        for btn in panel._buttons:
            assert panel_rect.contains(btn.rect), (
                f"Button '{btn.label}' rect {btn.rect} is outside panel {panel_rect}"
            )


# ---------------------------------------------------------------------------
# ControlPanel: event routing
# ---------------------------------------------------------------------------


class TestControlPanelHandleEvent:
    def test_solve_button_click_triggers_callback(
        self, panel: ControlPanel, callbacks: dict[str, MagicMock]
    ) -> None:
        btn = panel._btn_solve
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=btn.rect.center)
        panel.handle_event(down)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=btn.rect.center)
        panel.handle_event(up)
        callbacks["on_solve"].assert_called_once()

    def test_load_button_click_triggers_callback(
        self, panel: ControlPanel, callbacks: dict[str, MagicMock]
    ) -> None:
        btn = panel._btn_load
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=btn.rect.center)
        panel.handle_event(down)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=btn.rect.center)
        panel.handle_event(up)
        callbacks["on_load"].assert_called_once()

    def test_reset_button_click_triggers_callback(
        self, panel: ControlPanel, callbacks: dict[str, MagicMock]
    ) -> None:
        btn = panel._btn_reset
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=btn.rect.center)
        panel.handle_event(down)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=btn.rect.center)
        panel.handle_event(up)
        callbacks["on_reset"].assert_called_once()

    def test_new_button_click_triggers_callback(
        self, panel: ControlPanel, callbacks: dict[str, MagicMock]
    ) -> None:
        btn = panel._btn_new
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=btn.rect.center)
        panel.handle_event(down)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=btn.rect.center)
        panel.handle_event(up)
        callbacks["on_new"].assert_called_once()

    def test_handle_event_returns_true_for_button_click(
        self, panel: ControlPanel
    ) -> None:
        btn = panel._btn_solve
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=btn.rect.center)
        assert panel.handle_event(down) is True

    def test_handle_event_returns_false_for_miss(
        self, panel: ControlPanel
    ) -> None:
        # Click far outside all buttons and slider
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(5000, 5000))
        assert panel.handle_event(event) is False


# ---------------------------------------------------------------------------
# ControlPanel: internal bus events
# ---------------------------------------------------------------------------


class TestControlPanelBusEvents:
    def test_undo_button_publishes_undo_requested(
        self, panel: ControlPanel, bus: EventBus
    ) -> None:
        received: list[UndoRequested] = []
        bus.subscribe(UndoRequested, received.append)

        btn = panel._btn_undo
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=btn.rect.center)
        panel.handle_event(down)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=btn.rect.center)
        panel.handle_event(up)

        assert len(received) == 1

    def test_redo_button_publishes_redo_requested(
        self, panel: ControlPanel, bus: EventBus
    ) -> None:
        received: list[RedoRequested] = []
        bus.subscribe(RedoRequested, received.append)

        btn = panel._btn_redo
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=btn.rect.center)
        panel.handle_event(down)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=btn.rect.center)
        panel.handle_event(up)

        assert len(received) == 1

    def test_theme_button_publishes_theme_changed(
        self, panel: ControlPanel, bus: EventBus
    ) -> None:
        received: list[ThemeChanged] = []
        bus.subscribe(ThemeChanged, received.append)

        btn = panel._btn_theme
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=btn.rect.center)
        panel.handle_event(down)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=btn.rect.center)
        panel.handle_event(up)

        assert len(received) == 1
        assert isinstance(received[0].theme_name, str)

    def test_speed_change_publishes_speed_changed(
        self, panel: ControlPanel, bus: EventBus
    ) -> None:
        received: list[SpeedChanged] = []
        bus.subscribe(SpeedChanged, received.append)

        panel._on_speed_change(15.0)

        assert len(received) == 1
        assert received[0].steps_per_second == 15.0


# ---------------------------------------------------------------------------
# ControlPanel: theme cycling
# ---------------------------------------------------------------------------


class TestControlPanelThemeCycle:
    def test_cycle_theme_changes_active_theme(
        self, panel: ControlPanel, theme_manager: ThemeManager
    ) -> None:
        original = theme_manager.active.name
        panel._cycle_theme()
        assert theme_manager.active.name != original

    def test_cycle_theme_cycles_all_builtins(
        self, panel: ControlPanel, theme_manager: ThemeManager
    ) -> None:
        names_seen = {theme_manager.active.name}
        for _ in range(5):
            panel._cycle_theme()
            names_seen.add(theme_manager.active.name)
        assert len(names_seen) >= 3  # light, dark, solarized all seen
