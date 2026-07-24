"""Gymnasium 环境层。

P-CODE-013 修复：在模块导入时调用 register_envs()，注册 UpkieStanding-v0 和
UpkieVelocity-v0 到 Gymnasium 注册表。原实现中 register_envs() 定义了但从未被调用，
导致 gym.make("UpkieStanding-v0") 会因环境未注册而失败。
register_envs() 内部有 try/except，重复注册会被静默忽略，无副作用。
"""

from upkie_mujoco_course.envs.registration import register_envs

# 导入 envs 包时自动注册环境，允许 gym.make("UpkieStanding-v0") 工作
register_envs()

