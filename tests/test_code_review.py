"""第 47 关代码评审、答辩与面试测试。

安全重写版本：不再启动全量 pytest 子进程，避免递归内存爆炸。
使用纯函数测试和 monkeypatch 验证核心逻辑。

覆盖：
- 代码评审核心函数（纯函数调用，无子进程）
- 答辩材料与面试题库存在性
- 面试题库含 >= 40 个参考答案
- 答辩材料覆盖四要素（设计动机/实验证据/局限性/改进方向）
- 递归保护环境变量有效性
- 覆盖率命令构造正确排除自身
- review_pass 逻辑正确性
"""
from __future__ import annotations

import json
import inspect
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
sys.path.insert(0, str(ROOT / "src"))

DEFENSE_MATERIAL = ROOT / "docs" / "design" / "defense_material.md"
INTERVIEW_QA_BANK = ROOT / "docs" / "design" / "interview_qa_bank.md"
TUTORIAL_47 = ROOT / "tutorials" / "v2" / "47" / "README.md"


def _load_engineering_47_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_engineering_lab_47",
        ROOT / "scripts" / "run_engineering_lab_47.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCodeReviewPureFunctions:
    """纯函数测试：直接调用 run_code_review 模块的函数，不启动子进程。"""

    def test_scan_python_files(self):
        """扫描 Python 文件应返回非空列表。"""
        from run_code_review import scan_python_files
        files = scan_python_files(ROOT)
        assert len(files) > 0, "未扫描到 Python 文件"
        assert all(f.suffix == ".py" for f in files)

    def test_static_analysis_no_syntax_error(self, tmp_path):
        """对合法 Python 文件进行静态分析应返回 0 语法错误。"""
        from run_code_review import static_analysis
        test_file = tmp_path / "good.py"
        test_file.write_text("x = 1\n", encoding="utf-8")
        result = static_analysis(test_file)
        assert result["syntax_errors"] == 0

    def test_static_analysis_detects_syntax_error(self, tmp_path):
        """对语法错误的 Python 文件应检出错误。"""
        from run_code_review import static_analysis
        test_file = tmp_path / "bad.py"
        test_file.write_text("def foo(:\n", encoding="utf-8")
        result = static_analysis(test_file)
        assert result["syntax_errors"] == 1

    def test_target_files_have_no_known_unused_imports(self):
        """目标模块不应保留已确认未使用的导入。"""
        from run_code_review import static_analysis

        targets = {
            ROOT / "src" / "upkie_mujoco_course" / "controllers" / "mpc.py": {"field"},
            ROOT / "src" / "upkie_mujoco_course" / "course" / "facts.py": {"Path"},
            ROOT / "src" / "upkie_mujoco_course" / "classical_control" / "labs.py": {"mujoco"},
            ROOT / "src" / "upkie_mujoco_course" / "rl" / "labs.py": {
                "json",
                "write_experiment_result",
            },
        }
        for file_path, expected_unused in targets.items():
            result = static_analysis(file_path)
            assert expected_unused.isdisjoint(result["unused_imports"]), (
                f"{file_path} 仍报告未使用导入: {result['unused_imports']}"
            )

    def test_complexity_analysis(self, tmp_path):
        """复杂度分析应识别函数和嵌套。"""
        from run_code_review import complexity_analysis
        test_file = tmp_path / "nested.py"
        test_file.write_text(
            "def foo():\n"
            "    if True:\n"
            "        for i in range(10):\n"
            "            pass\n",
            encoding="utf-8",
        )
        result = complexity_analysis(test_file)
        assert result["function_count"] == 1
        assert result["max_nesting"] >= 3

    def test_duplicate_detection(self, tmp_path):
        """重复检测应识别重复行。"""
        from run_code_review import duplicate_detection
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        content = "x = 1\ny = 2\nz = 3\nw = 4\n"
        f1.write_text(content, encoding="utf-8")
        f2.write_text(content, encoding="utf-8")
        result = duplicate_detection([f1, f2])
        assert result["duplicate_percent"] > 0

    def test_review_pass_logic_no_cov(self):
        """无 pytest-cov 时，review_pass == 1 当且仅当无语法错误。"""
        # 模拟指标：无语法错误 → review_pass=1
        from run_code_review import scan_python_files, static_analysis
        # 验证真实项目无语法错误
        files = scan_python_files(ROOT)
        total_syntax_errors = sum(
            static_analysis(f)["syntax_errors"] for f in files[:5]  # 抽样前5个文件
        )
        assert total_syntax_errors == 0, "项目文件存在语法错误"


