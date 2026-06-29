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


@app.get("/api/test/batch")
async def test_batch():
    """批量推送多条模拟信号（不同股票、不同类型）"""
    from app.core.signal_queue import SignalEvent, _handle_signal

    events = [
        SignalEvent("600519", "贵州茅台", "异动放量", 1580.0, 6.8,
            {"volume_ratio": 4.2, "reason": "季报超预期"},
            "季报超预期推动资金抢筹，量比4.2倍，主力净流入8.5亿",
            "异动信号", "**贵州茅台**（600519）\n\n信号：异动放量\n价格：**1580.00**\n涨幅：**+6.80%**\n量比：**4.2**"),
        SignalEvent("300750", "宁德时代", "VWAP突破", 245.6, 4.5,
            {"vwap_distance": 2.3, "reason": "新能源政策利好"},
            "股价站稳VWAP上方，新能源板块集体走强，北向资金持续加仓",
            "信号提醒", "**宁德时代**（300750）\n\n信号：VWAP突破\n价格：**245.60**\n涨幅：**+4.50%**"),
        SignalEvent("002415", "海康威视", "连续拉升", 35.8, 5.2,
            {"volume_ratio": 3.8, "reason": "AI概念带动"},
            "连续30分钟放量拉升，AI概念热度升温，短线资金持续流入",
            "异动信号", "**海康威视**（002415）\n\n信号：连续拉升\n价格：**35.80**\n涨幅：**+5.20%**"),
        SignalEvent("601012", "隆基绿能", "逼近涨停", 28.9, 9.8,
            {"limit_distance": 0.2, "reason": "光伏板块爆发"},
            "涨幅9.8%逼近涨停，光伏板块整体涨幅超5%，封单资金2.3亿",
            "涨停预警", "**隆基绿能**（601012）\n\n信号：逼近涨停\n价格：**28.90**\n涨幅：**+9.80%**"),
    ]
    for ev in events:
        await _handle_signal(ev)
    return {"ok": True, "message": f"已推送 {len(events)} 条模拟信号（MySQL + WS）"}


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
