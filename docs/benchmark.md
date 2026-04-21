# Benchmark

本文件由 `scripts/benchmark.py` 追加生成，记录不同数据规模下的性能数据。

说明：
- **构建耗时**：`run_pipeline + build_nodes + build_relations + compute_co_occurrence` 的总时间（不含 Neo4j 写入）。
- **查询延迟**：在真实 Neo4j 图上执行 N 次并取中位数（每次前 `invalidate_cache()` 清缓存，测量 cold path）。

## Benchmark @ 2026-04-21 16:24:01

### 构建耗时

| n_jds | clean(s) | model(s) | jobs | skills | REQUIRES_SKILL | CO_OCCURS_WITH |
|------:|---------:|---------:|-----:|-------:|---------------:|---------------:|
| 120 | 0.045 | 0.015 | 120 | 1400 | 2217 | 4728 |
| 600 | 0.176 | 0.059 | 600 | 1400 | 11085 | 4728 |

