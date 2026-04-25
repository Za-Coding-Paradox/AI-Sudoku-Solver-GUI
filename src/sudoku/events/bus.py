"""EventBus — the application-wide publish/subscribe backbone.

Architecture
------------
The EventBus is a **thread-safe singleton**.  Every module that wants to
participate in inter-module communication imports and uses the *same*
instance via :func:`EventBus.get_instance`.

Design goals
~~~~~~~~~~~~
1. **Fully decoupled** — publishers never import subscribers and vice-versa.
2. **Typed** — subscriptions are keyed on the exact :class:`Event` subclass,
   so mypy can verify handler signatures.
3. **Wildcard support** — subscribing to the base :class:`Event` class
   receives *every* event (useful for logging and debugging).
4. **Thread-safe dispatch** — handlers are always called on the thread that
   called :meth:`publish`.  The bus itself is protected by a ``threading.Lock``
   only during subscription/unsubscription; dispatch is lock-free so
   handlers cannot deadlock.
5. **Error isolation** — exceptions in one handler do not prevent other
   handlers from running.  Errors are logged to stderr and emitted as a
   nested :class:`ErrorRaised` event (guarded to prevent infinite loops).

Usage
-----
    from sudoku.events import EventBus, CellChanged, CellCoord

    bus = EventBus.get_instance()

    # Subscribe
    def on_cell_changed(event: CellChanged) -> None:
        print(f"Cell {event.coord} changed to {event.new_value}")

    bus.subscribe(CellChanged, on_cell_changed)

    # Publish
    bus.publish(CellChanged(coord=CellCoord(0, 0), old_value=0, new_value=5))

    # Unsubscribe
    bus.unsubscribe(CellChanged, on_cell_changed)
"""

from __future__ import annotations

import sys
import threading
import traceback
from collections import defaultdict
from typing import Any, Callable, Type

from sudoku.events.types import Event, ErrorRaised

# Type alias for a handler callable.
Handler = Callable[[Any], None]


class EventBus:
    """Application-wide publish/subscribe event bus (singleton).

    Thread safety
    -------------
    ``_handlers`` is protected by ``_lock`` during mutation (subscribe /
    unsubscribe) but is *read* without the lock during dispatch.  This is
    safe because:
    - Python's GIL guarantees that dict reads are atomic.
    - We take a shallow copy of the handler list before iterating, so
      concurrent unsubscribes during dispatch cannot cause ``RuntimeError``.
    """

    _instance: EventBus | None = None
    _instance_lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        # Map: event type → list of handlers.
        self._handlers: defaultdict[Type[Event], list[Handler]] = defaultdict(list)
        self._lock = threading.Lock()
        # Prevents infinite loops if ErrorRaised handler itself raises.
        self._publishing_error = False

    @classmethod
    def get_instance(cls) -> "EventBus":
        """Return the application-wide singleton, creating it if necessary."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton — intended for use in tests only."""
        with cls._instance_lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Subscribe / Unsubscribe
    # ------------------------------------------------------------------

    def subscribe(self, event_type: Type[Event], handler: Handler) -> None:
        """Register *handler* to be called whenever *event_type* is published.

        Subscribing to :class:`~sudoku.events.types.Event` (the base class)
        acts as a wildcard — the handler receives every event regardless of type.

        Parameters
        ----------
        event_type:
            The concrete Event subclass to listen for (or ``Event`` for all).
        handler:
            A callable that accepts a single argument of type *event_type*.
        """
        with self._lock:
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: Type[Event], handler: Handler) -> None:
        """Remove *handler* from *event_type*'s subscriber list.

        No-op if *handler* was not subscribed.
        """
        with self._lock:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass  # Not subscribed — fine.

    def unsubscribe_all(self, handler: Handler) -> None:
        """Remove *handler* from every event type it may be subscribed to."""
        with self._lock:
            for handlers in self._handlers.values():
                try:
                    handlers.remove(handler)
                except ValueError:
                    pass

    def clear(self) -> None:
        """Remove all subscriptions (useful between tests)."""
        with self._lock:
            self._handlers.clear()

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    def publish(self, event: Event) -> None:
        """Publish *event* to all matching subscribers.

        Dispatch order
        --------------
        1. Handlers subscribed to the exact type of *event*.
        2. Handlers subscribed to :class:`Event` (wildcard).

        Both lists are snapshotted before iteration so that handlers
        that subscribe or unsubscribe during dispatch take effect only
        on the *next* publish call.

        Error handling
        --------------
        If a handler raises an exception, the error is printed to stderr
        and an :class:`~sudoku.events.types.ErrorRaised` event is published
        (once — no recursion).
        """
        event_type = type(event)

        # Snapshot under the lock.
        with self._lock:
            specific: list[Handler] = list(self._handlers.get(event_type, []))
            wildcards: list[Handler] = list(self._handlers.get(Event, []))

        all_handlers = specific + [h for h in wildcards if h not in specific]

        for handler in all_handlers:
            try:
                handler(event)
            except Exception:  # noqa: BLE001
                tb = traceback.format_exc()
                print(
                    f"[EventBus] Unhandled exception in handler "
                    f"{handler!r} for event {event!r}:\n{tb}",
                    file=sys.stderr,
                )
                if not self._publishing_error:
                    self._publishing_error = True
                    try:
                        self.publish(
                            ErrorRaised(
                                message=f"Handler error: {handler.__name__}",
                                detail=tb,
                            )
                        )
                    finally:
                        self._publishing_error = False

    # ------------------------------------------------------------------
    # Introspection (debugging / testing)
    # ------------------------------------------------------------------

    def subscriber_count(self, event_type: Type[Event]) -> int:
        """Return the number of handlers registered for *event_type*."""
        with self._lock:
            return len(self._handlers.get(event_type, []))

    def has_subscribers(self, event_type: Type[Event]) -> bool:
        """Return True when at least one handler is registered for *event_type*."""
        return self.subscriber_count(event_type) > 0

    def registered_event_types(self) -> list[Type[Event]]:
        """Return a list of all event types that currently have at least one subscriber."""
        with self._lock:
            return [et for et, handlers in self._handlers.items() if handlers]

    def __repr__(self) -> str:
        types = self.registered_event_types()
        return f"EventBus(subscriptions={len(types)} event types)"
