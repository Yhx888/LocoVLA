from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.course.checkpoint import TEST_TARGETS
from upkie_mujoco_course.course.checkpoint import run_chapter_checkpoint
from upkie_mujoco_course.course.dashboard_data import load_experiment_results


def _completed_chapters(output_root: Path) -> set[str]:
    return {
        str(result["chapter_id"])
        for result in load_experiment_results(output_root)
        if result.get("chapter_id") is not None
        and result.get("passed") is True
        and result.get("acceptance_valid") is True
        and result.get("contract_status") == "current"
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="运行课程关卡的测试、日志和可视化三重验收")
    parser.add_argument("--chapter", required=True, help="关卡编号，例如 00、17 或 H01")
    parser.add_argument(
        "--engineering-build",
        action="store_true",
        help="仅用于课程工程建设，显式跳过学习者先修门控",
    )
    parser.add_argument("--output-root", default="outputs", help="验收产物根目录")
    parser.add_argument("--source-root", default=None, help="源码与证据引用根目录")
    parser.add_argument("--seed", type=int, default=0, help="验收固定随机种子，只允许 0")
    parser.add_argument(
        "--no-viewer",
        action="store_true",
        default=True,
        help="无界面运行（验收始终启用）",
    )
    args = parser.parse_args()
    if args.seed != 0:
        parser.error("正式验收必须使用固定 seed=0")
    chapter = args.chapter
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    source_root = Path(args.source_root) if args.source_root is not None else ROOT
    if not source_root.is_absolute():
        source_root = ROOT / source_root
    learner_completion = not args.engineering_build
    completed_chapters = _completed_chapters(output_root) if learner_completion else set()

    # 捕获三重证据校验失败（来自 _require_experiment_evidence）并打印具体缺失清单
    try:
        result_path = run_chapter_checkpoint(
            chapter,
            output_root=output_root,
            learner_completion=learner_completion,
            completed_chapters=completed_chapters,
            source_root=source_root,
        )
    except RuntimeError as exc:
        raise SystemExit(f"关卡 {chapter} 验收失败（证据校验未通过）:\n{exc}")
    except Exception as exc:  # 其它异常也给出友好提示，避免裸 traceback
        raise SystemExit(f"关卡 {chapter} 验收出现异常: {exc}")

    result = json.loads(result_path.read_text(encoding="utf-8"))
    if not result["passed"]:
        # 测试失败：打印测试目标和日志路径，便于定位
        config = result.get("config", {}) if isinstance(result.get("config"), dict) else {}
        test_targets = config.get("test_targets") or TEST_TARGETS.get(chapter, "<未配置>").split()
        log_paths = result.get("logs", []) or []
        raise SystemExit(
            f"关卡 {chapter} 未通过自动测试。\n"
            f"  测试目标: {' '.join(test_targets)}\n"
            f"  结果契约: {result_path}\n"
            f"  日志路径: {', '.join(log_paths) if log_paths else '<无>'}"
        )
    print(f"关卡 {chapter} 自动验收通过，证据见: {result_path}")


if __name__ == "__main__":
    main()
