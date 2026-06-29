# 开发日志

## [2026-06-30] 端到端链路测试 + WS 实时异动流验证 + 批量测试端点

### 新增
- **`GET /api/test/batch`** — 批量推送 4 条不同信号的模拟数据（贵州茅台异动放量、宁德时代VWAP突破、海康威视连续拉升、隆基绿能逼近涨停），走完整 MySQL + WebSocket 链路
- 前端 `Dashboard.vue` 实时异动流接收测试通过

### 测试验证
- LLM 链路（DeepSeek API）— 涨停分析 ✅ / 信号解读 ✅ / B站摘要 ✅ / 批量分析 ✅
- 信号完整链路（模拟推送 → MySQL 写入 → WS 广播 → 前端实时异动流）✅
- 钉钉推送链路 — B站动态推送 / 股票信号推送 ✅
- B站看板数据确认获取到动态 ✅

### 已知问题
- **实时异动流不回溯历史** — `liveFeed` 是纯内存数组，只存 WS 连接后新消息，切换页面/刷新后不展示之前的数据
- **Windows uvicorn --reload 热重载卡死** — 新增路由不识别，需 taskkill 全杀后冷启动（重复出现）

### 修复
- 端口进程残留清理：多个 uvicorn 实例卡住，需 `taskkill -f -pid` 逐一清理

---

## [2026-06-29~30] LLM 解读持久化修复 + 手动分析 API + 前端完善

### 修复
- **stock_monitor.py LLM 分析结果不入库** — 根因：`batch_analyze_signals` 在所有信号入队之后才调用，且结果无关联方式回写 DB。修复：将信号检测和入队分离为两步，先在 `pending_signals` 暂存，批量 LLM 分析完成后，将解读文本挂到 `SignalEvent.llm_analysis` 再统一入队列。SignalEvent 入队时已携带 LLM 解读 → consumer 写入 DB 时 `llm_analysis` 不再为 NULL。
- **limit_up.py 涨停 LLM 分析后不入库** — 原先 LLM 分析完 `reason_llm` 和 `reason_tags` 只用于钉钉推送，第 240 行 `# TODO` 未实现入库。修复：LLM 分析后遍历 `stocks` 调用 `crud.upsert_limit_up()` 写入 `limit_up_daily` 表。

### 新增
- **`POST /api/signals/{id}/analyze`** — 手动触发单条信号 LLM 解读的后端端点。信号已有解读则直接返回；没有则调用 `llm.analyze_stock_signal()` 生成、写入 DB 并返回。
- **`crud.update_signal_llm(signal_id, llm_analysis)`** — 只更新信号 LLM 解读字段的新 CRUD 函数。
- **`analyzeSignal(id)`** — 前端 API 层新增函数，调用 POST /analyze。
- **Signals.vue** — 详情抽屉 LLM 区域改为始终显示：已有解读展示全文，没有则显示"生成解读"按钮，点击触发手动分析。
- **Dashboard.vue** — 最近信号表格点击行打开详情抽屉（展示基础信息 + 技术参数 + LLM 解读）；LLM 列有内容时紫色显示，悬停 tooltip 查看全文。

### 已知问题
- Windows `uvicorn --reload` 热重载可能不识别新增路由，需要完全 kill 进程后冷启动

---

## [2026-06-29] 项目初始化

- 创建 StockGod 项目骨架
- 设计数据库 6 张表（signals/price_snapshots/llm_logs/signal_accuracy/bili_dynamics/limit_up_daily）
- 完成 FastAPI 入口 + 配置模块 + MySQL 连接池
- 从原 stock 项目移植 core 逻辑（stock_core/dingtalk/llm client）
- 开发涨停抓取模块（limit_up.py），含东方财富接口对接和 LLM 涨停原因分析
- 编写后端 README、项目 README、创建 project-wiki

## [2026-06-28] 异步改造 + 监控系统 + CRUD

- 修复 3 个移植文件的导入路径（`from src` → `from app`）和同步→异步改造（LLM/钉钉/stock_core）
- 数据库建表并初始化 MySQL
- 编写 `app/db/crud.py` — 6 张表全部异步 CRUD，实测通过
- 创建 `app/core/task_manager.py` — 后台任务生命周期管理（自动重启）
- 创建 `app/core/signal_queue.py` — asyncio.Queue 桥接（监控→MySQL+钉钉推送，consumer 模式）
- 创建 `app/core/monitors/stock_monitor.py` — 股票监控主循环（20s 间隔，信号检测→入队）
- 创建 `app/core/monitors/bili_monitor.py` — B站监控主循环（async 版，bilibili-api v17+ 扫码登录）
- 注册后台任务到 main.py lifespan
- 健康检查端点扩展：返回 tasks 状态 + queue 统计
- 添加 `/api/health/tasks` 端点
- `.env` 补充 MYSQL_PASSWORD，修正 config.py BACKEND_DIR 路径

### 已创建文件

| 文件 | 说明 |
|------|------|
| `backend/app/main.py` | FastAPI 入口 + 健康检查 + CORS |
| `backend/app/config.py` | 统一配置（从 .env 加载） |
| `backend/app/db/pool.py` | MySQL 连接池 |
| `backend/app/db/models.py` | 表名常量 |
| `backend/app/db/migrations/001_init.sql` | 6 张表建表脚本 |
| `backend/scripts/init_db.py` | 数据库初始化脚本 |
| `backend/app/db/crud.py` | 6 张表全部异步 CRUD |
| `backend/app/core/task_manager.py` | 后台任务生命周期管理（自动重启） |
| `backend/app/core/signal_queue.py` | asyncio.Queue 桥接（监控→MySQL+钉钉推送） |
| `backend/app/core/monitors/stock_monitor.py` | 股票监控主循环（20s 间隔轮询） |
| `backend/app/core/monitors/bili_monitor.py` | B站监控主循环（async 版，扫码登录） |
| `backend/requirements.txt` | Python 依赖 |
| `backend/.env` | 环境变量（从原项目复制） |
| `README.md` | 项目根目录说明 |
| `project-wiki/*` | 项目维基文档 |

### 待实现（Phase 1）

- [x] 监控主循环改为 async
- [x] 信号写入 MySQL（asyncio.Queue → DB）
- [x] B站监控改为 async
- [x] 后台任务管理器（自动重启 + 生命周期）
- [ ] WebSocket 实时推送
- [ ] API 路由 20+ 个端点
- [ ] 钉钉回调迁移

### 待实现（后续 Phase）

- [ ] Phase 2: Vue 前端
- [ ] Phase 3: 涨停分析（已预写模块）
- [ ] Phase 4: 信号准确率追踪、持仓联动、RAG 增强
