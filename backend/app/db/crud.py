"""
数据库 CRUD 操作

所有表的增删查操作集中在这里，各业务模块通过这里读写数据库。
"""

from datetime import date, datetime
from typing import Any

from app.db import pool
from app.db.models import *


# ============================================================
#  Signals — 股票信号
# ============================================================

async def insert_signal(
    stock_code: str, stock_name: str, signal_type: str,
    trigger_time: datetime, price: float, change_pct: float | None = None,
    signal_detail: dict | None = None, llm_analysis: str | None = None,
) -> int:
    sql = (
        f"INSERT INTO {TBL_SIGNALS} "
        "(stock_code, stock_name, signal_type, trigger_time, price, change_pct, signal_detail, llm_analysis) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    )
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (
                stock_code, stock_name, signal_type,
                trigger_time, price, change_pct,
                json.dumps(signal_detail, ensure_ascii=False) if signal_detail else None,
                llm_analysis,
            ))
            return cur.lastrowid


async def list_signals(
    stock_code: str | None = None, signal_type: str | None = None,
    limit: int = 50, offset: int = 0,
) -> list[dict]:
    conditions, params = [], []
    if stock_code:
        conditions.append("stock_code = %s")
        params.append(stock_code)
    if signal_type:
        conditions.append("signal_type = %s")
        params.append(signal_type)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT * FROM {TBL_SIGNALS} {where} ORDER BY trigger_time DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]


async def get_signal(signal_id: int) -> dict | None:
    sql = f"SELECT * FROM {TBL_SIGNALS} WHERE id = %s"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (signal_id,))
            row = await cur.fetchone()
            return _row_to_dict(cur, row) if row else None


async def update_signal_llm(signal_id: int, llm_analysis: str) -> bool:
    """更新信号的 LLM 解读"""
    sql = f"UPDATE {TBL_SIGNALS} SET llm_analysis = %s WHERE id = %s"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (llm_analysis, signal_id))
            return cur.rowcount > 0


async def count_signals_today() -> int:
    sql = f"SELECT COUNT(*) FROM {TBL_SIGNALS} WHERE DATE(trigger_time) = CURDATE()"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
            return (await cur.fetchone())[0]


# ============================================================
#  Price Snapshots — 价格快照
# ============================================================

async def insert_price_snapshot(
    stock_code: str, snapshot_time: datetime, price: float,
    change_pct: float | None = None, volume_ratio: float | None = None,
    signal_id: int | None = None,
) -> int:
    sql = (
        f"INSERT INTO {TBL_PRICE_SNAPSHOTS} "
        "(stock_code, snapshot_time, price, change_pct, volume_ratio, signal_id) "
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (stock_code, snapshot_time, price, change_pct, volume_ratio, signal_id))
            return cur.lastrowid


async def list_price_snapshots(stock_code: str, limit: int = 100) -> list[dict]:
    sql = f"SELECT * FROM {TBL_PRICE_SNAPSHOTS} WHERE stock_code = %s ORDER BY snapshot_time DESC LIMIT %s"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (stock_code, limit))
            rows = await cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]


# ============================================================
#  LLM Logs — LLM 调用日志
# ============================================================

async def insert_llm_log(
    scenario: str, input_text: str, output_text: str,
    stock_code: str | None = None, model: str | None = None,
    tokens_input: int = 0, tokens_output: int = 0,
) -> int:
    sql = (
        f"INSERT INTO {TBL_LLM_LOGS} "
        "(scenario, input_text, output_text, stock_code, model, tokens_input, tokens_output) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    )
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (scenario, input_text, output_text, stock_code, model, tokens_input, tokens_output))
            return cur.lastrowid


async def count_llm_tokens_today() -> dict:
    sql = f"SELECT SUM(tokens_input), SUM(tokens_output) FROM {TBL_LLM_LOGS} WHERE DATE(created_at) = CURDATE()"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
            row = await cur.fetchone()
            return {"input": row[0] or 0, "output": row[1] or 0}


# ============================================================
#  Signal Accuracy — 信号准确率追踪
# ============================================================

async def insert_signal_accuracy(signal_id: int) -> int:
    sql = f"INSERT IGNORE INTO {TBL_SIGNAL_ACCURACY} (signal_id) VALUES (%s)"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (signal_id,))
            return cur.lastrowid


async def update_signal_accuracy(
    signal_id: int, *,
    price_5min: float | None = None, price_15min: float | None = None,
    price_30min: float | None = None, price_close: float | None = None,
    close_change: float | None = None, verdict: str | None = None,
):
    fields, params = [], []
    if price_5min is not None:
        fields.append("price_5min = %s"); params.append(price_5min)
    if price_15min is not None:
        fields.append("price_15min = %s"); params.append(price_15min)
    if price_30min is not None:
        fields.append("price_30min = %s"); params.append(price_30min)
    if price_close is not None:
        fields.append("price_close = %s"); params.append(price_close)
    if close_change is not None:
        fields.append("close_change = %s"); params.append(close_change)
    if verdict is not None:
        fields.append("verdict = %s"); params.append(verdict)
    if not fields:
        return

    sql = f"UPDATE {TBL_SIGNAL_ACCURACY} SET {', '.join(fields)} WHERE signal_id = %s"
    params.append(signal_id)
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)


