"""SB3 callback 工具。"""

from __future__ import annotations

from stable_baselines3.common.callbacks import CheckpointCallback


def make_checkpoint_callback(save_freq: int, save_path: str, name_prefix: str = "ppo_upkie") -> CheckpointCallback:
    return CheckpointCallback(save_freq=int(save_freq), save_path=save_path, name_prefix=name_prefix)

