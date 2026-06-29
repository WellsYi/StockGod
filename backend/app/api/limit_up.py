"""
涨停分析 API 路由
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.db import crud

router = APIRouter(prefix="/api", tags=["limit-up"])


@router.get("/limit-up")
async def list_limit_up(
    trade_date: Annotated[date | None, Query(description="交易日期筛选")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    """涨停板列表"""
    rows = await crud.list_limit_up(trade_date=trade_date, limit=limit)
    return rows


@router.get("/limit-up/{item_id}")
async def get_limit_up(item_id: int):
    """涨停单条详情"""
    row = await crud.get_limit_up(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return row
