"""测试硬件审计模块（hardware 章节）。

覆盖场景：
- 仓库快照审计（audit_repository_snapshot）产出结构
- run_hardware_audit 命令行入口
- 审计报告字段契约
"""
import json

from upkie_mujoco_course.hardware.audit import audit_repository_snapshot
from upkie_mujoco_course.hardware.audit import run_hardware_audit
from upkie_mujoco_course.course.checkpoint import REQUIRED_EXPERIMENT_RESULTS
from upkie_mujoco_course.course.checkpoint import REQUIRED_PORTFOLIO_REPORTS


def _snapshot():
    return {
        "commit": "abc123",
        "default_branch": "master",
        "root_paths": ["README.md", "3.Software/wl_pro_robot/main.ino"],
        "readme": "ESP32, L6234PD013TR, AS5600, MPU6050, 4 PCB, 3 GH1.25 4PIN",
        "source_headers": ["// MIT License\n// Copyright 2024 Mu Shibo"],
    }


def test_h01_audit_blocks_procurement_when_root_license_and_bom_evidence_are_incomplete():
    audit = audit_repository_snapshot(_snapshot())

    assert audit["root_license_present"] is False
    assert audit["procurement_freeze_approved"] is False
    assert audit["procurement_freeze_reason"]
    assert audit["source_mit_header_ratio"] == 1.0
    assert audit["bom_items"][0]["evidence_status"] == "README 已提及，实际目录未找到"


def test_h01_lab_writes_a_real_audit_result_with_frozen_procurement(tmp_path, recwarn):
    result_path = run_hardware_audit(
        "H01",
        output_root=tmp_path,
        source_root=tmp_path,
        snapshot=_snapshot(),
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["passed"] is True
    assert result["metrics"]["procurement_freeze_blocked"] == 1.0
    assert (tmp_path / result["plots"][0]).is_file()
    assert (tmp_path / result["logs"][0]).is_file()
    assert (tmp_path / "portfolio" / "H01" / "evidence.json").is_file()
    portfolio = json.loads(
        (tmp_path / "portfolio" / "H01" / "evidence.json").read_text(encoding="utf-8")
    )
    assert portfolio["passed"] is True
    assert not recwarn


def test_h01_checkpoint_requires_hardware_audit_evidence():
    assert REQUIRED_EXPERIMENT_RESULTS["H01"] == "hardware_H01.json"
    assert REQUIRED_PORTFOLIO_REPORTS["H01"] == "evidence.json"
