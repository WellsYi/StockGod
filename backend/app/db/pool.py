"""
MySQL 连接池管理

提供异步 MySQL 连接池，基于 aiomysql。
各模块通过 get_conn() 上下文管理器获取连接。
"""

from contextlib import asynccontextmanager

import aiomysql
from app import config

_pool = None


async def create_pool():
    """创建全局连接池（应用启动时调用）"""
    global _pool
    _pool = await aiomysql.create_pool(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DB,
        charset="utf8mb4",
        autocommit=True,
        maxsize=10,
        minsize=1,
    )
    return _pool


async def close_pool():
    """关闭连接池（应用关闭时调用）"""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


@asynccontextmanager
async def get_conn():
    """获取数据库连接（上下文管理器）

    用法:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                result = await cur.fetchone()
    """
    if _pool is None:
        raise RuntimeError("数据库连接池未初始化，请先调用 create_pool()")
    async with _pool.acquire() as conn:
        yield conn


async def check_health() -> bool:
    """检查数据库连接是否正常"""
    if _pool is None:
        return False
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
        return True
    except Exception:
        return False
