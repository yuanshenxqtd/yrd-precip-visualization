"""极简进程内 TTL 缓存。

用途：大屏自动刷新时会反复请求指标卡、排行榜、地图数据，
这些接口都要做全表聚合。加一层 60 秒 TTL 缓存可以显著降低数据库压力
（对应 docs/PLAN.md 第 8.3 节）。
"""

from __future__ import annotations

import time
from typing import Any, Callable


class TTLCache:
    """按 key 缓存任意可序列化结果，超过 TTL 或容量上限后失效。"""

    def __init__(self, ttl_seconds: int = 60, max_entries: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._store: dict[str, tuple[float, Any]] = {}
        self.hits = 0
        self.misses = 0

    def get_or_set(self, key: str, producer: Callable[[], Any]) -> Any:
        now = time.monotonic()
        cached = self._store.get(key)
        if cached is not None and now - cached[0] < self.ttl_seconds:
            self.hits += 1
            return cached[1]

        self.misses += 1
        value = producer()
        if len(self._store) >= self.max_entries:
            self._store.clear()  # 简单策略：满了整体清空，够用
        self._store[key] = (now, value)
        return value

    def clear(self) -> None:
        self._store.clear()

    def stats(self) -> dict[str, Any]:
        return {
            "ttl_seconds": self.ttl_seconds,
            "entries": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
        }


# 全局缓存实例：聚合类接口共用
summary_cache = TTLCache(ttl_seconds=60)
map_cache = TTLCache(ttl_seconds=120)
trend_cache = TTLCache(ttl_seconds=300)
