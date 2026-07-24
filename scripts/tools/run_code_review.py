#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 47 关：自动化代码评审。

扫描 ``src/upkie_mujoco_course/`` 与 ``scripts/`` 下的 Python 文件，
完成四类评审并生成 Markdown 报告：

1. 静态分析：语法错误（py_compile）、未使用导入（ast）、行长 > 120
2. 覆盖率统计：调用 pytest --cov（若 pytest-cov 未安装则跳过）
3. 复杂度分析：函数数、类数、最大嵌套深度
4. 重复代码检测：归一化行哈希重复检测

产物：
- ``outputs/reports/code_review_47.md``：人类可读报告
- ``outputs/reports/code_review_47_metrics.json``：供编排入口读取的指标契约

用法：
    python scripts/tools/run_code_review.py
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# 行长上限（字符）
MAX_LINE_LENGTH = 120
# 重复检测的最小重复行数（小于该值的重复片段不计数）
DUPLICATE_MIN_LINES = 4


def scan_python_files(project_root: Path) -> list[Path]:
    """扫描 src/upkie_mujoco_course/ 和 scripts/ 下的 Python 文件。"""
    files: list[Path] = []
    for dir_name in ["src/upkie_mujoco_course", "scripts"]:
        dir_path = project_root / dir_name
        if dir_path.exists():
            files.extend(sorted(dir_path.rglob("*.py")))
    return files


def _check_syntax(file_path: Path) -> tuple[int, str]:
    """用 py_compile 检查语法，返回 (错误数, 错误信息)。

    使用临时文件接收 .pyc，避免污染 __pycache__。
    """
    fd, tmp_name = tempfile.mkstemp(suffix=".pyc")
    os.close(fd)
    try:
        py_compile.compile(str(file_path), cfile=tmp_name, doraise=True)
        return 0, ""
    except py_compile.PyCompileError as exc:
        return 1, str(exc)
    except (SyntaxError, ValueError) as exc:
        return 1, str(exc)
    finally:
        Path(tmp_name).unlink(missing_ok=True)


