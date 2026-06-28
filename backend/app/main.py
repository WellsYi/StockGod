"""
StockGod — FastAPI 应用入口

启动: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import pool
from app.core import signal_queue
from app.core.task_manager import manager
from app.core.ws_manager import manager as ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时
    try:
        await pool.create_pool()
        print("[StockGod] 数据库连接池已创建")
    except Exception as e:
        print(f"[StockGod] 数据库连接失败: {e}")

    # 启动信号队列 consumer
    signal_queue.start()

    # 注册后台监控任务
    from app.core.monitors.stock_monitor import stock_monitor_main
    from app.core.monitors.bili_monitor import bili_monitor_main

    manager.register("stock-monitor", stock_monitor_main)
    manager.register("bili-monitor", bili_monitor_main)

    # B站监控需要登录凭据，仅在配置了 UID 时启动
    if pool._pool is not None:
        print("[StockGod] 数据库就绪，监控任务可以写入数据")
    await manager.start_all()

    yield

    # 关闭时
    await manager.stop_all()
    await signal_queue.stop()
    if pool._pool:
        await pool.close_pool()
        print("[StockGod] 数据库连接池已关闭")


app = FastAPI(
    title="StockGod",
    description="股神 — 股票盯盘 + B站监控 + RAG 问答系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
#  路由注册
# ============================================================

from app.api import bili, dingtalk, limit_up, monitor, signals, stocks, ws

app.include_router(signals.router)
app.include_router(bili.router)
app.include_router(dingtalk.router)
app.include_router(limit_up.router)
app.include_router(monitor.router)
app.include_router(stocks.router)
app.include_router(ws.router)


# ============================================================
#  API 端点
# ============================================================

@app.get("/")
async def root():
    return {"name": "StockGod", "version": "1.0.0", "status": "running"}


@app.get("/api/test/signal")
async def test_signal():
    """推送一条模拟信号（测试用：MySQL + 钉钉 + WebSocket 完整链路）"""
    from app.core.signal_queue import SignalEvent, _handle_signal

    event = SignalEvent(
        stock_code="000001",
        stock_name="平安银行",
        signal_type="异常放量",
        price=12.34,
        change_pct=3.25,
        signal_detail={"volume_ratio": 3.5, "reason": "模拟测试数据"},
        llm_analysis="测试推送 — 验证完整链路",
        push_title="🧪 测试信号",
        push_content=(
            "**平安银行**（000001）\n\n"
            "信号：异常放量\n现价：**12.34**\n涨幅：**+3.25%**\n\n"
            "这是一条模拟测试数据，用于验证完整推送链路。"
        ),
    )
    await _handle_signal(event)
    return {"ok": True, "message": "信号已推送（MySQL + 钉钉 + WebSocket）"}


@app.get("/api/health")
async def health():
    """健康检查"""
    db_ok = await pool.check_health()
    queue_stats = await signal_queue.get_stats()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "disconnected",
        "tasks": manager.get_status(),
        "queue": queue_stats,
        "ws_connections": ws_manager.active_count,
        "version": "1.0.0",
    }


@app.get("/api/health/tasks")
async def task_status():
    """后台任务状态"""
    return {"tasks": manager.get_status()}
