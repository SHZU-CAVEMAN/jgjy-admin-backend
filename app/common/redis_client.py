"""Redis 连接池访问封装。"""

from flask import current_app
from redis import Redis
from redis.connection import ConnectionPool

_pool: ConnectionPool | None = None


def init_redis() -> None:
    """初始化进程级 Redis 连接池。"""
    global _pool
    _pool = ConnectionPool.from_url(
        current_app.config["REDIS_URL"],
        decode_responses=True,
    )


def get_redis() -> Redis:
    """返回使用共享连接池的 Redis 客户端。

    异常：
        RuntimeError：Redis 尚未初始化。
    """
    if _pool is None:
        raise RuntimeError("Redis has not been initialized")
    return Redis(connection_pool=_pool)


def prefixed_key(module: str, key: str) -> str:
    """构建带命名空间的缓存键。"""
    return f"jgjy:{module}:{key}"
