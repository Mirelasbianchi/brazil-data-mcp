"""A tiny in-memory TTL cache for async functions.

Holidays, banks and CEPs rarely change, and the public APIs rate-limit aggressively
(BrasilAPI answers 429 under bursts), so repeated agent calls are served from memory.
"""

import functools
import time
from collections import OrderedDict

MAX_ENTRIES = 512


def ttl_cache(seconds: float):
    def decorator(fn):
        store: OrderedDict[tuple, tuple[float, object]] = OrderedDict()

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            if key in store and now - store[key][0] < seconds:
                store.move_to_end(key)
                return store[key][1]
            value = await fn(*args, **kwargs)
            store[key] = (now, value)
            if len(store) > MAX_ENTRIES:
                store.popitem(last=False)
            return value

        wrapper.cache_clear = store.clear
        return wrapper

    return decorator
