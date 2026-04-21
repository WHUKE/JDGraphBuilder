"""全局配置：路径常量、Neo4j 连接参数"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ── 路径 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
CLEANED_DIR = DATA_DIR / "cleaned"
MAPPINGS_DIR = DATA_DIR / "mappings"

# ── 加载 .env ─────────────────────────────────────────
load_dotenv(PROJECT_ROOT / ".env")

# ── Neo4j ─────────────────────────────────────────────
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Neo4j 可靠性配置（P0.3）
NEO4J_MAX_RETRIES = int(os.getenv("NEO4J_MAX_RETRIES", "3"))
NEO4J_RETRY_BACKOFF = float(os.getenv("NEO4J_RETRY_BACKOFF", "1.5"))
NEO4J_CONN_TIMEOUT = float(os.getenv("NEO4J_CONN_TIMEOUT", "30"))

# ── 数据校验常量 ──────────────────────────────────────
VALID_EDUCATION = ["博士", "硕士", "本科", "大专", "不限"]
VALID_PROFICIENCY = ["了解", "熟悉", "熟练", "精通", "不限"]

# ── 批量导入 ──────────────────────────────────────────
BATCH_SIZE = 500

# ── 查询缓存 ──────────────────────────────────────────
QUERY_CACHE_TTL = float(os.getenv("QUERY_CACHE_TTL", "300"))  # 秒
