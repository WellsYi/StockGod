# StockGod 项目记忆

> ⚡ **唤醒指令：当阿杰说"小茗"并涉及 StockGod 项目时，先读取本文件恢复项目上下文。**
>
> 记录项目的"状态"——当前进展、活跃决策、待办事项、重要约定。
> 每次开始工作前读这个，能快速恢复上下文。

---

## 📋 当前快照（2026-06-29）

### 🎯 项目定位
下一代股票盯盘 + B站监控 + 涨停分析系统。
**不是**东方财富/同花顺的替代品——不做K线图，只做**复盘和统计**。

### 🏗 当前阶段
**Phase 1 后端底座 ✅ + Phase 2 前端进行中（Vue 3 框架已搭建）**

已就绪：
- 项目骨架、目录结构 ✅
- 数据库 6 张表建表 SQL ✅
- FastAPI 入口 + 配置 + MySQL 连接池 ✅
- core 逻辑从原项目移植并改为 async ✅
- 涨停抓取模块预写 ✅
- 6 张表全部异步 CRUD ✅
- 后台任务管理器（自动重启） ✅
- 信号队列桥接（asyncio.Queue → MySQL + 钉钉推送 + WebSocket 广播） ✅
- 股票监控主循环（轮询+信号检测+入队） ✅
- B站监控主循环（async 版，扫码登录） ✅
- 应用生命周期整合（lifespan 启动/关闭） ✅
- WebSocket 实时推送（ConnectionManager + /ws 端点） ✅
- API 路由（signals、accuracy、bili、limit-up、monitor、dingtalk）共 20 条路由 ✅
- 钉钉回调迁移（POST /api/dingtalk/callback，兼容旧 add/remove/list/status） ✅
- project-wiki 8 篇文档 ✅
- **Vue 3 前端框架搭建完成（脚手架 + 6 个页面 + 路由 + API 层 + WS composable）** ✅

待实现（后续）：
- [ ] 前端对接 - 阿杰自己动手学前后端对接（从调 /api/health 开始）
- [ ] RAG 问答界面（占位）
- [ ] Phase 3: 涨停分析完整联调
- [ ] Phase 4: 深化

### 🔑 活跃决策
| ADR | 结论 | 说明 |
|-----|------|------|
| 数据库 | MySQL | 阿杰熟，有扩展空间 |
| ORM | 不用，直接 SQL | 表少查询简单，SQL 更可控 |
| 与原项目关系 | 新建 StockGod，原 `stock` 不动 | 线上服务不能断 |
| 向量库 | ChromaDB | 数据量小，零配置 |
| 前端定位 | 不做K线图，只做复盘 | 看盘用东方财富 |
| RAG | DeepSeek embedding 走 API | 不占本地资源 |
| Embedding | DeepSeek text-embedding-v2 | 已有 Key，省事 |
| 监控架构 | asyncio.Queue + consumer | 解耦监控与写入，防积压 |
| 前端 UI | Ant Design Vue 4 | 暗色主题，全局注册 a- 前缀组件 |

