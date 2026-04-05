-- JDGraphBuilder: Neo4j Schema 初始化脚本
-- 执行方式: 在 Neo4j Browser 中逐条执行，或通过 schema_initializer.py 自动执行

-- ══════════════════════════════════════════════════
-- 唯一性约束（同时自动创建索引）
-- ══════════════════════════════════════════════════

CREATE CONSTRAINT skill_name IF NOT EXISTS
FOR (s:Skill) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT location_name IF NOT EXISTS
FOR (l:Location) REQUIRE l.name IS UNIQUE;

CREATE CONSTRAINT education_level IF NOT EXISTS
FOR (e:Education) REQUIRE e.level IS UNIQUE;

CREATE CONSTRAINT category_name IF NOT EXISTS
FOR (c:Category) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT job_source IF NOT EXISTS
FOR (j:Job) REQUIRE j.source_file IS UNIQUE;

-- ══════════════════════════════════════════════════
-- 全文索引（支持模糊搜索）
-- ══════════════════════════════════════════════════

CREATE FULLTEXT INDEX skill_search IF NOT EXISTS
FOR (s:Skill) ON EACH [s.name];

CREATE FULLTEXT INDEX job_search IF NOT EXISTS
FOR (j:Job) ON EACH [j.title];
