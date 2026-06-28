"""
股票盯盘系统 — 核心模块

行情获取、信号检测、定时简报。
"""

from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path

import httpx

from app import config
from app.core.notifier import dingtalk
from app.core.llm import client as llm
from app.db import pool
from app.db.crud import list_stock_pool, insert_stock_pool, delete_stock_pool


# ============================================================
#  股票池管理
# ============================================================

async def load_stocks() -> list:
    try:
        rows = await list_stock_pool()
        # DB 列名 stock_code/stock_name → 兼容旧代码的 code/name
        return [
            {"code": r["stock_code"], "name": r["stock_name"], "market": r["market"]}
            for r in rows
        ]
    except Exception:
        return []


async def save_stocks(stocks: list):
    """全量替换股票池"""
    from app.db.models import TBL_STOCK_POOL
    async with pool.get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"DELETE FROM {TBL_STOCK_POOL}")
            for s in stocks:
                await cur.execute(
                    f"INSERT INTO {TBL_STOCK_POOL} (stock_code, stock_name, market) VALUES (%s, %s, %s)",
                    (s["code"], s.get("name", s["code"]), s.get("market", 0)),
                )


def resolve_market(code: str) -> int:
    code = code.strip()
    return 1 if code.startswith(("6", "9")) else 0


# ============================================================
#  数据获取
# ============================================================

async def fetch_stock_name(code: str, market: int) -> str:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f57,f58",
            )
            name = (resp.json().get("data", {}).get("f58") or "").strip()
            return name if name else code
    except Exception:
        return code


