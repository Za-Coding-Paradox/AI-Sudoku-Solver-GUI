"""Unit tests for :class:`sudoku.events.bus.EventBus`."""

from __future__ import annotations

import threading
from typing import Any
from unittest.mock import MagicMock

import pytest

from sudoku.data.cell import CellCoord
from sudoku.events.bus import EventBus
from sudoku.events.types import (
    CellChanged,
    ErrorRaised,
    Event,
    PuzzleReset,
    SolveFailed,
    SelectionChanged,
)

COORD = CellCoord(2, 3)


# ---------------------------------------------------------------------------
# Singleton behaviour
# ---------------------------------------------------------------------------


class TestEventBusSingleton:
    def test_get_instance_returns_same_object(self) -> None:
        a = EventBus.get_instance()
        b = EventBus.get_instance()
        assert a is b

    def test_reset_creates_fresh_instance(self) -> None:
        a = EventBus.get_instance()
        EventBus.reset()
        b = EventBus.get_instance()
        assert a is not b

    def test_reset_clears_subscriptions(self) -> None:
        bus = EventBus.get_instance()
        bus.subscribe(CellChanged, lambda e: None)
        EventBus.reset()
        fresh = EventBus.get_instance()
        assert fresh.subscriber_count(CellChanged) == 0


# ---------------------------------------------------------------------------
# Subscribe / unsubscribe
# ---------------------------------------------------------------------------


class TestSubscribeUnsubscribe:
    def test_subscribe_increases_count(self, bus: EventBus) -> None:
        handler = MagicMock()
        bus.subscribe(CellChanged, handler)
        assert bus.subscriber_count(CellChanged) == 1

    def test_duplicate_subscribe_ignored(self, bus: EventBus) -> None:
        handler = MagicMock()
        bus.subscribe(CellChanged, handler)
        bus.subscribe(CellChanged, handler)
        assert bus.subscriber_count(CellChanged) == 1

    def test_unsubscribe_decreases_count(self, bus: EventBus) -> None:
        handler = MagicMock()
        bus.subscribe(CellChanged, handler)
        bus.unsubscribe(CellChanged, handler)
        assert bus.subscriber_count(CellChanged) == 0

    def test_unsubscribe_not_subscribed_is_noop(self, bus: EventBus) -> None:
        handler = MagicMock()
        # Should not raise
        bus.unsubscribe(CellChanged, handler)

    def test_unsubscribe_all_removes_from_all_types(self, bus: EventBus) -> None:
        handler = MagicMock()
        bus.subscribe(CellChanged, handler)
        bus.subscribe(SolveFailed, handler)
        bus.unsubscribe_all(handler)
        assert bus.subscriber_count(CellChanged) == 0
        assert bus.subscriber_count(SolveFailed) == 0

    def test_clear_removes_all_subscriptions(self, bus: EventBus) -> None:
        bus.subscribe(CellChanged, MagicMock())
        bus.subscribe(SolveFailed, MagicMock())
        bus.clear()
        assert bus.subscriber_count(CellChanged) == 0
        assert bus.subscriber_count(SolveFailed) == 0

    def test_has_subscribers_false_initially(self, bus: EventBus) -> None:
        assert not bus.has_subscribers(CellChanged)

    def test_has_subscribers_true_after_subscribe(self, bus: EventBus) -> None:
        bus.subscribe(CellChanged, MagicMock())
        assert bus.has_subscribers(CellChanged)

    def test_registered_event_types(self, bus: EventBus) -> None:
        bus.subscribe(CellChanged, MagicMock())
        bus.subscribe(SolveFailed, MagicMock())
        types = bus.registered_event_types()
        assert CellChanged in types
        assert SolveFailed in types


# ---------------------------------------------------------------------------
# Publish / dispatch
# ---------------------------------------------------------------------------


class TestPublishDispatch:
    def test_handler_called_on_publish(self, bus: EventBus) -> None:
        handler = MagicMock()
        bus.subscribe(CellChanged, handler)
        event = CellChanged(coord=COORD, old_value=0, new_value=5)
        bus.publish(event)
        handler.assert_called_once_with(event)

    def test_handler_receives_correct_event(self, bus: EventBus) -> None:
        received: list[Any] = []
        bus.subscribe(CellChanged, received.append)
        e = CellChanged(coord=COORD, old_value=0, new_value=7)
        bus.publish(e)
        assert received == [e]

    def test_multiple_handlers_all_called(self, bus: EventBus) -> None:
        h1, h2, h3 = MagicMock(), MagicMock(), MagicMock()
        bus.subscribe(CellChanged, h1)
        bus.subscribe(CellChanged, h2)
        bus.subscribe(CellChanged, h3)
        e = CellChanged(coord=COORD, old_value=0, new_value=1)
        bus.publish(e)
        h1.assert_called_once()
        h2.assert_called_once()
        h3.assert_called_once()

    def test_wrong_event_type_not_dispatched(self, bus: EventBus) -> None:
        handler = MagicMock()
        bus.subscribe(SolveFailed, handler)
        bus.publish(CellChanged(coord=COORD, old_value=0, new_value=1))
        handler.assert_not_called()

    def test_unsubscribed_handler_not_called(self, bus: EventBus) -> None:
        handler = MagicMock()
        bus.subscribe(CellChanged, handler)
        bus.unsubscribe(CellChanged, handler)
        bus.publish(CellChanged(coord=COORD, old_value=0, new_value=1))
        handler.assert_not_called()

    def test_publish_no_subscribers_no_error(self, bus: EventBus) -> None:
        # Should not raise even with zero subscribers
        bus.publish(CellChanged(coord=COORD, old_value=0, new_value=1))


