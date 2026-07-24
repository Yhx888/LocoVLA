"""测试 Gymnasium 环境标准接口合规性。

覆盖场景：
- StandingEnv 通过 gymnasium.utils.env_checker.check_env
- 环境重置 / 步进 / 关闭接口符合规范
- 观测空间与动作空间定义正确
"""
import warnings

from gymnasium.utils.env_checker import check_env

from upkie_mujoco_course.envs.standing_env import StandingEnv


def test_standing_env_passes_gymnasium_check_env():
    env = StandingEnv(max_episode_steps=2)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        check_env(env, skip_render_check=True)
    env.close()
    messages = [str(item.message) for item in captured]
    assert not any("action spaces" in message for message in messages)
    assert not any("infinity" in message for message in messages)
