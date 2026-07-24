"""轮地摩擦与打滑演示脚本。

遍历不同的摩擦系数和轮端力矩，观察从纯滚动到打滑的转变。
输出每种配置下的前进距离和是否打滑，展示打滑临界点。

实验设计：
  构建一个最小化测试台车：底盘通过自由关节连接世界（受重力），
  但通过每步重置姿态来保持直立。轮子通过铰链关节连接到底盘。
  重力提供固定的法向力 F_n = mg，摩擦锥 |F_t| <= mu * F_n 固定。
  当轮端力矩 tau > mu * F_n * r 时，轮子打滑。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import mujoco


# ---------------------------------------------------------------------------
# 构建最小化测试台车模型
# ---------------------------------------------------------------------------

def build_test_rig(friction: float) -> tuple[mujoco.MjModel, mujoco.MjData]:
    """构建一个最小化的轮地摩擦测试台车。

    结构：
      world
        floor（平面）
        cart（自由关节，受重力，姿态被锁定）
          wheel（球形轮子，绕 Y 轴旋转）

    参数:
        friction: 地面与轮子之间的滑动摩擦系数

    返回:
        (model, data)
    """
    spec = mujoco.MjSpec()

    # 仿真参数
    spec.option.timestep = 0.002
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_RK4
    spec.option.gravity = [0, 0, -9.81]

    # 地面
    floor = spec.worldbody.add_geom(name="floor")
    floor.type = mujoco.mjtGeom.mjGEOM_PLANE
    floor.size = [10.0, 10.0, 0.1]
    floor.friction = [friction, 0.05, 0.01]
    floor.contype = 1
    floor.conaffinity = 1

    # 底盘 body：通过自由关节连接（6 DOF，受重力）
    cart = spec.worldbody.add_body(name="cart")
    cart.add_freejoint(name="cart_free")
    # 底盘可视化
    cart_geom = cart.add_geom(name="cart_visual")
    cart_geom.type = mujoco.mjtGeom.mjGEOM_BOX
    cart_geom.size = [0.05, 0.03, 0.02]
    cart_geom.mass = 2.0  # 底盘质量 2 kg
    # 初始位置：使轮子刚好在地面上
    cart.pos = [0, 0, 0.12]

    # 轮子 body：通过铰链关节连接到底盘（绕 Y 轴旋转）
    wheel = cart.add_body(name="wheel")
    wheel.add_joint(name="wheel_axis", type=mujoco.mjtJoint.mjJNT_HINGE, axis=[0, 1, 0])
    # 轮子可视化：球体（半径 = Upkie 轮子半径 0.06m）
    wheel_geom = wheel.add_geom(name="wheel_geom")
    wheel_geom.type = mujoco.mjtGeom.mjGEOM_SPHERE
    wheel_geom.size = np.array([0.06, 0.0, 0.0])
    wheel_geom.friction = [friction, 0.05, 0.01]
    wheel_geom.mass = 0.3  # 轮子质量 0.3 kg
    wheel_geom.contype = 1
    wheel_geom.conaffinity = 1
    wheel.pos = [0, 0, -0.06]  # 轮子在底盘下方

    # 力矩执行器
    actuator = spec.add_actuator(name="wheel_motor")
    actuator.trntype = mujoco.mjtTrn.mjTRN_JOINT
    actuator.target = "wheel_axis"
    actuator.set_to_motor()
    actuator.gear[0] = 1.0
    actuator.ctrllimited = True
    actuator.ctrlrange = [-2.0, 2.0]

    model = spec.compile()
    data = mujoco.MjData(model)

    return model, data


# ---------------------------------------------------------------------------
# 实验运行
# ---------------------------------------------------------------------------

def run_experiment(
    friction: float,
    ctrl_value: float,
    duration: float = 2.0,
) -> dict:
    """在给定摩擦系数和轮端力矩下运行仿真。"""
    model, data = build_test_rig(friction)

    wheel_radius = 0.06

    # 前向仿真初始化
    mujoco.mj_forward(model, data)

    # 先跑 50 步让接触稳定
    for _ in range(50):
        data.ctrl[0] = 0.0
        # 锁定姿态
        data.qpos[3] = 1.0
        data.qpos[4] = 0.0
        data.qpos[5] = 0.0
        data.qpos[6] = 0.0
        data.qvel[3] = 0.0
        data.qvel[4] = 0.0
        data.qvel[5] = 0.0
        mujoco.mj_step(model, data)

    # 测量稳定后的法向力
    mujoco.mj_forward(model, data)
    measured_fn = 0.0
    for i in range(data.ncon):
        force = np.zeros(6)
        mujoco.mj_contactForce(model, data, i, force)
        measured_fn += force[0]

    # 记录初始位置
    x0 = data.qpos[0]

    n_steps = int(duration / model.opt.timestep)
    total_wheel_rotation = 0.0

    for _ in range(n_steps):
        data.ctrl[0] = ctrl_value
        # 锁定姿态：防止倾倒
        data.qpos[3] = 1.0
        data.qpos[4] = 0.0
        data.qpos[5] = 0.0
        data.qpos[6] = 0.0
        data.qvel[3] = 0.0
        data.qvel[4] = 0.0
        data.qvel[5] = 0.0

        # 记录步进前的轮子角度
        wheel_angle_before = data.qpos[7]

        mujoco.mj_step(model, data)

        # 累计轮子旋转量
        wheel_angle_after = data.qpos[7]
        total_wheel_rotation += abs(wheel_angle_after - wheel_angle_before)

    forward_distance = data.qpos[0] - x0
    # 纯滚动条件：前进距离 = 轮子总旋转角度 * 半径
    expected_distance = total_wheel_rotation * wheel_radius
    if expected_distance > 1e-6:
        slip_ratio = abs(forward_distance - expected_distance) / expected_distance
    else:
        slip_ratio = 0.0
    is_slipping = slip_ratio > 0.5  # 纯滚动时约 0.2（模型伪影），真正打滑时接近 1.0

    return {
        "forward_distance": forward_distance,
        "slip_ratio": slip_ratio,
        "is_slipping": is_slipping,
        "measured_fn": measured_fn,
    }


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------

def main() -> None:
    """演示轮地摩擦与打滑现象。"""
    print("=" * 60)
    print("轮地摩擦与打滑演示")
    print("=" * 60)
    print()

    total_mass = 2.3  # kg
    g = 9.81
    wheel_radius = 0.06
    theoretical_fn = total_mass * g

    print(f"测试台车参数:")
    print(f"  总质量: {total_mass:.1f} kg")
    print(f"  理论法向力 (mg): {theoretical_fn:.3f} N")
    print(f"  轮子半径: {wheel_radius} m")
    print()

    friction_values = [1.0, 0.3, 0.1, 0.03]
    ctrl_values = [0.1, 0.3, 0.5, 1.0, 2.0]

    for mu in friction_values:
        tau_critical = mu * theoretical_fn * wheel_radius

        print("-" * 60)
        print(f"摩擦系数 = {mu}")
        print(f"  理论临界力矩 = {tau_critical:.4f} N*m")

        for ctrl in ctrl_values:
            result = run_experiment(mu, ctrl)

            slip_label = "打滑" if result["is_slipping"] else "无打滑"
            print(
                f"  ctrl = {ctrl:.1f}: {slip_label}, "
                f"前进距离 = {result['forward_distance']:.4f} m, "
                f"打滑比率 = {result['slip_ratio']:.3f}"
            )

        print()

    print("=" * 60)
    print("总结")
    print("=" * 60)
    print("1. 高摩擦系数下，轮端力矩在 ctrlrange 内不会打滑。")
    print("2. 低摩擦系数下，即使较小的力矩也会导致打滑。")
    print("3. 打滑判据：轮子边缘线速度远大于底盘前进速度。")
    print("4. 临界力矩 tau_max = mu * F_n * r，超过此值纯滚动条件被破坏。")
    print()
    print("注意：如需复现明显打滑现象，建议将地面摩擦系数降低到 0.1 以下。")


if __name__ == "__main__":
    main()
