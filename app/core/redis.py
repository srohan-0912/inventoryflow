import redis

from app.core.config import settings


redis_client: redis.Redis = redis.Redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


def check_redis_connection() -> bool:
    try:
        return bool(redis_client.ping())
    except redis.RedisError:
        return False


def close_redis_connection() -> None:
    redis_client.close()