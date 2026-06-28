"""
涨停抓取模块

每日收盘后抓取全市场涨停股票，分析涨停原因，入库+推送。
数据源：东方财富行情中心。
"""

from __future__ import annotations

import json
from datetime import datetime, date
from typing import Any

import httpx

from app import config
from app.core.notifier import dingtalk
from app.core.llm import client as llm


# ============================================================
#  接口常量
# ============================================================

# 涨停板筛选: 主板/创业板/科创板, 全部A股涨幅榜
LIMIT_UP_URL = (
    "https://push2.eastmoney.com/api/qt/clist/get"
    "?pn=1&pz=100&po=1&np=1"
    "&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f62,f115,f128,f140,f136"
    "&fs=m:0+t:6+f:!2"  # A股, 涨幅排序, 排除退市等
    "&fid=f3"
)


# ============================================================
#  数据获取
# ============================================================

async def fetch_limit_up_stocks() -> list[dict]:
    """获取当日涨停股票列表

    返回:
        [{"code", "name", "price", "change_pct", "turnover_rate", ...}, ...]
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(LIMIT_UP_URL, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()

    raw_list = data.get("data", {}).get("diff", [])
    if not raw_list:
        return []

    results = []
    for item in raw_list:
        pct = (item.get("f3") or 0) / 100
        # 精确过滤: 主板>=9.8%, 创业板/科创板>=19.5%
        board = _detect_board(item.get("f12", ""))
        threshold = 19.5 if board in ("创业板", "科创板") else 9.8
        if pct < threshold:
            continue

        results.append({
            "code": item.get("f12", ""),
            "name": item.get("f14", ""),
            "price": (item.get("f2") or 0) / 10000 if (item.get("f2") or 0) > 1000 else (item.get("f2") or 0) / 100,
            "change_pct": pct,
            "high": (item.get("f15") or 0) / 100 if item.get("f15") else 0,
            "low": (item.get("f16") or 0) / 100 if item.get("f16") else 0,
            "amount": (item.get("f20") or 0) / 1e8 if item.get("f20") else 0,
            "turnover_rate": (item.get("f62") or 0) / 100 if item.get("f62") else 0,
            "board_type": board,
        })

    return results


def _detect_board(code: str) -> str:
    if code.startswith(("30", "301")):
        return "创业板"
    if code.startswith(("688", "689")):
        return "科创板"
    if code.startswith(("00", "001", "002", "003", "60", "605")):
        return "主板"
    if code.startswith(("4", "8")):
        return "北交所"
    return "其他"


# ============================================================
#  涨停原因分析（LLM）
# ============================================================

async def analyze_reason(
    code: str, name: str, price: float, change_pct: float,
    turnover_rate: float, board_type: str,
    concept_tags: list[str],
    limit_times: int,
) -> tuple[str, list[str]]:
    """LLM 分析涨停原因

    Returns:
        (reason_text, [reason_tags])
    """
    tags_str = "、".join(concept_tags) if concept_tags else "未知"
    prompt = (
        f"股票：{name}（{code}）\n"
        f"价格：{price}  涨幅：{change_pct:+.2f}%\n"
        f"换手率：{turnover_rate}%  所属板块：{board_type}\n"
        f"所属概念：{tags_str}\n"
        f"连板次数：{limit_times}次\n\n"
        f"请分析该股票今日涨停的原因，输出格式：\n"
        f"原因：<简要说明涨停原因，2-3句话>\n"
        f"标签：<原因标签，逗号分隔，如：板块联动,政策利好,业绩预增,消息刺激,资金推动,超跌反弹>"
    )

    sp = (
        "你是一个A股涨停原因分析助手。根据用户提供的股票数据，分析涨停原因。"
        "输出格式固定，不要加多余文字。"
    )

    # 由于当前 LLM 客户端是异步的，直接调用
    result = await llm.chat(sp, prompt, max_tokens=512, temperature=0.3)

    # 解析输出
    reason = result
    tags = []
    if "标签：" in result:
        parts = result.split("标签：")
        reason = parts[0].replace("原因：", "").strip()
        if len(parts) > 1:
            tags = [t.strip() for t in parts[1].split(",") if t.strip()]

    return reason, tags


# ============================================================
#  概念板块获取（从东方财富）
# ============================================================

async def fetch_concept_tags(code: str) -> list[str]:
    """获取股票所属概念板块"""
    url = (
        f"https://push2.eastmoney.com/api/qt/stock/get"
        f"?secid={code}&fields=f57,f58,f127"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            data = resp.json().get("data", {})
            # f127 是概念板块字符串
            concept_str = data.get("f127", "")
            if concept_str:
                return [c.strip() for c in concept_str.split(";") if c.strip()]
    except Exception:
        pass
    return []


# ============================================================
#  连板次数计算（需要查询当日+前几日的涨停记录）
# ============================================================

async def calc_limit_times(code: str, current_date: date) -> int:
    """简单版：暂返回1，后续通过查询数据库历史记录实现"""
    # TODO: 查 limit_up_daily 表中该股票最近连续涨停天数
    return 1


# ============================================================
#  推送
# ============================================================

def build_push_message(stocks: list[dict]) -> str:
    """构建钉钉推送消息"""
    if not stocks:
        return "今日无涨停股票"

    lines = [f"📊 今日涨停 {len(stocks)} 只", ""]
    for s in stocks[:20]:  # 最多20只
        times = f" {s['limit_times']}连板" if s['limit_times'] > 1 else ""
        lines.append(
            f"**{s['name']}**（{s['code']}）"
            f"　{s['price']:.2f}　**+{s['change_pct']:.2f}%**{times}"
        )
        if s.get('reason_llm'):
            lines.append(f"> {s['reason_llm'][:80]}...")
        if s.get('concept_tags'):
            lines.append(f" 概念：{'、'.join(s['concept_tags'][:5])}")
        lines.append("")

    return "\n".join(lines)


# ============================================================
#  主流程
# ============================================================

async def run_daily_check():
    """每日收盘后运行：抓取涨停 → LLM分析 → 入库 → 推送"""
    today = date.today()
    if today.weekday() >= 5:
        print("[涨停] 周末跳过")
        return

    print(f"[涨停] 开始抓取 {today}...")

    # 1. 获取涨停列表
    stocks = await fetch_limit_up_stocks()
    if not stocks:
        print("[涨停] 今日无涨停")
        await dingtalk.send_stock("📊 今日涨停", "今日无涨停股票")
        return

    print(f"[涨停] 共 {len(stocks)} 只涨停")

    # 2. 逐只分析
    for s in stocks:
        # 获取概念
        concepts = await fetch_concept_tags(s["code"])
        s["concept_tags"] = concepts

        # 计算连板
        s["limit_times"] = await calc_limit_times(s["code"], today)

        # LLM 分析原因
        if config.LLM_API_KEY:
            reason, tags = await analyze_reason(
                s["code"], s["name"], s["price"], s["change_pct"],
                s["turnover_rate"], s["board_type"],
                concepts, s["limit_times"],
            )
            s["reason_llm"] = reason
            s["reason_tags"] = tags
            print(f"  {s['name']}: {reason[:50]}...")

    # 3. 推送钉钉
    msg = build_push_message(stocks)
    await dingtalk.send_stock(f"📊 今日涨停 {len(stocks)} 只", msg)

    # 4. 入库（TODO: 等MySQL模块就绪后写入 limit_up_daily 表）

    print(f"[涨停] 完成，今日 {len(stocks)} 只涨停")
