"""统一实验结果契约。"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from upkie_mujoco_course.utils.paths import project_root


RESULT_SCHEMA_VERSION = "2.0"
_SOURCE_STATE_FIELDS = {
    "commit",
    "git_dirty",
    "tracked_diff_sha256",
    "untracked_manifest_sha256",
    "source_digest",
    "requirements_lock_sha256",
}
# source_digest 只纳入可跨环境稳定复现的字段。
# 未跟踪文件清单（untracked_manifest_sha256）仍会记录在 source_state 中供人工核对，
# 但不再参与指纹计算：否则工作区里任何一个临时/未跟踪文件的增删改，都会让全部已生成
# 证据同时失效（坎1）。tracked_diff 与 requirements.lock 在计算哈希前统一换行符，
# 使 Windows 与 WSL2 得到同一份指纹（坎2），无需为不同环境分开记录两套指纹。
_SOURCE_DIGEST_FIELDS = (
    "commit",
    "git_dirty",
    "tracked_diff_sha256",
    "requirements_lock_sha256",
)
_GENERATED_TOP_LEVEL = {
    ".git",
    ".venv",
    "build",
    "diagrams",
    "install",
    "log",
    "outputs",
}
_ROS2_GENERATED = {"build", "install", "log"}
_TRACKED_DIFF_EXCLUDES = (
    ":(exclude).venv/**",
    ":(exclude)build/**",
    ":(exclude)diagrams/**",
    ":(exclude)install/**",
    ":(exclude)log/**",
    ":(exclude)outputs/**",
    ":(exclude)ros2_ws/build/**",
    ":(exclude)ros2_ws/install/**",
    ":(exclude)ros2_ws/log/**",
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalize_newlines(payload: bytes) -> bytes:
    """统一换行符，消除 Windows/WSL2 之间 CRLF 与 LF 的跨环境差异。"""

    return payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _source_digest(source_state: dict[str, Any]) -> str:
    payload = json.dumps(
        {name: source_state.get(name) for name in _SOURCE_DIGEST_FIELDS},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(payload)


def _git_output(root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
    )
    return completed.stdout if completed.returncode == 0 else b""


def _requirements_lock_digest(root: Path) -> str:
    lock = root / "requirements.lock"
    if lock.is_file():
        return _sha256(_normalize_newlines(lock.read_bytes()))
    candidates = [root / "pyproject.toml", *sorted(root.glob("requirements*.txt"))]
    payload = b"".join(
        path.name.encode("utf-8") + b"\0" + _normalize_newlines(path.read_bytes()) + b"\0"
        for path in candidates
        if path.is_file()
    )
    return _sha256(payload)


def _untracked_manifest(root: Path) -> tuple[bytes, bool]:
    names = _git_output(root, "ls-files", "--others", "--exclude-standard", "-z")
    entries: list[bytes] = []
    for raw_name in names.split(b"\0"):
        if not raw_name:
            continue
        relative = Path(raw_name.decode("utf-8", errors="surrogateescape"))
        parts = relative.parts
        if not parts or parts[0] in _GENERATED_TOP_LEVEL:
            continue
        if len(parts) >= 2 and parts[0] == "ros2_ws" and parts[1] in _ROS2_GENERATED:
            continue
        path = root / relative
        try:
            if path.is_file():
                entries.append(
                    relative.as_posix().encode("utf-8")
                    + b"\0"
                    + _sha256(path.read_bytes()).encode("ascii")
                )
        except OSError:
            # Windows 下失效的目录联接会同时令 stat 和读取失败，不应阻断源码摘要。
            continue
    return b"\n".join(sorted(entries)), bool(entries)


def capture_source_state(root: str | Path | None = None) -> dict[str, Any]:
    """采集当前提交、工作区差异和依赖锁的可复核摘要。"""

    source_root = Path(root).resolve() if root is not None else project_root().resolve()
    commit = _git_output(source_root, "rev-parse", "HEAD").decode("ascii", errors="replace").strip() or "unknown"
    tracked_diff = _git_output(
        source_root,
        "diff",
        "--binary",
        "--no-ext-diff",
        "HEAD",
        "--",
        ".",
        *_TRACKED_DIFF_EXCLUDES,
    )
    untracked_manifest, has_untracked = _untracked_manifest(source_root)
    requirements_digest = _requirements_lock_digest(source_root)
    tracked_digest = _sha256(_normalize_newlines(tracked_diff))
    untracked_digest = _sha256(untracked_manifest)
    source_state = {
        "commit": commit,
        "git_dirty": bool(tracked_diff) or has_untracked,
        "tracked_diff_sha256": tracked_digest,
        "untracked_manifest_sha256": untracked_digest,
        "requirements_lock_sha256": requirements_digest,
    }
    source_state["source_digest"] = _source_digest(source_state)
    return source_state


def _condition_passes(actual: float, condition: dict[str, Any]) -> bool:
    target = float(condition["value"])
    operator = condition["operator"]
    comparisons = {
        "<=": actual <= target,
        "<": actual < target,
        ">=": actual >= target,
        ">": actual > target,
        "==": actual == target,
    }
    if operator not in comparisons:
        raise ValueError(f"不支持的验收运算符: {operator}")
    return bool(comparisons[operator])


def _normalize_reference(item: str, root: Path) -> str:
    path = Path(item)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    return Path(os.path.relpath(resolved, root)).as_posix()


def _validate_reference_boundaries(items: list[str], root: Path, category: str) -> None:
    for item in items:
        resolved = Path(item).resolve() if Path(item).is_absolute() else (root / item).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"{category} 引用路径必须位于项目根目录内: {item}") from exc


def assess_experiment_result(
    result: dict[str, Any],
    *,
    current_source_state: dict[str, Any] | None = None,
    validate_references: bool = True,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """校验结果真实性；旧契约保持可读，但永远不计为有效完成。"""

    errors: list[str] = []
    stale = False
    if result.get("schema_version") != RESULT_SCHEMA_VERSION:
        return {
            "valid": False,
            "stale": False,
            "status": "legacy",
            "errors": [f"schema_version 必须为 {RESULT_SCHEMA_VERSION}"],
        }

    chapter_id = result.get("chapter_id")
    if not isinstance(chapter_id, str) or not chapter_id:
        errors.append("chapter_id 必须是非空字符串")
    if result.get("passed") is not True:
        errors.append("passed 必须为 true")
    if not isinstance(result.get("seed"), int) or isinstance(result.get("seed"), bool):
        errors.append("seed 必须是整数")
    if not isinstance(result.get("config"), dict):
        errors.append("config 必须是对象")
    try:
        created_at = datetime.fromisoformat(str(result.get("created_at")))
        if created_at.tzinfo is None:
            raise ValueError
    except ValueError:
        errors.append("created_at 必须是带时区的 ISO 8601 时间")

    metrics = result.get("metrics")
    conditions = result.get("pass_conditions")
    checks = result.get("checks")
    if not isinstance(metrics, dict) or not metrics:
        errors.append("metrics 必须是非空对象")
    if not isinstance(conditions, dict) or not conditions:
        errors.append("pass_conditions 必须是非空对象")
    if not isinstance(checks, dict) or not checks:
        errors.append("checks 必须是非空对象")
    elif not all(value is True for value in checks.values()):
        errors.append("checks 必须全部为 true")
    if isinstance(metrics, dict) and isinstance(conditions, dict) and isinstance(checks, dict):
        if set(conditions) != set(checks) or not set(conditions).issubset(metrics):
            errors.append("metrics、pass_conditions 与 checks 的指标不一致")
        else:
            for name, condition in conditions.items():
                try:
                    expected = _condition_passes(float(metrics[name]), condition)
                except (KeyError, TypeError, ValueError):
                    errors.append(f"指标 {name} 的验收条件无效")
                    continue
                if checks.get(name) is not expected:
                    errors.append(f"指标 {name} 的 checks 与实际条件不一致")

    source_state = result.get("source_state")
    if not isinstance(source_state, dict) or set(source_state) != _SOURCE_STATE_FIELDS:
        errors.append("source_state 字段不完整")
    else:
        commit = source_state.get("commit")
        if not isinstance(commit, str) or not commit.strip():
            errors.append("source_state.commit 必须是非空字符串")
        if not isinstance(source_state.get("git_dirty"), bool):
            errors.append("source_state.git_dirty 必须是布尔值")
        for name in _SOURCE_STATE_FIELDS - {"commit", "git_dirty"}:
            value = source_state.get(name)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(char not in "0123456789abcdef" for char in value.lower())
            ):
                errors.append(f"source_state.{name} 必须是 SHA-256")
        expected_digest = _source_digest(source_state)
        if source_state.get("source_digest") != expected_digest:
            errors.append("source_state 内部摘要与各字段不一致")
            stale = True
        current = current_source_state or capture_source_state(root)
        for name in _SOURCE_DIGEST_FIELDS:
            if source_state.get(name) != current.get(name):
                errors.append(f"source_state.{name} 与当前源码不一致，结果已过期")
                stale = True
        if source_state.get("source_digest") != current.get("source_digest"):
            errors.append("source_state.source_digest 与当前源码不一致，结果已过期")
            stale = True

    reference_root = Path(root).resolve() if root is not None else project_root().resolve()
    for category in ("plots", "logs"):
        references = result.get(category)
        if not isinstance(references, list) or not references:
            errors.append(f"{category} 必须包含真实证据路径")
            continue
        for item in references:
            if not isinstance(item, str) or Path(item).is_absolute():
                errors.append(f"{category} 必须使用项目相对路径")
                continue
            resolved = (reference_root / item).resolve()
            try:
                resolved.relative_to(reference_root)
            except ValueError:
                errors.append(f"{category} 引用路径必须位于项目根目录内: {item}")
                continue
            if validate_references and not resolved.is_file():
                errors.append(f"{category} 引用文件不存在: {item}")
    videos = result.get("videos", [])
    if not isinstance(videos, list):
        errors.append("videos 必须是数组")
    else:
        for item in videos:
            if not isinstance(item, str) or Path(item).is_absolute():
                errors.append("videos 必须使用项目相对路径")
                continue
            resolved = (reference_root / item).resolve()
            try:
                resolved.relative_to(reference_root)
            except ValueError:
                errors.append(f"videos 引用路径必须位于项目根目录内: {item}")
                continue
            if validate_references and not resolved.is_file():
                errors.append(f"videos 引用文件不存在: {item}")

    return {
        "valid": not errors,
        "stale": stale,
        "status": "stale" if stale else "valid" if not errors else "invalid",
        "errors": errors,
    }


def write_experiment_result(
    path: str | Path,
    *,
    chapter_id: str,
    seed: int,
    config: dict[str, Any],
    metrics: dict[str, float],
    pass_conditions: dict[str, dict[str, Any]],
    plots: list[str] | None = None,
    videos: list[str] | None = None,
    logs: list[str] | None = None,
    git_commit: str | None = None,
    validate_references: bool = True,
    root: str | Path | None = None,
) -> Path:
    """写出可追溯、可由仪表盘读取的实验结果。"""

    source_root = Path(root).resolve() if root is not None else project_root().resolve()
    raw_references = {
        "plots": plots or [],
        "videos": videos or [],
        "logs": logs or [],
    }
    for category, items in raw_references.items():
        _validate_reference_boundaries(items, source_root, category)
    references = {
        category: [_normalize_reference(item, source_root) for item in items]
        for category, items in raw_references.items()
    }
    if validate_references:
        missing = [
            f"{category}: {item}"
            for category, items in references.items()
            for item in items
            if not (source_root / item).is_file()
        ]
        if missing:
            raise RuntimeError(
                "write_experiment_result 引用了不存在的文件:\n  - " + "\n  - ".join(missing)
            )

    checks = {
        name: name in metrics and _condition_passes(float(metrics[name]), condition)
        for name, condition in pass_conditions.items()
    }
    source_state = capture_source_state(source_root)
    data = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "chapter_id": chapter_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit or source_state["commit"],
        "source_state": source_state,
        "seed": int(seed),
        "config": config,
        "metrics": metrics,
        "pass_conditions": pass_conditions,
        "checks": checks,
        "passed": bool(checks) and all(checks.values()),
        **references,
    }
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
