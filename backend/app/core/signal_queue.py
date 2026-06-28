"""
信号队列桥接

监控任务检测到信号/动态后，Push 到 asyncio.Queue，
后台 consumer 批量写入 MySQL，解耦监控与写入。
"""

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from app.core.notifier import dingtalk
from app.core.ws_manager import manager as ws_manager
from app.db import crud


@dataclass
class SignalEvent:
    """股票信号事件"""
    stock_code: str
    stock_name: str
    signal_type: str
    price: float
    change_pct: float | None = None
    signal_detail: dict | None = None
    llm_analysis: str | None = None
    push_title: str = ""
    push_content: str = ""

    @property
    def trigger_time(self) -> datetime:
        return datetime.now()


@dataclass
class BiliEvent:
    """B站动态事件"""
    dynamic_id: str
    author: str
    content: str
    llm_summary: str | None = None
    link_url: str | None = None

    @property
    def pushed_at(self) -> datetime:
        return datetime.now()


# 全局队列
_queue: asyncio.Queue[SignalEvent | BiliEvent] = asyncio.Queue(maxsize=500)

# consumer 任务引用
_consumer_task: asyncio.Task | None = None


async def push(event: SignalEvent | BiliEvent):
    """压入事件到队列（非阻塞，满则丢弃）"""
    try:
        _queue.put_nowait(event)
    except asyncio.QueueFull:
        print(f"  [队列] 队列满，丢弃事件: {type(event).__name__}")


async def _consumer():
    """后台 consumer：从队列取事件，写入 MySQL + 钉钉推送"""
    while True:
        event = await _queue.get()
        try:
            if isinstance(event, SignalEvent):
                await _handle_signal(event)
            elif isinstance(event, BiliEvent):
                await _handle_bili(event)
        except Exception as e:
            print(f"  [队列] 处理失败: {e}")
        finally:
            _queue.task_done()


async def _handle_signal(event: SignalEvent):
    """处理股票信号：写入 MySQL -> 推送钉钉"""
    # 写入 signals 表
    sid = await crud.insert_signal(
        stock_code=event.stock_code,
        stock_name=event.stock_name,
        signal_type=event.signal_type,
        trigger_time=event.trigger_time,
        price=event.price,
        change_pct=event.change_pct,
        signal_detail=event.signal_detail,
        llm_analysis=event.llm_analysis,
    )

    # 创建准确率追踪记录
    await crud.insert_signal_accuracy(sid)

    # 推送钉钉
    if event.push_content:
        await dingtalk.send_stock(event.push_title or event.signal_type, event.push_content)

    # 广播到 WebSocket
    await ws_manager.broadcast("signal", {
        "id": sid,
        "stock_code": event.stock_code,
        "stock_name": event.stock_name,
        "signal_type": event.signal_type,
        "price": event.price,
        "change_pct": event.change_pct,
        "signal_detail": event.signal_detail,
        "llm_analysis": event.llm_analysis,
        "push_title": event.push_title,
        "trigger_time": event.trigger_time.isoformat(),
    })


async def _handle_bili(event: BiliEvent):
    """处理B站动态：写入 MySQL -> 推送钉钉"""
    # 先查是否已存在（幂等）
    existing = await crud.get_bili_dynamic(event.dynamic_id)
    if existing:
        return

    # 写入 bili_dynamics 表
    await crud.insert_bili_dynamic(
        dynamic_id=event.dynamic_id,
        author=event.author,
        content=event.content,
        llm_summary=event.llm_summary,
        link_url=event.link_url,
        pushed_at=datetime.now(),
    )

    # 推送钉钉
    if event.llm_summary:
        lines = [
            f"**{event.author}** 发布新动态\n",
            f"{event.llm_summary}",
        ]
        if event.link_url:
            lines.append(f"\n[查看原文]({event.link_url})")
        text = "\n".join(lines)
        await dingtalk.send_bili(f"📺 {event.author} 更新了", text, link_url=event.link_url)

    # 广播到 WebSocket
    await ws_manager.broadcast("bili_dynamic", {
        "dynamic_id": event.dynamic_id,
        "author": event.author,
        "content": event.content,
        "llm_summary": event.llm_summary,
        "link_url": event.link_url,
        "pushed_at": datetime.now().isoformat(),
    })


def start():
    """启动 consumer（应用启动时调用）"""
    global _consumer_task
    if _consumer_task is None or _consumer_task.done():
        _consumer_task = asyncio.create_task(_consumer(), name="signal-queue-consumer")
        print("[队列] consumer 已启动")


async def stop():
    """停止 consumer（应用关闭时调用）"""
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
        print("[队列] consumer 已停止")


async def get_stats() -> dict:
    """获取队列统计"""
    return {
        "queue_size": _queue.qsize(),
        "consumer_running": _consumer_task is not None and not _consumer_task.done(),
    }
