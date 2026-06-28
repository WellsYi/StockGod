"""
钉钉回调 API 路由

接收钉钉机器人的回调请求（自定义机器人出站回调），
解析指令并执行对应操作（add/remove/list/status），
通过 dingtalk.send_raw() 回复到钉钉群。

兼容旧项目 `python -m src.monitors.stock webhook` 的指令格式。
旧入口: HTTPServer(:5800) → 新入口: POST /api/dingtalk/callback
"""

import re

from fastapi import APIRouter, Request

from app import config
from app.core.llm import client as llm
from app.core.monitors import stock_core as sc
from app.core.notifier import dingtalk

router = APIRouter(prefix="/api/dingtalk", tags=["dingtalk"])


# ── 辅助函数 ──


def _clean_msg(text: str) -> str:
    """去掉 @机器人 前缀（兼容钉钉群聊 @ 格式）"""
    text = re.sub(r'@.*? ', '', text)  #   是钉钉 @ 后的空格
    text = re.sub(r'@.*?\s', '', text)
    return text.strip()


async def _stock_status_text() -> str:
    """生成股票池状态文本"""
    stocks = await sc.load_stocks()
    if not stocks:
        return "股票池为空"
    lines = [f"股票池（共 {len(stocks)} 只）："]
    for s in stocks:
        m = "上证" if s.get("market") == 1 else "深证"
        lines.append(f"  {s['code']}  {s['name']}  {m}")
    return "\n".join(lines)


async def _cmd_add(args: list[str]) -> str:
    """添加股票到池"""
    if not args:
        return "用法: add <股票代码>"
    code = args[0]
    market = sc.resolve_market(code)
    stocks = await sc.load_stocks()
    if any(s["code"] == code for s in stocks):
        return f"{code} 已在股票池中"

    name = (await sc.fetch_stock_name(code, market)) or code
    stocks.append({"code": code, "name": name, "market": market})
    await sc.save_stocks(stocks)

    market_name = "上证" if market == 1 else "深证"
    data = await sc.fetch_full_quote(code, market)
    if not data:
        await dingtalk.send_stock(f"{name} 已添加",
            f"[OK] {name}（{code}）已添加到股票池，当前非交易时段，盘面数据待补充。")
        return f"[OK] 已添加 {name}({code})"

    # 解析行情字段
    price = data.get("f43", 0) / 100.0
    high = data.get("f44", 0) / 100.0
    low = data.get("f45", 0) / 100.0
    open_p = data.get("f46", 0) / 100.0
    volume = data.get("f47", 0)
    amount = data.get("f48", 0) / 1e8
    close_yest = data.get("f60", 0) / 100.0
    change_pct = data.get("f170", 0) / 100.0
    turnover_rate = data.get("f168", 0) / 100.0
    quantity_ratio = data.get("f50", 0) / 100.0
    amplitude = data.get("f171", 0) / 100.0 if data.get("f171") else 0
    total_mv = data.get("f116", 0) / 1e8
    free_mv = data.get("f117", 0) / 1e8
    high_52w = data.get("f162", 0) / 100.0 if data.get("f162") else 0
    low_52w = data.get("f167", 0) / 100.0 if data.get("f167") else 0

    bars = await sc.fetch_daily_klines(code, market, 20)

    vol_lot = volume / 10000 if volume else 0
    raw_report = (
        f"**{name}**（{code}）\n\n"
        f"**▎市值**\n"
        f"总市值　{total_mv:.1f}亿　流通　{free_mv:.1f}亿\n\n"
        f"**▎价格**\n"
        f"现价　**{price:.2f}**　涨跌 **{change_pct:+.2f}%**\n"
        f"今开　{open_p:.2f}　昨收　{close_yest:.2f}\n"
        f"最高　{high:.2f}　最低　{low:.2f}　振幅　{amplitude:.2f}%\n"
        f"52周　{low_52w:.2f} ~ {high_52w:.2f}\n\n"
        f"**▎量能**\n"
        f"成交　{amount:.2f}亿（{vol_lot:.0f}万手）\n"
        f"换手　{turnover_rate:.2f}%　量比　{quantity_ratio:.2f}"
    )
    await dingtalk.send_stock(f"{name} 已添加 — 盘面速览", raw_report)

    if config.LLM_API_KEY:
        analysis = await llm.analyze_new_stock(
            name=name, code=code, market_name=market_name,
            price=price, change_pct=change_pct,
            high=high, low=low,
            volume=vol_lot, amount=amount,
            turnover_rate=turnover_rate,
            quantity_ratio=quantity_ratio,
            amplitude=amplitude,
            total_mv=total_mv, free_mv=free_mv,
            high_52w=high_52w, low_52w=low_52w,
            open=open_p, close_yest=close_yest,
            recent_days=bars,
        )
        if not analysis.startswith("[LLM"):
            await dingtalk.send_stock(f"🧠 {name} AI分析", f"{name}（{code}）\n\n{analysis}")

    return f"[OK] 已添加 {name}({code})"


async def _cmd_remove(args: list[str]) -> str:
    """从股票池删除"""
    if not args:
        return "用法: remove <股票代码>"
    code = args[0]
    stocks = await sc.load_stocks()
    new_stocks = [s for s in stocks if s["code"] != code]
    if len(new_stocks) == len(stocks):
        return f"未找到 {code}"
    await sc.save_stocks(new_stocks)
    return f"[OK] 已删除 {code}"


async def _run_cmd(cmd: str) -> str:
    """解析并执行钉钉指令"""
    parts = cmd.strip().split()
    if not parts:
        return "支持命令: add/remove/list/status"
    action = parts[0].lower()
    try:
        if action == "add":
            return await _cmd_add(parts[1:])
        elif action in ("remove", "del", "delete"):
            return await _cmd_remove(parts[1:])
        elif action in ("list", "status"):
            return await _stock_status_text()
        else:
            return f"未知: {action}\n支持: add/remove/list/status"
    except Exception as e:
        return f"失败: {e}"


# ── 端点 ──


@router.post("/callback")
async def dingtalk_callback(request: Request):
    """接收钉钉出站回调 Webhook

    钉钉群聊中 @机器人 后发送的消息会转发到此端点。
    支持指令: add <代码> / remove <代码> / list / status
    """
    body = await request.json()

    # 解析消息字段（兼容新旧字段名）
    text = ""
    sender_nick = body.get("senderNick", "")
    conversation_type = body.get("conversationType", "")

    msg_body = body.get("text", body.get("content", {}))
    if isinstance(msg_body, dict):
        text = msg_body.get("content", "")
    else:
        text = str(msg_body)

    # 群聊中必须 @了机器人才回复，否则静默
    if conversation_type == "2":
        at_users = body.get("atUsers", body.get("at_users", []))
        if not at_users:
            return {"msg": "ok"}

    clean = _clean_msg(text)
    if not clean:
        return {"msg": "ok"}

    print(f"  [钉钉回调] 来自: {sender_nick}  指令: {clean}")

    # 执行命令
    result = await _run_cmd(clean)
    reply = f"@{sender_nick}\n\n{result}" if sender_nick else result
    await dingtalk.send_raw({"msgtype": "text", "text": {"content": reply[:2000]}})

    return {"msg": "ok"}
