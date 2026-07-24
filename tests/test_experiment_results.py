"""测试实验结果写入（course.results）。

覆盖场景：
- write_experiment_result 写入 JSON 产物
- 结果文件字段契约（章节、指标、时间戳）
- 重复写入与覆盖行为
"""
import json
import hashlib
from pathlib import Path

import pytest

from upkie_mujoco_course.course import results
from upkie_mujoco_course.course.results import write_experiment_result


def test_experiment_result_contains_reproducibility_contract(tmp_path):
    path = write_experiment_result(
        tmp_path / "result.json",
        chapter_id="12",
        seed=7,
        config={"controller": "classic"},
        metrics={"max_pitch_rad": 0.12},
        pass_conditions={"max_pitch_rad": {"operator": "<=", "value": 0.5}},
        plots=["outputs/plots/pitch.png"],
        videos=["outputs/videos/classic.mp4"],
        logs=["outputs/logs/classic.jsonl"],
        validate_references=False,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "2.0"
    assert data["chapter_id"] == "12"
    assert data["seed"] == 7
    assert data["passed"] is True
    assert data["metrics"]["max_pitch_rad"] == 0.12
    assert data["plots"] and data["videos"] and data["logs"]
    assert all(not Path(item).is_absolute() for key in ("plots", "videos", "logs") for item in data[key])
    assert set(data["source_state"]) == {
        "commit",
        "git_dirty",
        "tracked_diff_sha256",
        "untracked_manifest_sha256",
        "source_digest",
        "requirements_lock_sha256",
    }


def test_minimal_forged_json_is_invalid_even_when_passed_is_true():
    assessment = results.assess_experiment_result({"chapter_id": "18", "passed": True})

    assert assessment["valid"] is False
    assert assessment["status"] == "legacy"
    assert "schema_version" in " ".join(assessment["errors"])


def test_result_with_old_source_digest_is_stale(tmp_path):
    path = write_experiment_result(
        tmp_path / "result.json",
        chapter_id="18",
        seed=0,
        config={"controller": "lqr"},
        metrics={"max_pitch_rad": 0.1},
        pass_conditions={"max_pitch_rad": {"operator": "<=", "value": 0.5}},
        validate_references=False,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    data["source_state"]["source_digest"] = "0" * 64

    assessment = results.assess_experiment_result(data, current_source_state=results.capture_source_state())

    assert assessment["valid"] is False
    assert assessment["stale"] is True
    assert assessment["status"] == "stale"


def _source_digest(source_state: dict) -> str:
    payload = json.dumps(
        {
            "commit": source_state["commit"],
            "git_dirty": source_state["git_dirty"],
            "tracked_diff_sha256": source_state["tracked_diff_sha256"],
            "requirements_lock_sha256": source_state["requirements_lock_sha256"],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_untracked_manifest_change_does_not_invalidate_result(tmp_path):
    """坎1修复：未跟踪文件清单变化不得让已生成证据失效。"""

    path = write_experiment_result(
        tmp_path / "result.json",
        chapter_id="18",
        seed=0,
        config={"lab": "18"},
        metrics={"score": 1.0},
        pass_conditions={"score": {"operator": "==", "value": 1.0}},
        plots=["outputs/plots/x.png"],
        logs=["outputs/logs/x.jsonl"],
        validate_references=False,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    current = dict(data["source_state"])
    # 模拟工作区新增/变更了未跟踪文件，只有未跟踪清单指纹发生变化。
    current["untracked_manifest_sha256"] = "9" * 64

    assessment = results.assess_experiment_result(
        data, current_source_state=current, validate_references=False
    )

    assert assessment["valid"] is True
    assert assessment["stale"] is False


@pytest.mark.parametrize(
    ("field", "forged_value"),
    [
        ("commit", "forged-commit"),
        ("git_dirty", False),
        ("tracked_diff_sha256", "1" * 64),
        ("requirements_lock_sha256", "3" * 64),
    ],
)
def test_source_state_fields_cannot_be_forged_even_with_recomputed_digest(tmp_path, field, forged_value):
    path = write_experiment_result(
        tmp_path / "result.json",
        chapter_id="18",
        seed=0,
        config={"lab": "18"},
        metrics={"score": 1.0},
        pass_conditions={"score": {"operator": "==", "value": 1.0}},
        validate_references=False,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    current = dict(data["source_state"])
    if field == "git_dirty" and forged_value == current[field]:
        forged_value = not current[field]
    data["source_state"][field] = forged_value
    data["source_state"]["source_digest"] = _source_digest(data["source_state"])

    assessment = results.assess_experiment_result(data, current_source_state=current)

    assert assessment["valid"] is False
    assert assessment["stale"] is True
    assert field in " ".join(assessment["errors"])


def test_source_digest_must_match_its_own_source_state_fields(tmp_path):
    path = write_experiment_result(
        tmp_path / "result.json",
        chapter_id="18",
        seed=0,
        config={"lab": "18"},
        metrics={"score": 1.0},
        pass_conditions={"score": {"operator": "==", "value": 1.0}},
        validate_references=False,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    data["source_state"]["commit"] = "forged-commit"

    assessment = results.assess_experiment_result(
        data,
        current_source_state=dict(data["source_state"], commit="real-commit"),
    )

    assert assessment["valid"] is False
    assert "内部摘要" in " ".join(assessment["errors"])


@pytest.mark.parametrize("plot_reference", ["absolute", "parent"])
def test_write_rejects_evidence_path_outside_project_root_before_creating_result(tmp_path, plot_reference):
    root = tmp_path / "project"
    root.mkdir()
    outside_plot = tmp_path / "outside.png"
    outside_plot.write_bytes(b"png")
    inside_log = root / "result.log"
    inside_log.write_text("ok\n", encoding="utf-8")
    result_path = root / "result.json"
    reference = str(outside_plot) if plot_reference == "absolute" else "../outside.png"

    with pytest.raises((ValueError, RuntimeError), match="项目根目录"):
        write_experiment_result(
            result_path,
            chapter_id="18",
            seed=0,
            config={"lab": "18"},
            metrics={"score": 1.0},
            pass_conditions={"score": {"operator": "==", "value": 1.0}},
            plots=[reference],
            logs=[str(inside_log)],
            root=root,
        )

    assert not result_path.exists()
