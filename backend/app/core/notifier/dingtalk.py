"""
钉钉推送模块

两个机器人独立配置，但共享同一套签名和发送逻辑。
"""

import hmac
import hashlib
import base64
import urllib.parse
import time

import httpx

from app import config


def _gen_sign(timestamp: str, secret: str) -> str:
    """生成 HMAC-SHA256 签名"""
    sign_str = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        sign_str.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return urllib.parse.quote_plus(base64.b64encode(hmac_code))


async def send(
    webhook: str,
    secret: str,
    title: str,
    content: str,
    link_url: str = None,
) -> bool:
    """发送 Markdown 消息到钉钉"""
    url = webhook
    if secret:
        ts = str(int(time.time() * 1000))
        sign = _gen_sign(ts, secret)
        url += f"&timestamp={ts}&sign={sign}"

    if link_url:
        title_line = f"[{title}]({link_url})\n\n"
    else:
        title_line = f"**{title}**\n\n"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title[:50],
            "text": title_line + content,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return resp.json().get("errcode") == 0
    except Exception as e:
        print(f"  [钉钉] 推送失败: {e}")
        return False


async def send_bili(title: str, content: str, link_url: str = None) -> bool:
    """发送到 B站监控机器人"""
    return await send(
        webhook=config.DINGTALK_BILI_WEBHOOK,
        secret=config.DINGTALK_BILI_SECRET,
        title=title,
        content=content,
        link_url=link_url,
    )


async def send_stock(title: str, content: str, link_url: str = None) -> bool:
    """发送到股票监控机器人"""
    return await send(
        webhook=config.DINGTALK_STOCK_WEBHOOK,
        secret=config.DINGTALK_STOCK_SECRET,
        title=title,
        content=content,
        link_url=link_url,
    )


async def send_raw(payload: dict) -> bool:
    """发送原始消息体（用于回调回复）"""
    url = config.DINGTALK_STOCK_WEBHOOK
    if config.DINGTALK_STOCK_SECRET:
        ts = str(int(time.time() * 1000))
        sign = _gen_sign(ts, config.DINGTALK_STOCK_SECRET)
        url += f"&timestamp={ts}&sign={sign}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return resp.json().get("errcode") == 0
    except Exception as e:
        print(f"  [钉钉] 回复失败: {e}")
        return False
