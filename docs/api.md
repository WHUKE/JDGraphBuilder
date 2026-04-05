# 查询 API 文档

## 职位查询 (`src/query/job_query.py`)

### `find_jobs_by_skills(client, skills, limit=20)`
给定技能列表，返回匹配度最高的职位。

### `find_jobs_by_location(client, city, limit=50)`
查询指定城市的所有职位。

### `find_jobs_by_education(client, level, limit=50)`
查询指定学历要求及以下的职位。

### `get_job_detail(client, source_file)`
获取职位完整详情。

## 技能查询 (`src/query/skill_query.py`)

### `get_top_skills(client, limit=30)`
热门技能排行（被最多职位要求的技能）。

### `get_related_skills(client, skill_name, limit=20)`
查询与指定技能共现频率最高的技能。

### `get_skill_tree(client, skill_name)`
查询指定技能的父/子技能层级关系。

### `get_skills_by_category(client, category, limit=50)`
查询某分类下的所有技能。

## 路径查询 (`src/query/path_query.py`)

### `get_skill_gap(client, user_skills, target_job_title)`
分析用户当前技能与目标职位要求的差距。返回已掌握技能、缺失技能和匹配率。

### `get_job_transition(client, from_job_title, to_job_title)`
分析两个职位间的技能重叠度和需补充的技能。

## 统计查询 (`src/query/stats_query.py`)

### `get_graph_overview(client)`
图谱概览：各类节点和关系的数量。

### `get_skill_distribution(client, limit=50)`
各技能被职位要求的频次统计。

### `get_location_distribution(client)`
各城市的职位数量统计。

### `get_education_distribution(client)`
各学历层次的职位数量统计。

### `get_category_distribution(client)`
各职位类别的职位数量统计。

### `get_skill_category_distribution(client)`
各技能类别的技能数量和关联职位数。

## CLI 使用

```bash
# 按技能匹配职位
python -m src.cli.query --skill Python Django MySQL

# 按地点筛选
python -m src.cli.query --location 北京

# 按学历筛选
python -m src.cli.query --education 本科

# 职位详情
python -m src.cli.query --detail xyh_01.txt

# 关联技能
python -m src.cli.query --related Java

# 技能层级
python -m src.cli.query --tree "Spring Boot"

# 技能差距分析
python -m src.cli.query --gap Python Django --target 后端开发

# 职位跳转分析
python -m src.cli.query --path 前端开发 全栈开发

# 热门技能
python -m src.cli.query --trending

# 图谱统计
python -m src.cli.stats
```
