-- JDGraphBuilder: 常用查询示例
-- 在 Neo4j Browser (http://localhost:7474) 中执行

-- ══════════════════════════════════════════════════
-- 1. 图谱概览
-- ══════════════════════════════════════════════════

-- 各类节点数量
MATCH (n)
RETURN labels(n)[0] AS label, count(n) AS count
ORDER BY count DESC;

-- 各类关系数量
MATCH ()-[r]->()
RETURN type(r) AS type, count(r) AS count
ORDER BY count DESC;

-- ══════════════════════════════════════════════════
-- 2. 热门技能 Top 20
-- ══════════════════════════════════════════════════

MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill)
RETURN s.name AS skill, s.category AS category, count(j) AS job_count
ORDER BY job_count DESC
LIMIT 20;

-- ══════════════════════════════════════════════════
-- 3. 按技能匹配职位
-- ══════════════════════════════════════════════════

-- 示例: 掌握 Python 和 MySQL 的用户匹配职位
MATCH (j:Job)-[r:REQUIRES_SKILL]->(s:Skill)
WHERE s.name IN ["Python", "MySQL"]
WITH j, count(s) AS matched, collect(s.name) AS skills
RETURN j.title AS job, matched, skills
ORDER BY matched DESC
LIMIT 10;

-- ══════════════════════════════════════════════════
-- 4. 技能共现关系
-- ══════════════════════════════════════════════════

-- 示例: 与 Java 共现最多的技能
MATCH (s:Skill {name: "Java"})-[r:CO_OCCURS_WITH]-(other:Skill)
RETURN other.name AS skill, r.job_count AS co_occurrence
ORDER BY co_occurrence DESC
LIMIT 15;

-- ══════════════════════════════════════════════════
-- 5. 地域分布
-- ══════════════════════════════════════════════════

MATCH (j:Job)-[:LOCATED_IN]->(l:Location)
RETURN l.name AS city, count(j) AS jobs
ORDER BY jobs DESC;

-- ══════════════════════════════════════════════════
-- 6. 技能层级关系
-- ══════════════════════════════════════════════════

-- 查看所有 parent-child 技能关系
MATCH (parent:Skill)-[:PARENT_OF]->(child:Skill)
RETURN parent.name AS parent, child.name AS child, child.category AS category
ORDER BY parent.name;

-- ══════════════════════════════════════════════════
-- 7. 职位详情
-- ══════════════════════════════════════════════════

-- 示例: 查看某个职位的完整信息
MATCH (j:Job {source_file: "xyh_01.txt"})
OPTIONAL MATCH (j)-[rs:REQUIRES_SKILL]->(req:Skill)
OPTIONAL MATCH (j)-[:LOCATED_IN]->(l:Location)
OPTIONAL MATCH (j)-[:REQUIRES_EDUCATION]->(e:Education)
OPTIONAL MATCH (j)-[:BELONGS_TO]->(c:Category)
RETURN j.title AS title,
       collect(DISTINCT l.name) AS locations,
       e.level AS education,
       c.name AS category,
       collect(DISTINCT {skill: req.name, proficiency: rs.proficiency}) AS required_skills;

-- ══════════════════════════════════════════════════
-- 8. 技能差距分析
-- ══════════════════════════════════════════════════

-- 示例: 用户会 JavaScript + Vue.js，目标职位的技能差距
WITH ["JavaScript", "Vue.js"] AS my_skills
MATCH (j:Job)-[r:REQUIRES_SKILL]->(s:Skill)
WHERE j.title CONTAINS "全栈"
WITH j, my_skills,
     collect({name: s.name, proficiency: r.proficiency}) AS required
RETURN j.title,
       [s IN required WHERE s.name IN my_skills] AS matched,
       [s IN required WHERE NOT s.name IN my_skills] AS to_learn;
