"""
涨停分析 API 路由
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

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
