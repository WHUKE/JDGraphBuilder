"""技能层级规则库：当 LLM 未输出 parent 时按内置规则兜底。

规则形式：PARENT_RULES 是正向字典 parent → list[child]。
反向索引在模块加载时自动构建：child_lower → parent（原大小写）。

仅在技能的 parent 为空/None 时才补全，永不覆盖已有 parent。
"""

from __future__ import annotations

# ── 正向规则：父技能 → 子技能列表 ─────────────────────
# 选择原则：只列出业界广泛认可的从属关系，避免把"同一生态"当作"父子"。
# 所有键值使用标准化后的规范名称（与 normalizer 输出一致）。
PARENT_RULES: dict[str, list[str]] = {
    # Spring 生态
    "Spring": [
        "Spring Boot",
        "Spring Cloud",
        "Spring MVC",
        "Spring Security",
        "Spring Data",
        "Spring Data JPA",
        "Spring AOP",
        "Spring WebFlux",
    ],
    "Spring Cloud": [
        "Spring Cloud Alibaba",
        "Spring Cloud Gateway",
        "Spring Cloud Config",
    ],
    # Vue 生态
    "Vue.js": [
        "Vue Router",
        "Vuex",
        "Pinia",
        "Nuxt.js",
        "Vue CLI",
        "Vite",  # Vite 与 Vue 关系密切但非严格从属，保留看需求
        "Element UI",
        "Element Plus",
    ],
    # React 生态
    "React": [
        "React Router",
        "Redux",
        "Next.js",
        "React Native",
        "MobX",
        "Ant Design",
        "Material-UI",
    ],
    # Angular 生态
    "Angular": [
        "RxJS",
        "NgRx",
    ],
    # Docker / 容器
    "Docker": [
        "Docker Compose",
        "Dockerfile",
        "Docker Swarm",
    ],
    # Kubernetes 生态
    "Kubernetes": [
        "Helm",
        "Istio",
        "kubectl",
        "Kubeadm",
        "K3s",
        "K8s Operator",
    ],
    # Git 生态
    "Git": [
        "GitHub",
        "GitLab",
        "Gitflow",
        "GitLab CI",
        "GitHub Actions",
    ],
    # Node.js 生态
    "Node.js": [
        "Express",
        "Express.js",
        "Koa",
        "Koa.js",
        "NestJS",
        "Nest.js",
        "Egg.js",
        "npm",
        "pnpm",
        "yarn",
    ],
    # Python 生态
    "Python": [
        "Django",
        "Flask",
        "FastAPI",
        "Tornado",
        "Celery",
        "SQLAlchemy",
        "Pandas",
        "NumPy",
        "Scikit-learn",
        "Matplotlib",
    ],
    # Java 生态
    "Java": [
        "JVM",
        "Maven",
        "Gradle",
        "MyBatis",
        "Hibernate",
    ],
    # 大数据 / Hadoop 生态
    "Hadoop": [
        "HDFS",
        "MapReduce",
        "YARN",
        "Hive",
        "HBase",
    ],
    "Spark": [
        "Spark SQL",
        "Spark Streaming",
        "PySpark",
    ],
    # 消息队列
    "Kafka": [
        "Kafka Connect",
        "Kafka Streams",
    ],
    # 数据库 — 谨慎只列强从属
    "MySQL": [
        "InnoDB",
    ],
    "Elasticsearch": [
        "Kibana",
        "Logstash",
        "Beats",
    ],
    # 前端构建 / 语言
    "TypeScript": [],
    "JavaScript": [
        "ES6",
        "TypeScript",  # TS 本质是 JS 超集
    ],
    # 深度学习
    "PyTorch": [
        "TorchVision",
        "PyTorch Lightning",
    ],
    "TensorFlow": [
        "Keras",
        "TensorFlow Lite",
    ],
    # 云平台
    "AWS": [
        "S3",
        "EC2",
        "Lambda",
    ],
}


def _build_child_to_parent() -> dict[str, str]:
    """根据 PARENT_RULES 反向构建 child_lower → parent_original_case。

    若同一 child 在多个 parent 下出现（理论上不应），取第一个出现的。
    """
    mapping: dict[str, str] = {}
    for parent, children in PARENT_RULES.items():
        for child in children:
            key = child.strip().lower()
            if key and key not in mapping:
                mapping[key] = parent
    return mapping


_CHILD_TO_PARENT: dict[str, str] = _build_child_to_parent()


def infer_parent(skill_name: str | None, existing_parent: str | None) -> str | None:
    """根据规则推断 parent 技能名。

    - 已有非空 existing_parent：直接返回，不覆盖。
    - skill_name 命中规则：返回规则中的 parent。
    - 无命中：返回 None。

    大小写不敏感；自环（skill == parent）自动过滤。
    """
    if existing_parent and existing_parent.strip():
        return existing_parent.strip()

    if not skill_name or not skill_name.strip():
        return None

    key = skill_name.strip().lower()
    parent = _CHILD_TO_PARENT.get(key)
    if not parent:
        return None

    # 防自环
    if parent.strip().lower() == key:
        return None

    return parent
