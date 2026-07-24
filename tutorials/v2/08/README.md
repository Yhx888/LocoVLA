# 08 自由基座与空间姿态

> 建设状态：可执行
> 阶段：机器人仿真
> 作品集目录：`outputs/portfolio/08`

## 岗位任务

你的交付物是一份"姿态表示对比报告"：用四元数和欧拉角两种方式描述 Upkie 在不同倾斜状态下的姿态，分析万向节锁发生的条件，并证明四元数插值比欧拉角插值更平滑。面试官会问："为什么不用三个角度表示姿态？四元数到底解决了什么问题？"

具体交付：

1. 一段 Python 脚本，把 Upkie 从直立旋转到倒立，分别用四元数和欧拉角记录姿态轨迹。
2. 一张图展示万向节锁发生在哪个角度，此时欧拉角的哪个分量出现奇异性。
3. 一段 slerp（球面线性插值）代码，在两个姿态之间生成平滑过渡。

## 学习目标

- **能理解**：解释为什么三维旋转不能用 3 个参数无奇异地全局表示，以及四元数怎样解决这个问题。
- **能推导**：从四元数乘法公式出发，推导旋转矩阵和角速度之间的关系，不跳步。
- **能实现**：用 `mujoco.mju_mat2Quat` 和 `mujoco.mju_quat2Vel` 在四元数和角速度之间转换。

## 前置关卡

完成 `07`（URDF、MJCF 与模型审计）的证据验收。你需要理解：

- Upkie 的 `qpos` 中 `qpos[3:7]` 是四元数 `[w, x, y, z]`
- free joint 贡献 7 维 qpos（3 平移 + 4 四元数）
- 铰链关节只有 1 个自由度，不需要四元数

## 先观察现象

**错误基线实验**：用欧拉角描述 Upkie 绕两个轴同时旋转的姿态。

```python
import numpy as np

# Upkie 先绕 X 轴转 90 度（侧倾），再绕 Y 轴转 90 度（前倾）
roll, pitch, yaw = 90, 90, 0  # 度数

# 尝试用欧拉角计算"绕 Z 轴的旋转"
# 当 pitch = 90 度时，roll 和 yaw 的效果混合
print(f"当 pitch=90 度时，增加 roll 和减少 yaw 的效果相同")
print(f"这就是万向节锁：两个旋转轴对齐，丢失一个自由度")
```

**记录观察**：在 pitch 接近 90 度时，roll 和 yaw 的变化对最终姿态的影响变得不可区分。

## 直觉与概念

<!-- upkie-animation:08-core -->

### 万向节锁：三个环的物理限制

想象三个套在一起的金属环（万向节）：外环绕 X 轴转，中环绕 Y 轴转，内环绕 Z 轴转。

当外环绕 X 轴转 90 度时，中环的 Y 轴和内环的 Z 轴会**对齐到同一方向**。此时你转动外环和内环，效果完全相同——你丢失了一个独立的旋转自由度。

这就是万向节锁（gimbal lock）：不是算法 bug，而是用 3 个参数表示 3 自由度旋转的**拓扑限制**。数学上已经证明：不存在一种用 3 个参数表示 SO(3) 的方法能避免所有奇异点。

### 四元数：4 个参数表示 3 自由度

四元数 `q = w + xi + yj + zk` 用 4 个参数加一个约束 `|q| = 1`（单位四元数）来表示旋转。多出的 1 个维度正是避免奇异性的代价。

**生活类比**：地球表面是二维的（经度+纬度），但你需要 3 个笛卡尔坐标 (x, y, z) 加上约束 `x^2 + y^2 + z^2 = R^2` 来无奇异地描述它。如果你只用经纬度，在北极会出现"经度无定义"的奇点。

### 四元数的几何意义

一个单位四元数 `q = [cos(theta/2), sin(theta/2) * n]` 表示：

- 绕单位轴 `n = [nx, ny, nz]` 旋转
- 旋转角度 `theta`

注意半角 `theta/2`：这是因为四元数通过"sandwich product" `q * p * q^{-1}` 施加旋转，半角出现两次。

## 教科书级展开

### 四元数乘法

**公式**：

$$
q1 \cdot q2 = [w1 \cdot w2 - v1.v2,  w1 \cdot v2 + w2 \cdot v1 + v1 x v2]
$$

其中 `q = [w, v]`，`v = [x, y, z]` 是向量部分。

**符号拆解**：

| 符号 | 含义 | 类型 |
|---|---|---|
| `w1, w2` | 四元数的标量部分 | 实数 |
| `v1, v2` | 四元数的向量部分 | R^3 向量 |
| `.` | 点积 | 标量 |
| `x` | 叉积 | R^3 向量 |

**数值算例**：

