# StockGod 项目维基

> 股神 — 下一代股票盯盘 + B站监控 + 涨停分析系统

🧠 **唤醒机制：当阿杰说"小茗"并涉及此项目时，先读 [[MEMORY|项目记忆]] 恢复上下文。**

## 📋 快速导航

| 文档 | 说明 |
|------|------|
| [[project-wiki/ARCHITECTURE|系统架构]] | 整体架构、数据流、技术栈 |
| [[project-wiki/DATABASE|数据库设计]] | 6张表的详细设计、ER关系、索引说明 |
| [[project-wiki/API|API 接口文档]] | 所有端点、请求响应示例 |
| [[project-wiki/CHANGELOG|开发日志]] | 按时间记录开发进度和决策 |
| [[project-wiki/DECISIONS|设计决策]] | 关键选型考量（ADR） |
| [[project-wiki/ROADMAP|开发路线图]] | Phase 1-4 计划与进度 |
| [[project-wiki/SETUP|环境搭建]] | 从零开始的部署步骤 |

## 🏗 项目概览

```
StockGod/
├── backend/          # FastAPI 后端 (Python)
├── frontend/         # Vue 3 前端
├── data/             # JSON 缓存
├── logs/             # 日志
└── project-wiki/     # ← 你在这里
```

## 🚀 快速启动

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # 编辑配置
python scripts/init_db.py
uvicorn app.main:app --reload
```

## 📊 当前状态

| 模块 | 状态 |
|------|------|
| 后端骨架 | ✅ 已完成 |
| 数据库建表脚本 | ✅ 已完成 |
| 涨停抓取模块 | ✅ 已完成（含 LLM 分析） |
| 核心监控逻辑 | ✅ 已改造为 async |
| DB CRUD | ✅ 已完成（6 张表） |
| 后台任务管理器 | ✅ 已完成（自动重启） |
| 信号队列桥接 | ✅ 已完成（Queue→MySQL+钉钉+WS） |
| 股票监控循环 | ✅ 已完成（20s 轮询） |
| B站监控循环 | ✅ 已完成（async 扫码登录，多UID） |
| API 路由 | ✅ 已完成（20+ 端点） |
| WebSocket | ✅ 已完成（ConnectionManager+广播） |
| 钉钉回调迁移 | ✅ 已完成（兼容旧命令） |
| 前端框架 | ✅ 已完成（Vue3+Ant Design+6页面） |
| 前端对接 | 📝 阿杰自己动手学 |
| RAG | 📝 Phase 3 待启动 |
| 信号准确率 | 📝 Phase 4 待启动 |

---

> 此 wiki 位于项目内部，与代码一同版本控制。
> 保持文档与代码同步。
