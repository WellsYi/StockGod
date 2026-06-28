# StockGod

> 股神 — 下一代股票盯盘 + B站监控 + 涨停分析系统
> 前后端分离，FastAPI + MySQL + RAG + Vue 3

## 核心功能

| 模块 | 功能 |
|------|------|
| 股票盯盘 | 多股实时监控、5种信号检测（放量异动/VWAP突破/急涨急跌/逼近涨跌停/连续走势） |
| 定时简报 | 开盘定势/盘面进展/午盘总结/下午盘面/收盘总结 |
| B站监控 | UP主动态轮询、LLM 摘要、钉钉推送 |
| 涨停分析 | 每日全市场涨停抓取、概念板块识别、LLM 涨停原因分析、连板追踪 |
| 信号准确率 | 自动追踪每类信号命中率（触发后5min/30min/收盘涨跌） |
| RAG 问答 | 基于历史分析的智能问答（信号记录/涨停原因/LLM分析全文检索） |
| 钉钉集成 | 实时推送 + 回调命令（增删查股票） |
| 实时看板 | WebSocket 推送信号/价格/B站动态 |
| 历史记录 | 信号/价格快照/LLM调用/涨停/B站动态 全部存 MySQL |

## 项目结构

```
StockGod/
├── backend/                      # FastAPI 后端
│   ├── app/
│   │   ├── api/                  # API 路由层
│   │   │   ├── stocks.py         # 股票池 CRUD + 单股详情
│   │   │   ├── signals.py        # 信号查询/统计/准确率
│   │   │   ├── limit_up.py       # 涨停查询/统计
│   │   │   ├── bili.py           # B站动态/统计
│   │   │   ├── monitor.py        # 监控状态/控制
│   │   │   ├── dingtalk.py       # 钉钉回调
│   │   │   ├── rag.py            # RAG 问答
│   │   │   └── ws.py             # WebSocket
│   │   ├── core/                 # 核心业务层
│   │   │   ├── monitors/
│   │   │   │   ├── stock_core.py # 行情/信号检测（纯函数）
│   │   │   │   ├── stock.py      # 股票监控主循环（async）
│   │   │   │   ├── bili.py       # B站监控（async）
│   │   │   │   └── limit_up.py   # 涨停抓取（async）
│   │   │   ├── notifier/
│   │   │   │   └── dingtalk.py   # 钉钉推送
│   │   │   ├── llm/
│   │   │   │   └── client.py     # LLM 客户端（DeepSeek）
│   │   │   └── scheduler.py      # 后台任务管理器
│   │   ├── db/
│   │   │   ├── pool.py           # MySQL 连接池
│   │   │   ├── models.py         # SQL 常量/表名
│   │   │   └── migrations/
│   │   │       └── 001_init.sql  # 6张表建表脚本
│   │   ├── rag/
│   │   │   ├── vector_store.py   # ChromaDB 封装
│   │   │   └── pipeline.py       # 检索→增强→生成
│   │   ├── config.py             # 统一配置
│   │   └── main.py               # FastAPI 入口
│   ├── scripts/
│   │   └── init_db.py            # 数据库初始化脚本
│   ├── .env
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
├── frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── Dashboard.vue     # 异动看板（首页）
│   │   │   ├── StockDetail.vue   # 单只股票详情
│   │   │   ├── Signals.vue       # 信号历史
│   │   │   ├── LimitUp.vue       # 涨停分析
│   │   │   ├── BiliDynamics.vue  # B站动态
│   │   │   ├── MonitorStatus.vue # 监控状态
│   │   │   └── RAGChat.vue       # RAG 问答
│   │   ├── components/
│   │   ├── api/
│   │   ├── router/
│   │   └── stores/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── data/                         # JSON 缓存（不动）
├── logs/
└── .gitignore
```

## 数据库（6张表）

| 表 | 用途 |
|----|------|
| `signals` | 股票信号记录（含 LLM 分析） |
| `price_snapshots` | 价格快照（信号准确率追踪） |
| `llm_logs` | LLM 调用日志（算账 + RAG 数据源） |
| `signal_accuracy` | 信号准确率（命中/骗线标签） |
| `bili_dynamics` | B站动态记录 |
| `limit_up_daily` | 每日涨停记录（含 LLM 原因分析/概念标签/连板） |

## API 概览（20+ 端点）

| 分组 | 端点 | 功能 |
|------|------|------|
| 健康检查 | `GET /api/health` | 服务状态 |
| 股票管理 | `GET/POST /api/stocks`、`GET/DELETE /api/stocks/{code}` | 增删查 |
| 信号 | `GET /api/signals`、`/types`、`/stats`、`/accuracy` | 查询统计 |
| 涨停 | `GET /api/limit-up/today`、`/history`、`/{code}`、`/stats` | 涨停分析 |
| B站 | `GET /api/bili/dynamics`、`/stats` | 动态查询 |
| 监控 | `GET /api/monitor/status`、`POST /pause\|/resume` | 控制 |
| 钉钉 | `POST /api/dingtalk/callback` | 回调入口 |
| RAG | `POST /api/rag/query` | 智能问答 |
| WebSocket | `WS /ws` | 实时推送 |

## 快速开始

> **⚠️ 重要：所有命令必须在 Git Bash 终端执行！** CMD/PowerShell 会走不同 Python 版本导致 `ModuleNotFoundError`。

```bash
# 后端
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 MySQL/钉钉/LLM 配置
# B站首次使用需扫码登录（Git Bash 中执行）：
python -c "from app.core.monitors.bili_monitor import _login; import asyncio; asyncio.run(_login())"
# 凭据保存到 data/bili_credential.json，以后无需再扫码
python scripts/init_db.py
uvicorn app.main:app --reload

# 前端（另一终端）
cd frontend
npm install
npm run dev
```

### 测试推送

验证后端到前端的实时推送链路是否正常：

```bash
curl http://127.0.0.1:8000/api/test/signal
```

前端 Dashboard 的实时异动流会收到一条测试信号。

### 常见启动问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: No module named 'bilibili_api'` | 用了 CMD/PowerShell 而非 Git Bash | 切换到 Git Bash 重试 |
| `[WinError 10013]` 端口被占用 | 上次进程未完全退出 | `taskkill /F /IM python.exe` 再启动 |
| B站监控报 `cannot access local variable 'summary'` | 变量作用域缩进问题 | 重启后端即可（已修复） |

## 开发计划

- **Phase 1**（~6.5天）：后端底座 — FastAPI + MySQL + 信号/B站入库 + WebSocket + API
- **Phase 2**（~4天）：前端看板 — 异动看板 + 股票管理 + 信号历史 + RAG
- **Phase 3**（~3天）：涨停分析 — 抓取 + LLM 分析 + API + 前端
- **Phase 4**（按需）：信号准确率追踪 + 持仓联动 + 钉钉 RAG 增强

## 原项目

原 `stock` 项目（`F:\projects\stock\`）保持不变，StockGod 从零开始重构。
