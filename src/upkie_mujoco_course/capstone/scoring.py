"""第 45 关综合评分计算。"""
from __future__ import annotations
from typing import Any

# 评分维度 → 毕业门槛映射
# 8 类毕业门槛各对应一个评分维度；system_score 取所有维度最小值（木桶原理）。
DIMENSION_TO_GATE = {
    "code": "code_tests",
    "physics": "physical_metrics",
    "robustness": "robustness",
    "realtime": "realtime",
    "safety": "safety",
    "docs": "documentation",
    # design_review 和 oral_defense 也计入综合评分
    "design_review": "design_review",
    "oral_defense": "oral_defense",
}


def compute_system_score(evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """计算综合评分 system_score = min(所有维度)。

    每个维度评分：passed=1.0, failed=0.0
    system_score = min(所有维度评分)

    取最小值而非平均值的物理含义：毕业项目要求"全链路无短板"，
    任何一个维度不通过都意味着系统存在未闭环的风险，
    因此综合评分由最弱维度决定（木桶原理）。
    """
    dimension_scores = {}
    for dim, gate in DIMENSION_TO_GATE.items():
        ev = evidence.get(gate, {})
        dimension_scores[dim] = 1.0 if ev.get("passed", False) else 0.0

    system_score = min(dimension_scores.values()) if dimension_scores else 0.0
    return {
        "system_score": system_score,
        "dimension_scores": dimension_scores,
    }
