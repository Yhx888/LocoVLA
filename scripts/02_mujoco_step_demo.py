from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from upkie_mujoco_course.sim.runner import SimulationRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="MuJoCo 最小步进 demo")
    parser.add_argument("--duration", type=float, default=3.0, help="仿真时长（秒）")
    parser.add_argument("--no-viewer", action="store_true", help="不打开可视化窗口")
    args = parser.parse_args()
    runner = SimulationRunner()
    if not args.no_viewer:
        runner.open_viewer()
    runner.reset("stand")
    while runner.time < args.duration:
        runner.step(np.zeros(runner.model.nu))
    print(f"步进完成: sim_time={runner.time:.3f}s, obs_dim={runner.observation().shape[0]}")
    runner.close()


if __name__ == "__main__":
    main()

