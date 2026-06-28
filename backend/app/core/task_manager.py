"""
后台任务管理器

管理和监控所有 async 后台任务的生命周期（启动/停止/状态）。
"""

import asyncio
import signal
from typing import Callable, Awaitable


class TaskManager:
    """注册、启动、停止后台任务"""

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._factories: dict[str, Callable[[], Awaitable[None]]] = {}

    def register(self, name: str, factory: Callable[[], Awaitable[None]]):
        """注册一个后台任务工厂函数"""
        self._factories[name] = factory

    async def start_all(self):
        """启动所有已注册的任务"""
        for name, factory in self._factories.items():
            if name not in self._tasks or self._tasks[name].done():
                task = asyncio.create_task(_run_forever(name, factory), name=name)
                self._tasks[name] = task
                print(f"[任务] {name} 已启动")

    async def stop_all(self):
        """停止所有任务"""
        for name, task in self._tasks.items():
            if not task.done():
                task.cancel()
        # 等待所有任务结束
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
            print(f"[任务] 已停止 {len(self._tasks)} 个任务")
        self._tasks.clear()

    def stop(self, name: str):
        """停止指定任务"""
        task = self._tasks.get(name)
        if task and not task.done():
            task.cancel()
            print(f"[任务] {name} 已停止")

    def get_status(self) -> dict[str, str]:
        """获取所有任务状态"""
        return {
            name: "running" if not task.done() else "stopped"
            for name, task in self._tasks.items()
        }

    @property
    def running(self) -> bool:
        return any(not t.done() for t in self._tasks.values())


async def _run_forever(name: str, factory: Callable[[], Awaitable[None]]):
    """自动重启的任务包装器"""
    while True:
        try:
            await factory()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"  [任务] {name} 异常退出，5秒后重启: {e}")
            await asyncio.sleep(5)


# 全局单例
manager = TaskManager()
