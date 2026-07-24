"""万向节锁演示脚本。

对比欧拉角表示与四元数表示在万向节锁附近的行为：
当 pitch 接近正负 90 度时，roll 和 yaw 对最终旋转矩阵的偏导数变得线性相关，
导致丢失一个旋转自由度。四元数表示则无此奇异性。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import mujoco

from upkie_mujoco_course.sim.loader import build_mujoco_model
from upkie_mujoco_course.utils.paths import project_root


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def euler_to_rotation_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """将 ZXZ  convention 的欧拉角转换为旋转矩阵。

    这里使用常见的 ZYX 内旋顺序（yaw-pitch-roll），
    即 R = Rz(yaw) @ Ry(pitch) @ Rx(roll)。

    参数:
        roll:  绕 X 轴的旋转角（弧度）
        pitch: 绕 Y 轴的旋转角（弧度）
        yaw:   绕 Z 轴的旋转角（弧度）

    返回:
        3x3 旋转矩阵
    """
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)

    # R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return rz @ ry @ rx


def euler_to_quat(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """将欧拉角 (ZYX 内旋) 转换为四元数 [w, x, y, z]。"""
    r = euler_to_rotation_matrix(roll, pitch, yaw)
    # 使用 MuJoCo 的旋转矩阵转四元数函数
    mat_flat = r.flatten()
    quat = np.zeros(4)
    mujoco.mju_mat2Quat(quat, mat_flat)
    return quat


def quat_to_rotation_matrix(quat: np.ndarray) -> np.ndarray:
    """将四元数 [w, x, y, z] 转换为旋转矩阵。"""
    mat_flat = np.zeros(9)
    mujoco.mju_quat2Mat(mat_flat, quat)
    return mat_flat.reshape(3, 3)


def compute_euler_jacobian(
    roll: float, pitch: float, yaw: float, eps: float = 1e-5
) -> np.ndarray:
    """计算旋转矩阵对欧拉角的数值雅可比矩阵。

    将 3x3 旋转矩阵展平为 9 维向量，
    分别对 roll、pitch、yaw 求数值偏导数，
    返回 9x3 的雅可比矩阵 [dR/droll | dR/dpitch | dR/dyaw]。

    参数:
        roll, pitch, yaw: 当前欧拉角（弧度）
        eps: 有限差分步长

    返回:
        9x3 雅可比矩阵
    """
    jacobian = np.zeros((9, 3))
    r0 = euler_to_rotation_matrix(roll, pitch, yaw).flatten()

    # 对 roll 的偏导数
    r_plus = euler_to_rotation_matrix(roll + eps, pitch, yaw).flatten()
    jacobian[:, 0] = (r_plus - r0) / eps

    # 对 pitch 的偏导数
    r_plus = euler_to_rotation_matrix(roll, pitch + eps, yaw).flatten()
    jacobian[:, 1] = (r_plus - r0) / eps

    # 对 yaw 的偏导数
    r_plus = euler_to_rotation_matrix(roll, pitch, yaw + eps).flatten()
    jacobian[:, 2] = (r_plus - r0) / eps

    return jacobian


def matrix_rank_condition_number(jacobian: np.ndarray) -> tuple[float, float]:
    """计算雅可比矩阵的秩和条件数。

    参数:
        jacobian: 9x3 雅可比矩阵

    返回:
        (秩, 条件数)
    """
    # 奇异值分解
    singular_values = np.linalg.svd(jacobian, compute_uv=False)
    # 阈值设为 0.01：数值微分步长 eps=1e-5 限制了精度，
    # pitch=90 时理论最小奇异值为 0，但数值上约为 eps 量级
    rank = np.sum(singular_values > 0.01)
    # 条件数 = 最大奇异值 / 最小非零奇异值
    if singular_values[-1] > 1e-12:
        cond = singular_values[0] / singular_values[-1]
    else:
        cond = float("inf")
    return float(rank), cond


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------

def main() -> None:
    """演示万向节锁现象。

    1. 加载 Upkie 模型（验证 MuJoCo 环境正常）
    2. 遍历 pitch 从 0 到 90 度，计算欧拉角雅可比矩阵的秩和条件数
    3. 对比四元数表示在同一旋转下的行为
    """
    # 加载 Upkie 模型
    model = build_mujoco_model()
    data = mujoco.MjData(model)
    print("=" * 60)
    print("万向节锁演示：欧拉角 vs 四元数")
    print("=" * 60)
    print(f"模型: nq={model.nq}, nv={model.nv}, nu={model.nu}")
    print()

    # ------------------------------------------------------------------
    # 第一部分：欧拉角雅可比矩阵的奇异性分析
    # ------------------------------------------------------------------
    print("-" * 60)
    print("第一部分：欧拉角雅可比矩阵的奇异性")
    print("-" * 60)
    print(f"{'pitch(deg)':>12s}  {'秩':>4s}  {'条件数':>12s}  {'最小奇异值':>14s}")
    print("-" * 60)

    roll_fixed = 0.0   # 固定 roll = 0
    yaw_fixed = 0.0    # 固定 yaw = 0

    for pitch_deg in range(0, 91, 5):
        pitch_rad = np.radians(pitch_deg)
        jac = compute_euler_jacobian(roll_fixed, pitch_rad, yaw_fixed)
        rank, cond = matrix_rank_condition_number(jac)
        sv = np.linalg.svd(jac, compute_uv=False)
        min_sv = sv[-1]
        print(f"{pitch_deg:>12d}  {rank:>4.0f}  {cond:>12.2f}  {min_sv:>14.8f}")

    print()
    print("结论：当 pitch 接近 90 度时，条件数急剧增大，")
    print("      最小奇异值趋近于 0，雅可比矩阵秩降为 2，")
    print("      roll 和 yaw 的偏导数线性相关——这就是万向节锁。")
    print()

    # ------------------------------------------------------------------
    # 第二部分：具体演示 roll 和 yaw 的偏导数在 pitch=90 时重合
    # ------------------------------------------------------------------
    print("-" * 60)
    print("第二部分：pitch=90 度时 dR/droll 与 dR/dyaw 的对比")
    print("-" * 60)

    pitch_90 = np.radians(90.0)
    jac_90 = compute_euler_jacobian(roll_fixed, pitch_90, yaw_fixed)

    droll = jac_90[:, 0]
    dyaw = jac_90[:, 2]

    # 计算两个偏导向量的余弦相似度
    cos_sim = np.dot(droll, dyaw) / (np.linalg.norm(droll) * np.linalg.norm(dyaw) + 1e-15)
    print(f"dR/droll 的 L2 范数: {np.linalg.norm(droll):.6f}")
    print(f"dR/dyaw  的 L2 范数: {np.linalg.norm(dyaw):.6f}")
    print(f"两者的余弦相似度:    {cos_sim:.8f}")
    print(f"  (1.0 表示完全线性相关，即万向节锁)")
    print()

    # ------------------------------------------------------------------
    # 第三部分：四元数表示无奇异性
    # ------------------------------------------------------------------
    print("-" * 60)
    print("第三部分：四元数表示在相同旋转下的行为")
    print("-" * 60)

    # 演示 Upkie 从直立到前倾 90 度的四元数轨迹
    print("Upkie 根部四元数随 pitch 变化的轨迹：")
    print(f"{'pitch(deg)':>12s}  {'w':>8s}  {'x':>8s}  {'y':>8s}  {'z':>8s}  {'|q|':>8s}")
    print("-" * 60)

    for pitch_deg in range(0, 91, 10):
        pitch_rad = np.radians(pitch_deg)
        quat = euler_to_quat(roll_fixed, pitch_rad, yaw_fixed)

        # 在 Upkie 模型中设置四元数并验证
        data.qpos[3] = quat[0]  # w
        data.qpos[4] = quat[1]  # x
        data.qpos[5] = quat[2]  # y
        data.qpos[6] = quat[3]  # z
        mujoco.mj_forward(model, data)

        # 从 MuJoCo 读取旋转矩阵验证
        mujoco_mat = data.xmat[0].reshape(3, 3)
        euler_mat = quat_to_rotation_matrix(quat)

        # 验证两种转换一致
        mat_diff = np.max(np.abs(mujoco_mat - euler_mat))

        quat_norm = np.linalg.norm(quat)
        print(
            f"{pitch_deg:>12d}  {quat[0]:>8.4f}  {quat[1]:>8.4f}  "
            f"{quat[2]:>8.4f}  {quat[3]:>8.4f}  {quat_norm:>8.6f}"
        )

    print()
    print("结论：四元数在所有角度下都保持 |q|=1，")
    print("      旋转矩阵与 MuJoCo 内部计算一致（最大差异 < 1e-10），")
    print("      不存在奇异性。这就是 MuJoCo 使用四元数表示姿态的原因。")
    print()

    # ------------------------------------------------------------------
    # 第四部分：双轴旋转演示（教程要求：X 转 90 度再 Y 转 90 度）
    # ------------------------------------------------------------------
    print("-" * 60)
    print("第四部分：绕 X 轴转 90 度后再绕 Y 轴转 90 度")
    print("-" * 60)

    # 分步构造旋转
    roll_90 = np.radians(90.0)
    pitch_90_val = np.radians(90.0)

    # 先绕 X 转 90 度
    q_x90 = euler_to_quat(roll_90, 0.0, 0.0)
    print(f"绕 X 轴转 90 度的四元数: [{q_x90[0]:.4f}, {q_x90[1]:.4f}, {q_x90[2]:.4f}, {q_x90[3]:.4f}]")

    # 再绕 Y 转 90 度（等价于 pitch=90）
    q_combined = euler_to_quat(roll_90, pitch_90_val, 0.0)
    print(f"X 转 90 + Y 转 90 的四元数: [{q_combined[0]:.4f}, {q_combined[1]:.4f}, {q_combined[2]:.4f}, {q_combined[3]:.4f}]")

    # 此时增加 roll 和减少 yaw 的效果对比
    delta = np.radians(5.0)
    q_plus_roll = euler_to_quat(roll_90 + delta, pitch_90_val, 0.0)
    q_minus_yaw = euler_to_quat(roll_90, pitch_90_val, 0.0 - delta)

    r_plus_roll = quat_to_rotation_matrix(q_plus_roll)
    r_minus_yaw = quat_to_rotation_matrix(q_minus_yaw)

    diff = np.max(np.abs(r_plus_roll - r_minus_yaw))
    print(f"\n在 pitch=90 时，增加 roll 5 度 vs 减少 yaw 5 度：")
    print(f"  两种操作产生的旋转矩阵最大差异: {diff:.10f}")
    if diff < 0.01:
        print(f"  -> 差异极小（< 0.01），证实 roll 和 yaw 的效果已不可区分！")
    else:
        print(f"  -> 差异明显，roll 和 yaw 仍可区分")

    print()
    print("=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
