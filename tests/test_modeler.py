"""建模模块测试"""

from src.modeler.co_occurrence import compute_co_occurrence
from src.modeler.node_builder import build_nodes
from src.modeler.relation_builder import build_relations


class TestBuildNodes:
    def test_jobs_count(self, sample_jds_for_modeling):
        nodes = build_nodes(sample_jds_for_modeling)
        assert len(nodes["jobs"]) == 2

    def test_skills_dedup(self, sample_jds_for_modeling):
        nodes = build_nodes(sample_jds_for_modeling)
        skill_names = {s["name"] for s in nodes["skills"]}
        # MySQL appears in both JDs but should be deduplicated
        assert "MySQL" in skill_names
        # Spring is referenced as parent but should also be created
        assert "Spring" in skill_names

    def test_locations_dedup(self, sample_jds_for_modeling):
        nodes = build_nodes(sample_jds_for_modeling)
        loc_names = {l["name"] for l in nodes["locations"]}
        assert "北京" in loc_names
        assert "上海" in loc_names
        assert len(loc_names) == 2

    def test_education_with_rank(self, sample_jds_for_modeling):
        nodes = build_nodes(sample_jds_for_modeling)
        for edu in nodes["educations"]:
            if edu["level"] == "本科":
                assert edu["rank"] == 1

    def test_categories(self, sample_jds_for_modeling):
        nodes = build_nodes(sample_jds_for_modeling)
        cat_names = {c["name"] for c in nodes["categories"]}
        assert "后端开发" in cat_names
        assert "前端开发" in cat_names


class TestBuildRelations:
    def test_requires_skill(self, sample_jds_for_modeling):
        relations = build_relations(sample_jds_for_modeling)
        req = relations["requires_skill"]
        # JD1 has 3 required + JD2 has 3 required = 6
        assert len(req) == 6

    def test_prefers_skill(self, sample_jds_for_modeling):
        relations = build_relations(sample_jds_for_modeling)
        pref = relations["prefers_skill"]
        # JD1 has 1 preferred, JD2 has 0
        assert len(pref) == 1

    def test_parent_of(self, sample_jds_for_modeling):
        relations = build_relations(sample_jds_for_modeling)
        parent_of = relations["parent_of"]
        # Spring → Spring Boot
        parents = {(r["parent"], r["child"]) for r in parent_of}
        assert ("Spring", "Spring Boot") in parents

    def test_located_in(self, sample_jds_for_modeling):
        relations = build_relations(sample_jds_for_modeling)
        # JD1: 北京+上海, JD2: 北京 = 3
        assert len(relations["located_in"]) == 3


class TestCoOccurrence:
    def test_basic(self, sample_jds_for_modeling):
        co = compute_co_occurrence(sample_jds_for_modeling, min_count=1)
        # Both JDs have MySQL, so MySQL+Java and MySQL+Vue.js etc should exist
        assert len(co) > 0
        # Check co-occurrence includes MySQL with something from both JDs
        pair_names = {(c["skill_a"], c["skill_b"]) for c in co}
        # MySQL appears in both JDs with other skills
        has_mysql_pair = any("MySQL" in (a, b) for a, b in pair_names)
        assert has_mysql_pair

    def test_min_count_filter(self, sample_jds_for_modeling):
        co = compute_co_occurrence(sample_jds_for_modeling, min_count=2)
        # Only pairs appearing in >= 2 JDs: MySQL appears in both
        for item in co:
            assert item["job_count"] >= 2

    def test_weight_normalized(self, sample_jds_for_modeling):
        co = compute_co_occurrence(sample_jds_for_modeling, min_count=1)
        if co:
            # First item (highest count) should have weight 1.0
            assert co[0]["weight"] == 1.0
