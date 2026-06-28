"""
数据库初始化脚本

用法: python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiomysql
from app import config


async def init_db():
    """连接 MySQL 并执行建表脚本"""
    # 先连接（不指定库）创建数据库
    conn = await aiomysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        charset="utf8mb4",
        autocommit=True,
    )
    async with conn.cursor() as cur:
        await cur.execute(f"CREATE DATABASE IF NOT EXISTS `{config.MYSQL_DB}` DEFAULT CHARACTER SET utf8mb4")
        print(f"[OK] 数据库 {config.MYSQL_DB} 已就绪")
    conn.close()

    # 切换到目标库执行建表
    conn = await aiomysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DB,
        charset="utf8mb4",
        autocommit=True,
    )

    sql_path = Path(__file__).resolve().parent.parent / "app" / "db" / "migrations" / "001_init.sql"
    sql = sql_path.read_text("utf-8")

    # 按分号分割逐条执行
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    async with conn.cursor() as cur:
        for stmt in statements:
            if stmt.upper().startswith("--"):
                continue
            try:
                await cur.execute(stmt)
                print(f"  [SQL] {stmt[:60]}...")
            except Exception as e:
                print(f"[WARN] {e}")

    conn.close()

    print("[OK] 所有表已创建")
    print(f"   - signals")
    print(f"   - price_snapshots")
    print(f"   - llm_logs")
    print(f"   - signal_accuracy")
    print(f"   - bili_dynamics")
    print(f"   - limit_up_daily")
    print(f"   - stock_pool")

    # 预置股票池（重新连接）
    conn = await aiomysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DB,
        charset="utf8mb4",
        autocommit=True,
    )
    async with conn.cursor() as cur:
        preset = [
            {"code": "000001", "name": "平安银行", "market": 0},
            {"code": "002230", "name": "科大讯飞", "market": 0},
            {"code": "300750", "name": "宁德时代", "market": 0},
            {"code": "600519", "name": "贵州茅台", "market": 1},
        ]
        for s in preset:
            await cur.execute(
                "INSERT IGNORE INTO stock_pool (stock_code, stock_name, market) VALUES (%s, %s, %s)",
                (s["code"], s["name"], s["market"]),
            )
        print(f"[OK] 预置股票池导入 ({len(preset)} 只)")
    conn.close()


if __name__ == "__main__":
    asyncio.run(init_db())
