"""
WebSocket 连接管理器

管理所有 WebSocket 客户端连接，提供广播能力。
供 signal_queue 在事件处理后调用。
"""

import asyncio
import json
from datetime import date, datetime
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """管理 WebSocket 连接和广播"""

    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        print(f"  [WS] 客户端连接，当前 {len(self._connections)} 个连接")

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._connections.discard(ws)
        print(f"  [WS] 客户端断开，当前 {len(self._connections)} 个连接")

    async def broadcast(self, event_type: str, data: dict[str, Any]):
        """向所有连接的客户端广播消息"""
        payload = json.dumps(
            {
                "type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            },
            ensure_ascii=False,
            default=self._json_default,
        )
        async with self._lock:
            dead: list[WebSocket] = []
            for ws in self._connections:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.discard(ws)

    @property
    def active_count(self) -> int:
        return len(self._connections)

    @staticmethod
    def _json_default(obj: Any) -> str:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# 全局单例
manager = ConnectionManager()
