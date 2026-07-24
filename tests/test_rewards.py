"""测试奖励函数模块。

覆盖场景：
- 站立奖励（standing_reward）数值与符号
- 正则项（动作平滑度、能量惩罚）
- 奖励组合工具与有限性检查
"""
import numpy as np

from upkie_mujoco_course.rewards.common import combine_rewards, finite_float
from upkie_mujoco_course.rewards.regularization import action_smoothness_penalty, energy_penalty
from upkie_mujoco_course.rewards.standing import standing_reward
from upkie_mujoco_course.rewards.velocity import velocity_tracking_reward


def test_reward_functions_return_finite_float():
    state = {"pitch": 0.1, "base_height": 0.0, "both_wheels_contact": True, "forward_velocity": 0.2}
    action = np.array([0.1, -0.2])
    assert isinstance(standing_reward(state), float)
    assert isinstance(velocity_tracking_reward(state, target_velocity=0.0), float)
    assert isinstance(energy_penalty(action), float)
    assert isinstance(action_smoothness_penalty(action, np.zeros_like(action)), float)
    total = combine_rewards({"alive": 1.0, "upright": 2.0}, {"alive": 1.0, "upright": 0.5})
    assert total == 2.0
    assert finite_float(float("nan"), fallback=-1.0) == -1.0


def test_velocity_reward_prefers_matching_target():
    matching = velocity_tracking_reward({"forward_velocity": 0.5}, target_velocity=0.5)
    wrong = velocity_tracking_reward({"forward_velocity": -0.5}, target_velocity=0.5)
    assert matching > wrong


def test_standing_reward_prefers_target_height_over_floor_height():
    target_height = 0.42
    standing = {
        "pitch": 0.0,
        "base_height": target_height,
        "both_wheels_contact": True,
    }
    on_floor = {**standing, "base_height": 0.0}

    assert standing_reward(standing, target_height=target_height) > standing_reward(
        on_floor,
        target_height=target_height,
    )
