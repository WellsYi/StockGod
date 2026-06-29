"""
股票监控主循环

定时轮询股票池行情 → 信号检测 → 入队列 → LLM 解读（批量）→ 定时简报
"""

import asyncio
from datetime import datetime

from app import config
from app.core.monitors import stock_core as sc
from app.core import signal_queue
from app.core.llm import client as llm


async def _monitor_loop():
    """单次监控循环：遍历股票池，检测信号"""
    stocks = await sc.load_stocks()
    if not stocks:
        await asyncio.sleep(config.STOCK_CHECK_INTERVAL)
        return

    state = sc.load_state()
    signals_batch = []
    pending_signals = []  # 暂存待入队信号（携带行情数据）

    for item in stocks:
        code = item.get("code", "")
        name = item.get("name", "")
        market = sc.resolve_market(code)
        st = sc.get_stock_state(state, code)

        # 获取行情
        q = await sc.fetch_quote(code, market)
        if not q:
            continue

        # 获取分钟K线（用于信号检测）
        bars = await sc.fetch_minute_klines(code, market, count=60)

        # 信号检测
        alerts = []
        for detector in [sc.check_volume_burst, sc.check_vwap_break, sc.check_limit_alert]:
            try:
                alert = detector(q, bars, st["alerts_sent"], code, name)
                if alert:
                    alerts.append(alert)
                    st["alerts_sent"].append(alert["alert_id"])
            except Exception as e:
                print(f"  {code} 信号检测异常: {e}")

        # 收集信号（暂不入队）
        for alert in alerts:
            signals_batch.append({
                "name": name, "code": code, "price": q["now"],
                "change_pct": q["change_pct"],
                "signal_type": alert["signal_type"],
                "detail": alert["detail"],
            })
            pending_signals.append({
                "code": code, "name": name, "price": q["now"],
                "change_pct": q["change_pct"],
                "signal_type": alert["signal_type"],
                "signal_detail": {
                    "ratio": q.get("quantity_ratio"),
                    "turnover": q.get("turnover_rate"),
                    "amount": q.get("amount"),
                },
                "content": alert.get("content", ""),
            })

        # 定时简报（直接推送，无需LLM）
        now_slot = datetime.now().strftime("%H%M")
        if now_slot in sc.BRIEF_SLOTS and not st["briefs_sent"].get(now_slot):
            daily_bars = await sc.fetch_daily_klines(code, market)
            msg = sc.build_brief(now_slot, code, name, q, bars, daily_bars)
            if msg:
                slot_name = sc.BRIEF_NAMES.get(now_slot, now_slot)
                await signal_queue.push(signal_queue.SignalEvent(
                    stock_code=code,
                    stock_name=name,
                    signal_type=f"定时简报-{slot_name}",
                    price=q["now"],
                    change_pct=q["change_pct"],
                    push_title=f"📋 {name} {slot_name}",
                    push_content=msg,
                ))
                st["briefs_sent"][now_slot] = True

    # 批量 LLM 分析
    analyses: list[str] = []
    if signals_batch and config.LLM_API_KEY:
        try:
            analyses = await llm.batch_analyze_signals(signals_batch)
        except Exception as e:
            print(f"  [监控] 批量LLM分析失败: {e}")

    # 将信号（携带 LLM 解读）入队
    for i, s in enumerate(pending_signals):
        llm_text = analyses[i] if i < len(analyses) else None
        await signal_queue.push(signal_queue.SignalEvent(
            stock_code=s["code"],
            stock_name=s["name"],
            signal_type=s["signal_type"],
            price=s["price"],
            change_pct=s["change_pct"],
            signal_detail=s["signal_detail"],
            llm_analysis=llm_text,
            push_title=f"{'🚨' if '砸盘' in s['signal_type'] else '⚡'} {s['name']} {s['signal_type']}",
            push_content=s["content"],
        ))

    sc.save_state(state)


async def stock_monitor_main():
    """股票监控主循环（由 TaskManager 调用，自动重启）"""
    print(f"[监控] 股票监控启动，间隔 {config.STOCK_CHECK_INTERVAL}s")
    while True:
        try:
            await _monitor_loop()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"  [监控] 循环异常: {e}")
        await asyncio.sleep(config.STOCK_CHECK_INTERVAL)
