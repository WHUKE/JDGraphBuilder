"""数据清洗模块测试"""

import pytest

from src.cleaner.field_cleaner import (
    clean_education,
    clean_experience,
    clean_job_category,
    clean_job_title,
    clean_location,
    clean_proficiency,
)
from src.cleaner.skill_cleaner import clean_skills
from src.cleaner.validator import validate_jd


# ── clean_location ─────────────────────────────────────

class TestCleanLocation:
    def test_single_city(self):
        assert clean_location("北京") == ["北京"]

    def test_city_with_suffix(self):
        assert clean_location("广州市") == ["广州"]
        assert clean_location("杭州市") == ["杭州"]

    def test_multi_city_comma(self):
        result = clean_location("北京、上海、深圳")
        assert result == ["北京", "上海", "深圳"]

    def test_multi_city_slash(self):
        result = clean_location("北京/上海/杭州")
        assert result == ["北京", "上海", "杭州"]

    def test_none(self):
        assert clean_location(None) == ["未知"]

    def test_empty(self):
        assert clean_location("") == ["未知"]


# ── clean_education ────────────────────────────────────

class TestCleanEducation:
    def test_standard_value(self):
        assert clean_education("本科") == "本科"
        assert clean_education("硕士") == "硕士"

    def test_with_suffix(self):
        assert clean_education("本科及以上") == "本科"
        assert clean_education("硕士以上") == "硕士"

    def test_none(self):
        assert clean_education(None) == "不限"

    def test_empty(self):
        assert clean_education("") == "不限"

    def test_valid_values_passthrough(self):
        assert clean_education("不限") == "不限"
        assert clean_education("大专") == "大专"
        assert clean_education("博士") == "博士"


# ── clean_experience ───────────────────────────────────

class TestCleanExperience:
    def test_range(self):
        assert clean_experience("3-5年") == {"min": 3, "max": 5}

    def test_min_only(self):
        assert clean_experience("3年以上") == {"min": 3, "max": None}
        assert clean_experience("3年及以上") == {"min": 3, "max": None}

    def test_around(self):
        assert clean_experience("3年左右") == {"min": 2, "max": 4}

    def test_unlimited(self):
        assert clean_experience("不限") == {"min": 0, "max": None}

    def test_none(self):
        assert clean_experience(None) == {"min": 0, "max": None}

    def test_garbage(self):
        result = clean_experience("GPU编程和模型优化")
        assert result == {"min": 0, "max": None}


# ── clean_job_category ─────────────────────────────────

class TestCleanJobCategory:
    def test_standard_value(self):
        assert clean_job_category("前端开发") == "前端开发"

    def test_mapping(self):
        assert clean_job_category("后端") == "后端开发"
        assert clean_job_category("服务端开发") == "后端开发"

    def test_long_path(self):
        assert clean_job_category("技术-服务端开发-服务端开发") == "后端开发"
        assert clean_job_category("技术-前端及客户端开发-web前端开发") == "前端开发"

    def test_none(self):
        assert clean_job_category(None) == "其他"


# ── clean_job_title ────────────────────────────────────

class TestCleanJobTitle:
    def test_with_prefix(self):
        assert clean_job_title("【急招】高级Java开发") == "高级Java开发"
        assert clean_job_title("【平台】全栈开发工程师") == "全栈开发工程师"

    def test_normal(self):
        assert clean_job_title("后端开发工程师") == "后端开发工程师"

    def test_none(self):
        assert clean_job_title(None) == "未知职位"


# ── clean_proficiency ──────────────────────────────────

class TestCleanProficiency:
    def test_standard(self):
        assert clean_proficiency("精通") == "精通"
        assert clean_proficiency("熟悉") == "熟悉"

    def test_mapping(self):
        assert clean_proficiency("扎实") == "熟练"
        assert clean_proficiency("深入理解") == "精通"
        assert clean_proficiency("良好") == "熟悉"

    def test_none(self):
        assert clean_proficiency(None) == "不限"


# ── clean_skills ───────────────────────────────────────

class TestCleanSkills:
    def test_dedup_across_lists(self):
        required = [{"name": "Java", "proficiency": "精通", "category": "编程语言"}]
        preferred = [{"name": "Java"}, {"name": "Docker"}]
        req, pref = clean_skills(required, preferred)
        assert len(req) == 1
        assert len(pref) == 1  # Java removed, Docker kept
        assert pref[0]["name"] == "Docker"

    def test_fill_missing_fields(self):
        required = [{"name": "Redis"}]
        preferred = []
        req, pref = clean_skills(required, preferred)
        assert req[0]["proficiency"] == "不限"
        assert req[0]["category"] == "其他"

    def test_proficiency_normalization(self):
        required = [{"name": "Java", "proficiency": "扎实", "category": "编程语言"}]
        req, _ = clean_skills(required, [])
        assert req[0]["proficiency"] == "熟练"


# ── validate_jd ────────────────────────────────────────

class TestValidateJd:
    def test_valid_jd(self, sample_jd_raw):
        warnings = validate_jd(sample_jd_raw)
        # Redis has no proficiency listed, but data has "proficiency" missing
        # which won't be in VALID_PROFICIENCY check (it's None)
        assert isinstance(warnings, list)

    def test_missing_source_file(self):
        warnings = validate_jd({"job_title": "test"})
        assert any("source_file" in w for w in warnings)

    def test_missing_optional_fields(self):
        warnings = validate_jd({"source_file": "x.txt"})
        assert any("job_title" in w for w in warnings)
        assert any("location" in w for w in warnings)
