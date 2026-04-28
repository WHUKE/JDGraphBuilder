"""图可视化查询测试。"""

from unittest.mock import MagicMock, patch

from src.query.graph_query import get_visual_graph


class TestGraphQuery:
    @patch("src.query.graph_query.find_jobs_by_skills")
    @patch("src.query.graph_query.get_related_skills")
    @patch("src.query.graph_query.get_top_skills")
    def test_get_visual_graph(self, mock_get_top_skills, mock_get_related_skills, mock_find_jobs_by_skills):
        mock_get_top_skills.return_value = [
            {"name": "Python", "category": "编程语言", "job_count": 42},
        ]
        mock_get_related_skills.return_value = [
            {"name": "Django", "category": "后端框架", "job_count": 18, "weight": 0.86},
        ]
        mock_find_jobs_by_skills.return_value = [
            {
                "title": "后端开发",
                "source_file": "job_01.json",
                "locations": ["北京"],
                "education": "本科",
                "category": "后端开发",
                "matched": 1,
            }
        ]

        client = MagicMock()
        graph = get_visual_graph(client, skill_limit=1, related_skill_limit=1, jobs_per_skill=1)

        assert graph["meta"]["skill_limit"] == 1
        assert any(node["id"] == "skill:Python" for node in graph["nodes"])
        assert any(node["type"] == "role" for node in graph["nodes"])
        assert any(edge["source"] == "job:job_01.json" and edge["target"] == "skill:Python" for edge in graph["edges"])
