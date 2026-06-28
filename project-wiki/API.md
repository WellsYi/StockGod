# API 接口文档

Base URL: `http://localhost:8000/api`

完整 Swagger 文档启动后访问: `http://localhost:8000/docs`

---

## 健康检查

### `GET /api/health`

服务健康检查，返回数据库连接状态、监控存活等信息。

```json
{
  "status": "ok",
  "db": "connected",
  "tasks": {"stock-monitor": "running"},
  "queue": {"queue_size": 0, "consumer_running": true},
  "version": "1.0.0"
}
```

---

## 股票管理

### `GET /api/stocks`
股票池列表。

### `GET /api/stocks/{code}`
单只股票详情（基本信息 + 今日信号 + 今日价格区间）。

### `POST /api/stocks`
添加股票到监控池。添加后自动获取行情+LLM基本面分析+钉钉推送。

```json
// Request
{ "code": "605006" }

// Response
{
  "code": "605006",
  "name": "山东黄金",
  "market": "上证",
  "analysis_pushed": true
}
```

### `DELETE /api/stocks/{code}`
从监控池删除股票。

---

## 信号管理

### `GET /api/signals?date=&code=&type=&page=1&size=20`
信号历史列表，支持按日期/股票代码/信号类型筛选，分页。

### `GET /api/signals/types`
信号类型列表（前端下拉框用）。

```json
["异常放量拉升", "盘中急涨", "盘中急跌", "VWAP突破", "逼近涨停", "连续拉升", "连续砸盘"]
```

### `GET /api/signals/stats`
今日异动聚合——各类型信号数量、各股票触发次数。

### `GET /api/signals/accuracy`
信号准确率统计——按类型汇总命中率。

```json
[
  { "signal_type": "异常放量拉升", "total": 23, "hit": 15, "miss": 5, "pending": 3, "hit_rate": "75.0%" }
]
```

---

## 涨停分析

### `GET /api/limit-up/today`
今日涨停股票列表，含 LLM 原因分析和概念标签。

### `GET /api/limit-up/history?date=&page=1&size=20`
历史涨停记录，按日期筛选。

### `GET /api/limit-up/{code}`
指定股票的历史涨停记录。

### `GET /api/limit-up/stats`
涨停统计——板块分布、概念分布、连板排名。

```json
{
  "date": "2026-06-28",
  "total": 45,
  "by_board": { "主板": 30, "创业板": 10, "科创板": 3, "ST": 2 },
  "by_concept": { "人工智能": 8, "新能源": 6, "芯片": 5 },
  "top_limit_times": [
    { "code": "002910", "name": "庄园牧场", "times": 3 }
  ]
}
```

---

## B站动态

### `GET /api/bili/dynamics?author=&page=1&size=20`
B站动态历史列表，支持按 UP主名称筛选。

### `GET /api/bili/stats`
B站监控统计（今日推送数、UP主列表、最后检查时间）。

---

## 监控控制

### `GET /api/monitor/status`
监控运行状态（股票监控/B站监控/涨停抓取各自的存活状态）。

### `POST /api/monitor/pause`
暂停所有监控。

### `POST /api/monitor/resume`
恢复所有监控。

---

## 钉钉

### `POST /api/dingtalk/callback`
钉钉机器人回调入口，支持命令：
- `add {code}` — 添加股票
- `remove {code}` — 删除股票
- `list` — 查看股票池
- `status` — 查看状态

---

## RAG

### `POST /api/rag/query`
RAG 智能问答。

```json
// Request
{ "query": "山东黄金最近3天的信号汇总" }

// Response
{
  "answer": "山东黄金近3天触发了2次信号...",
  "sources": ["信号记录 x3", "LLM分析 x2"]
}
```

---

## WebSocket

### `WS /ws`
实时推送通道。连接后自动接收以下消息：

```json
// 信号推送
{ "type": "signal", "data": { "code": "605006", "name": "山东黄金", "signal_type": "盘中急涨", "price": 28.50, "time": "..." } }

// 价格推送
{ "type": "price", "data": { "code": "605006", "price": 28.50, "change_pct": 2.35, "time": "..." } }

// B站推送
{ "type": "bili", "data": { "author": "UP主", "content": "...", "link": "...", "time": "..." } }
```

---

## 通用约定

| 项目 | 约定 |
|------|------|
| 分页参数 | `?page=1&size=20` |
| 分页返回 | `{"items": [...], "total": N}` |
| 时间格式 | `YYYY-MM-DD HH:mm:ss` / `YYYY-MM-DD HH:mm:ss.SSS` |
| 错误格式 | `{"detail": "错误信息"}` |
| 认证 | 开发阶段无认证（本地内网使用） |