- `$q1` — [cos(45 deg), sin(45 deg), 0, 0]  # 绕 X 轴转 90 deg
= [0.707, 0.707, 0, 0]
- `$q2` — [cos(45 deg), 0, sin(45 deg), 0]  # 绕 Y 轴转 90 deg
= [0.707, 0, 0.707, 0]
$$
q1 \cdot q2 = [0.707 \cdot 0.707 - (0.707 \cdot 0 + 0 \cdot 0.707 + 0 \cdot 0),
            0.707*[0, 0.707, 0] + 0.707*[0.707, 0, 0]
              + [0.707,0,0] x [0,0.707,0]]
        = [0.5 - 0,
            [0, 0.5, 0] + [0.5, 0, 0] + [0, 0, 0.5]]
        = [0.5, 0.5, 0.5, 0.5]
$$

验证：`|q|^2 = 0.25 + 0.25 + 0.25 + 0.25 = 1.0`

**物理意义**：先绕 Y 轴转 90 deg，再绕 X 轴转 90 deg，等价于绕 `[1,1,1]` 方向转 120 deg（因为 `cos(60 deg) = 0.5`，`theta = 120 deg`）。

### 四元数到旋转矩阵

**公式**：

$$
R = [1-2(y^2+z^2)   2(xy-wz)     2(xz+wy)  ]
    [2(xy+wz)     1-2(x^2+z^2)   2(yz-wx)   ]
    [2(xz-wy)     2(yz+wx)     1-2(x^2+y^2) ]
$$

**MuJoCo 中的用法**：

```python
import mujoco
import numpy as np

# 四元数 -> 旋转矩阵
quat = np.array([1.0, 0.0, 0.0, 0.0])  # 单位四元数（无旋转）
mat = np.zeros(9)  # 3x3 展平为 9 元素
mujoco.mju_quat2Mat(mat, quat)
R = mat.reshape(3, 3)
print(f"旋转矩阵:\n{R}")
# 预期：单位矩阵

# 旋转矩阵 -> 四元数
mat_back = np.zeros(4)
mujoco.mju_mat2Quat(mat_back, mat)
print(f"恢复的四元数: {mat_back}")
# 预期：[1, 0, 0, 0]
```

### 角速度与四元数导数

**公式**：

$$
dq/dt = 0.5 \cdot q (x) [0, \omega]
$$

其中 `omega = [wx, wy, wz]` 是角速度向量，`(x)` 是四元数乘法。

**物理意义**：角速度在体坐标系中测量（body-frame angular velocity），四元数导数通过半角关系把角速度映射到四元数空间的变化率。

**MuJoCo 中的对应**：`qvel[3:6]` 就是体坐标系下的角速度。MuJoCo 在内部用上述公式更新四元数，并在每步后重新归一化。

### Upkie 代码映射

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import mujoco
import numpy as np

from upkie_mujoco_course.sim.loader import build_mujoco_model

model = build_mujoco_model()
data = mujoco.MjData(model)

# 设置 Upkie 绕 Y 轴（前倾）旋转 30 度
# 教学简化：这里直接用硬编码索引 [3:7]。
# 实际应使用 SimulationRunner 的 joint_map 获取根部自由关节的 qpos 地址：
#   root_qpos = runner.joint_map.qposadr[runner.spec.root_joint_name]  # 0
#   data.qpos[root_qpos+3 : root_qpos+7] = ...
angle = np.radians(30)
data.qpos[3] = np.cos(angle / 2)   # w
data.qpos[4] = 0                     # x
data.qpos[5] = np.sin(angle / 2)   # y
data.qpos[6] = 0                     # z

mujoco.mj_forward(model, data)

# 读取旋转矩阵
mat = data.xmat[0].reshape(3, 3)  # 根部 body 的旋转矩阵
print(f"前倾 30 度的旋转矩阵:\n{np.round(mat, 3)}")
# 验证：第二列应接近 [0, 1, 0]（Y 轴不变）
# 第一列应有 cos(30) = 0.866 和 -sin(30) = -0.5
```

关键行设计原因：

- `data.qpos[3:7]` 直接操作四元数：不能像设置铰链关节那样用 `data.qpos[i] = angle`，必须用半角公式。教学简化使用了硬编码索引；实际项目中应通过 `runner.joint_map.qposadr` 获取四元数的起始地址。
- `data.xmat[0]`：MuJoCo 在 `mj_forward` 后计算每个 body 的世界坐标系旋转矩阵，`xmat` 是按 body 索引展平的 3x3 矩阵。

## 动手检查点

### 检查点 1：四元数归一化

```powershell
python -c "
import sys; sys.path.insert(0, 'src')
import mujoco, numpy as np
from upkie_mujoco_course.sim.loader import build_mujoco_model
m = build_mujoco_model()
d = mujoco.MjData(m)
mujoco.mj_step(m, d)
quat = d.qpos[3:7]
norm = np.linalg.norm(quat)
print(f'四元数: {quat}')
print(f'模长: {norm:.10f}')
assert abs(norm - 1.0) < 1e-6, f'四元数归一化失败: {norm}'
print('通过')
"
```

预期：模长偏差 < 1e-6。

### 检查点 2：万向节锁演示

请在 Python 中执行以下代码，观察当 pitch 接近正负 90 度时，roll 和 yaw 对最终旋转矩阵的偏导数变得线性相关：

```python
import numpy as np

