#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 44 关：文档-代码一致性自动检查脚本。

校验 ``docs/design/interface_contract.md`` 中描述的接口与
``ros2_ws/src/upkie_control/src/control_node.cpp`` 中的实际实现是否一致。

检查项：
  1. 文档中引用的所有配置文件路径（第 9 节"配置文件引用"）必须真实存在；
  2. 文档中描述的话题名称必须与 C++ 代码中的 ``create_publisher`` /
     ``create_subscription`` 调用一致；
  3. 文档中描述的服务名称必须与 C++ 代码中的 ``create_service`` 调用一致；
  4. 文档中不得残留 ``*.yaml`` 路径引用（项目自 v2 起统一使用 JSON 配置）。

输出：
  - JSON 报告：``outputs/results/doc_code_consistency_44.json``
  - 退出码：0=一致，1=不一致

Windows 端运行：
  .\\.venv\\Scripts\\python.exe scripts\\tools\\check_doc_code_consistency.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# 仓库根目录（本脚本位于 scripts/tools/ 下，上溯两级即根）
ROOT = Path(__file__).resolve().parents[2]

# 待校验文件路径
INTERFACE_CONTRACT = ROOT / "docs" / "design" / "interface_contract.md"
CONTROL_NODE_CPP = ROOT / "ros2_ws" / "src" / "upkie_control" / "src" / "control_node.cpp"

# 输出报告路径
OUTPUT_REPORT = ROOT / "outputs" / "results" / "doc_code_consistency_44.json"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """单条检查结果。"""

    name: str
    passed: bool
    detail: str = ""
    expected: Any = None
    actual: Any = None


