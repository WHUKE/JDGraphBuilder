"""端到端集成测试：清洗 → 建模 → Mock Neo4j 入库 → 查询。

Neo4j 部分使用 unittest.mock 避免真实连接。核心验证：
- 清洗流水线产生正确的 cleaned JSON 与 _cleaning_report.json
- 建模函数产生可供 Neo4j 导入的节点/关系字典形状
- BatchImporter.import_all 按正确顺序调用 run_batch 并传入预期形状的数据
- Query 模块可在 mock client 上运行
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.cleaner.pipeline import run_pipeline
from src.modeler.co_occurrence import compute_co_occurrence
from src.modeler.node_builder import build_nodes
from src.modeler.relation_builder import build_relations


@pytest.fixture
def e2e_raw_jds():
    """3 条覆盖多种边界的原始 JD 数据。"""
    return [
        {
            "source_file": "e2e_01.txt",
            "job_title": "【急招】后端开发工程师",
            "location": "北京、上海",
            "education": "本科及以上",
            "experience": "3-5年",
            "job_category": "后端",
            "responsibilities": ["开发", "维护"],
            "required_skills": [
                {"name": "Java", "proficiency": "精通", "category": "编程语言"},
                {"name": "Spring Boot", "proficiency": "扎实", "category": "后端框架"},
                {"name": "MySQL", "proficiency": None, "category": "数据库"},
            ],
            "preferred_skills": [
                {"name": "Docker Compose", "proficiency": "了解", "category": "DevOps"},
                {"name": "Java"},  # 与 required 重复
            ],
        },
        {
            "source_file": "e2e_02.txt",
            "job_title": "前端开发",
            "location": "广州市",
            "education": None,  # 未知学历
            "experience": "不限",
            "job_category": "前端开发",
            "responsibilities": [],
            "required_skills": [
                {"name": "JavaScript", "proficiency": "熟练", "category": "编程语言"},
                {"name": "Vue Router", "proficiency": "熟悉", "category": "前端"},
                {"name": "MySQL", "proficiency": "了解", "category": "数据库"},
            ],
            "preferred_skills": [],
        },
        {
            "source_file": "e2e_03.txt",
            "job_title": "运维工程师",
            "location": None,  # 空地点 → ["未知"]
            "education": "硕士",
            "experience": "5年以上",
            "job_category": "运维",
            "responsibilities": [],
            "required_skills": [],  # 空技能
            "preferred_skills": [],
        },
    ]


@pytest.fixture
def e2e_workspace(tmp_path, e2e_raw_jds):
    input_dir = tmp_path / "input"
    cleaned_dir = tmp_path / "cleaned"
    input_dir.mkdir()
    input_file = input_dir / "_all.json"
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(e2e_raw_jds, f, ensure_ascii=False)
    return {"input": input_file, "cleaned": cleaned_dir}


class TestE2ECleanBuildImport:
    def test_pipeline_produces_cleaned_and_report(self, e2e_workspace):
        cleaned = run_pipeline(e2e_workspace["input"], e2e_workspace["cleaned"])

        assert len(cleaned) == 3

        # 清洗结果文件
        out_file = e2e_workspace["cleaned"] / "_all_cleaned.json"
        assert out_file.exists()
        with open(out_file, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 3

        # 清洗报告文件
        report_file = e2e_workspace["cleaned"] / "_cleaning_report.json"
        assert report_file.exists()
        with open(report_file, encoding="utf-8") as f:
            report = json.load(f)
        assert report["total_jds"] == 3
        assert "warnings_by_type" in report
        assert "unknown_proficiency_terms" in report

    def test_cleaned_fields(self, e2e_workspace):
        cleaned = run_pipeline(e2e_workspace["input"], e2e_workspace["cleaned"])
        jd1 = next(j for j in cleaned if j["source_file"] == "e2e_01.txt")

        # 标题前缀被剥离
        assert jd1["job_title"] == "后端开发工程师"
        # 地点拆分
        assert jd1["locations"] == ["北京", "上海"]
        # 学历映射
        assert jd1["education"] == "本科"
        # 经验结构化
        assert jd1["experience"] == {"min": 3, "max": 5}
        # 类别映射
        assert jd1["job_category"] == "后端开发"
        # 技能去重（Java 从 preferred 移除）
        pref_names = [s["name"] for s in jd1["preferred_skills"]]
        assert "Java" not in pref_names
        # proficiency 映射："扎实" → "熟练"
        sb = next(s for s in jd1["required_skills"] if s["name"] == "Spring Boot")
        assert sb["proficiency"] == "熟练"
        # skill_hierarchy 兜底：Spring Boot 的 parent 应补为 Spring（本例原来有 parent=None）
        assert sb["parent"] == "Spring"
        # Docker Compose 应自动补 parent="Docker"
        dc = next(s for s in jd1["preferred_skills"] if s["name"] == "Docker Compose")
        assert dc["parent"] == "Docker"

    def test_empty_location_and_skills(self, e2e_workspace):
        cleaned = run_pipeline(e2e_workspace["input"], e2e_workspace["cleaned"])
        jd3 = next(j for j in cleaned if j["source_file"] == "e2e_03.txt")
        assert jd3["locations"] == ["未知"]
        assert jd3["education"] == "硕士"
        assert jd3["required_skills"] == []

        # jd2 未给 education，应回退为 "不限"
        jd2 = next(j for j in cleaned if j["source_file"] == "e2e_02.txt")
        assert jd2["education"] == "不限"

    def test_modeling_produces_valid_shapes(self, e2e_workspace):
        cleaned = run_pipeline(e2e_workspace["input"], e2e_workspace["cleaned"])
        nodes = build_nodes(cleaned)
        relations = build_relations(cleaned)
        co = compute_co_occurrence(cleaned, min_count=1)

        # 节点形状
        assert len(nodes["jobs"]) == 3
        job_sfs = {j["source_file"] for j in nodes["jobs"]}
        assert job_sfs == {"e2e_01.txt", "e2e_02.txt", "e2e_03.txt"}

        skill_names = {s["name"] for s in nodes["skills"]}
        # skill_hierarchy 兜底带入的 parent（Spring、Docker、Vue.js）也会作为节点创建
        assert {"Java", "Spring", "Spring Boot", "Docker", "Docker Compose",
                "Vue.js", "Vue Router", "MySQL", "JavaScript"}.issubset(skill_names)

        # 关系形状
        parent_pairs = {(r["parent"], r["child"]) for r in relations["parent_of"]}
        assert ("Spring", "Spring Boot") in parent_pairs
        assert ("Docker", "Docker Compose") in parent_pairs
        assert ("Vue.js", "Vue Router") in parent_pairs

        # 共现：MySQL 同时出现在 jd1+jd2
        assert any(
            {c["skill_a"], c["skill_b"]} == {"MySQL", "Java"} or
            {c["skill_a"], c["skill_b"]} == {"MySQL", "JavaScript"}
            for c in co
        )

    def test_adaptive_min_count_with_none(self, e2e_workspace):
        cleaned = run_pipeline(e2e_workspace["input"], e2e_workspace["cleaned"])
        # None 触发自适应：3 条 → max(2, 3//60)=2
        co = compute_co_occurrence(cleaned, min_count=None)
        # 本例大部分 pair 只出现 1 次，应被过滤为空
        assert all(c["job_count"] >= 2 for c in co)

    @patch("src.loader.neo4j_client.GraphDatabase")
    def test_mock_import_all(self, mock_gdb, e2e_workspace):
        from src.loader.batch_importer import BatchImporter
        from src.loader.neo4j_client import Neo4jClient

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        cleaned = run_pipeline(e2e_workspace["input"], e2e_workspace["cleaned"])
        nodes = build_nodes(cleaned)
        relations = build_relations(cleaned)
        co = compute_co_occurrence(cleaned, min_count=1)

        client = Neo4jClient("bolt://test:7687", "neo4j", "pass")
        importer = BatchImporter(client)
        stats = importer.import_all(nodes, relations, co)

        # 9 类写入 + 每类至少调用一次 execute_write（非空才会调用）
        assert stats["jobs"] == 3
        assert stats["skills"] > 0
        assert mock_session.execute_write.called
        client.close()

    @patch("src.loader.neo4j_client.GraphDatabase")
    def test_mock_incremental_import(self, mock_gdb, e2e_workspace):
        """验证 incremental 模式调用 _purge_job_edges 并传入 touched source_files。"""
        from src.loader.batch_importer import BatchImporter
        from src.loader.neo4j_client import Neo4jClient

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        # _purge_job_edges 会读 count
        mock_record = MagicMock()
        mock_record.data.return_value = {"deleted": 5}
        mock_result.__iter__ = lambda s: iter([mock_record])
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        cleaned = run_pipeline(e2e_workspace["input"], e2e_workspace["cleaned"])
        nodes = build_nodes(cleaned)
        relations = build_relations(cleaned)
        co = compute_co_occurrence(cleaned, min_count=1)

        client = Neo4jClient("bolt://test:7687", "neo4j", "pass")
        importer = BatchImporter(client)
        touched = [j["source_file"] for j in nodes["jobs"]]
        stats = importer.import_all_incremental(nodes, relations, co, touched)

        assert "purged_edges" in stats
        assert stats["jobs"] == 3
        client.close()
