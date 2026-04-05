"""图谱 Schema 定义：节点标签、关系类型、约束、索引"""

# ── 节点标签 ───────────────────────────────────────────
LABEL_JOB = "Job"
LABEL_SKILL = "Skill"
LABEL_LOCATION = "Location"
LABEL_EDUCATION = "Education"
LABEL_CATEGORY = "Category"

# ── 关系类型 ───────────────────────────────────────────
REL_REQUIRES_SKILL = "REQUIRES_SKILL"
REL_PREFERS_SKILL = "PREFERS_SKILL"
REL_REQUIRES_EDUCATION = "REQUIRES_EDUCATION"
REL_LOCATED_IN = "LOCATED_IN"
REL_BELONGS_TO = "BELONGS_TO"
REL_PARENT_OF = "PARENT_OF"
REL_CO_OCCURS_WITH = "CO_OCCURS_WITH"

# ── 学历等级（用于排序比较） ───────────────────────────
EDUCATION_RANK = {
    "不限": -1,
    "大专": 0,
    "本科": 1,
    "硕士": 2,
    "博士": 3,
}

# ── 约束和索引 Cypher ─────────────────────────────────
CONSTRAINTS = [
    "CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT location_name IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
    "CREATE CONSTRAINT education_level IF NOT EXISTS FOR (e:Education) REQUIRE e.level IS UNIQUE",
    "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT job_source IF NOT EXISTS FOR (j:Job) REQUIRE j.source_file IS UNIQUE",
]

INDEXES = [
    "CREATE FULLTEXT INDEX skill_search IF NOT EXISTS FOR (s:Skill) ON EACH [s.name]",
    "CREATE FULLTEXT INDEX job_search IF NOT EXISTS FOR (j:Job) ON EACH [j.title]",
]
