"""
B站动态 API 路由
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.db import crud

router = APIRouter(prefix="/api", tags=["bili"])


@router.get("/bili")
async def list_bili(
    author: Annotated[str | None, Query(description="作者筛选")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    """B站动态列表"""
    return await crud.list_bili_dynamics(author=author, limit=limit)


@router.get("/bili/{dynamic_id}")
async def get_bili(dynamic_id: str):
    """查询单条 B站动态"""
    row = await crud.get_bili_dynamic(dynamic_id)
    if not row:
        raise HTTPException(status_code=404, detail="动态不存在")
    return row
