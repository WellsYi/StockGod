"""
WebSocket 路由

提供实时推送端点，前端通过 WebSocket 连接接收信号和B站动态推送。
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.ws_manager import manager as ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket 主端点 — 前端连接此接口接收实时推送"""
    await ws_manager.connect(ws)
    try:
        # 保持连接存活，处理客户端发来的消息（如 ping）
        while True:
            data = await ws.receive_text()
            # 简单回应 ping
            if data.strip().lower() == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"  [WS] 连接异常: {e}")
    finally:
        await ws_manager.disconnect(ws)
