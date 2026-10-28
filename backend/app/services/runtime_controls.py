"""Small process-local controls for a bounded public demo deployment."""

import asyncio
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float, *, clock: Callable[[], float] = time.monotonic):
        self._ttl = ttl_seconds
        self._clock = clock
        self._items: dict[str, tuple[float, T]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> T | None:
        async with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= self._clock():
                self._items.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: T) -> None:
        async with self._lock:
            self._items[key] = (self._clock() + self._ttl, value)


class SlidingWindowRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: float = 60,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = self._clock()
        cutoff = now - self._window
        async with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self._limit:
                return False
            events.append(now)
            return True


class ConcurrencyGate:
    def __init__(self, limit: int) -> None:
        self._semaphore = asyncio.Semaphore(limit)

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        await self._semaphore.acquire()
        try:
            yield
        finally:
            self._semaphore.release()


class DemoControls:
    def __init__(
        self,
        *,
        search_limit: int,
        plan_limit: int,
        plan_concurrency: int,
        search_ttl: float,
        plan_ttl: float,
    ) -> None:
        self.search_limiter = SlidingWindowRateLimiter(search_limit)
        self.plan_limiter = SlidingWindowRateLimiter(plan_limit)
        self.plan_gate = ConcurrencyGate(plan_concurrency)
        self.search_cache: TTLCache[object] = TTLCache(search_ttl)
        self.plan_cache: TTLCache[object] = TTLCache(plan_ttl)
