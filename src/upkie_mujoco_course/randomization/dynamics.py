"""动力学随机化的配置验证与逐回合采样。"""

from __future__ import annotations

from typing import Any

import numpy as np


_FLOAT_FIELDS = {
    "mass_scale": {"minimum": 1e-8},
    "inertia_scale": {"minimum": 1e-8},
    "com_offset_m": {"minimum": None},
    "friction_scale": {"minimum": 1e-8},
    "joint_damping": {"minimum": 0.0},
    "actuator_strength_scale": {"minimum": 1e-8},
    "sensor_noise_std": {"minimum": 0.0},
    "initial_state_std": {"minimum": 0.0},
    "push_force": {"minimum": None},
    # terrain 字段由 terrain.py 模块独立校验和应用，这里仅声明为已知字段避免误报
    "terrain_slope_deg": {"minimum": -45.0},
    "terrain_roughness": {"minimum": 0.0},
}
_INTEGER_FIELDS = {
    "action_delay_steps": {"minimum": 0},
    "push_step": {"minimum": -1},
    "push_duration_steps": {"minimum": 0},
}
# 由 terrain.py 独立处理的字段集合，sample_episode_randomization 跳过它们
_TERRAIN_FIELDS = {"terrain_slope_deg", "terrain_roughness"}


def _interval(value: Any, name: str, *, integer: bool, minimum: float | None) -> tuple[float, float]:
    values = value if isinstance(value, (list, tuple)) else (value, value)
    if len(values) != 2:
        raise ValueError(f"{name} 必须是标量或含两个端点的区间")
    try:
        lower, upper = (float(values[0]), float(values[1]))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是有限数值") from exc
    if not np.isfinite(lower) or not np.isfinite(upper) or lower > upper:
        raise ValueError(f"{name} 的区间无效")
    if minimum is not None and lower < minimum:
        raise ValueError(f"{name} 不能小于 {minimum}")
    if integer and (not lower.is_integer() or not upper.is_integer()):
        raise ValueError(f"{name} 必须使用整数步数")
    return lower, upper


def validate_randomization_config(config: dict[str, Any]) -> None:
    """验证配置，防止负质量、负延迟等没有物理语义的实验设置。"""

    unknown = set(config) - set(_FLOAT_FIELDS) - set(_INTEGER_FIELDS)
    if unknown:
        raise ValueError(f"未知随机化字段: {', '.join(sorted(unknown))}")
    for name, rule in _FLOAT_FIELDS.items():
        if name in config:
            _interval(config[name], name, integer=False, minimum=rule["minimum"])
    for name, rule in _INTEGER_FIELDS.items():
        if name in config:
            _interval(config[name], name, integer=True, minimum=rule["minimum"])


def sample_episode_randomization(config: dict[str, Any], rng: np.random.Generator) -> dict[str, float | int]:
    """按固定 RNG 从配置中采样一组真正写入仿真器的回合参数。

    terrain_slope_deg/terrain_roughness 字段由 terrain.sample_terrain_config() 独立采样，
    本函数跳过它们，避免重复采样导致两次随机数消耗。
    """

    validate_randomization_config(config)
    sampled: dict[str, float | int] = {}
    for name, rule in _FLOAT_FIELDS.items():
        if name not in config or name in _TERRAIN_FIELDS:
            continue
        lower, upper = _interval(config[name], name, integer=False, minimum=rule["minimum"])
        sampled[name] = float(rng.uniform(lower, upper))
    for name, rule in _INTEGER_FIELDS.items():
        if name not in config:
            continue
        lower, upper = _interval(config[name], name, integer=True, minimum=rule["minimum"])
        sampled[name] = int(rng.integers(int(lower), int(upper) + 1))
    return sampled


def scaled_value(value: float, scale: float) -> float:
    return float(value) * float(scale)
