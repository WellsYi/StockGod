"""
LLM 客户端模块

封装 DeepSeek API 调用，提供统一的 text_summarize / analyze 等方法。
以后如果换模型（通义千问、ChatGPT），只改这里。
"""

from openai import AsyncOpenAI

from app import config


# 全局客户端（懒加载）
_client = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
    return _client


async def chat(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
) -> str:
    """通用的 LLM 对话接口"""
    if not config.LLM_API_KEY:
        return "[LLM 未配置]"

    client = _get_client()
    try:
        resp = await client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [LLM] 调用失败: {e}")
        return "[LLM 调用失败]"


async def summarize_dynamic(text: str) -> str:
    """摘要 B站动态内容"""
    sp = "你是一个财经/科技资讯摘要助手。用1-3句话概括用户给出的内容，突出核心信息。不要评价，不要加开场白。"
    return await chat(sp, text, max_tokens=200, temperature=0.3)


async def analyze_stock_signal(
    name: str,
    code: str,
    price: float,
    change_pct: float,
    signal_type: str,
    detail: str,
) -> str:
    """解读股票信号"""
    sp = (
        "你是一个A股盘面分析助手。根据用户提供的股票信号，给出简短解读（2-3句）。"
        "包含：信号含义、可能原因、关注点。不要说'建议咨询专业人士'之类的废话。"
        "用**加粗**标出关键结论和核心数字（价格、百分比、方向判断），让人一眼看到重点。"
    )
    msg = (
        f"股票：{name}（{code}）\n"
        f"现价：{price}  涨幅：{change_pct:+.2f}%\n"
        f"信号：{signal_type}\n"
        f"详情：{detail}"
    )
    return await chat(sp, msg, max_tokens=512, temperature=0.5)


async def batch_analyze_signals(signals: list[dict]) -> list[str]:
    """批量解读多个股票信号 — 一次 LLM 调用处理所有信号

    Args:
        signals: list of {"name", "code", "price", "change_pct", "signal_type", "detail"}
    Returns:
        每个信号对应的解读文本 list，顺序与输入一致
    """
    if not config.LLM_API_KEY:
        return []

    sp = (
        "你是一个A股盘面分析助手。下面有多个股票信号，请逐一解读。\n"
        "每个信号给出2-3句解读，包含信号含义、可能原因、关注点。\n"
        "用**加粗**标出关键结论和核心数字。\n"
        "每条解读以'信号N：'开头（N为序号1,2,3...），用空行隔开。\n"
        "示例格式：\n"
        "信号1：**XX股票异常放量**解读内容...\n\n"
        "信号2：**XX股票盘中急涨**解读内容...\n"
        "不要在开头和结尾加多余的话。"
    )

    lines = []
    for i, s in enumerate(signals, 1):
        lines.append(
            f"信号{i}：{s['name']}（{s['code']}）\n"
            f"现价：{s['price']}  涨幅：{s['change_pct']:+.2f}%\n"
            f"类型：{s['signal_type']}\n"
            f"详情：{s['detail']}"
        )
    msg = "\n\n".join(lines)

    try:
        result = await chat(sp, msg, max_tokens=1024, temperature=0.5)

        # 策略1：按 --- 分割
        parts = [p.strip() for p in result.split("---") if p.strip()]
        if len(parts) == len(signals):
            return parts

        # 策略2：按 "信号N：" 或 "信号 N：" 分割
        import re
        numbered = re.split(r"信号\s*\d+\s*[：:]", result)
        numbered = [p.strip() for p in numbered if p.strip()]
        if len(numbered) == len(signals):
            return numbered

        # 策略3：LLM 可能把结果合并写了（如只输出一段汇总），每一条都返回同样内容
        return [result] * len(signals)
    except Exception as e:
        print(f"  [LLM] 批量分析失败: {e}")
        return [""] * len(signals)


async def analyze_new_stock(
    name: str, code: str, market_name: str,
    price: float, change_pct: float,
    high: float, low: float,
    volume: float, amount: float, turnover_rate: float,
    quantity_ratio: float, amplitude: float,
    total_mv: float, free_mv: float,
    high_52w: float, low_52w: float,
    open: float, close_yest: float,
    recent_days: list,
) -> str:
    """新股添加时的综合分析——基本盘 + 最近走势"""
    sp = (
        "你是一个A股基本面分析助手。根据用户提供的股票数据，写一份简洁的新股报告（4-6句）。"
        "包含：公司基本面概况（市值规模）、今日盘面表现、近期走势趋势、关注要点。"
        "不要说'建议咨询专业人士'之类的废话。语言简洁直接。"
    )

    # 近期走势描述
    recent_str = ""
    if recent_days:
        closes = [b["close"] for b in recent_days if "close" in b]
        if len(closes) >= 2:
            week_change = (closes[-1] - closes[0]) / closes[0] * 100
            recent_str = f"\n近{len(closes)}天涨跌：{week_change:+.2f}%"

    msg = (
        f"名称：{name}（{code}）\n"
        f"市场：{market_name}\n"
        f"总市值：{total_mv:.1f}亿  流通市值：{free_mv:.1f}亿\n"
        f"现价：{price:.2f}  涨幅：{change_pct:+.2f}%\n"
        f"今开：{open:.2f}  昨收：{close_yest:.2f}\n"
        f"最高：{high:.2f}  最低：{low:.2f}\n"
        f"振幅：{amplitude:.2f}%\n"
        f"成交额：{amount:.2f}亿  换手率：{turnover_rate:.2f}%\n"
        f"量比：{quantity_ratio:.2f}\n"
        f"52周范围：{low_52w:.2f} - {high_52w:.2f}"
        f"{recent_str}"
    )
    return await chat(sp, msg, max_tokens=512, temperature=0.5)