### 📐 活跃约定
- **新旧共存**：原项目 `F:\projects\stock\` 不变，StockGod 在 `F:\projects\StockGod\`
- **钉钉推送保持**：无论后端怎么改，钉钉推送不能断
- **JSON 文件不动**：现有缓存/凭据继续用，不迁移
- **数据库只存历史**：状态类数据（当天简报发了没）继续用 JSON
- **先有后端再有前端**：Phase 1 后端全跑通才开 Phase 2
- **文档与代码同步**：改代码同步更新 project-wiki
- **Git Bash**：所有 python/npm 命令在 Git Bash 执行，CMD/PowerShell 会走错 Python 版本

### ❓ 待确认问题
- B站监控需要首次扫码登录（已封装，运行一次即可）
- MySQL 装在哪？（本地开发机还是 ECS？如果 ECS 内存不够装 MySQL 怎么办？）
- Phase 1 新旧共存策略：新建 backend/ 还是直接改？（倾向新建）

### 📝 上次工作记录
**2026-06-28：**
- 修复 3 个移植文件的导入路径（`from src` → `from app`）和同步→异步改造
- 创建 6 张表并连接 MySQL
- 编写 `app/db/crud.py` — 6 张表全部异步 CRUD，实测通过
- 创建 `app/core/task_manager.py` — 后台任务生命周期管理（自动重启）
- 创建 `app/core/signal_queue.py` — asyncio.Queue 桥接（监控→MySQL+钉钉推送）
- 创建 `app/core/monitors/stock_monitor.py` — 股票监控主循环（20s 间隔）
- 创建 `app/core/monitors/bili_monitor.py` — B站监控主循环（扫码登录+轮询）
- 注册后台任务到主应用 lifespan，全部 4 个端点通过测试

**2026-06-28（第2轮）：**
- 创建 `app/core/ws_manager.py` — WebSocket 连接管理器（ConnectionManager），线程安全广播
- 创建 `app/api/ws.py` — WebSocket 端点 `GET /ws`，支持 ping/pong 保活
- 修改 `signal_queue.py` — `_handle_signal` 和 `_handle_bili` 处理完后广播到 WebSocket
- 修改 `main.py` — 注册 ws 路由，健康检查增加 `ws_connections` 字段
- signal_queue 的 WebSocket 广播自动清理断开的连接

**2026-06-28（第3轮）：**
- 创建 `app/api/signals.py` — 信号列表 GET /api/signals、查详情 GET /api/signals/{id}、今日统计 GET /api/signals/today、准确率列表 GET /api/accuracy、准确率更新 PATCH /api/accuracy/{id}
- 创建 `app/api/bili.py` — B站动态列表 GET /api/bili、详情 GET /api/bili/{dynamic_id}
- 重写 `app/api/limit_up.py` — 涨停列表 GET /api/limit-up
- 创建 `app/api/monitor.py` — 监控状态 GET /api/monitor、启停 POST /api/monitor/{name}/start|stop
- 修改 `main.py` — 注册全部 5 个 routers，共 19 条路由（含内置 /docs、/health 等），导入验证通过

**2026-06-28（第4轮）：**
- 创建 `app/api/dingtalk.py` — 钉钉回调端点 `POST /api/dingtalk/callback`
  - 兼容旧项目所有指令：add/remove/list/status
  - 群聊 @机器人 校验，静默忽略非 @ 消息
  - add 命令自动触发盘面速览推送 + LLM 基本面分析
  - 使用 `dingtalk.send_raw()` 文本回复到钉钉群
- 修改 `main.py` — 注册 dingtalk 路由
- **Phase 1 底座基本完成**，共 20 条路由

**2026-06-29：**
- **后端重启验证** — 旧进程残留占用 8000 端口，`taskkill` 清理后重新启动
- 启动后验证：/api/health ✅、/api/signals/today ✅、/api/monitor ✅
- stock-monitor 自动运行中，bili-monitor 未注册（待修复）
- **修复 B站多 UID 监控**：config.py 将 `BILI_UID` 拆分为 `BILI_UIDS` 列表，`.env` 配置两个 UID（`3706959876327428,2081301693`），bili_monitor.py 遍历所有 UID 拉取动态
- 注册 bili-monitor 到 TaskManager（之前遗漏，main.py lifespan 只注册了 stock-monitor）
- 修复 bili_monitor.py 两处缩进错误（if 内缩进错位 + summary 变量作用域越界），导致启动崩溃和运行时 UnboundLocalError
- B站 BILI_CHECK_INTERVAL 从 10s 调整为 60s（防 B站 API 限流，原 10s 过于频繁易触发 IP 级封禁）
- **Dashboard 异动看板全面重构**：4 个 KPI 指标卡 + 实时异动流（WS 推送，max-height 250px 固定高度，新条目闪烁动画）+ 信号类型分布柱状图 + 最近信号表格 + 后台任务快捷启停
- 修复 `@ant-design/icons-vue` v7 白屏：`context.attrs` 在 Vue 3.5+ 中丢失，用 `h()` 包裹图标 VNode
- 修复 WebSocket 断开不自动重连：`ws.onclose` 加 `setTimeout(connectWs, 3000)`，后端 reload 后前端自动恢复
- 实时异动流过滤 B站空数据：`meaningfulFeed` computed，只展示有实际数据的 B站动态
- B站扫码登录成功（首次需在 Git Bash 终端执行 `python -c "..."` 扫码，凭据保存到 `data/bili_credential.json`）
- **⚠️ 坑：所有 python/npm 命令必须在 Git Bash 中执行，CMD/PowerShell 会走不同 Python 版本导致 ModuleNotFoundError**
- **股票池迁移 JSON → MySQL**：新建 `stock_pool` 表，`stock_core.load_stocks/save_stocks` 改为 async DB 操作，所有调用方加 `await`（stocks API、dingtalk、stock_monitor 共 5 个文件）
- 新建 `GET /api/stocks`、`POST /api/stocks`、`DELETE /api/stocks/{code}` 三个 REST 端点
- 新建 `StockManager.vue` 前端页面（表格展示 + 添加输入框 + 删除确认弹窗），侧栏新增"股票池"菜单项
- 修复 `check_vwap_break` 参数顺序错乱（签名 `(bars, q, ...)` vs 调用 `(q, bars, ...)`）
- 修复 `check_limit_alert` 参数缺少 `bars`（签名 4 参，调用传 5 参）
- 新增 `GET /api/test/signal` 测试端点，手动触发 WebSocket 广播验证前端实时流
- 模拟数据推送验证：MySQL 写入 ✅、API 查询 ✅、WebSocket 广播 ✅

---
## Phase 2 前端

**2026-06-28：**
- **Phase 2 前端启动 — Vue 3 + Vite 框架搭建完成**
- 前端文件结构：`package.json` / `vite.config.js` / `index.html` / `src/main.js`
- 布局系统：`App.vue`（左侧导航 + 顶栏 WS 状态）+ `style.css`（暗色全局样式）
- 路由 6 个页面：Dashboard / Signals / LimitUp / BiliDynamics / MonitorStatus / RAGChat
- API 层 `api/index.js`：封装 axios，覆盖所有后端端点
- WebSocket composable `composables/useWebSocket.js`
- 6 个页面全部实现：
  - **Dashboard**：统计卡片 + 最近信号表 + 任务状态 + B站动态 + 实时 WS 推送日志
  - **Signals**：信号历史表格 + stock_code/signal_type 筛选
  - **LimitUp**：涨停板表格 + trade_date 筛选 + 连板/封单/概念展示
  - **BiliDynamics**：卡片网格布局 + 作者筛选 + LLM 摘要
  - **MonitorStatus**：任务启停控制按钮
  - **RAGChat**：占位页面
- Vite 代理 `/api` → `:8000`，`/ws` → `ws://:8000`
- 构建验证：`npm install` + `vite build` ✅，代理健康检查 ✅

