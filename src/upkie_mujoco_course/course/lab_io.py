"""统一实验产物 IO：write_result / log / plot / portfolio 四件套抽取。

在 estimation/rl/vla/mpc labs 中共同复用，避免"写 result → 存 log → 画图 →
写 portfolio"序列 duplicate 化的重复代码块。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from upkie_mujoco_course.course.results import write_experiment_result
from upkie_mujoco_course.utils.paths import project_root


def resolve_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    return root if root.is_absolute() else project_root() / root


def artifact_paths(output_root: str | Path, prefix: str, chapter_id: str) -> dict[str, Path]:
    root = resolve_output_root(output_root)
    return {
        "root": root,
        "plot": root / "plots" / f"{prefix}_{chapter_id}.png",
        "log": root / "logs" / f"{prefix}_{chapter_id}.json",
        "result": root / "results" / f"{prefix}_{chapter_id}.json",
        "portfolio": root / "portfolio" / chapter_id / "evidence.json",
    }


def finalize_lab_artifacts(
    *,
    output_root: str | Path,
    prefix: str,
    chapter_id: str,
    metrics: dict[str, float],
    pass_conditions: dict[str, dict[str, Any]],
    log: dict[str, Any],
    plot_path: Path,
    seed: int | None = None,
    config: dict[str, Any] | None = None,
    extra_plots: list[str] | None = None,
    extra_logs: list[str] | None = None,
    portfolio_extra: dict[str, Any] | None = None,
    source_root: str | Path | None = None,
) -> Path:
    """把 metrics/log 一次性落到 log / result / portfolio 三件套，返回 result 路径。

    - `prefix` 决定文件名前缀，例如 estimation / rl / vla / mpc。
    - `plot_path` 必须已经真实写盘。函数会把它写入 result.plots。
    - `log` dict 会 json.dumps 后写入 log 文件；`seed`/`config` 缺省时从 log 抽取。
    """

    paths = artifact_paths(output_root, prefix, chapter_id)
    paths["log"].parent.mkdir(parents=True, exist_ok=True)
    paths["log"].write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    resolved_seed = int(seed) if seed is not None else int(log.get("seed", 0))
    resolved_config: dict[str, Any] = dict(config or {})
    resolved_config.setdefault("lab", f"{prefix}_{chapter_id}")

    plots = [str(plot_path)]
    if extra_plots:
        plots.extend(str(item) for item in extra_plots)
    logs = [str(paths["log"])]
    if extra_logs:
        logs.extend(str(item) for item in extra_logs)

    written_result = write_experiment_result(
        paths["result"],
        chapter_id=chapter_id,
        seed=resolved_seed,
        config=resolved_config,
        metrics=metrics,
        pass_conditions=pass_conditions,
        plots=plots,
        logs=logs,
        root=source_root,
    )
    result = json.loads(written_result.read_text(encoding="utf-8"))
    paths["portfolio"].parent.mkdir(parents=True, exist_ok=True)
    portfolio_payload: dict[str, Any] = {
        "chapter_id": chapter_id,
        "passed": result["passed"],
        "result_path": str(written_result),
        "plots": result["plots"],
        "logs": result["logs"],
        "metrics": result["metrics"],
    }
    if portfolio_extra:
        portfolio_payload.update(portfolio_extra)
    paths["portfolio"].write_text(
        json.dumps(portfolio_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return written_result
