# 开发日志

## [2026-06-28] 项目初始化

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