**2026-06-29（第3轮）：**
- **股票池管理前后端**：新建 `stocks.py` REST 路由（3 端点）+ `StockManager.vue` 页面（表格 + 添加/删除）
- **股票池 JSON → MySQL 迁移**：新增 `stock_pool` 表、CRUD 函数，`stock_core.load_stocks/save_stocks` 改为 async DB 操作，所有调用方加 `await`
- 修复 `check_vwap_break` 参数顺序 + `check_limit_alert` 参数缺失
- 新增 `GET /api/test/signal` 测试端点走完整链路（MySQL + 钉钉 + WebSocket），验证通过
- 模拟数据推送验证：MySQL 写入 ✅、API 查询 ✅、WebSocket 广播 ✅、钉钉推送 ✅
- 项目准备上传 GitHub（`git init` + `.gitignore` 已就绪）

> 阿杰说"记录一下爱" — 叫我"小茗"，协作愉快，一起把 StockGod 做好。

## GitHub 仓库操作记录

### 创建步骤
1. 本地 `git init` 初始化仓库
2. `git add .` 暂存所有文件（`.gitignore` 已过滤 `node_modules/`、`.env`、`__pycache__/`、`data/*` 等）
3. `git commit -m "init: StockGod 项目初始化"`
4. GitHub 新建仓库 `StockGod`（不勾选 README/LICENSE/.gitignore）
5. `git remote add origin https://github.com/<用户名>/StockGod.git`
6. `git branch -M main && git push -u origin main`

### 后续推送
```bash
git add .
git commit -m "描述修改内容"
git push
```
密码用 Personal Access Token（GitHub → Settings → Developer settings → Personal access tokens）。

> 详细步骤见 README.md 末尾的「GitHub 仓库创建与代码上传」章节。

**2026-06-28（第2轮）：**
- **UI 框架迁移：手写 CSS → Ant Design Vue 4**
- 安装 `ant-design-vue` + `@ant-design/icons-vue`，全局注册
- 重构 `main.js`：引入 Ant Design 全局注册 + reset.css
- 重构 `App.vue`：`a-layout` / `a-layout-sider` / `a-menu` 暗色侧栏 + `a-badge` WS 状态
- 所有 6 个页面改为 Ant Design 模板标签（`a-card` / `a-table` / `a-statistic` / `a-tag` / `a-list` / `a-row` / `a-col` / `a-date-picker` 等）
- 修复关键问题：Ant Design 全局注册后组件必须用 `a-` 前缀（大写驼峰名在 `<template>` 中不生效）
- 构建验证：`vite build` ✅

---

## ⏳ 长期待办

### Phase 2 前端（~4天）
- [x] Vue 3 + Vite 初始化
- [x] UI 框架切换为 Ant Design Vue 4 暗色主题
- [x] 异动看板 Dashboard（实时异动流 + 信号类型分布 + KPI 卡片 + 任务控制）
- [x] 股票池管理（增删 + MySQL + 前端界面）
- [x] B站动态 + 监控状态（已完成）
- [ ] 信号历史 + 涨停分析详情
- [ ] RAG 问答界面（占位）

### Phase 3 涨停分析（~3天，模块已预写）
- [x] API 路由 + 钉钉推送联调
- [ ] 前端涨停页面（列表已完成）

### Phase 4 深化
- [ ] 信号准确率自动追踪
- [ ] 持仓记录 + 信号联动
- [ ] 钉钉 RAG 增强
- [ ] Docker 部署

---

> 记忆文档在每次工作结束后更新。
> 跟代码 wiki 不同，这里记的是"项目在想什么"而不是"项目长什么样"。