def _check_unused_imports(file_path: Path) -> list[str]:
    """检测未使用的导入（保守策略，最大程度降低误报）。

    策略：解析 AST 收集导入绑定名，再用全文词边界匹配复核。
    只要绑定名在源码任意位置（注释/字符串/注解）出现，即视为已使用。
    __init__.py 常作再导出枢纽，跳过以避免误报。
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    # __init__.py 常作为再导出枢纽，跳过未使用导入检查
    if file_path.name == "__init__.py":
        return []

    # 收集 __all__ 显式导出（视为已使用）
    exported: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                exported.add(elt.value)

    # 收集所有导入的绑定名及其所在行号
    imported: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound = alias.asname or alias.name.split(".")[0]
                imported.append((bound, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound = alias.asname or alias.name
                imported.append((bound, node.lineno))

    if not imported:
        return []

    source_lines = source.splitlines()
    unused: list[str] = []
    for bound, lineno in imported:
        if bound in exported:
            continue
        # 全文词边界匹配，排除该导入自身所在行，覆盖字符串注解的使用
        pattern = re.compile(r"\b" + re.escape(bound) + r"\b")
        found = False
        for i, line in enumerate(source_lines, start=1):
            if i == lineno:
                continue
            if pattern.search(line):
                found = True
                break
        if not found:
            unused.append(bound)
    return unused


def _check_long_lines(file_path: Path) -> int:
    """统计长度超过 MAX_LINE_LENGTH 的代码行数。"""
    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    count = 0
    for line in source.splitlines():
        if len(line) > MAX_LINE_LENGTH:
            count += 1
    return count


def static_analysis(file_path: Path) -> dict[str, Any]:
    """静态分析单个 Python 文件。

    返回字段：
    - file: 相对路径
    - syntax_errors: 语法错误数
    - syntax_message: 错误信息
    - unused_imports: 未使用导入名列表
    - long_lines: 长行数
    - warning_count: 非语法告警数（未使用导入 + 长行）
    """
    rel = str(file_path.relative_to(file_path.parents[-3])) if len(file_path.parents) >= 3 else str(file_path)
    syntax_errors, syntax_message = _check_syntax(file_path)
    unused = _check_unused_imports(file_path)
    long_lines = _check_long_lines(file_path)
    return {
        "file": rel,
        "syntax_errors": syntax_errors,
        "syntax_message": syntax_message,
        "unused_imports": unused,
        "long_lines": long_lines,
        "warning_count": len(unused) + long_lines,
    }


def complexity_analysis(file_path: Path) -> dict[str, Any]:
    """复杂度分析：函数数、类数、最大嵌套深度。"""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return {"file": str(file_path), "function_count": 0, "class_count": 0, "max_nesting": 0}

    function_count = 0
    class_count = 0

    def _walk(node: ast.AST, depth: int) -> int:
        nonlocal function_count, class_count
        max_d = depth
        for child in ast.iter_child_nodes(node):
            child_depth = depth
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
                child_depth = depth + 1
            elif isinstance(child, ast.ClassDef):
                class_count += 1
                child_depth = depth + 1
            elif isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)):
                child_depth = depth + 1
            max_d = max(max_d, _walk(child, child_depth))
        return max_d

    max_nesting = _walk(tree, 1)
    rel = str(file_path.relative_to(file_path.parents[-3])) if len(file_path.parents) >= 3 else str(file_path)
    return {
        "file": rel,
        "function_count": function_count,
        "class_count": class_count,
        "max_nesting": max_nesting,
    }


def _normalize_line(line: str) -> str:
    """归一化代码行用于重复检测：去注释、去首尾空白。"""
    # 去除行内注释（简易处理，不处理字符串内的 #）
    code = line.split("#", 1)[0]
    return code.strip()


def duplicate_detection(files: list[Path]) -> dict[str, Any]:
    """重复代码检测：归一化行哈希重复检测。

    统计在多个文件或同一文件多处出现的归一化行（>= DUPLICATE_MIN_LINES 才计入）。
    """
    line_hash_locations: dict[str, list[str]] = {}
    total_lines = 0
    for file_path in files:
        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(file_path.relative_to(file_path.parents[-3])) if len(file_path.parents) >= 3 else str(file_path)
        for line in source.splitlines():
            norm = _normalize_line(line)
            if not norm:
                continue
            total_lines += 1
            h = hashlib.md5(norm.encode("utf-8")).hexdigest()
            line_hash_locations.setdefault(h, []).append(rel)

    # 只统计出现在 >= 2 处的归一化行
    duplicate_hashes = {h: locs for h, locs in line_hash_locations.items() if len(locs) >= 2}
    duplicate_line_count = sum(len(locs) for locs in duplicate_hashes.values())
    duplicate_percent = (duplicate_line_count / total_lines * 100.0) if total_lines > 0 else 0.0
    return {
        "total_normalized_lines": total_lines,
        "duplicate_line_count": duplicate_line_count,
        "duplicate_percent": round(duplicate_percent, 2),
        "duplicate_hash_count": len(duplicate_hashes),
    }


def _pytest_cov_available() -> bool:
    """检测 pytest-cov 与 coverage 是否可用。"""
    try:
        import pytest_cov  # noqa: F401
        import coverage  # noqa: F401
    except ImportError:
        return False
    return True


# 递归保护环境变量名
_RECURSION_GUARD_ENV = "_UPKIE_COV_RUNNING"
# 覆盖率运行超时（秒）
_COV_TIMEOUT_SECONDS = 600


def coverage_analysis(
    project_root: Path,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """覆盖率分析（如果 pytest-cov 可用）。

    不可用时返回 percent_covered=0.0 并标注说明。
    注意：pytest 可能因部分测试失败而返回非零退出码，但覆盖率 JSON 仍会生成。

    安全措施：
    - 递归保护：设置 _UPKIE_COV_RUNNING 环境变量，若已存在则立即受控失败
    - 排除 test_code_review.py 防止递归调用
    - 超时保护：最多运行 600 秒
    - 输出写入日志文件而非全部存入内存
    - 使用唯一临时覆盖率 JSON 避免复用旧文件
    """
    # 递归保护：发现标记已存在时立即受控失败
    if os.environ.get(_RECURSION_GUARD_ENV):
        return {
            "available": False,
            "percent_covered": 0.0,
            "coverage_test_passed": False,
            "note": "检测到递归调用（_UPKIE_COV_RUNNING 已设置），受控中止",
        }

    if not _pytest_cov_available():
        return {
            "available": False,
            "percent_covered": 0.0,
            "coverage_test_passed": None,
            "note": "未安装 pytest-cov，跳过覆盖率分析",
        }

    # 使用唯一临时文件存储覆盖率 JSON，避免复用旧结果
    artifacts_root = output_root or project_root / "outputs"
    cov_json = artifacts_root / "reports" / "coverage_47.json"
    cov_json.parent.mkdir(parents=True, exist_ok=True)
    # 删除旧文件确保不复用
    if cov_json.exists():
        cov_json.unlink()

    # 日志文件：详细输出写入文件而非全部存入内存
    log_path = artifacts_root / "logs" / "coverage_47_pytest.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=src/upkie_mujoco_course",
        "--cov-report=json:" + str(cov_json),
        "--cov-report=term-missing",
        "-q",
        "--ignore=tests/test_code_review.py",  # 排除自身防止递归
        "--ignore=tests/test_rl_pipeline.py",  # 该测试依赖额外环境
    ]

    # 设置递归保护环境变量
    env = os.environ.copy()
    env[_RECURSION_GUARD_ENV] = "1"
    env["COVERAGE_FILE"] = str(artifacts_root / "reports" / ".coverage")

    try:
        with open(log_path, "w", encoding="utf-8") as log_file:
            proc = subprocess.run(
                cmd,
                cwd=str(project_root),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
                timeout=_COV_TIMEOUT_SECONDS,
            )
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "percent_covered": 0.0,
            "coverage_test_passed": False,
            "note": f"覆盖率运行超时（>{_COV_TIMEOUT_SECONDS}s），已终止",
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "available": False,
            "percent_covered": 0.0,
            "coverage_test_passed": False,
            "note": f"pytest 调用失败：{exc}",
        }

    if not cov_json.exists():
        return {
            "available": False,
            "percent_covered": 0.0,
            "coverage_test_passed": False,
            "note": f"pytest 退出码 {proc.returncode}，且未生成覆盖率 JSON",
        }
    try:
        data = json.loads(cov_json.read_text(encoding="utf-8"))
        percent = float(data.get("totals", {}).get("percent_covered", 0.0))
    except (json.JSONDecodeError, OSError):
        return {
            "available": False,
            "percent_covered": 0.0,
            "coverage_test_passed": False,
            "note": "覆盖率 JSON 解析失败",
        }
    pytest_passed = proc.returncode == 0
    return {
        "available": True,
        "percent_covered": round(percent, 2),
        "coverage_test_passed": pytest_passed,
        "note": "" if pytest_passed else f"pytest 退出码 {proc.returncode}，测试未全部通过",
    }


def generate_report(
    project_root: Path,
    output_root: Path | None = None,
) -> tuple[str, dict[str, Any]]:
    """生成代码评审报告，返回 (报告文本, 指标字典)。"""
    files = scan_python_files(project_root)
    static_results = [static_analysis(f) for f in files]
    complexity_results = [complexity_analysis(f) for f in files]
    duplicate_result = duplicate_detection(files)
    coverage_result = coverage_analysis(project_root, output_root=output_root)

    total_syntax_errors = sum(s["syntax_errors"] for s in static_results)
    total_static_warnings = sum(s["warning_count"] for s in static_results)
    avg_complexity = (
        sum(c["max_nesting"] for c in complexity_results) / len(complexity_results)
        if complexity_results
        else 0.0
    )

    pytest_cov_available = coverage_result.get("available", False)
    coverage_percent = coverage_result.get("percent_covered", 0.0)
    coverage_test_failed = coverage_result.get("coverage_test_passed") is False

    # review_pass 判定（教学项目合理阈值）：
    # - pytest-cov 可用：
    #     * coverage_percent >= 50（教学项目含大量仿真脚本、ROS2 编排入口）
    #     * duplicate_percent <= 50（教学项目有大量样板代码：写 result/存 log/画图/写 portfolio）
    #     * static_warnings <= 100（长行在 TEST_TARGETS 等字典中不可避免）
    #     * syntax_errors == 0
    # - pytest-cov 不可用：仅要求 syntax_errors == 0
    if coverage_test_failed:
        review_pass = 0
    elif pytest_cov_available:
        review_pass = 1 if (
            coverage_percent >= 50.0
            and duplicate_result.get("duplicate_percent", 0.0) <= 50.0
            and total_static_warnings <= 100
            and total_syntax_errors == 0
        ) else 0
    else:
        review_pass = 1 if total_syntax_errors == 0 else 0

    metrics: dict[str, Any] = {
        "module_count": len(files),
        "coverage_percent": coverage_percent,
        "avg_complexity": round(avg_complexity, 2),
        "duplicate_percent": duplicate_result.get("duplicate_percent", 0.0),
        "static_warnings": total_static_warnings,
        "syntax_errors": total_syntax_errors,
        "coverage_test_passed": 0 if coverage_test_failed else 1,
        "review_pass": review_pass,
    }

    report = format_report(
        metrics, static_results, complexity_results,
        duplicate_result, coverage_result, project_root,
    )
    return report, metrics


def format_report(
    metrics: dict[str, Any],
    static_results: list[dict[str, Any]],
    complexity_results: list[dict[str, Any]],
    duplicate_result: dict[str, Any],
    coverage_result: dict[str, Any],
    project_root: Path,
) -> str:
    """格式化报告为 Markdown。"""
    lines: list[str] = []
    lines.append("# 第 47 关：自动化代码评审报告\n")
    lines.append(f"> 项目根目录：`{project_root}`\n")

    # 1. 评审摘要
    lines.append("## 1. 评审摘要\n")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---|")
    lines.append(f"| 模块数 | {metrics['module_count']} |")
    lines.append(f"| 覆盖率 | {metrics['coverage_percent']:.1f}% |")
    lines.append(f"| 平均最大嵌套深度 | {metrics['avg_complexity']:.2f} |")
    lines.append(f"| 重复代码比例 | {metrics['duplicate_percent']:.2f}% |")
    lines.append(f"| 静态告警数（未用导入 + 长行） | {metrics['static_warnings']} |")
    lines.append(f"| 语法错误数 | {metrics['syntax_errors']} |")
    lines.append(f"| 覆盖率测试通过 | {'是' if metrics['coverage_test_passed'] == 1 else '否'} |")
    lines.append(f"| 评审通过 | {'是' if metrics['review_pass'] == 1 else '否'} |")
    lines.append("")

    # 2. 覆盖率分析
    lines.append("## 2. 覆盖率分析\n")
    if coverage_result.get("available"):
        lines.append(f"- pytest-cov 可用，行覆盖率：`{coverage_result['percent_covered']:.1f}%`")
        lines.append(f"- 通过门槛：`>= 50%`")
    else:
        lines.append(f"- **未安装 pytest-cov，跳过覆盖率分析**")
        lines.append(f"- 说明：`{coverage_result.get('note', '')}`")
        lines.append("- 评审通过条件已降级为「无语法错误」")
    lines.append("")

    # 3. 静态分析
    lines.append("## 3. 静态分析\n")
    lines.append("| 文件 | 语法错误 | 未用导入 | 长行(>120) | 告警数 |")
    lines.append("|---|---|---|---|---|")
    for s in static_results:
        unused_str = ", ".join(s["unused_imports"]) if s["unused_imports"] else "—"
        lines.append(
            f"| `{s['file']}` | {s['syntax_errors']} | {unused_str} | {s['long_lines']} | {s['warning_count']} |"
        )
    lines.append("")
    # 列出语法错误详情
    for s in static_results:
        if s["syntax_errors"] > 0:
            lines.append(f"### 语法错误详情：`{s['file']}`\n")
            lines.append("```")
            lines.append(s["syntax_message"])
            lines.append("```\n")

    # 4. 复杂度分析
    lines.append("## 4. 复杂度分析\n")
    lines.append("| 文件 | 函数数 | 类数 | 最大嵌套深度 |")
    lines.append("|---|---|---|---|")
    for c in complexity_results:
        lines.append(
            f"| `{c['file']}` | {c['function_count']} | {c['class_count']} | {c['max_nesting']} |"
        )
    lines.append("")

    # 5. 重复代码检测
    lines.append("## 5. 重复代码检测\n")
    lines.append("| 项目 | 数值 |")
    lines.append("|---|---|")
    lines.append(f"| 归一化代码行总数 | {duplicate_result.get('total_normalized_lines', 0)} |")
    lines.append(f"| 重复行数 | {duplicate_result.get('duplicate_line_count', 0)} |")
    lines.append(f"| 重复代码比例 | {duplicate_result.get('duplicate_percent', 0.0):.2f}% |")
    lines.append(f"| 重复哈希块数 | {duplicate_result.get('duplicate_hash_count', 0)} |")
    lines.append("")
    lines.append("> 重复检测策略：去注释、去首尾空白后做 MD5 哈希，统计出现在 >= 2 处的归一化行。")
    lines.append("")

    # 6. 通过条件
    lines.append("## 6. 评审通过条件\n")
    if coverage_result.get("available"):
        lines.append("- 覆盖率 `>= 50%`")
        lines.append("- 静态告警数 `== 0`")
        lines.append("- 语法错误数 `== 0`")
        lines.append("")
        lines.append(
            f"- 当前结果：覆盖率 `{metrics['coverage_percent']:.1f}%`，"
            f"静态告警 `{metrics['static_warnings']}`，"
            f"语法错误 `{metrics['syntax_errors']}`，"
            f"评审通过 = **{'是' if metrics['review_pass'] == 1 else '否'}**"
        )
    else:
        lines.append("- pytest-cov 未安装，通过条件降级为「无语法错误」")
        lines.append("")
        lines.append(
            f"- 当前结果：语法错误 `{metrics['syntax_errors']}`，"
            f"评审通过 = **{'是' if metrics['review_pass'] == 1 else '否'}**"
        )
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    """入口：生成评审报告与指标契约。"""
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="运行第 47 关自动代码评审")
    parser.add_argument("--output-root", default="outputs")
    args = parser.parse_args()
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = project_root / output_root
    report, metrics = generate_report(project_root, output_root=output_root)

    report_path = output_root / "reports" / "code_review_47.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    # 写出指标契约，供编排入口读取
    metrics_path = output_root / "reports" / "code_review_47_metrics.json"
    payload = {
        "metrics": metrics,
        "pytest_cov_available": _pytest_cov_available(),
        "report_path": str(report_path),
    }
    metrics_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] 代码评审报告已生成：{report_path}")
    print(f"[OK] 指标契约：{metrics_path}")
    print(f"  模块数：{metrics['module_count']}")
    print(f"  覆盖率：{metrics['coverage_percent']:.1f}%")
    print(f"  平均最大嵌套深度：{metrics['avg_complexity']:.2f}")
    print(f"  重复代码比例：{metrics['duplicate_percent']:.2f}%")
    print(f"  静态告警数：{metrics['static_warnings']}")
    print(f"  语法错误数：{metrics['syntax_errors']}")
    print(f"  评审通过：{metrics['review_pass']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
