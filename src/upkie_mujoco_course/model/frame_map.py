"""body、geom 和 site 映射。"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco


@dataclass(frozen=True)
class FrameMap:
    body_ids: dict[str, int]
    geom_ids: dict[str, int]
    site_ids: dict[str, int]


def _names(model: mujoco.MjModel, obj_type: mujoco.mjtObj, count: int) -> dict[str, int]:
    result: dict[str, int] = {}
    for idx in range(count):
        name = mujoco.mj_id2name(model, obj_type, idx)
        if name:
            result[str(name)] = int(idx)
    return result


def build_frame_map(model: mujoco.MjModel) -> FrameMap:
    return FrameMap(
        body_ids=_names(model, mujoco.mjtObj.mjOBJ_BODY, model.nbody),
        geom_ids=_names(model, mujoco.mjtObj.mjOBJ_GEOM, model.ngeom),
        site_ids=_names(model, mujoco.mjtObj.mjOBJ_SITE, model.nsite),
    )

