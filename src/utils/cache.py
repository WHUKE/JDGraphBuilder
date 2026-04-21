"""进程内 TTL 缓存。

用途：装饰只读查询函数（stats_query / skill_query），在 TTL 内命中返回缓存，
构建流程结束后可通过 invalidate_cache() 主动清空。

设计：
- 不依赖 Redis，进程内 dict + 时间戳。
- 缓存键忽略 Neo4jClient 参数（位置 0 或 self），其余位置/关键字参数参与键生成。
- 线程安全：采用粗粒度锁（满足本项目单进程 CLI 场景，性能足够）。
"""

from __future__ import annotations

import functools
import threading
import time
from typing import Any, Callable

_DEFAULT_TTL: float = 300.0  # 秒

_store: dict[tuple, tuple[float, Any]] = {}
_lock = threading.Lock()


def _make_key(func: Callable, args: tuple, kwargs: dict) -> tuple:
    """生成缓存键：函数全名 + 除第一个位置参数外的 args + 排序后的 kwargs。

    第一个位置参数通常是 Neo4jClient 实例（不可哈希且不应影响缓存），故跳过。
    """
    skip_first = args[1:] if args else ()
    kwarg_items = tuple(sorted(kwargs.items()))
    return (f"{func.__module__}.{func.__qualname__}", skip_first, kwarg_items)


def cached(ttl: float = _DEFAULT_TTL) -> Callable:
    """TTL 缓存装饰器。

    Args:
        ttl: 过期时间（秒），默认 300。
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = _make_key(func, args, kwargs)
            now = time.time()
            with _lock:
                entry = _store.get(key)
                if entry is not None and (now - entry[0]) < ttl:
                    return entry[1]
            # 未命中：执行并回填（锁外执行以避免长查询阻塞其它键）
            result = func(*args, **kwargs)
            with _lock:
                _store[key] = (now, result)
            return result
        wrapper.__wrapped_cache_key__ = func.__qualname__  # type: ignore[attr-defined]
        return wrapper
    return decorator


def invalidate_cache() -> int:
    """清空所有缓存，返回清理的条目数。"""
    with _lock:
        n = len(_store)
        _store.clear()
    return n


def cache_size() -> int:
    """当前缓存条目数（调试用）。"""
    with _lock:
        return len(_store)