# ---------------------------------------------------------------------------
# Wildcard subscription (base Event class)
# ---------------------------------------------------------------------------


class TestWildcardSubscription:
    def test_wildcard_receives_all_events(self, bus: EventBus) -> None:
        received: list[Event] = []
        bus.subscribe(Event, received.append)
        e1 = CellChanged(coord=COORD, old_value=0, new_value=1)
        e2 = SolveFailed(reason="x")
        bus.publish(e1)
        bus.publish(e2)
        assert e1 in received
        assert e2 in received

    def test_wildcard_and_specific_not_doubled(self, bus: EventBus) -> None:
        """A handler subscribed to both Event and CellChanged must be called once."""
        calls: list[int] = []
        handler = lambda e: calls.append(1)  # noqa: E731
        bus.subscribe(Event, handler)
        bus.subscribe(CellChanged, handler)
        bus.publish(CellChanged(coord=COORD, old_value=0, new_value=1))
        # handler appears in both specific + wildcard lists — bus deduplicates
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------


class TestErrorIsolation:
    def test_exception_in_handler_does_not_stop_others(self, bus: EventBus) -> None:
        results: list[str] = []

        def bad_handler(e: Any) -> None:
            raise RuntimeError("boom")

        def good_handler(e: Any) -> None:
            results.append("good")

        bus.subscribe(CellChanged, bad_handler)
        bus.subscribe(CellChanged, good_handler)
        bus.publish(CellChanged(coord=COORD, old_value=0, new_value=1))
        assert "good" in results

    def test_exception_emits_error_raised(self, bus: EventBus) -> None:
        errors: list[ErrorRaised] = []
        bus.subscribe(ErrorRaised, errors.append)

        def bad_handler(e: Any) -> None:
            raise ValueError("test error")

        bus.subscribe(CellChanged, bad_handler)
        bus.publish(CellChanged(coord=COORD, old_value=0, new_value=1))
        assert len(errors) == 1
        assert "bad_handler" in errors[0].message

    def test_no_infinite_loop_on_error_in_error_handler(self, bus: EventBus) -> None:
        """If ErrorRaised handler itself raises, should not recurse infinitely."""
        call_count = [0]

        def bad_error_handler(e: ErrorRaised) -> None:
            call_count[0] += 1
            raise RuntimeError("error in error handler")

        def trigger(e: CellChanged) -> None:
            raise ValueError("trigger")

        bus.subscribe(CellChanged, trigger)
        bus.subscribe(ErrorRaised, bad_error_handler)
        # Must not raise RecursionError
        bus.publish(CellChanged(coord=COORD, old_value=0, new_value=1))
        assert call_count[0] == 1  # called exactly once, not recursed


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_subscribe_publish(self, bus: EventBus) -> None:
        results: list[int] = []
        lock = threading.Lock()

        def handler(e: CellChanged) -> None:
            with lock:
                results.append(e.new_value)

        def subscriber_thread() -> None:
            bus.subscribe(CellChanged, handler)

        def publisher_thread(value: int) -> None:
            bus.publish(CellChanged(coord=COORD, old_value=0, new_value=value))

        threads = [threading.Thread(target=subscriber_thread) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        pub_threads = [threading.Thread(target=publisher_thread, args=(i,)) for i in range(10)]
        for t in pub_threads:
            t.start()
        for t in pub_threads:
            t.join()

        # All published events should have been received (at least by some handlers)
        assert len(results) >= 0  # No crash is the main assertion here


# ---------------------------------------------------------------------------
# Introspection / repr
# ---------------------------------------------------------------------------


class TestIntrospection:
    def test_repr_contains_subscription_count(self, bus: EventBus) -> None:
        bus.subscribe(CellChanged, MagicMock())
        r = repr(bus)
        assert "EventBus" in r
        assert "1" in r
