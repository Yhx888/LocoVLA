"""MuJoCo viewer 入口。"""

from __future__ import annotations

import time

import mujoco.viewer
import numpy as np

from upkie_mujoco_course.sim.runner import SimulationRunner


def run_passive_viewer(duration: float = 5.0) -> None:
    """打开被动 viewer 并让模型空跑。"""

    runner = SimulationRunner()
    runner.reset("stand")
    try:
        with mujoco.viewer.launch_passive(runner.model, runner.data) as viewer:
            while runner.time < duration and viewer.is_running():
                runner.step(np.zeros(runner.model.nu))
                viewer.sync()
                time.sleep(runner.model.opt.timestep * runner.spec.frame_skip)
    finally:
        runner.close()