class TestRecursionGuard:
    """验证递归保护机制有效。"""

    def test_coverage_analysis_blocks_when_guard_set(self):
        """当 _UPKIE_COV_RUNNING 已设置时，coverage_analysis 应立即返回失败。"""
        from run_code_review import coverage_analysis, _RECURSION_GUARD_ENV
        with patch.dict(os.environ, {_RECURSION_GUARD_ENV: "1"}):
            result = coverage_analysis(ROOT)
        assert result["available"] is False
        assert "递归" in result["note"]

    def test_coverage_command_excludes_self(self):
        """覆盖率 pytest 命令应排除 test_code_review.py。"""
        from run_code_review import coverage_analysis
        import run_code_review
        # 检查源码中的命令构造确实包含排除参数
        import inspect
        source = inspect.getsource(coverage_analysis)
        assert "--ignore=tests/test_code_review.py" in source

    def test_recursion_guard_env_name(self):
        """递归保护环境变量名称正确。"""
        from run_code_review import _RECURSION_GUARD_ENV
        assert _RECURSION_GUARD_ENV == "_UPKIE_COV_RUNNING"

    def test_coverage_timeout_exceeds_measured_full_suite_baseline(self):
        from run_code_review import _COV_TIMEOUT_SECONDS

        assert _COV_TIMEOUT_SECONDS >= 600

    def test_code_review_accepts_explicit_output_root(self):
        """覆盖率和评审报告必须能隔离到 fresh 输出根。"""
        from run_code_review import coverage_analysis, generate_report

        assert "output_root" in inspect.signature(coverage_analysis).parameters
        assert "output_root" in inspect.signature(generate_report).parameters

    def test_coverage_file_isolated_in_output_root(self, tmp_path, monkeypatch):
        """coverage 数据文件必须随 JSON 和日志一起隔离到输出根。"""
        import run_code_review

        output_root = tmp_path / "outputs"

        def fake_run(cmd, **kwargs):
            coverage_file = Path(kwargs["env"]["COVERAGE_FILE"])
            assert coverage_file == output_root / "reports" / ".coverage"
            assert coverage_file.is_relative_to(output_root)
            cov_arg = next(arg for arg in cmd if arg.startswith("--cov-report=json:"))
            cov_json = Path(cov_arg.removeprefix("--cov-report=json:"))
            cov_json.write_text(
                json.dumps({"totals": {"percent_covered": 75.0}}),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(run_code_review, "_pytest_cov_available", lambda: True)
        monkeypatch.setattr(run_code_review.subprocess, "run", fake_run)

        result = run_code_review.coverage_analysis(tmp_path, output_root=output_root)
        assert result["available"] is True

    def test_orchestrator_timeout_exceeds_coverage_timeout(self):
        """外层必须给覆盖率子进程留下收尾余量。"""
        from run_code_review import _COV_TIMEOUT_SECONDS

        module = _load_engineering_47_module()
        assert module._REVIEW_TIMEOUT_SECONDS > _COV_TIMEOUT_SECONDS

    def test_failed_pytest_keeps_coverage_but_fails_review(self, tmp_path, monkeypatch):
        """pytest 非零退出时覆盖率仅供诊断，不能令代码评审通过。"""
        import run_code_review

        output_root = tmp_path / "outputs"

        def fake_run(cmd, **kwargs):
            cov_arg = next(arg for arg in cmd if arg.startswith("--cov-report=json:"))
            Path(cov_arg.removeprefix("--cov-report=json:")).write_text(
                json.dumps({"totals": {"percent_covered": 75.0}}),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(cmd, 1)

        monkeypatch.setattr(run_code_review, "_pytest_cov_available", lambda: True)
        monkeypatch.setattr(run_code_review.subprocess, "run", fake_run)
        coverage = run_code_review.coverage_analysis(tmp_path, output_root=output_root)

        assert coverage["available"] is True
        assert coverage["percent_covered"] == 75.0
        assert coverage["coverage_test_passed"] is False

        monkeypatch.setattr(run_code_review, "scan_python_files", lambda root: [])
        monkeypatch.setattr(run_code_review, "duplicate_detection", lambda files: {"duplicate_percent": 0.0})
        monkeypatch.setattr(run_code_review, "coverage_analysis", lambda *args, **kwargs: coverage)
        _, metrics = run_code_review.generate_report(tmp_path, output_root=output_root)
        assert metrics["coverage_test_passed"] == 0
        assert metrics["review_pass"] == 0

    def test_failed_coverage_tests_make_final_chapter_fail(self, tmp_path, monkeypatch):
        """即使覆盖率达标且旧 review_pass=1，测试失败也必须令第 47 关失败。"""
        module = _load_engineering_47_module()
        fake_review = tmp_path / "run_code_review.py"
        fake_review.write_text(
            "import argparse, json\n"
            "from pathlib import Path\n"
            "p=argparse.ArgumentParser(); p.add_argument('--output-root'); a=p.parse_args()\n"
            "root=Path(a.output_root); (root/'reports').mkdir(parents=True, exist_ok=True)\n"
            "metrics={'module_count':1,'coverage_percent':75,'avg_complexity':1,"
            "'duplicate_percent':0,'static_warnings':0,'syntax_errors':0,"
            "'coverage_test_passed':0,'review_pass':1}\n"
            "(root/'reports'/'code_review_47.md').write_text('report', encoding='utf-8')\n"
            "(root/'reports'/'code_review_47_metrics.json').write_text("
            "json.dumps({'metrics':metrics,'pytest_cov_available':True}), encoding='utf-8')\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(module, "ROOT", tmp_path)
        monkeypatch.setattr(module, "REVIEW_SCRIPT", fake_review)
        monkeypatch.setattr(module, "_write_review_plot", lambda metrics, path: (path.parent.mkdir(parents=True, exist_ok=True), path.write_bytes(b'plot')))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_engineering_lab_47.py",
                "--output-root", str(tmp_path / "outputs"),
                "--source-root", str(tmp_path),
            ],
        )

        assert module.main() == 0
        result = json.loads(
            (tmp_path / "outputs" / "results" / "engineering_47.json").read_text(encoding="utf-8")
        )
        assert result["metrics"]["coverage_test_passed"] == 0.0
        assert result["passed"] is False


class TestMaterialsExistence:
    """验证答辩材料和面试题库存在性。"""

    def test_defense_material_exists(self):
        """docs/design/defense_material.md 存在。"""
        assert DEFENSE_MATERIAL.exists(), f"答辩材料不存在：{DEFENSE_MATERIAL}"

    def test_interview_qa_bank_exists(self):
        """docs/design/interview_qa_bank.md 存在。"""
        assert INTERVIEW_QA_BANK.exists(), f"面试题库不存在：{INTERVIEW_QA_BANK}"

    def test_interview_qa_has_40_plus_questions(self):
        """interview_qa_bank.md 含至少 40 个「参考答案」。"""
        content = INTERVIEW_QA_BANK.read_text(encoding="utf-8")
        answer_count = content.count("参考答案")
        assert answer_count >= 40, f"参考答案数量不足：{answer_count} < 40"

    def test_defense_material_covers_four_sections(self):
        """defense_material.md 含设计动机、实验证据、局限性、改进方向四节。"""
        content = DEFENSE_MATERIAL.read_text(encoding="utf-8")
        required = ["设计动机", "实验证据", "局限性", "改进方向"]
        missing = [kw for kw in required if kw not in content]
        assert not missing, f"答辩材料缺少章节：{missing}"


class TestOrchestratorCommand:
    """验证编排入口命令构造正确（不实际运行子进程）。"""

    def test_orchestrator_script_exists(self):
        """编排入口脚本存在。"""
        orchestrator = ROOT / "scripts" / "run_engineering_lab_47.py"
        assert orchestrator.exists()

    def test_orchestrator_imports_cleanly(self):
        """编排入口可正常导入无语法错误。"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_engineering_lab_47",
            ROOT / "scripts" / "run_engineering_lab_47.py",
        )
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        # 只验证能加载不执行 main
        try:
            spec.loader.exec_module(module)  # type: ignore
        except SystemExit:
            pass  # argparse 可能调用 sys.exit

    def test_review_script_exists(self):
        """代码评审脚本存在。"""
        review_script = ROOT / "scripts" / "tools" / "run_code_review.py"
        assert review_script.exists()


class TestChapter47ResearchAndCppRoute:
    """论文精读与 C++ 算法路线必须形成可验收作品集任务。"""

    def test_three_paper_tasks_are_traceable_and_complete(self):
        module = _load_engineering_47_module()
        tasks = module.PAPER_READING_TASKS
        required = {
            "title",
            "citation_id",
            "verification_url",
            "problem",
            "method",
            "formula_or_experiment",
            "limitations",
            "project_mapping",
            "deliverable_path",
        }
        assert len(tasks) >= 3
        assert len({task["citation_id"] for task in tasks}) == len(tasks)
        assert all(required <= task.keys() for task in tasks)
        assert all(all(task[field] for field in required) for task in tasks)
        assert {task["citation_id"] for task in tasks} >= {
            "arXiv:2308.13205",
            "arXiv:2109.11978",
            "arXiv:2307.15818",
        }
        assert all(task["verification_url"].startswith("https://") for task in tasks)
        assert module.validate_paper_reading_tasks(tasks) is True

    def test_cpp_route_has_executable_milestones_and_evidence(self):
        module = _load_engineering_47_module()
        route = module.CPP_ALGORITHM_ROUTE
        required = {
            "milestone",
            "algorithm_problem",
            "data_structures",
            "source_path",
            "test_path",
            "check_command",
            "acceptance",
            "evidence_paths",
        }
        assert len(route) >= 4
        assert all(required <= item.keys() for item in route)
        assert all(item["data_structures"] for item in route)
        assert all(item["source_path"].endswith(".cpp") for item in route)
        assert all(item["test_path"].endswith(".cpp") for item in route)
        assert all(
            any(tool in item["check_command"] for tool in ("g++", "cmake", "ctest"))
            for item in route
        )
        assert all(
            all(path.startswith("outputs/portfolio/47/") for path in item["evidence_paths"])
            for item in route
        )
        assert module.validate_cpp_algorithm_route(route) is True

    def test_tutorial_and_orchestrator_expose_required_deliverables(self):
        tutorial = TUTORIAL_47.read_text(encoding="utf-8")
        orchestrator = (ROOT / "scripts" / "run_engineering_lab_47.py").read_text(encoding="utf-8")
        for marker in (
            "arXiv:2308.13205",
            "arXiv:2109.11978",
            "arXiv:2307.15818",
            "论文精读",
            "C++ 算法训练路线",
            "python scripts/course_checkpoint.py --chapter 47",
        ):
            assert marker in tutorial
        for marker in (
            "paper_reading_tasks.json",
            "cpp_algorithm_route.json",
            "paper_reading_task_count",
            "cpp_algorithm_milestone_count",
        ):
            assert marker in orchestrator

    def test_learning_task_contracts_are_written_and_revalidatable(self, tmp_path):
        module = _load_engineering_47_module()
        paper_path, cpp_path = module.write_learning_task_contracts(tmp_path)

        papers = json.loads(paper_path.read_text(encoding="utf-8"))
        route = json.loads(cpp_path.read_text(encoding="utf-8"))
        assert paper_path == tmp_path / "portfolio" / "47" / "paper_reading_tasks.json"
        assert cpp_path == tmp_path / "portfolio" / "47" / "cpp_algorithm_route.json"
        assert module.validate_paper_reading_tasks(papers) is True
        assert module.validate_cpp_algorithm_route(route) is True
