#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 47 关：基于 token 序列的重复代码检测。

使用 Python ast 模块解析源码，将每个函数/方法的 token 序列归一化后比较，
检测跨文件和文件内的重复代码块。比单纯行哈希更准确，能识别变量重命名后的重复。

产物：outputs/results/duplicates_47.json
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
import tokenize
import io
from collections import defaultdict
from pathlib import Path
from typing import Any


def scan_python_files(project_root: Path) -> list[Path]:
    """扫描 src/upkie_mujoco_course/ 下的 Python 文件。"""
    target = project_root / "src" / "upkie_mujoco_course"
    if not target.exists():
        return []
    return sorted(target.rglob("*.py"))


def extract_token_sequence(source: str) -> list[str]:
    """提取源码的 token 类型序列（归一化，不含字面值）。

    将 NAME token 统一为 "N"，NUMBER 统一为 "NUM"，STRING 统一为 "STR"，
    保留操作符和关键字。这样能检测变量重命名后的重复代码。
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError):
        return []
    seq: list[str] = []
    for tok in tokens:
        ttype = tok.type
        tstring = tok.string
        if ttype == tokenize.NAME and tstring not in {
            "def", "class", "if", "elif", "else", "while", "for", "in",
            "try", "except", "finally", "with", "as", "return", "yield",
            "import", "from", "pass", "break", "continue", "raise", "assert",
            "global", "nonlocal", "lambda", "and", "or", "not", "is", "del",
            "True", "False", "None", "async", "await", "self", "cls",
        }:
            seq.append("N")  # 普通标识符归一化为 N
        elif ttype == tokenize.NUMBER:
            seq.append("NUM")
        elif ttype == tokenize.STRING:
            seq.append("STR")
        elif ttype in (tokenize.OP, tokenize.NAME):
            seq.append(tstring)
        # 忽略 COMMENT, NL, NEWLINE, INDENT, DEDENT, ENDMARKER
    return seq


def extract_functions(source: str, file_path: str) -> list[dict[str, Any]]:
    """提取文件中所有函数/方法，返回 token 序列和位置信息。"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    functions: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 提取函数体源码片段
            try:
                seg = ast.get_source_segment(source, node)
                if seg is None:
                    continue
            except Exception:
                continue
            tokens = extract_token_sequence(seg)
            if len(tokens) < 10:  # 太短的函数不参与重复检测
                continue
            token_hash = hashlib.md5("|".join(tokens).encode("utf-8")).hexdigest()
            functions.append({
                "file": file_path,
                "name": node.name,
                "lineno": node.lineno,
                "end_lineno": node.end_lineno or node.lineno,
                "line_count": (node.end_lineno or node.lineno) - node.lineno + 1,
                "token_count": len(tokens),
                "token_hash": token_hash,
            })
    return functions


def detect_duplicates(project_root: Path) -> dict[str, Any]:
    """检测重复代码：基于归一化 token 序列的函数级重复检测。"""
    files = scan_python_files(project_root)
    all_functions: list[dict[str, Any]] = []
    total_lines = 0

    for file_path in files:
        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(file_path.relative_to(project_root)).replace("\\", "/")
        total_lines += len(source.splitlines())
        funcs = extract_functions(source, rel)
        all_functions.extend(funcs)

    # 按 token_hash 分组，找出重复的函数组
    hash_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for func in all_functions:
        hash_groups[func["token_hash"]].append(func)

    # 重复组：同一 token_hash 出现在 >= 2 处
    duplicate_groups = {
        h: locs for h, locs in hash_groups.items() if len(locs) >= 2
    }

    # 统计重复行数（每个重复组的第一个实例不算重复，其余算）
    duplicate_line_count = 0
    duplicate_function_count = 0
    duplicate_details: list[dict[str, Any]] = []
    for h, locs in duplicate_groups.items():
        # 第一个实例不算重复
        for loc in locs[1:]:
            duplicate_line_count += loc["line_count"]
            duplicate_function_count += 1
        duplicate_details.append({
            "hash": h[:12],
            "locations": [
                {"file": loc["file"], "name": loc["name"],
                 "line": loc["lineno"], "lines": loc["line_count"]}
                for loc in locs
            ],
        })

    # 重复率 = 重复行数 / 总行数 * 100
    duplicate_percent = (duplicate_line_count / total_lines * 100.0) if total_lines > 0 else 0.0

    return {
        "method": "token_sequence_hash",
        "total_files": len(files),
        "total_functions": len(all_functions),
        "total_lines": total_lines,
        "duplicate_function_count": duplicate_function_count,
        "duplicate_line_count": duplicate_line_count,
        "duplicate_percent": round(duplicate_percent, 2),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_details": sorted(
            duplicate_details,
            key=lambda d: d["locations"][0]["lines"],
            reverse=True,
        )[:20],  # 只保留最大的 20 组用于报告
    }


def main() -> int:
    """入口：运行重复检测并写出结果。"""
    project_root = Path(__file__).resolve().parents[2]
    result = detect_duplicates(project_root)
    output = project_root / "outputs" / "results" / "duplicates_47.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 重复检测完成：{output}")
    print(f"  总文件数：{result['total_files']}")
    print(f"  总函数数：{result['total_functions']}")
    print(f"  总行数：{result['total_lines']}")
    print(f"  重复函数数：{result['duplicate_function_count']}")
    print(f"  重复行数：{result['duplicate_line_count']}")
    print(f"  重复率：{result['duplicate_percent']:.2f}%")
    print(f"  重复组数：{result['duplicate_group_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
