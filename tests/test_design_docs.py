"""第 44 关设计文档评审测试。

覆盖：
- system_design.md 与 interface_contract.md 存在
- system_design.md 覆盖需求/接口/风险/验证证据四层
- interface_contract.md 覆盖话题/服务/参数关键字
- 设计评审报告脚本可生成 outputs/reports/design_review_44.md
- system_design.md 含 8 类毕业门槛关键字
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN_DIR = ROOT / "docs" / "design"
SYSTEM_DESIGN = DESIGN_DIR / "system_design.md"
INTERFACE_CONTRACT = DESIGN_DIR / "interface_contract.md"
REPORT_SCRIPT = ROOT / "scripts" / "tools" / "generate_design_review_report.py"


def test_system_design_exists():
    """system_design.md 必须存在。"""
    assert SYSTEM_DESIGN.exists(), f"设计文档缺失：{SYSTEM_DESIGN}"


def test_interface_contract_exists():
    """interface_contract.md 必须存在。"""
    assert INTERFACE_CONTRACT.exists(), f"接口契约缺失：{INTERFACE_CONTRACT}"


def test_system_design_covers_four_layers():
    """system_design.md 必须覆盖需求层、接口层、风险层、验证证据层四个章节。"""
    text = SYSTEM_DESIGN.read_text(encoding="utf-8")
    required_layers = ["需求层", "接口层", "风险层", "验证证据层"]
    missing = [layer for layer in required_layers if layer not in text]
    assert not missing, f"system_design.md 缺少章节：{missing}"


def test_interface_contract_covers_topics():
    """interface_contract.md 必须覆盖 /imu、/wheel_torque、/safety_state 三个话题。"""
    text = INTERFACE_CONTRACT.read_text(encoding="utf-8")
    required_topics = ["/imu", "/wheel_torque", "/safety_state"]
    missing = [t for t in required_topics if t not in text]
    assert not missing, f"interface_contract.md 缺少话题：{missing}"


def test_interface_contract_covers_services():
    """interface_contract.md 必须覆盖 /estop、/arm、/reset 三个服务。"""
    text = INTERFACE_CONTRACT.read_text(encoding="utf-8")
    required_services = ["/estop", "/arm", "/reset"]
    missing = [s for s in required_services if s not in text]
    assert not missing, f"interface_contract.md 缺少服务：{missing}"


def test_interface_contract_covers_parameters():
    """interface_contract.md 必须覆盖 record_log、log_path、episode_id、pitch_safety_limit 参数。"""
    text = INTERFACE_CONTRACT.read_text(encoding="utf-8")
    required_params = ["record_log", "log_path", "episode_id", "pitch_safety_limit"]
    missing = [p for p in required_params if p not in text]
    assert not missing, f"interface_contract.md 缺少参数：{missing}"


def test_design_review_report_generated_in_explicit_output_root(tmp_path):
    """设计评审报告必须写入显式 fresh 输出根。"""
    proc = subprocess.run(
        [
            sys.executable,
            str(REPORT_SCRIPT),
            "--output-root",
            str(tmp_path),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, f"报告生成失败：{proc.stderr}"
    report_output = tmp_path / "reports" / "design_review_44.md"
    assert report_output.exists(), f"设计评审报告未生成：{report_output}"
    report_text = report_output.read_text(encoding="utf-8")
    # 报告必须包含评审摘要与评审结论两个章节
    assert "评审摘要" in report_text, "报告缺少评审摘要章节"
    assert "评审结论" in report_text, "报告缺少评审结论章节"


def test_graduation_gates_documented():
    """system_design.md 必须含 8 类毕业门槛关键字。"""
    text = SYSTEM_DESIGN.read_text(encoding="utf-8")
    required_gates = [
        "code_tests",
        "physical_metrics",
        "robustness",
        "realtime",
        "safety",
        "documentation",
        "design_review",
        "oral_defense",
    ]
    missing = [g for g in required_gates if g not in text]
    assert not missing, f"system_design.md 缺少毕业门槛关键字：{missing}"
