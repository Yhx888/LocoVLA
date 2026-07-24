"""VLA 示范数据集的持久化契约。"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import json
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class DemonstrationEpisode:
    rgb: np.ndarray
    depth: np.ndarray
    proprioception: np.ndarray
    action: np.ndarray
    instruction: str
    timestamp: np.ndarray
    metadata: dict = field(default_factory=dict)


def save_episode(episode: DemonstrationEpisode, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    steps = int(episode.timestamp.shape[0])
    arrays = (episode.rgb, episode.depth, episode.proprioception, episode.action)
    if any(int(array.shape[0]) != steps for array in arrays):
        raise ValueError("episode 各字段的时间维长度必须一致")
    np.savez_compressed(
        path,
        schema_version=np.asarray("1.0"),
        rgb=episode.rgb,
        depth=episode.depth,
        proprioception=episode.proprioception,
        action=episode.action,
        instruction=np.asarray(episode.instruction),
        timestamp=episode.timestamp,
        metadata=np.asarray(json.dumps(episode.metadata, ensure_ascii=False)),
    )
    return path


def load_episode(path: str | Path) -> DemonstrationEpisode:
    with np.load(Path(path), allow_pickle=False) as data:
        if "schema_version" not in data or str(data["schema_version"].item()) != "1.0":
            raise ValueError("VLA 示范数据版本缺失或不受支持")
        return DemonstrationEpisode(
            rgb=data["rgb"].copy(),
            depth=data["depth"].copy(),
            proprioception=data["proprioception"].copy(),
            action=data["action"].copy(),
            instruction=str(data["instruction"].item()),
            timestamp=data["timestamp"].copy(),
            metadata=json.loads(str(data["metadata"].item())) if "metadata" in data else {},
        )