async def list_signal_accuracy(verdict: str | None = None, limit: int = 50) -> list[dict]:
    conditions, params = [], []
    if verdict:
        conditions.append("verdict = %s"); params.append(verdict)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT * FROM {TBL_SIGNAL_ACCURACY} {where} ORDER BY updated_at DESC LIMIT %s"
    params.append(limit)
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]


# ============================================================
#  Bili Dynamics — B站动态记录
# ============================================================

async def insert_bili_dynamic(
    dynamic_id: str, author: str, content: str,
    llm_summary: str | None = None, link_url: str | None = None,
    pushed_at: datetime | None = None,
) -> int:
    sql = (
        f"INSERT IGNORE INTO {TBL_BILI_DYNAMICS} "
        "(dynamic_id, author, content, llm_summary, link_url, pushed_at) "
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (dynamic_id, author, content, llm_summary, link_url, pushed_at))
            return cur.lastrowid


async def list_bili_dynamics(author: str | None = None, limit: int = 30) -> list[dict]:
    conditions, params = [], []
    if author:
        conditions.append("author = %s"); params.append(author)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT * FROM {TBL_BILI_DYNAMICS} {where} ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]


async def get_bili_dynamic(dynamic_id: str) -> dict | None:
    sql = f"SELECT * FROM {TBL_BILI_DYNAMICS} WHERE dynamic_id = %s"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (dynamic_id,))
            row = await cur.fetchone()
            return _row_to_dict(cur, row) if row else None


# ============================================================
#  Limit Up Daily — 每日涨停记录
# ============================================================

async def upsert_limit_up(
    trade_date: date, stock_code: str, stock_name: str,
    price: float, change_pct: float | None = None,
    turnover_rate: float | None = None, fd_amount: float | None = None,
    limit_times: int = 1, board_type: str | None = None,
    reason_llm: str | None = None, reason_tags: list | None = None,
    concept_tags: list | None = None,
) -> int:
    sql = (
        f"INSERT INTO {TBL_LIMIT_UP_DAILY} "
        "(trade_date, stock_code, stock_name, price, change_pct, turnover_rate, "
        "fd_amount, limit_times, board_type, reason_llm, reason_tags, concept_tags) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AS new "
        "ON DUPLICATE KEY UPDATE "
        "price = new.price, change_pct = new.change_pct, "
        "turnover_rate = new.turnover_rate, fd_amount = new.fd_amount, "
        "limit_times = new.limit_times, reason_llm = new.reason_llm, "
        "reason_tags = new.reason_tags, concept_tags = new.concept_tags"
    )
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (
                trade_date, stock_code, stock_name, price, change_pct,
                turnover_rate, fd_amount, limit_times, board_type,
                reason_llm,
                json.dumps(reason_tags, ensure_ascii=False) if reason_tags else None,
                json.dumps(concept_tags, ensure_ascii=False) if concept_tags else None,
            ))
            return cur.lastrowid


async def list_limit_up(trade_date: date | None = None, limit: int = 50) -> list[dict]:
    conditions, params = [], []
    if trade_date:
        conditions.append("trade_date = %s"); params.append(trade_date)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT * FROM {TBL_LIMIT_UP_DAILY} {where} ORDER BY limit_times DESC, change_pct DESC LIMIT %s"
    params.append(limit)
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]


async def get_limit_up(item_id: int) -> dict | None:
    sql = f"SELECT * FROM {TBL_LIMIT_UP_DAILY} WHERE id = %s"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (item_id,))
            row = await cur.fetchone()
            return _row_to_dict(cur, row) if row else None


# ============================================================
#  Stock Pool — 股票池
# ============================================================

async def list_stock_pool() -> list[dict]:
    sql = f"SELECT * FROM {TBL_STOCK_POOL} ORDER BY stock_code"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
            rows = await cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]


async def insert_stock_pool(code: str, name: str, market: int):
    sql = f"INSERT IGNORE INTO {TBL_STOCK_POOL} (stock_code, stock_name, market) VALUES (%s, %s, %s)"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (code, name, market))


async def delete_stock_pool(code: str) -> bool:
    sql = f"DELETE FROM {TBL_STOCK_POOL} WHERE stock_code = %s"
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (code,))
            return cur.rowcount > 0


# ============================================================
#  工具
# ============================================================

import json


def _row_to_dict(cursor, row) -> dict:
    """将 MySQL 行转换为 dict"""
    d = {}
    for i, col in enumerate(cursor.description):
        val = row[i]
        # JSON 字段自动解析
        if isinstance(val, str) and col[0].endswith(("_json", "_tags", "_detail")):
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
        # datetime/date 转 str
        if isinstance(val, (datetime, date)):
            val = val.isoformat()
        d[col[0]] = val
    return d
