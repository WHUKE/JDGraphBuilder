"""Neo4j 数据库连接管理（含重试 / 超时 / 降级日志）"""

import logging
import os
import time

import certifi
from neo4j import GraphDatabase
from neo4j.exceptions import (
    DatabaseError,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)

from src.config import (
    BATCH_SIZE,
    NEO4J_CONN_TIMEOUT,
    NEO4J_DATABASE,
    NEO4J_MAX_RETRIES,
    NEO4J_PASSWORD,
    NEO4J_RETRY_BACKOFF,
    NEO4J_URI,
    NEO4J_USER,
)

# 让 Python SSL 使用 certifi 的 CA 证书（解决 Windows + Neo4j Aura SSL 验证失败）
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

logger = logging.getLogger(__name__)

# 可重试的异常类型
_RETRYABLE_EXC = (ServiceUnavailable, TransientError, SessionExpired)


class Neo4jClient:
    """Neo4j 连接管理，支持上下文管理器、指数退避重试。"""

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
        database: str = NEO4J_DATABASE,
        max_retries: int = NEO4J_MAX_RETRIES,
        retry_backoff: float = NEO4J_RETRY_BACKOFF,
        connection_timeout: float = NEO4J_CONN_TIMEOUT,
    ):
        self._driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            connection_timeout=connection_timeout,
            max_connection_lifetime=3600,
        )
        self._database = database
        self._max_retries = max(1, int(max_retries))
        self._retry_backoff = max(1.0, float(retry_backoff))
        # 打印 URI 与用户名（不打印密码）
        logger.info("连接 Neo4j: %s (user=%s, database=%s)", uri, user, database)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._driver.close()
        logger.info("Neo4j 连接已关闭")

    def verify_connectivity(self):
        try:
            self._driver.verify_connectivity()
        except Exception as e:
            logger.error("Neo4j 连接验证失败: %s", e)
            raise
        logger.info("Neo4j 连接验证成功")

    # ── 重试辅助 ───────────────────────────────────────

    def _with_retry(self, op_name: str, func, *args, **kwargs):
        """对 func(*args, **kwargs) 执行指数退避重试。

        仅对 _RETRYABLE_EXC 类异常重试；其它异常直接抛出。
        """
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return func(*args, **kwargs)
            except _RETRYABLE_EXC as e:
                last_exc = e
                if attempt >= self._max_retries:
                    logger.error(
                        "%s 第 %d/%d 次失败，放弃重试: %s",
                        op_name, attempt, self._max_retries, e,
                    )
                    raise
                sleep = self._retry_backoff ** (attempt - 1)
                logger.warning(
                    "%s 第 %d/%d 次失败，%.1fs 后重试: %s",
                    op_name, attempt, self._max_retries, sleep, e,
                )
                time.sleep(sleep)
            except DatabaseError:
                # 语义错误（如 Cypher 语法）不重试
                raise
        # 防御性分支（理论不可达）
        if last_exc:
            raise last_exc
        raise RuntimeError(f"{op_name} 重试机制异常：未知状态")

    # ── 查询接口 ───────────────────────────────────────

    def run_query(self, cypher: str, parameters: dict | None = None) -> list[dict]:
        """执行单条 Cypher 查询，返回结果列表。"""
        def _do():
            with self._driver.session(database=self._database) as session:
                result = session.run(cypher, parameters or {})
                return [record.data() for record in result]
        return self._with_retry("run_query", _do)

    def run_write(self, cypher: str, parameters: dict | None = None) -> None:
        """执行单条写入 Cypher。"""
        def _do():
            with self._driver.session(database=self._database) as session:
                session.execute_write(lambda tx: tx.run(cypher, parameters or {}))
        self._with_retry("run_write", _do)

    def run_batch(
        self,
        cypher: str,
        batch_data: list[dict],
        batch_size: int = BATCH_SIZE,
    ) -> int:
        """批量执行参数化 Cypher（使用 UNWIND）。"""
        total = 0
        for i in range(0, len(batch_data), batch_size):
            chunk = batch_data[i : i + batch_size]

            def _do(data=chunk):
                with self._driver.session(database=self._database) as session:
                    session.execute_write(
                        lambda tx: tx.run(cypher, {"batch": data})
                    )

            self._with_retry("run_batch", _do)
            total += len(chunk)
        return total
