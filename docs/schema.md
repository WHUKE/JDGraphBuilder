# 图谱 Schema 设计文档

## 节点类型（Labels）

| 节点标签 | 属性 | 说明 |
|----------|------|------|
| `Job` | `title`, `source_file`, `experience_min`, `experience_max`, `responsibilities` | 职位节点 |
| `Skill` | `name`, `category` | 技能节点（全局唯一，被多个 Job 共享） |
| `Location` | `name` | 工作地点节点 |
| `Education` | `level`, `rank` | 学历节点（rank: 不限=-1, 大专=0, 本科=1, 硕士=2, 博士=3） |
| `Category` | `name` | 职位类别节点 |

## 关系类型（Relationship Types）

| 关系 | 起点 → 终点 | 属性 | 说明 |
|------|-------------|------|------|
| `REQUIRES_SKILL` | `Job` → `Skill` | `proficiency` | 职位要求的必需技能 |
| `PREFERS_SKILL` | `Job` → `Skill` | `proficiency` | 职位的加分技能 |
| `REQUIRES_EDUCATION` | `Job` → `Education` | — | 职位的学历要求 |
| `LOCATED_IN` | `Job` → `Location` | — | 职位的工作地点 |
| `BELONGS_TO` | `Job` → `Category` | — | 职位所属类别 |
| `PARENT_OF` | `Skill` → `Skill` | — | 技能层级关系 |
| `CO_OCCURS_WITH` | `Skill` — `Skill` | `weight`, `job_count` | 技能共现关系（无向） |

## 约束与索引

```cypher
-- 唯一性约束
CREATE CONSTRAINT skill_name FOR (s:Skill) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT location_name FOR (l:Location) REQUIRE l.name IS UNIQUE;
CREATE CONSTRAINT education_level FOR (e:Education) REQUIRE e.level IS UNIQUE;
CREATE CONSTRAINT category_name FOR (c:Category) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT job_source FOR (j:Job) REQUIRE j.source_file IS UNIQUE;

-- 全文索引
CREATE FULLTEXT INDEX skill_search FOR (s:Skill) ON EACH [s.name];
CREATE FULLTEXT INDEX job_search FOR (j:Job) ON EACH [j.title];
```

## 数据规模

- 120 条 JD → 120 个 Job 节点
- 约 500+ 个去重 Skill 节点
- 约 15 个 Location 节点
- 4 个 Education 节点
- 约 10 个 Category 节点
- 数千条技能共现关系
