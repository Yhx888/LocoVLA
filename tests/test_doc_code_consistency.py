"""第 44 关：文档-代码一致性测试。

测试 ``scripts/tools/check_doc_code_consistency.py`` 的核心逻辑：
  - YAML 引用已从 interface_contract.md 移除
  - 文档中引用的 JSON 配置路径真实存在
  - 文档中描述的话题名称与 control_node.cpp 一致
  - 文档中描述的服务名称与 control_node.cpp 一致
  - /safety_state 发布语义描述与代码每个 tick 发布的行为一致
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts" / "tools"
# 将 scripts/tools 加入 sys.path，便于直接 import check_doc_code_consistency
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_doc_code_consistency as checker  # noqa: E402

INTERFACE_CONTRACT = ROOT / "docs" / "design" / "interface_contract.md"
CONTROL_NODE_CPP = ROOT / "ros2_ws" / "src" / "upkie_control" / "src" / "control_node.cpp"
REPORT_PATH = ROOT / "outputs" / "results" / "doc_code_consistency_44.json"
CHECK_SCRIPT = SCRIPTS_DIR / "check_doc_code_consistency.py"
ENGINEERING_44 = ROOT / "scripts" / "run_engineering_lab_44.py"


def _load_engineering_44_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_engineering_lab_44", ENGINEERING_44)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_no_yaml_references_in_interface_contract():
    """用例 1：interface_contract.md 中不得残留任何 configs/*.yaml 路径引用。"""
    assert INTERFACE_CONTRACT.exists(), f"接口文档缺失：{INTERFACE_CONTRACT}"
    doc_text = INTERFACE_CONTRACT.read_text(encoding="utf-8")
    yaml_refs = checker.find_yaml_references(doc_text)
    assert yaml_refs == [], (
        f"interface_contract.md 中仍存在 YAML 路径引用：{yaml_refs}，"
        "应已统一修正为 JSON 路径"
    )


def test_documented_config_paths_exist():
    """用例 2：interface_contract.md 中引用的所有 JSON 配置路径必须真实存在。"""
    assert INTERFACE_CONTRACT.exists(), f"接口文档缺失：{INTERFACE_CONTRACT}"
    doc_text = INTERFACE_CONTRACT.read_text(encoding="utf-8")
    config_paths = checker.extract_config_paths_from_doc(doc_text)
    assert len(config_paths) > 0, (
        "interface_contract.md 第 9 节未提取到任何 configs/*.json 路径，"
        "请补充配置文件引用表"
    )
    missing = [p for p in config_paths if not (ROOT / p).is_file()]
    assert missing == [], f"文档引用的配置文件在仓库中不存在：{missing}"


def test_topics_in_doc_match_code():
    """用例 3：interface_contract.md 中的话题名称必须与 control_node.cpp 一致。"""
    assert INTERFACE_CONTRACT.exists(), f"接口文档缺失：{INTERFACE_CONTRACT}"
    assert CONTROL_NODE_CPP.exists(), f"控制节点源码缺失：{CONTROL_NODE_CPP}"
    doc_text = INTERFACE_CONTRACT.read_text(encoding="utf-8")
    cpp_text = CONTROL_NODE_CPP.read_text(encoding="utf-8")
    doc_topics = set(checker.extract_topics_from_doc(doc_text))
    code_topics = set(checker.extract_topics_from_cpp(cpp_text))
    # 三个核心话题必须同时出现在文档与代码中
    required_topics = {"/imu", "/wheel_torque", "/safety_state"}
    assert required_topics.issubset(doc_topics), (
        f"文档缺少核心话题：{required_topics - doc_topics}"
    )
    assert required_topics.issubset(code_topics), (
        f"代码缺少核心话题：{required_topics - code_topics}"
    )
    # 文档与代码必须完全一致（双向匹配）
    assert doc_topics == code_topics, (
        f"话题集合不一致：文档={sorted(doc_topics)}，代码={sorted(code_topics)}"
    )


def test_services_in_doc_match_code():
    """用例 4：interface_contract.md 中的服务名称必须与 control_node.cpp 一致。"""
    doc_text = INTERFACE_CONTRACT.read_text(encoding="utf-8")
    cpp_text = CONTROL_NODE_CPP.read_text(encoding="utf-8")
    doc_services = set(checker.extract_services_from_doc(doc_text))
    code_services = set(checker.extract_services_from_cpp(cpp_text))
    required_services = {"/estop", "/arm", "/reset"}
    assert required_services.issubset(doc_services), (
        f"文档缺少核心服务：{required_services - doc_services}"
    )
    assert required_services.issubset(code_services), (
        f"代码缺少核心服务：{required_services - code_services}"
    )
    assert doc_services == code_services, (
        f"服务集合不一致：文档={sorted(doc_services)}，代码={sorted(code_services)}"
    )


def test_safety_state_publish_semantics_matches_code():
    """用例 5：/safety_state 发布语义必须为每个 tick 发布，不得描述为"状态变化时"。

    代码 control_node.cpp 的 control_tick() 每个 tick 调用
    safety_state_pub_->publish(state_msg)（第 290-294 行），文档描述必须与之一致。
    """
    doc_text = INTERFACE_CONTRACT.read_text(encoding="utf-8")
    # 话题清单中 /safety_state 行不得包含"状态变化时"
    for line in doc_text.splitlines():
        if "/safety_state" in line and "状态变化时" in line:
            pytest.fail(
                f"/safety_state 行仍描述为'状态变化时'，与代码每个 tick 发布不一致：\n{line}"
            )
    # 必须包含"每个控制 tick"的语义描述
    assert "每个控制 tick" in doc_text, (
        "/safety_state 必须描述为'每个控制 tick 发布一次'"
    )


def test_engineering_44_generates_doc_consistency_evidence(tmp_path):
    output_root = tmp_path / "outputs"
    proc = subprocess.run(
        [
            sys.executable,
            str(ENGINEERING_44),
            "--output-root",
            str(output_root),
            "--source-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_44.json"
    assert result_path.is_file()
    assert (output_root / "results" / "doc_code_consistency_44.json").is_file()
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["plots"]
    for reference in result["plots"]:
        assert (tmp_path / reference).is_file(), reference


def test_check_script_writes_to_explicit_output_root(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), "--output-root", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    report_path = tmp_path / "results" / "doc_code_consistency_44.json"
    assert report_path.is_file()
    assert json.loads(report_path.read_text(encoding="utf-8"))["overall_passed"] is True


def test_check_script_runs_and_returns_zero():
    """用例 6：check_doc_code_consistency.py 必须可执行并返回退出码 0。"""
    proc = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, (
        f"一致性检查脚本退出码非 0：{proc.returncode}\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    # 报告文件必须生成
    assert REPORT_PATH.exists(), f"一致性检查报告未生成：{REPORT_PATH}"
    # 报告中 overall_passed 必须为 true
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report.get("overall_passed") is True, (
        f"一致性检查报告 overall_passed != True：{report}"
    )


@pytest.mark.parametrize("failed_stage, returncode", [("report", 7), ("consistency", 9)])
def test_engineering_44_propagates_child_failure(tmp_path, monkeypatch, failed_stage, returncode):
    """设计报告或一致性检查非零退出时，编排入口必须立即失败。"""
    module = _load_engineering_44_module()
    output_root = tmp_path / "outputs"

    def fake_run(cmd, **kwargs):
        if str(module.REPORT_SCRIPT) in cmd:
            if failed_stage == "report":
                return subprocess.CompletedProcess(cmd, returncode)
            report = output_root / "reports" / "design_review_44.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text("report", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0)
        if str(module.CONSISTENCY_SCRIPT) in cmd:
            return subprocess.CompletedProcess(cmd, returncode)
        raise AssertionError(f"不应执行后续命令：{cmd}")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_engineering_lab_44.py",
            "--output-root", str(output_root),
            "--source-root", str(tmp_path),
        ],
    )

    assert module.main() == returncode
    assert not (output_root / "results" / "engineering_44.json").exists()


def test_engineering_44_metrics_come_from_current_artifacts(tmp_path, monkeypatch):
    """设计报告与一致性产物不达标时，不得被硬编码满分覆盖。"""
    module = _load_engineering_44_module()
    output_root = tmp_path / "outputs"
    report_text = (
        "## 1. 评审摘要\n\n"
        "| 项目 | 数值 |\n|---|---|\n"
        "| 设计文档字数（估算） | 321 |\n"
        "| 文档接口覆盖率 | 66.7% |\n"
        "| 接口总数（话题+服务+参数） | 9 |\n"
        "| FMEA 风险条目数 | 3 |\n"
        "| 毕业门槛类别数 | 7 |\n"
    )
    consistency = {
        "overall_passed": True,
        "checks": [{"name": f"check_{index}", "passed": True} for index in range(7)],
        "summary": {},
    }
    real_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if str(module.REPORT_SCRIPT) in cmd:
            report = output_root / "reports" / "design_review_44.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(report_text, encoding="utf-8")
        elif str(module.CONSISTENCY_SCRIPT) in cmd:
            path = output_root / "results" / "doc_code_consistency_44.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(consistency), encoding="utf-8")
        elif str(module.PLOT_SCRIPT) in cmd:
            plots = output_root / "plots"
            plots.mkdir(parents=True, exist_ok=True)
            (plots / "engineering_44_interface_map.png").write_bytes(b"plot")
            (plots / "engineering_44_doc_coverage.png").write_bytes(b"plot")
        else:
            return real_run(cmd, **kwargs)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_engineering_lab_44.py",
            "--output-root", str(output_root),
            "--source-root", str(tmp_path),
        ],
    )

    assert module.main() == 0
    result = json.loads(
        (output_root / "results" / "engineering_44.json").read_text(encoding="utf-8")
    )
    assert result["metrics"]["doc_coverage_percent"] == 66.7
    assert result["metrics"]["interface_count"] == 9.0
    assert result["metrics"]["risk_count"] == 3.0
    assert result["metrics"]["verification_count"] == 7.0
    assert result["metrics"]["design_doc_word_count"] == 321.0
    assert result["passed"] is False
    portfolio = (
        output_root / "portfolio" / "44" / "engineering_44_report.md"
    ).read_text(encoding="utf-8")
    assert "当前文档覆盖率：66.7%" in portfolio
    assert "当前接口总数：9" in portfolio
