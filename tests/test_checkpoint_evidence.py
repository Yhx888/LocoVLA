"""覆盖 _require_experiment_evidence 的三重证据 AND 校验。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from matplotlib import pyplot as plt

from upkie_mujoco_course.course import checkpoint as ckpt
from upkie_mujoco_course.course.checkpoint import _require_experiment_evidence as _check_evidence
from upkie_mujoco_course.course.results import write_experiment_result

# 用一个不与真实关卡冲突的虚构关卡号做测试，避免污染真实配置。
CHAPTER = "99"


def _require_experiment_evidence(root: Path, chapter_id: str) -> None:
    _check_evidence(root, chapter_id, source_root=root)


@pytest.fixture
def evidence_setup(tmp_path, monkeypatch):
    """在 tmp_path 下构造第 99 关的完整三重证据，返回可调整的句柄。"""

    monkeypatch.setitem(ckpt.REQUIRED_EXPERIMENT_RESULTS, CHAPTER, "engineering_99.json")
    monkeypatch.setitem(ckpt.REQUIRED_PORTFOLIO_REPORTS, CHAPTER, "evidence.json")

    # plots 真实文件
    plot_path = tmp_path / "plots" / "plot_99.png"
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(plot_path, np.zeros((2, 2, 3), dtype=np.uint8))

    # logs 真实文件
    log_path = tmp_path / "logs" / "log_99.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text('{"seed": 0}\n', encoding="utf-8")

    # results/{filename}：passed=True 且引用 plots / logs
    result_path = tmp_path / "results" / "engineering_99.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    write_experiment_result(
        result_path,
        chapter_id=CHAPTER,
        seed=0,
        config={"lab": "engineering"},
        metrics={"error": 0.0},
        pass_conditions={"error": {"operator": "<=", "value": 0.0}},
        plots=[str(plot_path)],
        logs=[str(log_path)],
        root=tmp_path,
    )

    # portfolio 真实文件
    portfolio_path = tmp_path / "portfolio" / CHAPTER / "evidence.json"
    portfolio_path.parent.mkdir(parents=True, exist_ok=True)
    portfolio_path.write_text(
        json.dumps(
            {
                "chapter_id": CHAPTER,
                "passed": True,
                "metrics": {"error": 0.0},
                "evidence": {"summary": "已完成真实实验"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "root": tmp_path,
        "plot_path": plot_path,
        "log_path": log_path,
        "result_path": result_path,
        "portfolio_path": portfolio_path,
    }


def _rewrite_result(result_path: Path, **overrides) -> None:
    """重写 results JSON，覆盖指定字段。"""
    data = json.loads(result_path.read_text(encoding="utf-8"))
    data.update(overrides)
    result_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_triple_evidence_complete_passes(evidence_setup):
    # 三重证据齐全时不抛错
    _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_multiple_required_results_are_combined_with_and(evidence_setup, monkeypatch):
    monkeypatch.setitem(
        ckpt.REQUIRED_EXPERIMENT_RESULTS,
        CHAPTER,
        ("engineering_99.json", "trajectory_99.json"),
    )

    with pytest.raises(RuntimeError, match="trajectory_99.json"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_missing_plots_raises(evidence_setup):
    # 缺 plots：把 plots 数组清空
    _rewrite_result(evidence_setup["result_path"], plots=[])
    with pytest.raises(RuntimeError, match="plots"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_missing_logs_raises(evidence_setup):
    # 缺 logs：把 logs 数组清空
    _rewrite_result(evidence_setup["result_path"], logs=[])
    with pytest.raises(RuntimeError, match="logs"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_missing_portfolio_raises(evidence_setup):
    # 缺 portfolio：删除 portfolio 文件
    evidence_setup["portfolio_path"].unlink()
    with pytest.raises(RuntimeError, match="portfolio"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_plots_reference_nonexistent_file_raises(evidence_setup):
    # plots 引用了不存在的文件
    missing_plot = "plots/missing.png"
    _rewrite_result(evidence_setup["result_path"], plots=[missing_plot])
    with pytest.raises(RuntimeError, match="plots"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_logs_reference_nonexistent_file_raises(evidence_setup):
    # logs 引用了不存在的文件
    missing_log = "logs/missing.jsonl"
    _rewrite_result(evidence_setup["result_path"], logs=[missing_log])
    with pytest.raises(RuntimeError, match="logs"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_truncated_plot_is_rejected(evidence_setup):
    evidence_setup["plot_path"].write_bytes(b"\x89PNG\r\n\x1a\n")

    with pytest.raises(RuntimeError, match="plots"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


@pytest.mark.parametrize("content", ["", "not-json\n"])
def test_empty_or_invalid_jsonl_log_is_rejected(evidence_setup, content):
    evidence_setup["log_path"].write_text(content, encoding="utf-8")

    with pytest.raises(RuntimeError, match="logs"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_empty_json_portfolio_is_rejected(evidence_setup):
    evidence_setup["portfolio_path"].write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="portfolio.*空"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


@pytest.mark.parametrize(
    "payload",
    [
        {"chapter_id": CHAPTER, "passed": True, "metrics": {}, "evidence": {"summary": "完成"}},
        {"chapter_id": CHAPTER, "passed": True, "metrics": {"score": 1.0}, "evidence": {}},
        {"chapter_id": "98", "passed": True, "metrics": {"score": 1.0}, "evidence": {"summary": "完成"}},
        {"chapter_id": CHAPTER, "passed": False, "metrics": {"score": 1.0}, "evidence": {"summary": "完成"}},
    ],
)
def test_json_portfolio_requires_substantive_acceptance_fields(evidence_setup, payload):
    evidence_setup["portfolio_path"].write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="portfolio"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_markdown_portfolio_requires_heading_and_metrics(evidence_setup, monkeypatch):
    monkeypatch.setitem(ckpt.REQUIRED_PORTFOLIO_REPORTS, CHAPTER, "report.md")
    report = evidence_setup["portfolio_path"].with_name("report.md")
    report.write_text("实验完成，但没有结构化标题和指标。", encoding="utf-8")

    with pytest.raises(RuntimeError, match="portfolio"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)

    report.write_text("# 第 99 关实验报告\n\n## 指标\n\n- error: 0.0\n", encoding="utf-8")
    _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_stale_source_digest_is_rejected(evidence_setup):
    data = json.loads(evidence_setup["result_path"].read_text(encoding="utf-8"))
    data["source_state"]["source_digest"] = "f" * 64
    evidence_setup["result_path"].write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RuntimeError, match="源码.*过期|source_digest"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_nonzero_seed_evidence_is_rejected(evidence_setup):
    _rewrite_result(evidence_setup["result_path"], seed=21)

    with pytest.raises(RuntimeError, match="固定 seed=0"):
        _require_experiment_evidence(evidence_setup["root"], CHAPTER)


def test_every_required_chapter_with_lab_command_requires_its_result(tmp_path):
    with pytest.raises(RuntimeError, match="关卡 01 缺少专属实验结果"):
        _require_experiment_evidence(tmp_path, "01")
