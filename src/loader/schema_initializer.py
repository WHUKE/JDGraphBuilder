"""Schema 初始化：创建约束、索引，支持重置数据库"""

import logging

from src.loader.neo4j_client import Neo4jClient
from src.modeler.schema import CONSTRAINTS, INDEXES

logger = logging.getLogger(__name__)


def init_schema(client: Neo4jClient) -> None:
    """创建所有约束和索引（幂等：使用 IF NOT EXISTS）。"""
    logger.info("初始化 Schema: %d 个约束, %d 个索引", len(CONSTRAINTS), len(INDEXES))

    for cypher in CONSTRAINTS:
        client.run_write(cypher)
        logger.debug("  约束: %s", cypher[:60])

    for cypher in INDEXES:
        client.run_write(cypher)
        logger.debug("  索引: %s", cypher[:60])

    logger.info("Schema 初始化完成")


def reset_database(client: Neo4jClient) -> None:
    """清空数据库中所有节点和关系。"""
    logger.warning("正在清空数据库...")

    # 分批删除，避免大事务导致内存溢出
    while True:
        result = client.run_query(
            "MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(*) AS deleted"
        )
        deleted = result[0]["deleted"] if result else 0
        if deleted == 0:
            break
        logger.info("  已删除 %d 个节点", deleted)

    # 删除约束和索引
    for constraint in client.run_query("SHOW CONSTRAINTS"):
        name = constraint.get("name")
        if name:
            client.run_write(f"DROP CONSTRAINT {name} IF EXISTS")

    for index in client.run_query("SHOW INDEXES"):
        name = index.get("name")
        idx_type = index.get("type", "")
        # 跳过内置的 lookup 索引
        if name and idx_type != "LOOKUP":
            client.run_write(f"DROP INDEX {name} IF EXISTS")

    logger.info("数据库已清空")
