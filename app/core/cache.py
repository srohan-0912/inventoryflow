import json
from typing import Any

import redis

from app.core.redis import redis_client


CACHE_TTL_SECONDS = 60


def product_list_cache_key(
    organization_id: int,
    skip: int,
    limit: int,
) -> str:
    return f"products:org:{organization_id}:list:{skip}:{limit}"


def product_detail_cache_key(
    organization_id: int,
    product_id: int,
) -> str:
    return f"products:org:{organization_id}:detail:{product_id}"


def get_cached_json(key: str) -> Any | None:
    try:
        cached_value = redis_client.get(key)

        if cached_value is None:
            return None

        try:
            return json.loads(cached_value)
        except (json.JSONDecodeError, TypeError):
            redis_client.delete(key)
            return None

    except redis.RedisError:
        return None


def set_cached_json(
    key: str,
    value: Any,
    ttl: int = CACHE_TTL_SECONDS,
) -> None:
    try:
        serialized = json.dumps(value, default=str)
        redis_client.set(key, serialized, ex=ttl)
    except redis.RedisError:
        pass


def invalidate_product_cache(
    organization_id: int,
) -> None:
    pattern = f"products:org:{organization_id}:*"

    try:
        keys = list(redis_client.scan_iter(match=pattern))

        if keys:
            redis_client.delete(*keys)

    except redis.RedisError:
        pass