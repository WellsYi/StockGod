# 环境搭建

## 前提条件

- Python 3.9+
- MySQL 8.0+
- Node.js 18+（前端开发时需要）

## 后端搭建

```bash
# 1. 克隆项目
cd StockGod/backend

# 2. 创建虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/Mac
# source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
```

编辑 `.env`，填入以下配置：

```ini
# MySQL 连接信息
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=stock_god

# 钉钉机器人 Webhook（没有可不填）
DINGTALK_STOCK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_STOCK_SECRET=SECxxx
DINGTALK_BILI_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_BILI_SECRET=SECxxx

# DeepSeek API Key（没有可不填）
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-flash

# B站监控 UID
BILI_UID=xxx
BILI_CHECK_INTERVAL=300

# 股票监控参数
STOCK_BURST_RATIO=3.0
STOCK_CHECK_INTERVAL=20
```

```bash
# 5. 初始化数据库
python scripts/init_db.py

# 6. 启动开发服务器
uvicorn app.main:app --reload
```

服务启动在 `http://localhost:8000`。

API 文档: `http://localhost:8000/docs`

## 前端搭建

```bash
cd StockGod/frontend
npm install
npm run dev
```

前端默认启动在 `http://localhost:5173`。

## Docker 部署（TODO）

```dockerfile
# 后续补充
```

## 环境变量参考

| 变量 | 必填 | 说明 |
|------|------|------|
| MYSQL_HOST | ✅ | MySQL 地址 |
| MYSQL_PORT | ✅ | MySQL 端口 |
| MYSQL_USER | ✅ | MySQL 用户 |
| MYSQL_PASSWORD | ✅ | MySQL 密码 |
| MYSQL_DB | ✅ | 数据库名（默认 stock_god） |
| LLM_API_KEY | ❌ | DeepSeek API Key |
| LLM_BASE_URL | ❌ | API 地址 |
| LLM_MODEL | ❌ | 模型名 |
| DINGTALK_STOCK_WEBHOOK | ❌ | 钉钉股票机器人 |
| DINGTALK_STOCK_SECRET | ❌ | 钉钉签名密钥 |
| BILI_UID | ❌ | B站监控 UID |
| STOCK_BURST_RATIO | ❌ | 放量异动阈值 |
