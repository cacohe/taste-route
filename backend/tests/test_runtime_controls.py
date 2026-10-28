import asyncio

from app.services.runtime_controls import ConcurrencyGate, SlidingWindowRateLimiter, TTLCache


def test_ttl_cache_expires_values():
    now = [10.0]
    cache = TTLCache[str](5, clock=lambda: now[0])

    async def scenario():
        await cache.set("paris", "value")
        assert await cache.get("paris") == "value"
        now[0] = 15.0
        assert await cache.get("paris") is None

    asyncio.run(scenario())


def test_rate_limiter_recovers_after_window():
    now = [10.0]
    limiter = SlidingWindowRateLimiter(2, 10, clock=lambda: now[0])

    async def scenario():
        assert await limiter.allow("client")
        assert await limiter.allow("client")
        assert not await limiter.allow("client")
        now[0] = 20.0
        assert await limiter.allow("client")

    asyncio.run(scenario())


def test_concurrency_gate_releases_slot_after_error():
    gate = ConcurrencyGate(1)

    async def scenario():
        try:
            async with gate.slot():
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        async with asyncio.timeout(0.1):
            async with gate.slot():
                return

    asyncio.run(scenario())
