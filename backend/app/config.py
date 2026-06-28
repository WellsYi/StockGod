"""
StockGod 统一配置

从 .env 加载所有配置，各模块从这里读取。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

# 加载 .env
load_dotenv(BACKEND_DIR / ".env")


# ============================================================
#  MySQL
# ============================================================
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "stock_god")

# ============================================================
#  钉钉
# ============================================================
DINGTALK_STOCK_WEBHOOK = os.getenv("DINGTALK_STOCK_WEBHOOK", "")
DINGTALK_STOCK_SECRET = os.getenv("DINGTALK_STOCK_SECRET", "")
DINGTALK_BILI_WEBHOOK = os.getenv("DINGTALK_BILI_WEBHOOK", "")
DINGTALK_BILI_SECRET = os.getenv("DINGTALK_BILI_SECRET", "")

# ============================================================
#  LLM 配置
# ============================================================
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# ============================================================
#  B站监控
# ============================================================
BILI_UID = os.getenv("BILI_UID", "")
BILI_UIDS = [uid.strip() for uid in BILI_UID.split(",") if uid.strip()]
BILI_CHECK_INTERVAL = int(os.getenv("BILI_CHECK_INTERVAL", "300"))

# ============================================================
#  股票监控
# ============================================================
STOCK_BURST_RATIO = float(os.getenv("STOCK_BURST_RATIO", "3.0"))
STOCK_CHECK_INTERVAL = int(os.getenv("STOCK_CHECK_INTERVAL", "20"))

# ============================================================
#  路径
# ============================================================
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
CRED_FILE = str(DATA_DIR / "bili_credential.json")
STOCKS_FILE = str(DATA_DIR / "stocks.json")
STATE_FILE = str(DATA_DIR / "stock_state.json")
ANN_CACHE_FILE = str(DATA_DIR / "stock_announcements.json")
BILI_CACHE_FILE = str(DATA_DIR / "bili_sent_ids.json")
