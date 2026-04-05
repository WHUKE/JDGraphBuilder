"""入库模块测试（使用 Mock Neo4j）"""

from unittest.mock import MagicMock, patch

import pytest

from src.loader.neo4j_client import Neo4jClient
from src.loader.schema_initializer import init_schema


class TestNeo4jClient:
    @patch("src.loader.neo4j_client.GraphDatabase")
    def test_context_manager(self, mock_gdb):
        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver

        with Neo4jClient("bolt://test:7687", "neo4j", "pass") as client:
            assert client is not None
        mock_driver.close.assert_called_once()

    @patch("src.loader.neo4j_client.GraphDatabase")
    def test_run_query(self, mock_gdb):
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_record = MagicMock()
        mock_record.data.return_value = {"name": "test"}

        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.run.return_value = [mock_record]

        mock_gdb.driver.return_value = mock_driver

        client = Neo4jClient("bolt://test:7687", "neo4j", "pass")
        result = client.run_query("MATCH (n) RETURN n.name AS name")
        assert result == [{"name": "test"}]
        client.close()

    @patch("src.loader.neo4j_client.GraphDatabase")
    def test_run_batch(self, mock_gdb):
        mock_driver = MagicMock()
        mock_session = MagicMock()

        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        mock_gdb.driver.return_value = mock_driver

        client = Neo4jClient("bolt://test:7687", "neo4j", "pass")
        data = [{"name": f"item_{i}"} for i in range(10)]
        total = client.run_batch("UNWIND $batch AS item MERGE (n:Test {name: item.name})", data, batch_size=3)
        assert total == 10
        client.close()


class TestSchemaInitializer:
    @patch("src.loader.neo4j_client.GraphDatabase")
    def test_init_schema(self, mock_gdb):
        mock_driver = MagicMock()
        mock_session = MagicMock()

        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        mock_gdb.driver.return_value = mock_driver

        client = Neo4jClient("bolt://test:7687", "neo4j", "pass")
        init_schema(client)
        # Should have called execute_write for each constraint + index
        assert mock_session.execute_write.call_count > 0
        client.close()
