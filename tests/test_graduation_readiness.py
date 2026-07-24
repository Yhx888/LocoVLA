"""测试毕业就绪报告（course.graduation）。

覆盖场景：
- build_graduation_gate_report 产出结构
- write_graduation_gate_report 写入文件
- 各关卡门控状态聚合正确
"""
import json
import hashlib
import hmac
import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest

from upkie_mujoco_course.course.graduation import build_graduation_gate_report
from upkie_mujoco_course.course.graduation import write_graduation_gate_report
from upkie_mujoco_course.course.results import write_experiment_result


def _result(chapter_id: str, passed: bool = True) -> dict:
    return {"chapter_id": chapter_id, "passed": passed, "result_path": f"outputs/results/{chapter_id}.json"}


def _valid_result(
    tmp_path,
    chapter_id: str,
    *,
    test_scope: str | None = None,
    full_config: dict | None = None,
    exit_code: float = 0.0,
) -> dict:
    plot = tmp_path / f"{chapter_id}.png"
    log = tmp_path / f"{chapter_id}.log"
    plot.write_bytes(b"png")
    log.write_text("ok\n", encoding="utf-8")
    metric = "test_exit_code" if test_scope else "score"
    config = {"lab": chapter_id}
    if test_scope:
        config = full_config or {
            "test_scope": "full",
            "command": ["python", "-m", "pytest", "-q", "tests"],
            "test_count": 299,
        }
    path = write_experiment_result(
        tmp_path / f"{chapter_id}.json",
        chapter_id=chapter_id,
        seed=0,
        config=config,
        metrics={metric: exit_code if test_scope else 1.0},
        pass_conditions={
            metric: {
                "operator": ">=" if test_scope else "==",
                "value": 0.0 if test_scope else 1.0,
            }
        },
        plots=[str(plot)],
        logs=[str(log)],
        root=tmp_path,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    data["result_path"] = str(path)
    return data


def _signed_review(path: Path, source_digest: str, secret: bytes, **overrides) -> Path:
    payload = {
        "chapter_id": "47",
        "reviewer": "课程人工评审员",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "decision": "passed",
        "source_digest": source_digest,
    }
    payload.update(overrides)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["signature"] = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_graduation_gate_report_keeps_missing_realtime_safety_review_and_defense_visible():
    report = build_graduation_gate_report([_result("18"), _result("31"), _result("37")])

    assert report["overall_passed"] is False
    assert report["gates"]["physical_metrics"]["passed"] is False
    assert report["gates"]["robustness"]["passed"] is False
    assert report["gates"]["realtime"]["passed"] is False
    assert report["gates"]["oral_defense"]["passed"] is False


def test_minimal_passed_json_cannot_self_certify_graduation():
    forged = [_result(chapter) for chapter in ("18", "31", "37", "42", "43", "44", "46", "47")]

    report = build_graduation_gate_report(forged)

    assert report["course_build_ready"] is False
    assert report["learner_graduated"] is False
    assert all(not gate["passed"] for gate in report["gates"].values())


def test_course_build_and_manual_learner_graduation_are_separate(tmp_path):
    results = [_valid_result(tmp_path, "full_pytest", test_scope="full")]
    results.extend(_valid_result(tmp_path, chapter) for chapter in ("18", "31", "42", "43", "44", "46"))
    defense = _valid_result(tmp_path, "47")
    results.append(defense)
    secret = b"test-only-review-secret"
    manual_review_path = _signed_review(
        tmp_path / "manual_review_47.json",
        defense["source_state"]["source_digest"],
        secret,
    )

    before_review = build_graduation_gate_report(results, root=tmp_path)
    defense["manual_review"] = {"passed": True}
    forged_inline_review = build_graduation_gate_report(results, root=tmp_path)
    local_file_only = build_graduation_gate_report(
        results,
        root=tmp_path,
        manual_review_path=manual_review_path,
    )
    local_signed_review = build_graduation_gate_report(
        results,
        root=tmp_path,
        manual_review_path=manual_review_path,
    )

    assert before_review["course_build_ready"] is True
    assert before_review["learner_graduated"] is False
    assert before_review["gates"]["oral_defense"]["passed"] is False
    assert forged_inline_review["learner_graduated"] is False
    assert local_file_only["learner_graduated"] is False
    assert local_signed_review["learner_graduated"] is False
    assert local_signed_review["manual_review_required"] is True
    assert local_signed_review["external_authority_required"] is True


def test_graduation_api_has_no_local_trusted_secret_escape_hatch():
    parameters = inspect.signature(build_graduation_gate_report).parameters

    assert "trusted_review_secret" not in parameters
    assert "trusted_review_key_sha256" not in parameters


@pytest.mark.parametrize(
    ("secret", "review_overrides"),
    [
        (b"wrong-secret", {}),
        (b"test-only-review-secret", {"reviewer": ""}),
    ],
)
def test_forged_signature_or_reviewer_cannot_graduate(tmp_path, secret, review_overrides):
    defense = _valid_result(tmp_path, "47")
    review_path = _signed_review(
        tmp_path / "manual_review_47.json",
        defense["source_state"]["source_digest"],
        secret,
        **review_overrides,
    )

    report = build_graduation_gate_report(
        [defense],
        root=tmp_path,
        manual_review_path=review_path,
    )

    assert report["gates"]["oral_defense"]["passed"] is False


def test_graduation_reloads_result_path_and_rejects_missing_or_forged_files(tmp_path):
    result = _valid_result(tmp_path, "18")
    result_path = result["result_path"]

    result["result_path"] = str(tmp_path / "missing.json")
    assert build_graduation_gate_report([result], root=tmp_path)["gates"]["physical_metrics"]["passed"] is False

    result["result_path"] = result_path
    Path(result_path).write_text('{"chapter_id":"18","passed":true}', encoding="utf-8")
    assert build_graduation_gate_report([result], root=tmp_path)["gates"]["physical_metrics"]["passed"] is False


@pytest.mark.parametrize(
    ("config", "exit_code"),
    [
        ({"test_scope": "full", "command": ["python", "-m", "pytest"], "test_count": 0}, 0.0),
        ({"test_scope": "full", "command": ["python", "-m", "pytest", "tests/test_vla.py"], "test_count": 8}, 0.0),
        ({"test_scope": "full", "command": ["python", "-m", "pytest", "tests"], "test_count": 299}, 1.0),
    ],
)
def test_full_pytest_requires_complete_command_count_and_zero_exit(tmp_path, config, exit_code):
    result = _valid_result(
        tmp_path,
        "full_pytest",
        test_scope="full",
        full_config=config,
        exit_code=exit_code,
    )

    report = build_graduation_gate_report([result], root=tmp_path)

    assert report["gates"]["code_tests"]["passed"] is False


def test_ordinary_experiment_json_cannot_serve_as_manual_review(tmp_path):
    defense = _valid_result(tmp_path, "47")

    report = build_graduation_gate_report(
        [defense],
        root=tmp_path,
        manual_review_path=defense["result_path"],
    )

    assert report["gates"]["oral_defense"]["passed"] is False


def test_vla_chapter_37_does_not_replace_full_pytest_evidence(tmp_path):
    results = [_valid_result(tmp_path, chapter) for chapter in ("18", "31", "37", "42", "43", "44", "46")]

    report = build_graduation_gate_report(results, root=tmp_path)

    assert report["gates"]["code_tests"]["passed"] is False
    assert "全量 pytest" in report["gates"]["code_tests"]["missing_reason"]


def test_graduation_gate_report_writes_machine_readable_evidence(tmp_path):
    path = write_graduation_gate_report(tmp_path, [_result("18"), _result("31"), _result("37")])
    report = json.loads(path.read_text(encoding="utf-8"))

    assert report["schema_version"] == "2.0"
    assert set(report["gates"]) == {
        "code_tests", "physical_metrics", "robustness", "realtime",
        "safety", "documentation", "design_review", "oral_defense",
    }
