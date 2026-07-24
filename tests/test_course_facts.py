"""测试课程事实（course.facts）一致性检查。

覆盖场景：
- 课程清单与教程目录的事实一致
- check_course_facts 返回通过
- 关键事实（章节数、关卡数）匹配
"""
from pathlib import Path

from upkie_mujoco_course.course.facts import check_course_facts


def test_course_facts_have_no_local_drift():
    assert check_course_facts() == []


def test_ci_runs_tests_compile_and_fact_check():
    path = Path(".github/workflows/ci.yml")
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "pytest" in text
    assert "compileall" in text
    assert "check_course_facts.py" in text


def test_status_documents_separate_course_build_from_learner_graduation():
    readme = Path("README.md").read_text(encoding="utf-8")
    syllabus = Path("docs/SYLLABUS.md").read_text(encoding="utf-8")
    handoff = Path("docs/guides/CONTINUATION_HANDOFF.md").read_text(encoding="utf-8")

    combined = "\n".join([readme, syllabus, handoff])
    assert "学习者毕业需要仓库外部人工答辩" in combined
    assert "8/8 `passed=true`" not in combined
    assert "全部 48 个必修关卡 checkpoint 均已通过" not in combined
    assert "飞书 00-47 文档已存在" in handoff
    assert "文件夹中共 48 篇正文已逐章回读" in handoff
    assert "learner_graduated=false" in handoff


def test_ros2_documentation_matches_built_test_counts_and_start_command():
    dependencies = Path("docs/guides/DEPENDENCIES.md").read_text(encoding="utf-8")
    system_design = Path("docs/design/system_design.md").read_text(encoding="utf-8")
    defense = Path("docs/design/defense_material.md").read_text(encoding="utf-8")
    interview = Path("docs/design/interview_qa_bank.md").read_text(encoding="utf-8")
    tutorial = Path("tutorials/v2/43/README.md").read_text(encoding="utf-8")

    assert "控制节点通信与安全门控测试（14 项 gtest）" in dependencies
    assert "日志契约与 CSV 导出测试（10 项 gtest）" in dependencies
    assert "安全状态机纯函数测试（15 项 gtest）" in dependencies
    assert "ros2 run upkie_control control_node" in system_design
    assert "upkie.launch.py" not in system_design
    assert "状态机 15 测试" in defense
    assert "安全测试覆盖 15 个 gtest" in interview
    assert "--gtest-count" not in tutorial
    assert "15 个 gtest" in tutorial


def test_engineering_entrypoints_accept_fixed_seed_argument():
    scripts = (
        "run_engineering_lab_40.py",
        "run_engineering_lab_41.py",
        "run_engineering_lab_42.py",
        "run_engineering_lab_43.py",
        "run_engineering_lab_44.py",
        "run_capstone_project.py",
        "run_engineering_lab_46.py",
        "run_engineering_lab_47.py",
    )
    for filename in scripts:
        source = (Path("scripts") / filename).read_text(encoding="utf-8")
        assert 'add_argument("--seed", type=int, default=0' in source
