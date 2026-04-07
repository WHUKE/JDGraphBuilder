# JDGraphBuilder

核心系统 — 将 JDParser 解析的 JD 结构化数据清洗、建模后导入 Neo4j 图数据库，提供图谱查询接口。

## 项目结构

```
JDGraphBuilder/
├── src/
│   ├── config.py           # 全局配置
│   ├── cleaner/            # 数据清洗模块
│   │   ├── field_cleaner.py  # 字段级清洗
│   │   ├── skill_cleaner.py  # 技能去重与补全
│   │   ├── validator.py      # 数据校验
│   │   └── pipeline.py       # 清洗流水线
│   ├── modeler/            # 图建模模块
│   │   ├── schema.py         # Schema 常量
│   │   ├── node_builder.py   # 节点提取与去重
│   │   ├── relation_builder.py # 关系构建
│   │   └── co_occurrence.py  # 技能共现计算
│   ├── loader/             # Neo4j 入库模块
│   │   ├── neo4j_client.py   # 连接管理
│   │   ├── schema_initializer.py # Schema 初始化
│   │   └── batch_importer.py # 批量导入
│   ├── query/              # 查询模块
│   │   ├── job_query.py      # 职位查询
│   │   ├── skill_query.py    # 技能查询
│   │   ├── path_query.py     # 路径分析
│   │   └── stats_query.py    # 统计查询
│   └── cli/                # 命令行入口
│       ├── clean.py
│       ├── build.py
│       ├── query.py
│       └── stats.py
├── data/
│   ├── input/              # JDParser 输出的 JSON
│   ├── cleaned/            # 清洗后的 JSON
│   └── mappings/           # 字段映射表
├── scripts/                # Cypher 脚本
├── tests/                  # 测试
└── docs/                   # 文档
```

## 环境准备

### 1. 安装 Python 依赖

```bash
# 需要 uv (https://docs.astral.sh/uv/)
cd JDGraphBuilder
uv sync
```

### 2. Neo4j 配置


[Neo4j](https://neo4j.com/download/) 
Start Free With AuraDB 或下载 Neo4j 到本地并启动服务。

### 3. 配置连接

复制 `.env.example` 为 `.env`，修改 Neo4j 连接信息：

```bash
cp .env.example .env
# 编辑 .env
NEO4J_URI=
NEO4J_USERNAME=
NEO4J_PASSWORD=
NEO4J_DATABASE=
```

## 使用方法

### 一键构建图谱

```bash
# 清洗 + 建模 + 导入 Neo4j
uv run python -m src.cli.build --input data/input/_all.json

# 重置数据库后重新导入
uv run python -m src.cli.build --input data/input/_all.json --reset

# 只执行清洗和建模（不连接 Neo4j）
uv run python -m src.cli.build --input data/input/_all.json --skip-import
```

### 单独清洗

```bash
uv run python -m src.cli.clean --input data/input/_all.json --output data/cleaned/
```

### 查询图谱

```bash
# 按技能匹配职位
uv run python -m src.cli.query --skill Python Django

# 按城市筛选
uv run python -m src.cli.query --location 北京

# 技能共现分析
uv run python -m src.cli.query --related Java

# 技能差距分析
uv run python -m src.cli.query --gap Python Django --target 后端开发

# 图谱统计
uv run python -m src.cli.stats
```

### 运行测试

```bash
uv run pytest
```

## 图谱 Schema

详见 [docs/schema.md](docs/schema.md)。

5 种节点类型：`Job`、`Skill`、`Location`、`Education`、`Category`

7 种关系类型：`REQUIRES_SKILL`、`PREFERS_SKILL`、`REQUIRES_EDUCATION`、`LOCATED_IN`、`BELONGS_TO`、`PARENT_OF`、`CO_OCCURS_WITH`

## 前置依赖

- Python ≥ 3.12
- Neo4j ≥ 5.0 (Community Edition)
- [JDParser](https://github.com/WHUKE/JDParser) — 上游项目，提供解析后的 JD 数据
