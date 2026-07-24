from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from upkie_mujoco_course.sim.runner import SimulationRunner
from upkie_mujoco_course.sim.viewer import run_passive_viewer


def main() -> None:
    parser = argparse.ArgumentParser(description="查看 Upkie MuJoCo 模型")
    parser.add_argument("--duration", type=float, default=3.0, help="运行时长，单位秒")
    parser.add_argument("--no-viewer", action="store_true", help="不打开 viewer，只做无界面步进")
    args = parser.parse_args()
    if args.no_viewer:
        runner = SimulationRunner()
        runner.reset("stand")
        while runner.time < args.duration:
            runner.step(np.zeros(runner.model.nu))
        print(f"无界面模型查看完成: sim_time={runner.time:.3f}s, nq={runner.model.nq}, nv={runner.model.nv}, nu={runner.model.nu}")
        runner.close()
    else:
        run_passive_viewer(duration=args.duration)


if __name__ == "__main__":
    main()

