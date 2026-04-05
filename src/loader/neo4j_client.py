"""Neo4j 数据库连接管理"""

import logging

from neo4j import GraphDatabase

from src.config import BATCH_SIZE, NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j 连接管理，支持上下文管理器。"""

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
        database: str = NEO4J_DATABASE,
    ):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        logger.info("连接 Neo4j: %s (database=%s)", uri, database)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._driver.close()
        logger.info("Neo4j 连接已关闭")

    def verify_connectivity(self):
        self._driver.verify_connectivity()
        logger.info("Neo4j 连接验证成功")

    def run_query(self, cypher: str, parameters: dict | None = None) -> list[dict]:
        """执行单条 Cypher 查询，返回结果列表。"""
        with self._driver.session(database=self._database) as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]

    def run_write(self, cypher: str, parameters: dict | None = None) -> None:
        """执行单条写入 Cypher。"""
        with self._driver.session(database=self._database) as session:
            session.execute_write(lambda tx: tx.run(cypher, parameters or {}))

    def run_batch(
        self,
        cypher: str,
        batch_data: list[dict],
        batch_size: int = BATCH_SIZE,
    ) -> int:
        """批量执行参数化 Cypher（使用 UNWIND）。

        Args:
            cypher: 包含 `UNWIND $batch AS item` 的 Cypher 语句
            batch_data: 参数数据列表
            batch_size: 每批大小

        Returns:
            处理的总记录数
        """
        total = 0
        for i in range(0, len(batch_data), batch_size):
            chunk = batch_data[i : i + batch_size]
            with self._driver.session(database=self._database) as session:
                session.execute_write(
                    lambda tx, data=chunk: tx.run(cypher, {"batch": data})
                )
            total += len(chunk)
        return total
