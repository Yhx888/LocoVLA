"""地形随机化模块。

通过倾斜 MuJoCo 重力向量模拟斜坡地形（slope_deg），并支持粗糙度（roughness）
作为后续扩展占位。本模块已整合到 BaseUpkieEnv._apply_reset_randomization() 流程：

1. validate_terrain_config(config) 在 BaseUpkieEnv.__init__ 中校验随机化配置
2. sample_terrain_config(config, rng) 在每个 episode reset 时采样地形参数
3. apply_terrain(model, terrain) 在 reset 时修改 model.opt.gravity 模拟斜坡

物理建模说明：
- 斜坡倾角 slope_deg（单位：度）通过旋转重力向量实现
  g_x = g * sin(slope_rad)（沿斜坡方向的水平分量）
  g_z = -g * cos(slope_rad)（垂直斜坡方向的分量）
- roughness 字段当前为占位，保留用于后续扩展（如随机扰动地面法向）
"""

from __future__ import annotations

from typing import Any

import numpy as np


# 地形配置字段：允许在 randomization 配置中作为区间 [low, high] 或标量出现
_TERRAIN_FLOAT_FIELDS = {
    "terrain_slope_deg": {"minimum": -45.0, "maximum": 45.0},
    "terrain_roughness": {"minimum": 0.0, "maximum": 1.0},
}


def flat_terrain_config() -> dict[str, float]:
    """返回平地地形配置（slope=0, roughness=0）。

    保留用于教学示例和默认值兜底，实际生产路径由 sample_terrain_config() 提供。
    """
    return {"slope_deg": 0.0, "roughness": 0.0}


def validate_terrain_config(config: dict[str, Any]) -> None:
    """校验 randomization 配置中的地形字段。

    本函数与 dynamics.validate_randomization_config 互补：
    dynamics 校验质量/摩擦/噪声等字段，本函数校验 terrain_slope_deg/terrain_roughness。
    未知字段不报错（由 dynamics 统一负责未知字段检测），仅校验已知字段区间合法性。
    """
    for name, rule in _TERRAIN_FLOAT_FIELDS.items():
        if name not in config:
            continue
        values = config[name] if isinstance(config[name], (list, tuple)) else (config[name], config[name])
        if len(values) != 2:
            raise ValueError(f"{name} 必须是标量或含两个端点的区间")
        try:
            lower, upper = float(values[0]), float(values[1])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} 必须是有限数值") from exc
        if not np.isfinite(lower) or not np.isfinite(upper) or lower > upper:
            raise ValueError(f"{name} 的区间无效")
        if rule["minimum"] is not None and lower < rule["minimum"]:
            raise ValueError(f"{name} 不能小于 {rule['minimum']}")
        if rule["maximum"] is not None and upper > rule["maximum"]:
            raise ValueError(f"{name} 不能大于 {rule['maximum']}")


def sample_terrain_config(config: dict[str, Any], rng: np.random.Generator) -> dict[str, float]:
    """按固定 RNG 从配置中采样一组地形参数。

    返回字典字段：
    - slope_deg: 斜坡倾角（度），正数表示向前下坡，负数表示向后下坡
    - roughness: 粗糙度占位（0.0-1.0），当前不影响仿真
    """
    sampled = {"slope_deg": 0.0, "roughness": 0.0}
    if "terrain_slope_deg" in config:
        values = config["terrain_slope_deg"]
        if isinstance(values, (list, tuple)):
            low, high = float(values[0]), float(values[1])
            sampled["slope_deg"] = float(rng.uniform(low, high))
        else:
            sampled["slope_deg"] = float(values)
    if "terrain_roughness" in config:
        values = config["terrain_roughness"]
        if isinstance(values, (list, tuple)):
            low, high = float(values[0]), float(values[1])
            sampled["roughness"] = float(rng.uniform(low, high))
        else:
            sampled["roughness"] = float(values)
    return sampled


def apply_terrain(model, terrain: dict[str, float]) -> None:
    """按地形参数修改 MuJoCo model.opt.gravity 模拟斜坡。

    本函数直接修改 model.opt.gravity，调用方需在 reset 时先恢复默认重力再调用本函数
    （BaseUpkieEnv._apply_reset_randomization 已处理）。

    物理推导：
    - 默认重力 g = [0, 0, -9.81]（沿 -z 方向）
    - 斜坡倾角 θ（弧度），绕 y 轴旋转重力向量：
      g_x = g * sin(θ)（机器人沿 +x 方向"下坡"加速）
      g_z = -g * cos(θ)（垂直斜坡平面的分量）
    - 当 θ=0 时，g_x=0, g_z=-g，即平地，与默认一致

    roughness 字段当前为占位，不影响仿真。
    """
    slope_deg = float(terrain.get("slope_deg", 0.0))
    slope_rad = np.radians(slope_deg)
    g = float(model.opt.gravity[2])  # 保留原始重力大小（负值）
    # 仅当原始重力非零才旋转，避免在零重力环境下产生 NaN
    if abs(g) < 1e-12:
        return
    model.opt.gravity[0] = -g * np.sin(slope_rad)  # 沿 +x 方向（下坡为正）
    model.opt.gravity[2] = g * np.cos(slope_rad)   # 沿 -z 方向（垂直斜坡）
