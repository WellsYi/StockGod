"""
股票信号 + 准确率追踪 API 路由
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.db import crud
from app.core.llm import client as llm

router = APIRouter(prefix="/api", tags=["signals"])


# ── 信号 ──


@router.get("/signals")
async def list_signals(
    stock_code: Annotated[str | None, Query(description="股票代码筛选")] = None,
    signal_type: Annotated[str | None, Query(description="信号类型筛选")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """查询信号列表"""
    return await crud.list_signals(
        stock_code=stock_code,
        signal_type=signal_type,
        limit=limit,
        offset=offset,
    )


@router.get("/signals/today")
async def count_signals_today():
    """今日信号数量"""
    count = await crud.count_signals_today()
    return {"count": count, "date": datetime.now().strftime("%Y-%m-%d")}


@router.get("/signals/{signal_id}")
async def get_signal(signal_id: int):
    """查询单条信号详情"""
    row = await crud.get_signal(signal_id)
    if not row:
        raise HTTPException(status_code=404, detail="信号不存在")
    return row


# ── LLM 解读 ──


@router.post("/signals/{signal_id}/analyze")
async def analyze_signal(signal_id: int):
    """手动触发单条信号的 LLM 解读"""
    row = await crud.get_signal(signal_id)
    if not row:
        raise HTTPException(status_code=404, detail="信号不存在")
    if not row.get("llm_analysis"):
        # 调用 LLM 生成解读
        detail_str = str(row.get("signal_detail", {}))
        analysis = await llm.analyze_stock_signal(
            name=row["stock_name"],
            code=row["stock_code"],
            price=row["price"],
            change_pct=row["change_pct"],
            signal_type=row["signal_type"],
            detail=detail_str,
        )
        await crud.update_signal_llm(signal_id, analysis)
        row["llm_analysis"] = analysis
    return row


# ── 准确率 ──


@router.get("/accuracy")
async def list_accuracy(
    verdict: Annotated[str | None, Query(description="判定结果筛选")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    """信号准确率列表"""
    return await crud.list_signal_accuracy(verdict=verdict, limit=limit)


@router.patch("/accuracy/{signal_id}")
async def update_accuracy(signal_id: int, body: dict):
    """更新信号准确率数据"""
    existing = await crud.get_signal(signal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="信号不存在")
    allowed = {"price_5min", "price_15min", "price_30min", "price_close", "close_change", "verdict"}
    payload = {k: v for k, v in body.items() if k in allowed}
    if not payload:
        raise HTTPException(status_code=400, detail="没有可更新的字段")
    await crud.update_signal_accuracy(signal_id, **payload)
    return {"updated": True}
