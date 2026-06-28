"""
B站 UP 主动态监控（async 版）

定时轮询 UP 主最新动态 → LLM 摘要 → 入队（写入 MySQL + 推送钉钉）
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from bilibili_api import user, Credential
from bilibili_api.login_v2 import QrCodeLogin, QrCodeLoginEvents

from app import config
from app.core import signal_queue
from app.core.llm import client as llm


# ============================================================
#  凭据管理
# ============================================================

def _load_credential() -> Credential | None:
    if Path(config.CRED_FILE).exists():
        data = json.loads(Path(config.CRED_FILE).read_text("utf-8"))
        return Credential(
            sessdata=data.get("sessdata", ""),
            bili_jct=data.get("bili_jct", ""),
            buvid3=data.get("buvid3", ""),
        )
    return None


def _save_credential(cred: Credential):
    data = {
        "sessdata": cred.sessdata,
        "bili_jct": cred.bili_jct,
        "buvid3": cred.buvid3,
    }
    Path(config.CRED_FILE).write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    print("[B站] 登录凭据已保存")


async def _login() -> Credential:
    """获取凭据：优先从文件加载，没有则扫码登录"""
    cred = _load_credential()
    if cred:
        print("[B站] 已加载登录凭据")
        return cred

    print("[B站] 首次运行，请扫码登录...")
    qr = QrCodeLogin()
    await qr.generate_qrcode()
    print(qr.get_qrcode_terminal())
    print("等待扫码...")

    import asyncio
    while True:
        event = await qr.check_state()
        if event == QrCodeLoginEvents.SCAN:
            print("已扫描，请在手机上确认...")
        elif event == QrCodeLoginEvents.CONF:
            print("已确认...")
        elif event == QrCodeLoginEvents.DONE:
            cred = qr.get_credential()
            _save_credential(cred)
            print("[B站] 登录成功！")
            return cred
        elif event == QrCodeLoginEvents.TIMEOUT:
            print("[B站] 二维码已过期")
            return None
        await asyncio.sleep(2)


# ============================================================
#  动态获取与解析
# ============================================================

async def _fetch_dynamics(uid: str, credential: Credential) -> list:
    """获取UP主最新动态（async）"""
    try:
        u = user.User(int(uid), credential)
        page = await u.get_dynamics_new(offset="")
        return page.get("items", [])
    except Exception as e:
        print(f"  [B站] 获取动态失败: {e}")
        return []


def _extract_info(item: dict) -> dict | None:
    """从动态中提取需要的信息"""
    try:
        dynamic_id = str(item.get("id_str", ""))
        modules = item.get("modules", {})
        author_module = modules.get("module_author", {})
        author_name = author_module.get("name", "未知UP主")

        # 提取描述文本
        desc_module = modules.get("module_dynamic", {})
        desc_obj = desc_module.get("desc") or {}
        desc = desc_obj.get("text", "") if isinstance(desc_obj, dict) else ""

        # 转发内容
        if not desc and "module_forward" in modules:
            fwd = modules["module_forward"]
            fwd_desc = fwd.get("module_dynamic", {}).get("desc") or {}
            desc = fwd_desc.get("text", "") if isinstance(fwd_desc, dict) else ""

        # 视频/图文/长文
        if not desc:
            major = desc_module.get("major", {})
            if major.get("archive"):
                desc = major["archive"].get("title", "")
            elif major.get("draw"):
                items = major["draw"].get("items", [])
                desc = items[0].get("text", "") if items else ""
            elif major.get("opus"):
                summary = major["opus"].get("summary", {})
                if summary:
                    desc = summary.get("text", "")

        desc = desc.strip()[:500] or "(无文字内容)"

        basic = item.get("basic", {})
        link = basic.get("jump_url", "")
        link = ("https:" + link) if link.startswith("//") else link or f"https://t.bilibili.com/{dynamic_id}"

        return {"id": dynamic_id, "author": author_name, "desc": desc, "link": link}
    except Exception:
        return None


# ============================================================
#  缓存
# ============================================================

def _load_sent_ids() -> set:
    if Path(config.BILI_CACHE_FILE).exists():
        return set(json.loads(Path(config.BILI_CACHE_FILE).read_text("utf-8")))
    return set()


def _save_sent_ids(ids: set):
    Path(config.BILI_CACHE_FILE).write_text(
        json.dumps(list(ids), ensure_ascii=False), encoding="utf-8"
    )


# ============================================================
#  主循环（由 TaskManager 调用）
# ============================================================

async def bili_monitor_main():
    """B站监控主循环（自动重启）"""
    print("[B站] B站监控启动")

    credential = await _login()
    if not credential:
        print("[B站] 登录失败，监控跳过")
        return

    sent_ids = _load_sent_ids()
    print(f"[B站] 已缓存 {len(sent_ids)} 条历史动态")

    import asyncio

    # 首次运行：只标记不推送
    if not sent_ids:
        print("[B站] 首次运行，标记最近动态为已读...")
        for uid in config.BILI_UIDS:
            items = await _fetch_dynamics(uid, credential)
            for item in items:
                info = _extract_info(item)
                if info:
                    sent_ids.add(info["id"])
        _save_sent_ids(sent_ids)
        print(f"[B站] 标记完成 ({len(sent_ids)} 条)")

    while True:
        print(f"{datetime.now().strftime('%H:%M:%S')} 检查B站新动态...")
        new_count = 0
        for uid in config.BILI_UIDS:
            items = await _fetch_dynamics(uid, credential)

            for item in reversed(items):
                info = _extract_info(item)
                if info and info["id"] not in sent_ids:
                    # LLM 摘要
                    summary = ""
                    if config.LLM_API_KEY:
                        try:
                            summary = await llm.summarize_dynamic(info["desc"])
                        except Exception as e:
                            print(f"  [B站] LLM摘要失败: {e}")

                    if summary and summary.startswith("[LLM"):
                        summary = ""

                    # 入队列（后续写入 MySQL + 推送钉钉）
                    await signal_queue.push(signal_queue.BiliEvent(
                        dynamic_id=info["id"],
                        author=info["author"],
                        content=info["desc"],
                        llm_summary=summary or info["desc"][:200],
                        link_url=info["link"],
                    ))

                    sent_ids.add(info["id"])
                    new_count += 1
                    print(f"  [B站] 新动态: {info['desc'][:30]}...")

        if new_count:
            print(f"  -> 处理 {new_count} 条新动态")
        _save_sent_ids(sent_ids)

        await asyncio.sleep(config.BILI_CHECK_INTERVAL)
