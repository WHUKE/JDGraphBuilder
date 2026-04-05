"""查询模块测试（使用 Mock Neo4j）"""

from unittest.mock import MagicMock, patch

from src.query.job_query import find_jobs_by_skills, get_job_detail
from src.query.skill_query import get_related_skills, get_top_skills
from src.query.stats_query import get_graph_overview


def _make_mock_client(query_results: list[dict]) -> MagicMock:
    """创建返回指定结果的 mock Neo4jClient。"""
    client = MagicMock()
    client.run_query.return_value = query_results
    return client


class TestJobQuery:
    def test_find_jobs_by_skills(self):
        mock_results = [
            {
                "title": "后端开发",
                "source_file": "test.txt",
                "matched": 2,
                "matched_skills": ["Java", "MySQL"],
                "locations": ["北京"],
                "education": "本科",
                "category": "后端开发",
            }
        ]
        client = _make_mock_client(mock_results)
        results = find_jobs_by_skills(client, ["Java", "MySQL"])
        assert len(results) == 1
        assert results[0]["matched"] == 2
        client.run_query.assert_called_once()

    def test_get_job_detail(self):
        mock_results = [
            {
                "title": "后端开发",
                "source_file": "test.txt",
                "experience_min": 3,
                "experience_max": 5,
                "responsibilities": ["开发"],
                "education": "本科",
                "category": "后端开发",
                "locations": ["北京"],
                "required_skills": [
                    {"name": "Java", "proficiency": "精通", "category": "编程语言"}
                ],
                "preferred_skills": [{"name": None, "proficiency": None, "category": None}],
            }
        ]
        client = _make_mock_client(mock_results)
        result = get_job_detail(client, "test.txt")
        assert result["title"] == "后端开发"
        # null skills should be filtered out
        assert len(result["preferred_skills"]) == 0


class TestSkillQuery:
    def test_get_top_skills(self):
        mock_results = [
            {"name": "Java", "category": "编程语言", "job_count": 50},
            {"name": "Python", "category": "编程语言", "job_count": 40},
        ]
        client = _make_mock_client(mock_results)
        results = get_top_skills(client, limit=10)
        assert len(results) == 2
        assert results[0]["name"] == "Java"

    def test_get_related_skills(self):
        mock_results = [
            {"name": "Spring Boot", "category": "后端框架", "job_count": 30, "weight": 0.95},
        ]
        client = _make_mock_client(mock_results)
        results = get_related_skills(client, "Java")
        assert len(results) == 1


class TestStatsQuery:
    def test_get_graph_overview(self):
        client = MagicMock()
        client.run_query.side_effect = [
            # node counts
            [
                {"label": "Job", "count": 120},
                {"label": "Skill", "count": 500},
            ],
            # relation counts
            [
                {"type": "REQUIRES_SKILL", "count": 1500},
            ],
        ]
        result = get_graph_overview(client)
        assert result["nodes"]["Job"] == 120
        assert result["relations"]["REQUIRES_SKILL"] == 1500
