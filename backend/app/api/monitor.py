"""
监控任务控制 API 路由
"""

from fastapi import APIRouter, HTTPException

from app.core.task_manager import manager

router = APIRouter(prefix="/api", tags=["monitor"])


@router.get("/monitor")
async def monitor_status():
    """所有监控任务状态"""
    return {"tasks": manager.get_status()}


@router.post("/monitor/{name}/start")
async def start_monitor(name: str):
    """启动指定监控任务"""
    if name not in manager.get_status():
        raise HTTPException(status_code=404, detail=f"未知任务: {name}")
    if manager.get_status()[name] == "running":
        return {"message": f"{name} 已在运行"}
    await manager.start_all()
    return {"message": f"{name} 已启动"}


@router.post("/monitor/{name}/stop")
async def stop_monitor(name: str):
    """停止指定监控任务"""
    if name not in manager.get_status():
        raise HTTPException(status_code=404, detail=f"未知任务: {name}")
    if manager.get_status()[name] == "stopped":
        return {"message": f"{name} 已停止"}
    manager.stop(name)
    return {"message": f"{name} 已停止"}