@dataclass
class ConsistencyReport:
    """一致性检查报告。"""

    checked_at: str
    overall_passed: bool = False
    checks: list[CheckResult] = field(default_factory=list)
    doc_topics: list[str] = field(default_factory=list)
    code_topics: list[str] = field(default_factory=list)
    doc_services: list[str] = field(default_factory=list)
    code_services: list[str] = field(default_factory=list)
    doc_config_paths: list[str] = field(default_factory=list)
    missing_config_paths: list[str] = field(default_factory=list)
    yaml_references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转字典（用于序列化为 JSON）。"""
        return {
            "checked_at": self.checked_at,
            "overall_passed": self.overall_passed,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "detail": c.detail,
                    "expected": c.expected,
                    "actual": c.actual,
                }
                for c in self.checks
            ],
            "summary": {
                "doc_topics": self.doc_topics,
                "code_topics": self.code_topics,
                "doc_services": self.doc_services,
                "code_services": self.code_services,
                "doc_config_paths": self.doc_config_paths,
                "missing_config_paths": self.missing_config_paths,
                "yaml_references": self.yaml_references,
            },
        }


# ---------------------------------------------------------------------------
# 文档解析
# ---------------------------------------------------------------------------


def _normalize_topic_name(name: str) -> str:
    """规整话题/服务名：去反引号、去首尾空白，确保带前导 /。"""
    s = name.strip().strip("`").strip()
    if not s.startswith("/"):
        s = "/" + s
    return s


def extract_topics_from_doc(doc_text: str) -> list[str]:
    """从 interface_contract.md 的话题清单表提取话题名。

    话题清单位于 ``## 1. 话题清单`` 章节下，第一列是话题名（如 ``/imu``）。
    """
    topics: list[str] = []
    seen: set[str] = set()
    lines = doc_text.splitlines()
    in_section = False
    in_table = False
    for line in lines:
        if line.startswith("## 1. 话题清单"):
            in_section = True
            in_table = False
            continue
        if in_section and line.startswith("## "):
            # 进入下一节，结束
            break
        if not in_section:
            continue
        stripped = line.strip()
        if stripped.startswith("|") and "---" not in stripped and "名称" not in stripped:
            # 表格数据行（跳过分隔行与表头行）
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if cells:
                name = _normalize_topic_name(cells[0])
                # 只接受 / 开头的合法话题名
                if name.startswith("/") and name not in seen:
                    seen.add(name)
                    topics.append(name)
            in_table = True
        elif in_table and not stripped.startswith("|"):
            # 表格结束
            break
    return topics


def extract_services_from_doc(doc_text: str) -> list[str]:
    """从 interface_contract.md 的服务清单表提取服务名。"""
    services: list[str] = []
    seen: set[str] = set()
    lines = doc_text.splitlines()
    in_section = False
    in_table = False
    for line in lines:
        if line.startswith("## 2. 服务清单"):
            in_section = True
            in_table = False
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section:
            continue
        stripped = line.strip()
        if stripped.startswith("|") and "---" not in stripped and "名称" not in stripped:
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if cells:
                name = _normalize_topic_name(cells[0])
                if name.startswith("/") and name not in seen:
                    seen.add(name)
                    services.append(name)
            in_table = True
        elif in_table and not stripped.startswith("|"):
            break
    return services


def extract_config_paths_from_doc(doc_text: str) -> list[str]:
    """从 interface_contract.md 第 9 节"配置文件引用"提取配置文件路径。

    匹配反引号包裹的 ``configs/...`` 路径。
    """
    paths: list[str] = []
    seen: set[str] = set()
    # 定位第 9 节范围
    lines = doc_text.splitlines()
    start_idx = -1
    end_idx = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("## 9."):
            start_idx = i + 1
        elif start_idx >= 0 and line.startswith("## "):
            end_idx = i
            break
    if start_idx < 0:
        return paths
    section_text = "\n".join(lines[start_idx:end_idx])
    # 匹配反引号内的 configs/xxx/xxx.json 路径
    for m in re.finditer(r"`(configs/[^\s`]+\.json)`", section_text):
        path = m.group(1)
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def find_yaml_references(doc_text: str) -> list[str]:
    """在文档中查找所有 *.yaml 或 *.yml 路径引用（用于回归检查）。"""
    refs: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"`?(configs/[^\s`]+\.ya?ml)`?", doc_text):
        ref = m.group(1)
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs


# ---------------------------------------------------------------------------
# C++ 代码解析
# ---------------------------------------------------------------------------


def extract_topics_from_cpp(cpp_text: str) -> list[str]:
    """从 control_node.cpp 提取话题名（create_publisher + create_subscription）。"""
    topics: list[str] = []
    seen: set[str] = set()
    pattern = re.compile(
        r'create_(?:publisher|subscription)<[^>]+>\s*\(\s*"([^"]+)"'
    )
    for m in pattern.finditer(cpp_text):
        name = m.group(1)
        if not name.startswith("/"):
            name = "/" + name
        if name not in seen:
            seen.add(name)
            topics.append(name)
    return topics


def extract_services_from_cpp(cpp_text: str) -> list[str]:
    """从 control_node.cpp 提取服务名（create_service）。"""
    services: list[str] = []
    seen: set[str] = set()
    pattern = re.compile(r'create_service<[^>]+>\s*\(\s*"([^"]+)"')
    for m in pattern.finditer(cpp_text):
        name = m.group(1)
        if not name.startswith("/"):
            name = "/" + name
        if name not in seen:
            seen.add(name)
            services.append(name)
    return services


# ---------------------------------------------------------------------------
# 主检查流程
# ---------------------------------------------------------------------------


def run_consistency_check() -> ConsistencyReport:
    """执行全部一致性检查，返回报告对象。"""
    from datetime import datetime, timezone

    report = ConsistencyReport(checked_at=datetime.now(timezone.utc).isoformat())

    # 文件存在性检查
    if not INTERFACE_CONTRACT.exists():
        report.checks.append(
            CheckResult(
                name="interface_contract_exists",
                passed=False,
                detail=f"接口文档不存在：{INTERFACE_CONTRACT}",
            )
        )
        report.overall_passed = False
        return report
    report.checks.append(
        CheckResult(
            name="interface_contract_exists",
            passed=True,
            detail=f"接口文档存在：{INTERFACE_CONTRACT}",
        )
    )

    if not CONTROL_NODE_CPP.exists():
        report.checks.append(
            CheckResult(
                name="control_node_cpp_exists",
                passed=False,
                detail=f"控制节点源码不存在：{CONTROL_NODE_CPP}",
            )
        )
        report.overall_passed = False
        return report
    report.checks.append(
        CheckResult(
            name="control_node_cpp_exists",
            passed=True,
            detail=f"控制节点源码存在：{CONTROL_NODE_CPP}",
        )
    )

    doc_text = INTERFACE_CONTRACT.read_text(encoding="utf-8")
    cpp_text = CONTROL_NODE_CPP.read_text(encoding="utf-8")

    # 提取接口
    report.doc_topics = extract_topics_from_doc(doc_text)
    report.code_topics = extract_topics_from_cpp(cpp_text)
    report.doc_services = extract_services_from_doc(doc_text)
    report.code_services = extract_services_from_cpp(cpp_text)
    report.doc_config_paths = extract_config_paths_from_doc(doc_text)
    report.yaml_references = find_yaml_references(doc_text)

    # 检查 1：话题名称一致性（文档与代码必须双向匹配）
    doc_topics_set = set(report.doc_topics)
    code_topics_set = set(report.code_topics)
    topics_match = doc_topics_set == code_topics_set
    missing_in_doc = sorted(code_topics_set - doc_topics_set)
    missing_in_code = sorted(doc_topics_set - code_topics_set)
    report.checks.append(
        CheckResult(
            name="topics_consistency",
            passed=topics_match,
            detail=(
                "话题名称文档与代码一致"
                if topics_match
                else f"文档缺少 {missing_in_doc}；代码缺少 {missing_in_code}"
            ),
            expected=sorted(doc_topics_set),
            actual=sorted(code_topics_set),
        )
    )

    # 检查 2：服务名称一致性
    doc_services_set = set(report.doc_services)
    code_services_set = set(report.code_services)
    services_match = doc_services_set == code_services_set
    missing_svc_in_doc = sorted(code_services_set - doc_services_set)
    missing_svc_in_code = sorted(doc_services_set - code_services_set)
    report.checks.append(
        CheckResult(
            name="services_consistency",
            passed=services_match,
            detail=(
                "服务名称文档与代码一致"
                if services_match
                else f"文档缺少 {missing_svc_in_doc}；代码缺少 {missing_svc_in_code}"
            ),
            expected=sorted(doc_services_set),
            actual=sorted(code_services_set),
        )
    )

    # 检查 3：配置文件路径存在性
    report.missing_config_paths = [
        p for p in report.doc_config_paths if not (ROOT / p).is_file()
    ]
    config_check_passed = (
        len(report.doc_config_paths) > 0 and len(report.missing_config_paths) == 0
    )
    report.checks.append(
        CheckResult(
            name="config_paths_exist",
            passed=config_check_passed,
            detail=(
                f"全部 {len(report.doc_config_paths)} 个配置文件路径真实存在"
                if config_check_passed
                else (
                    f"缺失配置文件：{report.missing_config_paths}"
                    if report.missing_config_paths
                    else "未在文档中找到任何 configs/*.json 引用"
                )
            ),
            expected=report.doc_config_paths,
            actual=[
                p for p in report.doc_config_paths if (ROOT / p).is_file()
            ],
        )
    )

    # 检查 4：YAML 引用回归（文档中不应残留 YAML 路径）
    yaml_check_passed = len(report.yaml_references) == 0
    report.checks.append(
        CheckResult(
            name="no_yaml_references",
            passed=yaml_check_passed,
            detail=(
                "文档中未残留任何 YAML 路径引用"
                if yaml_check_passed
                else f"文档中仍存在 YAML 路径引用：{report.yaml_references}"
            ),
            expected=[],
            actual=report.yaml_references,
        )
    )

    # 检查 5：/safety_state 发布语义（必须为每 tick 发布，非"状态变化时"）
    safety_state_correct = (
        "每个控制 tick" in doc_text
        and "状态变化时" not in doc_text.replace("## ", "")
    )
    # 严格判断：话题清单中 /safety_state 行不应出现"状态变化时"
    safety_line_correct = True
    for line in doc_text.splitlines():
        if "/safety_state" in line and "状态变化时" in line:
            safety_line_correct = False
            break
    safety_state_passed = safety_state_correct and safety_line_correct
    report.checks.append(
        CheckResult(
            name="safety_state_publish_semantics",
            passed=safety_state_passed,
            detail=(
                "/safety_state 发布语义为每个控制 tick 发布一次（100Hz）"
                if safety_state_passed
                else "/safety_state 发布语义描述与代码不一致（代码每个 tick 发布）"
            ),
            expected="每个控制 tick 发布一次（100Hz）",
            actual="见 docs/design/interface_contract.md 话题清单",
        )
    )

    # 总体通过条件：所有检查均通过
    report.overall_passed = all(c.passed for c in report.checks)
    return report


def main() -> int:
    """入口：执行检查、写报告、返回退出码。"""
    parser = argparse.ArgumentParser(description="检查第 44 关文档与代码一致性")
    parser.add_argument("--output-root", default="outputs")
    args = parser.parse_args()
    requested_root = Path(args.output_root)
    output_root = requested_root if requested_root.is_absolute() else ROOT / requested_root
    output_report = output_root / "results" / "doc_code_consistency_44.json"
    report = run_consistency_check()

    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 控制台打印摘要
    print(f"[INFO] 检查报告已写入：{output_report}")
    print(f"[INFO] 总体结果：{'通过' if report.overall_passed else '不一致'}")
    for c in report.checks:
        status = "[OK]" if c.passed else "[FAIL]"
        print(f"  {status} {c.name}: {c.detail}")

    return 0 if report.overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
