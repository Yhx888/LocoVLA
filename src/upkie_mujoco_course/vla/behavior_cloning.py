"""轻量视觉语言条件行为克隆。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from upkie_mujoco_course.vla.contracts import DemonstrationEpisode
from upkie_mujoco_course.vla.language import parse_task_instruction
from upkie_mujoco_course.vla.perception import detect_colored_target


def _features(rgb: np.ndarray, depth: np.ndarray, proprioception: np.ndarray, instruction: str) -> np.ndarray:
    task = parse_task_instruction(instruction)
    detection = detect_colored_target(rgb, depth, task.target_color)
    colors = [float(task.target_color == name) for name in ("red", "green", "blue")]
    distance = detection.distance if np.isfinite(detection.distance) else 10.0
    state = np.asarray(proprioception, dtype=float).reshape(-1)
    state_features = np.pad(state[:15], (0, max(0, 15 - state[:15].size)))
    return np.asarray(
        [float(detection.visible), detection.horizontal_offset, min(distance, 10.0), *colors, *state_features, 1.0],
        dtype=float,
    )


@dataclass(frozen=True)
class BehaviorCloningPolicy:
    weights: np.ndarray
    training_features: np.ndarray | None = None
    training_actions: np.ndarray | None = None
    feature_mean: np.ndarray | None = None
    feature_scale: np.ndarray | None = None

    @classmethod
    def fit(cls, episodes: Iterable[DemonstrationEpisode], ridge: float = 1e-4) -> "BehaviorCloningPolicy":
        feature_rows: list[np.ndarray] = []
        action_rows: list[np.ndarray] = []
        for episode in episodes:
            for index in range(episode.timestamp.shape[0]):
                feature_rows.append(
                    _features(
                        episode.rgb[index],
                        episode.depth[index],
                        episode.proprioception[index],
                        episode.instruction,
                    )
                )
                action_rows.append(np.asarray(episode.action[index], dtype=float))
        if not feature_rows:
            raise ValueError("至少需要一个示范样本")
        x = np.stack(feature_rows)
        y = np.stack(action_rows)
        regularizer = float(ridge) * np.eye(x.shape[1])
        weights = np.linalg.solve(x.T @ x + regularizer, x.T @ y)
        feature_mean = np.mean(x, axis=0)
        feature_scale = np.std(x, axis=0)
        feature_scale[feature_scale < 1e-6] = 1.0
        return cls(
            weights=weights,
            training_features=(x - feature_mean) / feature_scale,
            training_actions=y,
            feature_mean=feature_mean,
            feature_scale=feature_scale,
        )

    def predict(
        self,
        rgb: np.ndarray,
        depth: np.ndarray,
        proprioception: np.ndarray,
        instruction: str,
    ) -> np.ndarray:
        features = _features(rgb, depth, proprioception, instruction)
        if (
            self.training_features is not None
            and self.training_actions is not None
            and self.feature_mean is not None
            and self.feature_scale is not None
        ):
            normalized = (features - self.feature_mean) / self.feature_scale
            distances = np.linalg.norm(self.training_features - normalized, axis=1)
            count = 1
            neighbors = np.argpartition(distances, count - 1)[:count]
            weights = 1.0 / np.maximum(distances[neighbors], 1e-6)
            action = np.average(self.training_actions[neighbors], axis=0, weights=weights)
        else:
            action = features @ self.weights
        return np.clip(action, -1.0, 1.0)

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {"weights": self.weights}
        if self.training_features is not None:
            payload.update(
                {
                    "training_features": self.training_features,
                    "training_actions": self.training_actions,
                    "feature_mean": self.feature_mean,
                    "feature_scale": self.feature_scale,
                }
            )
        np.savez_compressed(output, **payload)
        return output

    @classmethod
    def load(cls, path: str | Path) -> "BehaviorCloningPolicy":
        with np.load(Path(path), allow_pickle=False) as data:
            optional = {
                name: data[name].copy() if name in data.files else None
                for name in ("training_features", "training_actions", "feature_mean", "feature_scale")
            }
            return cls(weights=data["weights"].copy(), **optional)