def euler_to_matrix(roll_deg, pitch_deg, yaw_deg):
    """将欧拉角 (XYZ 顺序) 转换为旋转矩阵。"""
    r, p, y = np.radians(roll_deg), np.radians(pitch_deg), np.radians(yaw_deg)
    Rx = np.array([[1, 0, 0], [0, np.cos(r), -np.sin(r)], [0, np.sin(r), np.cos(r)]])
    Ry = np.array([[np.cos(p), 0, np.sin(p)], [0, 1, 0], [-np.sin(p), 0, np.cos(p)]])
    Rz = np.array([[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx

# pitch 从 0 到 90 度，观察 roll 和 yaw 的效果差异
for pitch_deg in [0, 45, 80, 89, 90]:
    R_base = euler_to_matrix(0, pitch_deg, 0)
    # 分别增加 roll 和 yaw，比较旋转矩阵的变化
    dR_roll = euler_to_matrix(1, pitch_deg, 0) - R_base
    dR_yaw = euler_to_matrix(0, pitch_deg, 1) - R_base
    similarity = np.sum(dR_roll * dR_yaw) / (np.linalg.norm(dR_roll) * np.linalg.norm(dR_yaw) + 1e-12)
    print(f"pitch={pitch_deg:>3d}°: roll/yaw 偏导相似度 = {similarity:.6f}")
    # pitch=90 时相似度接近 1.0，说明两个偏导线性相关（万向节锁）
```

预期输出展示：当 pitch 接近 90 度时，roll 和 yaw 的偏导相似度趋近 1.0，表明两个旋转轴对齐，丢失一个自由度。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 08
```

## 可视化证据

在 `outputs/plots/checkpoint_08.png` 中绘制：

1. **上图**：Upkie 从直立到倒立的姿态轨迹，用四元数 slerp 插值（平滑）。
2. **中图**：同一轨迹用欧拉角表示，标注万向节锁发生的帧。
3. **下图**：四元数各分量 vs 时间，展示连续性（没有跳变）。

## 故障诊断挑战

**破坏**：在设置初始姿态时，忘记归一化四元数——设 `data.qpos[3:7] = [2, 0, 0, 0]` 而不是 `[1, 0, 0, 0]`。

**第一处异常**：`mj_forward` 后 `xmat` 中的值不在 [-1, 1] 范围内，或者旋转矩阵的行列式不等于 1.0。

**根因假设**：非单位四元数对应的不是旋转矩阵，而是一个包含缩放的变换矩阵。

**最小修复**：设置四元数后始终归一化：`data.qpos[3:7] /= np.linalg.norm(data.qpos[3:7])`。

**验证**：重新运行后旋转矩阵行列式为 1.0，所有元素在 [-1, 1] 范围内。

## 三档任务

### 基础任务

- 实现四元数乘法函数 `quat_mul(q1, q2)`，验证 `q * q_conj = [1, 0, 0, 0]`。
- 用 MuJoCo 设置 Upkie 绕三个轴分别旋转 30、45、60 度，验证旋转矩阵正确。

### 岗位挑战

- 实现 slerp 函数 `slerp(q1, q2, t)`，在两个姿态之间生成 100 个中间姿态。
- 对比 slerp 和欧拉角线性插值在大角度（> 90 度）下的差异，用旋转矩阵的 Frobenius 范数量化。

### 开放探索

- 研究轴角表示（axis-angle）和旋转矢量（rotation vector），与四元数比较优缺点。
- 写一段 200 字分析：为什么 MuJoCo 选择四元数而不是旋转矢量作为内部姿态表示？

## 复盘与面试

1. **为什么需要 4 个数表示 3 自由度旋转？** 3 个参数表示 SO(3) 必然有奇异点（这是拓扑定理）。四元数用 4 个参数加归一化约束避免了这个问题。

2. **万向节锁在 Upkie 中会发生吗？** 不会——Upkie 的根部用四元数（无奇异），腿部铰链关节只有 1 个自由度（不需要 3 个角度）。但如果你在外部用欧拉角分析 Upkie 的姿态，当躯干垂直时 yaw 和 roll 会混合。

3. **四元数的半角从哪来？** 四元数通过 `q * p * q^{-1}` 旋转一个点，每次乘 q 贡献 theta/2 的旋转，两次合起来是 theta。

4. **`qvel[3:6]` 是角速度，它的参考坐标系是什么？** 体坐标系（body frame），不是世界坐标系。这意味着当 Upkie 旋转时，角速度分量始终相对于躯干当前的前后/左右/上下方向。

## 下一关

关卡 `09`（执行器、传感器与单位）会假设你已经能从 `qpos` 和 `qvel` 中正确提取位置和姿态信息。本关产出的四元数操作代码将成为下一关读取 IMU 传感器数据时的基础——IMU 输出的就是四元数或角速度，你需要在两种表示之间自由转换。
