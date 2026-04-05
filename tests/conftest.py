"""pytest fixtures"""

import pytest


@pytest.fixture
def sample_jd_raw():
    """原始 JD 数据样本（模拟 JDParser 输出）。"""
    return {
        "source_file": "test_01.txt",
        "job_title": "【急招】高级Java开发",
        "location": "北京、上海、深圳",
        "education": "本科",
        "experience": "3-5年",
        "job_category": "技术-服务端开发-服务端开发",
        "responsibilities": ["负责后端开发", "负责系统设计"],
        "required_skills": [
            {"name": "Java", "proficiency": "精通", "category": "编程语言"},
            {"name": "Spring Boot", "proficiency": "熟练", "category": "后端框架", "parent": "Spring"},
            {"name": "MySQL", "proficiency": "熟悉", "category": "数据库"},
            {"name": "Redis", "category": "缓存"},  # proficiency 缺失
        ],
        "preferred_skills": [
            {"name": "Docker", "proficiency": "了解", "category": "DevOps工具"},
            {"name": "Java"},  # 与 required 重复，category 也缺失
        ],
    }


@pytest.fixture
def sample_jd_cleaned():
    """清洗后的 JD 数据样本。"""
    return {
        "source_file": "test_01.txt",
        "job_title": "高级Java开发",
        "locations": ["北京", "上海", "深圳"],
        "education": "本科",
        "experience": {"min": 3, "max": 5},
        "job_category": "后端开发",
        "responsibilities": ["负责后端开发", "负责系统设计"],
        "required_skills": [
            {"name": "Java", "proficiency": "精通", "category": "编程语言", "parent": None},
            {"name": "Spring Boot", "proficiency": "熟练", "category": "后端框架", "parent": "Spring"},
            {"name": "MySQL", "proficiency": "熟悉", "category": "数据库", "parent": None},
            {"name": "Redis", "proficiency": "不限", "category": "缓存", "parent": None},
        ],
        "preferred_skills": [
            {"name": "Docker", "proficiency": "了解", "category": "DevOps工具", "parent": None},
        ],
    }


@pytest.fixture
def sample_jds_for_modeling():
    """用于建模测试的多条清洗后 JD 数据。"""
    return [
        {
            "source_file": "test_01.txt",
            "job_title": "后端开发",
            "locations": ["北京", "上海"],
            "education": "本科",
            "experience": {"min": 3, "max": 5},
            "job_category": "后端开发",
            "responsibilities": [],
            "required_skills": [
                {"name": "Java", "proficiency": "精通", "category": "编程语言", "parent": None},
                {"name": "Spring Boot", "proficiency": "熟练", "category": "后端框架", "parent": "Spring"},
                {"name": "MySQL", "proficiency": "熟悉", "category": "数据库", "parent": None},
            ],
            "preferred_skills": [
                {"name": "Docker", "proficiency": "了解", "category": "DevOps工具", "parent": None},
            ],
        },
        {
            "source_file": "test_02.txt",
            "job_title": "前端开发",
            "locations": ["北京"],
            "education": "本科",
            "experience": {"min": 1, "max": 3},
            "job_category": "前端开发",
            "responsibilities": [],
            "required_skills": [
                {"name": "JavaScript", "proficiency": "精通", "category": "编程语言", "parent": None},
                {"name": "Vue.js", "proficiency": "熟练", "category": "前端框架", "parent": None},
                {"name": "MySQL", "proficiency": "了解", "category": "数据库", "parent": None},
            ],
            "preferred_skills": [],
        },
    ]
