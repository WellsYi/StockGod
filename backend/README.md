# StockGod Backend

FastAPI 后端服务，提供股票盯盘、B站监控、涨停分析、RAG 问答 API。

## 技术栈

- **框架**: FastAPI (async)
- **数据库**: MySQL (aiomysql)
- **向量库**: ChromaDB
- **LLM**: DeepSeek API
- **实时通信**: WebSocket

## 目录结构

```
backend/
├── app/
│   ├── api/              # API 路由
│   │   ├── stocks.py     # 股票池 CRUD + 单股详情
│   │   ├── signals.py    # 信号查询/统计/准确率
│   │   ├── limit_up.py   # 涨停查询/统计
│   │   ├── bili.py       # B站动态/统计
│   │   ├── monitor.py    # 监控状态/控制
│   │   ├── dingtalk.py   # 钉钉回调
│   │   ├── rag.py        # RAG 问答
│   │   └── ws.py         # WebSocket
│   ├── core/
│   │   ├── monitors/
│   │   │   ├── stock_core.py  # 行情获取/信号检测（纯函数）
│   │   │   ├── stock.py       # 股票监控主循环（async）
│   │   │   ├── bili.py        # B站监控（async）
│   │   │   └── limit_up.py    # 涨停抓取（async）
│   │   ├── notifier/
│   │   │   └── dingtalk.py    # 钉钉签名+推送
│   │   ├── llm/
│   │   │   └── client.py      # DeepSeek API 封装
│   │   └── scheduler.py       # 后台任务管理器
│   ├── db/
│   │   ├── pool.py            # MySQL 连接池
│   │   ├── models.py          # SQL 常量
│   │   └── migrations/
│   │       └── 001_init.sql   # 6张表建表脚本
│   ├── rag/
│   │   ├── vector_store.py    # ChromaDB 封装
│   │   └── pipeline.py        # 检索→增强→生成
│   ├── config.py              # 统一配置（.env）
│   └── main.py                # FastAPI 入口
├── scripts/
│   └── init_db.py             # 初始化数据库
├── .env / .env.example
├── requirements.txt
└── README.md
```

## 数据库表

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| `signals` | 信号记录 | code, type, time, price, llm_analysis |
| `price_snapshots` | 价格快照 | code, time, price, signal_id |
| `llm_logs` | LLM 日志 | scenario, input/output_text, tokens |
| `signal_accuracy` | 信号准确率 | signal_id, price_5/15/30min, verdict |
| `bili_dynamics` | B站动态 | dynamic_id, author, content, summary |
| `limit_up_daily` | 涨停记录 | code, price, limit_times, reason, concepts |

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 MySQL 连接信息、钉钉 Webhook、DeepSeek API Key

python scripts/init_db.py       # 初始化数据库
uvicorn app.main:app --reload   # 启动开发服务器
```

## API 文档

启动后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要端点

| 端点 | 功能 |
|------|------|
| `GET /api/health` | 健康检查 |
| `GET/POST/DELETE /api/stocks[/{code}]` | 股票池管理 |
| `GET /api/signals[?date&code&type&page]` | 信号历史 |
| `GET /api/signals/types` | 信号类型列表 |
| `GET /api/signals/stats` | 今日异动聚合 |
| `GET /api/signals/accuracy` | 信号准确率统计 |
| `GET /api/limit-up/today` | 今日涨停列表 |
| `GET /api/limit-up/history[?date]` | 历史涨停 |
| `GET /api/limit-up/{code}` | 单股涨停记录 |
| `GET /api/limit-up/stats` | 涨停统计 |
| `GET /api/bili/dynamics[?author&page]` | B站动态历史 |
| `GET /api/bili/stats` | B站监控统计 |
| `GET /api/monitor/status` | 监控状态 |
| `POST /api/monitor/pause` | 暂停监控 |
| `POST /api/monitor/resume` | 恢复监控 |
| `POST /api/dingtalk/callback` | 钉钉回调 |
| `POST /api/rag/query` | RAG 问答 |
| `WS /ws` | WebSocket 实时推送 |

## 环境变量 (.env)

```ini
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=stock_god

# 钉钉
DINGTALK_STOCK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_STOCK_SECRET=SECxxx
DINGTALK_BILI_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_BILI_SECRET=SECxxx

# DeepSeek
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-flash

# 监控参数
BILI_UID=xxx
BILI_CHECK_INTERVAL=300
STOCK_BURST_RATIO=3.0
STOCK_CHECK_INTERVAL=20
```
