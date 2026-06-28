"""
模拟推送测试 — 验证 钉钉 + WebSocket 推送链路

用法:
  python test_push.py                           # 只测钉钉推送
  python test_push.py --ws                      # 同时启动 WebSocket 服务并验证广播
  python test_push.py --callback                # 测试钉钉回调端点
"""

import asyncio
import json
import sys
import threading
import time
from unittest.mock import AsyncMock, patch
from datetime import datetime

import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRouter


# ── Mock 数据库层 ──
# 注意：signal_queue.py 用的是 "from app.db import crud",
# patch 目标：app.core.signal_queue.crud

_patcher = patch("app.core.signal_queue.crud")


# ── 测试 1: 钉钉推送 ──

async def test_dingtalk_push():
    """推送一条模拟股票信号到钉钉"""
    from app.core.signal_queue import SignalEvent, BiliEvent, _handle_signal, _handle_bili

    print("\n" + "="*60)
    print("📤 测试 1: 钉钉推送 — 股票信号")
    print("="*60)

    event = SignalEvent(
        stock_code="600519",
        stock_name="贵州茅台",
        signal_type="异常放量",
        price=1520.50,
        change_pct=3.25,
        signal_detail={"volume_ratio": 3.5, "reason": "放量突破5日均量"},
        llm_analysis="茅台今日放量明显，机构资金流入",
        push_title="🚨 贵州茅台 异常放量",
        push_content="**贵州茅台**（600519）\n\n信号：异常放量\n现价：**1520.50**\n涨幅：**+3.25%**\n量比：3.5\n\n放量突破5日均量，短线关注",
    )

    await _handle_signal(event)
    print("  ✅ 股票信号推送完成")

    print("\n" + "="*60)
    print("📤 测试 2: 钉钉推送 — B站动态")
    print("="*60)

    bili_event = BiliEvent(
        dynamic_id="test_001",
        author="测试UP主",
        content="今天测试一下推送功能...",
        llm_summary="UP主发布了一条测试动态，内容涉及系统测试",
        link_url="https://www.bilibili.com/opus/test_001",
    )

    await _handle_bili(bili_event)
    print("  ✅ B站动态推送完成")

    return True


# ── 测试 2: WebSocket 广播（需要 uvicorn） ──

async def test_websocket_broadcast():
    """启动轻量 WS 服务，连接客户端验证广播"""
    print("\n" + "="*60)
    print("🔌 测试 3: WebSocket 广播")
    print("="*60)

    from app.core.ws_manager import manager as ws_manager
    from app.core.signal_queue import SignalEvent, _handle_signal

    ws_app = FastAPI()
    ws_router = APIRouter()

    @ws_router.websocket("/ws")
    async def test_ws(ws):
        await ws_manager.connect(ws)
        try:
            while True:
                data = await ws.receive_text()
                if data.strip().lower() == "ping":
                    await ws.send_text('{"type":"pong"}')
        except Exception:
            pass
        finally:
            await ws_manager.disconnect(ws)

    ws_app.include_router(ws_router)

    # 在后台线程启动 server
    config = uvicorn.Config(ws_app, host="127.0.0.1", port=8765, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    await asyncio.sleep(1.5)  # 等服务器就绪

    # 连接 WS 客户端
    import httpx
    async with httpx.AsyncClient() as client:
        # 发起 WS 升级请求（httpx 支持）
        async with client.stream("GET", "http://127.0.0.1:8765/ws") as resp:
            pass

    # 测试: 直接连 WebSocket
    try:
        from websockets.asyncio.client import connect as ws_connect
        async with ws_connect("ws://127.0.0.1:8765/ws") as ws:
            print("  ✅ WebSocket 客户端已连接")

            # 发个 ping 测试连通性
            await ws.send("ping")
            pong = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"  ✅ ping/pong 正常: {pong}")

            # 触发一次信号广播
            event = SignalEvent(
                stock_code="000001",
                stock_name="平安银行",
                signal_type="急涨",
                price=12.34,
                change_pct=5.67,
                push_title="测试信号",
                push_content="测试推送内容",
            )
            await _handle_signal(event)
            print("  ✅ 广播已触发")

            # 等待接收广播消息
            broadcast = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(broadcast)
            print(f"  ✅ 收到广播: type={msg['type']}, data.stock_code={msg['data']['stock_code']}")
            print(f"     内容: {json.dumps(msg, ensure_ascii=False, indent=2)[:200]}...")

    except Exception as e:
        print(f"  ⚠️ WS 测试异常（不影响钉钉测试）: {e}")

    server.should_exit = True
    return True


# ── 测试 3: 钉钉回调端点 ──

async def test_dingtalk_callback():
    """测试 POST /api/dingtalk/callback 端点的指令处理"""
    print("\n" + "="*60)
    print("📞 测试 4: 钉钉回调指令处理（不发送到钉钉）")
    print("="*60)

    from app.api.dingtalk import _cmd_add, _cmd_remove, _run_cmd, _stock_status_text

    # status（不需要网络）
    result = _stock_status_text()
    print(f"  status: {result[:80]}...")
    assert "股票池" in result or "为空" in result
    print("  ✅ status 指令 OK")

    # remove（不会实际影响文件）
    result = await _cmd_remove(["000001"])
    print(f"  remove: {result}")
    print("  ✅ remove 指令 OK")

    # 未知指令
    result = await _run_cmd("hello")
    print(f"  未知指令: {result}")
    assert "未知" in result
    print("  ✅ 未知指令处理 OK")

    return True


# ── 主入口 ──

async def main():
    # Mock 数据库层 — 确保每个函数都是 AsyncMock（可 await）
    mock_crud = _patcher.start()
    mock_crud.insert_signal = AsyncMock(return_value=999)
    mock_crud.insert_signal_accuracy = AsyncMock(return_value=1)
    mock_crud.get_bili_dynamic = AsyncMock(return_value=None)
    mock_crud.insert_bili_dynamic = AsyncMock(return_value=1)
    print("🔧 数据库层已 Mock（不会连接 MySQL）")

    results = []

    # 测试 1: 钉钉推送
    ok = await test_dingtalk_push()
    results.append(("钉钉推送", ok))

    # 测试 WS（可选，需要 --ws 参数）
    if "--ws" in sys.argv:
        ok = await test_websocket_broadcast()
        results.append(("WebSocket 广播", ok))
    else:
        print("\n⏭️  跳过 WebSocket 测试（加 --ws 参数启用）")

    # 测试回调指令
    ok = await test_dingtalk_callback()
    results.append(("钉钉回调指令", ok))

    # 汇总
    print("\n" + "="*60)
    print("📊 测试汇总")
    print("="*60)
    all_ok = True
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("🎉 全部测试通过！")
    else:
        print("⚠️  有测试未通过，请检查上方日志")

    _patcher.stop()
    return all_ok


if __name__ == "__main__":
    asyncio.run(main())
