"""测试课程检查点（checkpoint）产物与字体配置。

覆盖场景：
- 检查点 JSON 产物字段契约
- matplotlib 字体管理器可加载中文字体
- 检查点编号与课程章节一致
"""
import json
from pathlib import Path
import sys

from matplotlib import font_manager
import pytest

from upkie_mujoco_course.course.checkpoint import STATUS_FONT_FAMILY
from upkie_mujoco_course.course.checkpoint import run_chapter_checkpoint
from scripts import course_checkpoint


def test_planned_chapter_cannot_be_marked_complete(tmp_path):
    # 第 44 关已建设完成，改用 H02（仍处于 planned 状态）验证拒绝逻辑
    with pytest.raises(RuntimeError, match="尚未建设完成"):
        run_chapter_checkpoint("H02", output_root=tmp_path)


def test_engineering_checkpoint_requires_real_lab_evidence(tmp_path):
    with pytest.raises(RuntimeError, match="缺少专属实验结果"):
        run_chapter_checkpoint("38", output_root=tmp_path, learner_completion=False)
    with pytest.raises(RuntimeError, match="缺少专属实验结果"):
        run_chapter_checkpoint("39", output_root=tmp_path, learner_completion=False)
    with pytest.raises(RuntimeError, match="缺少专属实验结果"):
        run_chapter_checkpoint("41", output_root=tmp_path, learner_completion=False)


def test_ready_chapter_runs_real_test_and_writes_result(tmp_path, recwarn):
    result_path = run_chapter_checkpoint(
        "19",
        output_root=tmp_path,
        learner_completion=False,
        source_root=tmp_path,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["metrics"]["test_exit_code"] == 0
    assert (tmp_path / "logs" / "checkpoint_19.log").exists()
    assert not [warning for warning in recwarn if "Glyph" in str(warning.message)]


def test_checkpoint_plot_font_has_normal_weight_without_fallback():
    # 选定的中文字体必须真实存在、且不回退到 matplotlib 默认拉丁字体（否则中文会变成豆腐块）。
    # 跨平台：Windows 解析到 simhei.ttf，Linux/CI 解析到已安装的开源 CJK 字体。
    path = font_manager.findfont(
        font_manager.FontProperties(family=STATUS_FONT_FAMILY, weight="normal"),
        fallback_to_default=False,
    )
    assert "dejavu" not in Path(path).name.lower()


def test_run_checkpoint_defaults_to_learner_prerequisite_gate(tmp_path):
    with pytest.raises(RuntimeError, match="先修未完成"):
        run_chapter_checkpoint("19", output_root=tmp_path)


def _passed_result(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"passed": true, "config": {}, "logs": []}', encoding="utf-8")
    return path


def test_course_checkpoint_cli_defaults_to_learner_mode(tmp_path, monkeypatch):
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "progress.json").write_text(
        '{"chapters":{"01":{"completed_checkpoints":["验收"],"evidence":[]}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(course_checkpoint, "ROOT", tmp_path)
    monkeypatch.setattr(
        course_checkpoint,
        "load_experiment_results",
        lambda _root: [{"chapter_id": "02", "passed": True, "acceptance_valid": True, "contract_status": "current"}],
        raising=False,
    )

    def fake_run(chapter, **kwargs):
        assert chapter == "03"
        assert kwargs["output_root"] == tmp_path / "outputs"
        assert kwargs["source_root"] == tmp_path
        assert kwargs["learner_completion"] is True
        assert kwargs["completed_chapters"] == {"02"}
        raise RuntimeError("学习者先修未完成: 02")

    monkeypatch.setattr(course_checkpoint, "run_chapter_checkpoint", fake_run)
    monkeypatch.setattr(sys, "argv", ["course_checkpoint.py", "--chapter", "03"])

    with pytest.raises(SystemExit, match="先修未完成"):
        course_checkpoint.main()


def test_course_checkpoint_cli_engineering_build_explicitly_bypasses_prerequisites(tmp_path, monkeypatch):
    monkeypatch.setattr(course_checkpoint, "ROOT", tmp_path)
    result_path = _passed_result(tmp_path / "outputs" / "results" / "checkpoint_19.json")

    def fake_run(chapter, **kwargs):
        assert chapter == "19"
        assert kwargs["learner_completion"] is False
        return result_path

    monkeypatch.setattr(course_checkpoint, "run_chapter_checkpoint", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        ["course_checkpoint.py", "--chapter", "19", "--engineering-build"],
    )

    course_checkpoint.main()


def test_course_checkpoint_cli_forwards_custom_roots_and_reads_selected_output(
    tmp_path, monkeypatch
):
    output_root = tmp_path / "fresh" / "outputs"
    source_root = tmp_path / "source"
    result_path = _passed_result(output_root / "results" / "checkpoint_03.json")
    observed = {}

    def fake_load(root):
        observed["loaded_root"] = root
        return [
            {
                "chapter_id": "02",
                "passed": True,
                "acceptance_valid": True,
                "contract_status": "current",
            }
        ]

    def fake_run(chapter, **kwargs):
        observed["chapter"] = chapter
        observed.update(kwargs)
        return result_path

    monkeypatch.setattr(course_checkpoint, "ROOT", tmp_path)
    monkeypatch.setattr(course_checkpoint, "load_experiment_results", fake_load)
    monkeypatch.setattr(course_checkpoint, "run_chapter_checkpoint", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "course_checkpoint.py",
            "--chapter",
            "03",
            "--output-root",
            str(Path("fresh") / "outputs"),
            "--source-root",
            str(source_root),
        ],
    )

    course_checkpoint.main()

    assert observed["loaded_root"] == output_root
    assert observed["chapter"] == "03"
    assert observed["output_root"] == output_root
    assert observed["source_root"] == source_root
    assert observed["completed_chapters"] == {"02"}


def test_course_checkpoint_cli_accepts_only_fixed_seed_and_headless(tmp_path, monkeypatch):
    result_path = _passed_result(tmp_path / "outputs" / "results" / "checkpoint_03.json")
    monkeypatch.setattr(course_checkpoint, "ROOT", tmp_path)
    monkeypatch.setattr(course_checkpoint, "load_experiment_results", lambda _root: [])
    monkeypatch.setattr(course_checkpoint, "run_chapter_checkpoint", lambda *_args, **_kwargs: result_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["course_checkpoint.py", "--chapter", "03", "--seed", "0", "--no-viewer"],
    )
    course_checkpoint.main()

    monkeypatch.setattr(
        sys,
        "argv",
        ["course_checkpoint.py", "--chapter", "03", "--seed", "7", "--no-viewer"],
    )
    with pytest.raises(SystemExit):
        course_checkpoint.main()
