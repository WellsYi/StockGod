"""
股票池管理 API 路由

提供 REST 接口增删查股票池（数据文件 data/stocks.json）。
复用 stock_core 的 load_stocks/save_stocks/resolve_market/fetch_stock_name。
"""

from fastapi import APIRouter, HTTPException

from app.core.monitors import stock_core as sc

router = APIRouter(prefix="/api", tags=["stocks"])


@router.get("/stocks")
async def list_stocks():
    """股票池列表"""
    return await sc.load_stocks()


@router.post("/stocks")
async def add_stock(body: dict):
    """添加股票到池"""
    code = body.get("code", "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="缺少股票代码")

    stocks = await sc.load_stocks()
    if any(s["code"] == code for s in stocks):
        raise HTTPException(status_code=409, detail=f"{code} 已在股票池中")

    market = sc.resolve_market(code)
    name = await sc.fetch_stock_name(code, market) or code
    entry = {"code": code, "name": name, "market": market}
    stocks.append(entry)
    await sc.save_stocks(stocks)

    market_name = "上证" if market == 1 else "深证"
    return {"message": f"已添加 {code} {name}（{market_name}）", "stock": entry}


@router.delete("/stocks/{code}")
async def remove_stock(code: str):
    """从股票池删除"""
    stocks = await sc.load_stocks()
    removed = [s for s in stocks if s["code"] != code]
    if len(removed) == len(stocks):
        raise HTTPException(status_code=404, detail=f"未找到 {code}")
    await sc.save_stocks(removed)
    return {"message": f"已删除 {code}"}