async def fetch_full_quote(code: str, market: int) -> dict | None:
    """获取完整行情 + 基本面字段"""
    url = (
        f"https://push2.eastmoney.com/api/qt/stock/get?"
        f"secid={market}.{code}&fields=f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,"
        f"f84,f85,f86,f100,f116,f117,f162,f167,f168,f169,f170,f171"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            data = resp.json().get("data")
            if not data:
                return None
            return data
    except Exception:
        return None


async def fetch_daily_klines(code: str, market: int, days: int = 60) -> list:
    """获取日K线（用于计算技术指标和近期涨跌）"""
    url = (
        f"https://push2.eastmoney.com/api/qt/stock/kline/get?"
        f"secid={market}.{code}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56,f57"
        f"&klt=101&fqt=1&lmt={days}&end=20500101"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = resp.json().get("data", {}).get("klines", [])
        bars = []
        for line in raw:
            parts = line.split(",")
            if len(parts) >= 3:
                bars.append({
                    "date": parts[0],
                    "close": float(parts[2]),
                    "high": float(parts[3]),
                    "low": float(parts[4]),
                    "volume": int(parts[5]),
                })
        return bars
    except Exception:
        return []


async def fetch_quote(code: str, market: int) -> dict | None:
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f86,f127,f168,f169,f170,f171"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            data = resp.json().get("data")
            if not data or not data.get("f43"):
                return None
            return {
                "now": data["f43"] / 100.0,
                "high": data.get("f44", 0) / 100.0,
                "low": data.get("f45", 0) / 100.0,
                "open": data.get("f46", 0) / 100.0,
                "volume": data.get("f47", 0),
                "amount": data.get("f48", 0),
                "close_yest": data.get("f60", 0) / 100.0,
                "change_amount": data.get("f169", 0) / 100.0,
                "change_pct": data.get("f170", 0) / 100.0,
                "turnover_rate": data.get("f168", 0) / 100.0,
                "quantity_ratio": data.get("f50", 0) / 100.0,
                "amplitude": data.get("f171", 0) / 100.0 if data.get("f171") else 0,
            }
    except Exception as e:
        print(f"  {code} 行情失败: {e}")
        return None


async def fetch_minute_klines(code: str, market: int, count: int = 60) -> list:
    url = f"https://push2.eastmoney.com/api/qt/stock/kline/get?secid={market}.{code}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56,f57&klt=1&fqt=1&lmt={count}&end=20500101"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = resp.json().get("data", {}).get("klines", [])
        bars = []
        for line in raw:
            parts = line.split(",")
            bars.append({
                "time": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": int(parts[5]),
            })
        return bars
    except Exception as e:
        print(f"  {code} K线失败: {e}")
        return []


async def fetch_announcements(code: str) -> list:
    url = f"https://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_size=10&page_index=1&ann_type=A&stock_list={code}&f_node=1&s_node=0"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            items = resp.json().get("data", {}).get("list", [])
        return [
            {
                "id": item.get("art_code", ""),
                "title": item.get("title_ch", ""),
                "time": item.get("display_time", ""),
                "categories": [c.get("column_name", "") for c in item.get("columns", [])],
            }
            for item in items
        ]
    except Exception:
        return []


# ============================================================
#  技术指标计算
# ============================================================

def calc_ma(bars: list, period: int) -> float:
    """移动平均线"""
    if len(bars) < period:
        return 0
    return sum(b["close"] for b in bars[-period:]) / period


def calc_macd(bars: list) -> dict:
    """MACD 指标（快线12日、慢线26日、信号9日）"""
    closes = [b["close"] for b in bars]
    if len(closes) < 26:
        return {"dif": 0, "dea": 0, "macd": 0, "signal": ""}

    def _ema(data: list, n: int) -> list:
        k = 2 / (n + 1)
        ema = [data[0]]
        for v in data[1:]:
            ema.append(v * k + ema[-1] * (1 - k))
        return ema

    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    dif = ema12[-1] - ema26[-1]

    dif_list = [ema12[i] - ema26[i] for i in range(len(ema26))]
    dea_list = _ema(dif_list, 9)
    dea = dea_list[-1]
    macd = 2 * (dif - dea)

    prev_dif = dif_list[-2] if len(dif_list) > 1 else dif
    prev_dea = dea_list[-2] if len(dea_list) > 1 else dea
    if dif > dea and prev_dif <= prev_dea:
        signal = "金叉 ↑"
    elif dif < dea and prev_dif >= prev_dea:
        signal = "死叉 ↓"
    elif dif > dea:
        signal = "多头"
    else:
        signal = "空头"

    return {"dif": round(dif, 3), "dea": round(dea, 3), "macd": round(macd, 3), "signal": signal}


def calc_kdj(bars: list) -> dict:
    """KDJ 指标（9, 3, 3）"""
    if len(bars) < 9:
        return {"k": 0, "d": 0, "j": 0, "signal": ""}

    recent = bars[-9:]
    highest = max(b["high"] for b in recent)
    lowest = min(b["low"] for b in recent)
    close = bars[-1]["close"]
    rsv = (close - lowest) / (highest - lowest) * 100 if highest != lowest else 50

    k = 50.0
    d = 50.0
    for _ in range(len(bars)):
        k = 2 / 3 * k + 1 / 3 * rsv
        d = 2 / 3 * d + 1 / 3 * k
    j = 3 * k - 2 * d

    if k > 80 and d > 80:
        signal = "超买区"
    elif k < 20 and d < 20:
        signal = "超卖区"
    elif k > d and k < 50:
        signal = "偏多"
    elif k < d and k > 50:
        signal = "偏空"
    else:
        signal = "中性"

    return {"k": round(k, 1), "d": round(d, 1), "j": round(j, 1), "signal": signal}


def calc_rsi(bars: list, period: int = 6) -> float:
    """RSI 相对强弱指标"""
    if len(bars) < period + 1:
        return 0
    gains, losses = 0, 0
    for i in range(-period, 0):
        change = bars[i]["close"] - bars[i - 1]["close"]
        if change > 0:
            gains += change
        else:
            losses -= change
    if losses == 0:
        return 100 if gains > 0 else 50
    rs = gains / losses
    return round(100 - 100 / (1 + rs), 1)


def calc_bollinger(bars: list, period: int = 20) -> dict:
    """布林带"""
    if len(bars) < period:
        return {"mid": 0, "upper": 0, "lower": 0, "width": 0}
    ma = calc_ma(bars, period)
    variance = sum((b["close"] - ma) ** 2 for b in bars[-period:]) / period
    std = variance ** 0.5
    return {
        "mid": round(ma, 2),
        "upper": round(ma + 2 * std, 2),
        "lower": round(ma - 2 * std, 2),
        "width": round(4 * std / ma * 100, 2) if ma else 0,
    }


def build_indicator_block(daily_bars: list) -> str:
    """构建小白友好版技术指标块"""
    if len(daily_bars) < 5:
        return ""

    ma5 = calc_ma(daily_bars, 5)
    ma10 = calc_ma(daily_bars, 10)
    ma20 = calc_ma(daily_bars, 20)
    macd = calc_macd(daily_bars)
    boll = calc_bollinger(daily_bars)
    rsi14 = calc_rsi(daily_bars, 14)

    pct_5d = (daily_bars[-1]["close"] - daily_bars[-5]["close"]) / daily_bars[-5]["close"] * 100 if len(daily_bars) >= 5 else 0
    pct_20d = (daily_bars[-1]["close"] - daily_bars[-20]["close"]) / daily_bars[-20]["close"] * 100 if len(daily_bars) >= 20 else 0

    lines = ["**▎趋势判断**"]

    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            lines.append(f"**均线多头排列**，短期趋势偏强　MA5 {ma5:.2f}")
        elif ma5 < ma10 < ma20:
            lines.append(f"**均线空头排列**，短期趋势偏弱　MA5 {ma5:.2f}")
        elif ma5 > ma10 and ma10 < ma20:
            lines.append(f"**短线走强**，中线还在整理　MA5 {ma5:.2f}")
        else:
            lines.append(f"均线交织，**方向不明确**　MA5 {ma5:.2f}")
    else:
        lines.append(f"MA5 {ma5:.2f}")

    if macd['signal'] in ("金叉 ↑", "多头"):
        lines.append(f"**MACD 偏多**，上涨动能还在　DIF {macd['dif']}")
    elif macd['signal'] in ("死叉 ↓", "空头"):
        lines.append(f"**MACD 偏空**，下跌动能占优　DIF {macd['dif']}")
    else:
        lines.append(f"MACD {macd['signal']}")

    if boll['upper'] and boll['lower']:
        pos = (daily_bars[-1]['close'] - boll['lower']) / (boll['upper'] - boll['lower'])
        if pos > 0.85:
            lines.append(f"价格**靠近布林上轨**，短线偏贵　带宽 {boll['width']}%")
        elif pos < 0.15:
            lines.append(f"价格**靠近布林下轨**，短线偏便宜　带宽 {boll['width']}%")
        else:
            lines.append(f"价格在布林中轨附近运行　带宽 {boll['width']}%")

    if rsi14 > 0:
        if rsi14 > 70:
            lines.append(f"**RSI 偏高（{rsi14}）**，短期可能过热")
        elif rsi14 < 30:
            lines.append(f"**RSI 偏低（{rsi14}）**，短期可能超卖")
        else:
            lines.append(f"RSI 中性（{rsi14}），未到极端区域")

    if pct_5d != 0 or pct_20d != 0:
        lines.append(f"近5日 {pct_5d:+.2f}%　近20日 {pct_20d:+.2f}%")

    return "\n".join(lines)


# ============================================================
#  信号检测
# ============================================================

def calc_vwap(bars: list) -> float:
    total_vol = sum(b["volume"] for b in bars)
    if total_vol == 0:
        return 0
    total_pv = sum(b["volume"] * (b["high"] + b["low"] + b["close"]) / 3 for b in bars)
    return total_pv / total_vol


def check_volume_burst(q: dict, bars: list, alerts_sent: list, code: str, name: str) -> dict | None:
    """瞬间放量拉升/砸盘检测"""
    if len(bars) < 33:
        return None
    vol_3min = sum(b["volume"] for b in bars[-3:])
    vol_30min_avg = sum(b["volume"] for b in bars[-33:-3]) / 30
    if vol_30min_avg <= 0:
        return None
    ratio = vol_3min / vol_30min_avg
    if ratio < config.STOCK_BURST_RATIO:
        return None
    price_change = (q["now"] - bars[-3]["open"]) / bars[-3]["open"] * 100
    direction = "拉升" if price_change > 1.0 else ("砸盘" if price_change < -1.0 else None)
    if direction is None:
        return None
    alert_id = f"burst_{direction}"
    if alert_id in alerts_sent:
        return None
    return {
        "alert_id": alert_id,
        "signal_type": f"异常放量{direction}",
        "detail": f"近3分钟量:{vol_3min/10000:.0f}万手 30分钟均量:{vol_30min_avg/10000:.0f}万手 量比:{ratio:.1f}倍 变动:{price_change:+.2f}%",
        "content": (
            f"**{name}**（{code}）\n\n"
            f"现价 **{q['now']:.2f}**　　涨跌 **{q['change_pct']:+.2f}%**\n\n"
            f"**▎量能**\n"
            f"近3分钟　{vol_3min/10000:.0f}万手\n"
            f"30分钟均　{vol_30min_avg/10000:.0f}万手\n"
            f"量比　**{ratio:.1f}倍**\n\n"
            f"**▎价格**\n"
            f"变动　{price_change:+.2f}%\n"
            f"换手率　{q['turnover_rate']:.2f}%"
        ),
    }


def check_vwap_break(q: dict, bars: list, alerts_sent: list, code: str, name: str) -> dict | None:
    """VWAP 分时均线突破检测"""
    if len(bars) < 5:
        return None
    vwap = calc_vwap(bars)
    if vwap <= 0:
        return None
    diff = (q["now"] - vwap) / vwap * 100
    direction = None
    if diff > 0.5 and q["quantity_ratio"] > 1.2:
        direction = "站上分时均线"
        alert_id = "vwap_up"
    elif diff < -0.5 and q["quantity_ratio"] > 1.2:
        direction = "跌破分时均线"
        alert_id = "vwap_dn"
    else:
        return None
    if alert_id in alerts_sent:
        return None
    return {
        "alert_id": alert_id,
        "signal_type": direction,
        "detail": f"现价:{q['now']:.2f} 均线:{vwap:.2f} 偏离:{diff:+.2f}% 量比:{q['quantity_ratio']:.2f}",
        "content": (
            f"**{name}**（{code}）\n\n"
            f"现价 **{q['now']:.2f}**　　涨跌 **{q['change_pct']:+.2f}%**\n\n"
            f"**▎均线**\n"
            f"分时均线　{vwap:.2f}\n"
            f"偏离　**{diff:+.2f}%**\n\n"
            f"**▎量能**\n"
            f"量比　{q['quantity_ratio']:.2f}\n"
            f"换手率　{q['turnover_rate']:.2f}%"
        ),
    }


def check_limit_alert(q: dict, bars: list, alerts_sent: list, code: str, name: str) -> dict | None:
    """逼近涨停/跌停检测"""
    close_yest = q["close_yest"]
    if close_yest <= 0:
        return None
    limit_up = round(close_yest * 1.10, 2)
    limit_dn = round(close_yest * 0.90, 2)
    now = q["now"]
    if now >= limit_up * 0.995 and limit_up - now > 0:
        alert_id = "limit_up"
        direction = "逼近涨停"
    elif now <= limit_dn * 1.005 and now - limit_dn > 0:
        alert_id = "limit_dn"
        direction = "逼近跌停"
    else:
        return None
    if alert_id in alerts_sent:
        return None
    return {
        "alert_id": alert_id,
        "signal_type": direction,
        "detail": f"现价:{now:.2f} 涨停价:{limit_up:.2f} 跌停价:{limit_dn:.2f}",
        "content": (
            f"**{name}**（{code}）\n\n"
            f"现价 **{now:.2f}**　　涨跌 **{q['change_pct']:+.2f}%**\n\n"
            f"**▎价格区间**\n"
            f"涨停价　{limit_up:.2f}\n"
            f"跌停价　{limit_dn:.2f}\n\n"
            f"**▎量能**\n"
            f"换手率　{q['turnover_rate']:.2f}%"
        ),
    }


# ============================================================
#  定时简报
# ============================================================

BRIEF_SLOTS = {"0935", "1030", "1130", "1400", "1500"}
BRIEF_NAMES = {"0935": "开盘定势", "1030": "盘面进展", "1130": "午盘总结", "1400": "下午盘面", "1500": "收盘总结"}


def build_brief(bkey: str, code: str, name: str, q: dict, bars: list, daily_bars: list = None) -> str | None:
    if bkey not in BRIEF_NAMES:
        return None

    ind_block = ""
    if daily_bars and len(daily_bars) >= 20 and bkey in ("1130", "1500"):
        ind_block = "\n\n" + "-" * 20 + "\n\n" + build_indicator_block(daily_bars)

    if bkey == "0935":
        close_yest = q["close_yest"]
        gap = (q["open"] - close_yest) / close_yest * 100 if close_yest else 0
        direction = "高开" if gap > 0.5 else ("低开" if gap < -0.5 else "平开")
        vol_5min = sum(b["volume"] for b in bars[:5]) if len(bars) >= 5 else 0
        return (
            f"**{name}**（{code}）\n\n"
            f"{direction}　{gap:+.2f}%\n\n"
            f"**▎价格**\n"
            f"开盘　{q['open']:.2f}　昨收　{close_yest:.2f}\n"
            f"涨跌幅　{q['change_pct']:+.2f}%\n\n"
            f"**▎量能**\n"
            f"前5分钟　{vol_5min/10000:.0f}万手"
        )
    elif bkey == "1030":
        return (
            f"**{name}**（{code}）\n\n"
            f"现价 **{q['now']:.2f}**　涨跌 **{q['change_pct']:+.2f}%**\n\n"
            f"**▎价格**\n"
            f"最高　{q['high']:.2f}　最低　{q['low']:.2f}\n\n"
            f"**▎量能**\n"
            f"成交额　{q['amount']/1e8:.2f}亿\n"
            f"换手率　{q['turnover_rate']:.2f}%　量比　{q['quantity_ratio']:.2f}"
        )
    elif bkey == "1130":
        trend = "单边上涨" if q["now"] > q["open"] + (q["high"] - q["low"]) * 0.6 else \
                "单边下跌" if q["now"] < q["open"] - (q["high"] - q["low"]) * 0.6 else "横盘震荡"
        return (
            f"**{name}**（{code}）\n\n"
            f"走势　**{trend}**\n"
            f"收盘　**{q['now']:.2f}**　涨跌 **{q['change_pct']:+.2f}%**\n\n"
            f"**▎价格**\n"
            f"开盘　{q['open']:.2f}　最高　{q['high']:.2f}　最低　{q['low']:.2f}\n\n"
            f"**▎量能**\n"
            f"成交额　{q['amount']/1e8:.2f}亿　换手率　{q['turnover_rate']:.2f}%"
            f"{ind_block}"
        )
    elif bkey == "1400":
        return (
            f"**{name}**（{code}）\n\n"
            f"现价 **{q['now']:.2f}**　涨跌 **{q['change_pct']:+.2f}%**\n\n"
            f"**▎价格**\n"
            f"开盘　{q['open']:.2f}　最高　{q['high']:.2f}　最低　{q['low']:.2f}\n\n"
            f"**▎量能**\n"
            f"换手率　{q['turnover_rate']:.2f}%　量比　{q['quantity_ratio']:.2f}"
        )
    elif bkey == "1500":
        trend = "单边上涨" if q["now"] > q["open"] + (q["high"] - q["low"]) * 0.6 else \
                "单边下跌" if q["now"] < q["open"] - (q["high"] - q["low"]) * 0.6 else "横盘震荡"
        volume_desc = "放量" if q["quantity_ratio"] > 1.5 else (
            "缩量" if q["quantity_ratio"] < 0.7 else "量能持平"
        )
        return (
            f"**{name}**（{code}）\n\n"
            f"收盘 **{q['now']:.2f}**　涨跌 **{q['change_pct']:+.2f}%**\n"
            f"走势 **{trend}**　量能 **{volume_desc}**\n\n"
            f"**▎价格**\n"
            f"开盘　{q['open']:.2f}　最高　{q['high']:.2f}　最低　{q['low']:.2f}\n\n"
            f"**▎量能**\n"
            f"振幅　{q['amplitude']:.2f}%\n"
            f"成交额　{q['amount']/1e8:.2f}亿　换手率　{q['turnover_rate']:.2f}%"
            f"{ind_block}"
        )
    return None


# ============================================================
#  状态管理
# ============================================================

def _default_state() -> dict:
    return {
        "date": str(date.today()),
        "briefs_sent": {s: False for s in BRIEF_SLOTS},
        "alerts_sent": [],
        "pushed_weekend": False,
    }


def load_state() -> dict:
    if Path(config.STATE_FILE).exists():
        try:
            return json.loads(Path(config.STATE_FILE).read_text("utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict):
    Path(config.STATE_FILE).write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_stock_state(state: dict, code: str) -> dict:
    today = str(date.today())
    st = state.get(code)
    if st and st.get("date") == today:
        return st
    st = _default_state()
    state[code] = st
    return st


# ============================================================
#  公告缓存
# ============================================================

def load_ann_cache() -> dict:
    if Path(config.ANN_CACHE_FILE).exists():
        try:
            return json.loads(Path(config.ANN_CACHE_FILE).read_text("utf-8"))
        except Exception:
            return {}
    return {}


def save_ann_cache(cache: dict):
    Path(config.ANN_CACHE_FILE).write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )
