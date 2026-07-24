"""测试课程清单（course.manifest）与进度管理。

覆盖场景：
- 课程清单覆盖所有必需章节
- CourseProgress 进度计算正确
- 章节先修关系与命令配置一致
"""
from upkie_mujoco_course.course.manifest import load_course_manifest
from upkie_mujoco_course.course.progress import CourseProgress


def test_course_manifest_covers_all_required_chapters():
    manifest = load_course_manifest()
    assert manifest["version"] == "0.3.0"
    chapter_ids = [chapter["id"] for chapter in manifest["chapters"]]
    assert len(chapter_ids) == 58
    assert len(set(chapter_ids)) == 58
    assert chapter_ids[:3] == ["00", "01", "02"]
    assert chapter_ids[47] == "47"
    assert chapter_ids[-2:] == ["H09", "H10"]
    by_id = {chapter["id"]: chapter for chapter in manifest["chapters"]}
    for chapter_id in ["01", "02", "03", "04", "05"]:
        assert by_id[chapter_id]["status"] == "ready"
        assert by_id[chapter_id]["commands"][0] == (
            f"python scripts/run_foundation_lab.py --chapter {chapter_id}"
        )
    assert by_id["11"]["status"] == "ready"
    assert by_id["11"]["commands"][0] == "python scripts/11_model_contract_lab.py"
    for chapter_id in ["13", "14", "15", "16", "18"]:
        assert by_id[chapter_id]["status"] == "ready"
        assert by_id[chapter_id]["commands"][0] == (
            f"python scripts/run_classical_control_lab.py --chapter {chapter_id}"
        )
    for chapter_id in ["20", "21", "22", "23"]:
        assert by_id[chapter_id]["status"] == "ready"
        assert by_id[chapter_id]["commands"][0] == (
            f"python scripts/run_estimation_optimization_lab.py --chapter {chapter_id}"
        )
    for chapter_id in ["27", "31"]:
        assert by_id[chapter_id]["status"] == "ready"
        assert by_id[chapter_id]["commands"][0] == (
            f"python scripts/run_rl_lab.py --chapter {chapter_id}"
        )
    assert by_id["H01"]["status"] == "ready"
    assert by_id["H01"]["prerequisites"] == []
    assert by_id["H01"]["commands"][0] == "python scripts/run_hardware_audit.py --chapter H01"
    assert by_id["38"]["status"] == "ready"
    assert by_id["38"]["commands"][0] == "python scripts/run_engineering_lab.py --chapter 38"
    assert by_id["39"]["status"] == "ready"
    assert by_id["39"]["commands"][0] == "python scripts/run_engineering_lab.py --chapter 39"
    assert by_id["41"]["status"] == "ready"
    assert by_id["36"]["status"] == "ready"
    assert by_id["37"]["status"] == "ready"
    for chapter in manifest["chapters"]:
        assert {
            "id",
            "stage",
            "title",
            "task",
            "commands",
            "checkpoints",
            "acceptance",
            "visualizations",
            "portfolio",
            "completion",
            "prerequisites",
        } <= set(chapter)
        assert chapter["completion"]["required_evidence"] == ["test", "log", "visual"]


def test_course_progress_records_checkpoint_and_stage_completion(tmp_path):
    path = tmp_path / "progress.json"
    progress = CourseProgress(path)
    progress.complete_checkpoint("00", "环境检查", evidence="pytest 通过")
    restored = CourseProgress(path)
    assert restored.chapter_status("00")["completed_checkpoints"] == ["环境检查"]
    assert restored.chapter_status("00")["evidence"] == ["pytest 通过"]
