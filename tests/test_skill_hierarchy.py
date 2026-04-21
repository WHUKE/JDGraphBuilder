"""技能层级规则库单元测试"""

from src.cleaner.skill_hierarchy import PARENT_RULES, infer_parent


class TestInferParent:
    def test_existing_parent_preserved(self):
        """已有 parent 不应被覆盖。"""
        assert infer_parent("Spring Boot", "Spring") == "Spring"
        # 即使规则里没有的 parent 也应原样保留
        assert infer_parent("Spring Boot", "CustomParent") == "CustomParent"

    def test_rule_hit(self):
        assert infer_parent("Spring Boot", None) == "Spring"
        assert infer_parent("Vue Router", None) == "Vue.js"
        assert infer_parent("Helm", None) == "Kubernetes"
        assert infer_parent("Docker Compose", None) == "Docker"
        assert infer_parent("React Router", None) == "React"

    def test_rule_hit_with_empty_existing(self):
        """空字符串视作无 parent，应命中规则。"""
        assert infer_parent("Helm", "") == "Kubernetes"
        assert infer_parent("Helm", "   ") == "Kubernetes"

    def test_case_insensitive(self):
        assert infer_parent("spring boot", None) == "Spring"
        assert infer_parent("HELM", None) == "Kubernetes"
        assert infer_parent("vue router", None) == "Vue.js"

    def test_unknown_skill(self):
        assert infer_parent("SomeVeryRareSkill", None) is None
        assert infer_parent("随意乱写", None) is None

    def test_empty_name(self):
        assert infer_parent(None, None) is None
        assert infer_parent("", None) is None
        assert infer_parent("   ", None) is None

    def test_no_self_loop(self):
        """若规则里某个 skill 同时作 parent 与 child，不应产生自环。"""
        # 构造场景：当前规则表里不会出现，但做防御性验证
        # 通过检查 _CHILD_TO_PARENT 不包含自指
        for parent, children in PARENT_RULES.items():
            for child in children:
                assert child.strip().lower() != parent.strip().lower(), \
                    f"规则表存在自环: {parent} -> {child}"


class TestParentRules:
    def test_rules_non_empty(self):
        assert len(PARENT_RULES) > 0

    def test_key_values_are_strings(self):
        for parent, children in PARENT_RULES.items():
            assert isinstance(parent, str) and parent.strip()
            assert isinstance(children, list)
            for c in children:
                assert isinstance(c, str) and c.strip()
