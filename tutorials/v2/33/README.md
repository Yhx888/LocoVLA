# 33 RGB-D 相机与目标检测

> 建设状态：可执行
> 阶段：应用型 VLA
> 作品集目录：`outputs/portfolio/33`

## 岗位任务

你的交付物是一份"视觉感知验证报告"：在 MuJoCo 仿真中配置 RGB-D 相机，运行目标检测模型，验证检测结果的像素坐标可以正确转换为世界坐标下的目标距离和方位。面试官会问："你怎么从一张图片中算出目标离机器人多远？深度图的噪声和缺失值你怎么处理？"

具体交付：

1. 一段代码，在 MuJoCo 中配置相机并渲染 RGB 和深度图。
2. 一张检测叠加图：原始 RGB + 检测框 + 估计距离。
3. 一段分析，比较不同光照条件和目标距离下的检测精度。

## 学习目标

- **能理解**：解释针孔相机模型中像素坐标 (u,v) 到世界坐标 (X,Y,Z) 的转换公式，以及深度图在这个转换中的作用。
- **能推导**：给定相机内参矩阵 K 和外参矩阵 T，从像素 (u,v) 和深度 d 计算目标的世界坐标。
- **能实现**：用 MuJoCo 的 renderer 生成 RGB-D 图像，用简单的颜色阈值或预训练模型检测目标。

## 前置关卡

完成 `32`（具身任务与分层架构）的证据验收。你需要理解：

- 分层架构中任务层的输入（图像）和输出（目标位置）
- 坐标系变换的基本概念（关卡 03）
- MuJoCo 的传感器配置（关卡 09）

## 先观察现象

**错误基线实验**：不使用深度图，只用 RGB 图像估计目标距离。

```python
# 假设目标是一个红色球体
# 只用 RGB：从像素大小估计距离
pixel_radius = 50  # 目标在图像中的半径（像素）
real_radius = 0.05  # 真实半径（m）
focal_length = 500  # 像素单位

estimated_distance = focal_length * real_radius / pixel_radius
print(f"估计距离: {estimated_distance:.2f} m")
# 问题：像素大小受目标尺寸和距离共同影响
# 如果目标尺寸不知道，距离就估不准
```

**记录观察**：只用 RGB 的距离估计依赖于"知道目标真实尺寸"这个假设。深度图直接给出距离，不需要这个假设。

## 直觉与概念

<!-- upkie-animation:33-intuition -->

### RGB-D 相机：两只"眼"

RGB-D 相机同时输出两种图像：

- **RGB 图像**：普通彩色照片，告诉你"看到了什么"
- **深度图**：每个像素一个距离值，告诉你"它有多远"

这就像你的两只眼睛提供立体视觉——但深度相机更直接，它已经帮你算好了距离。

### 针孔相机模型

世界坐标 (X, Y, Z)  →  像素坐标 (u, v)
$$
u = fx \cdot \frac{X}{Z} + cx
v = fy \cdot \frac{Y}{Z} + cy
$$
fx, fy = 焦距（像素单位）
cx, cy = 光心（像素坐标）
- `$Z` — 深度（相机到目标的距离）

**反向转换**（从像素到世界）：

已知 (u, v) 和深度 d:
X = (u - cx) * d / fx
Y = (v - cy) * d / fy
Z = d

## 教科书级展开

<!-- upkie-animation:33-parameter -->

### MuJoCo 相机配置

```python
import mujoco
import numpy as np

model = mujoco.MjModel.from_xml_path("assets/upkie.xml")
data = mujoco.MjData(model)

# 渲染器配置（与 demonstrations.py:render_rgbd 一致）
renderer = mujoco.Renderer(model, height=120, width=160)

# 渲染 RGB（使用 onboard_camera）
mujoco.mj_forward(model, data)
renderer.disable_depth_rendering()
renderer.update_scene(data, camera="onboard_camera")
rgb = renderer.render().copy()  # shape: (120, 160, 3)

# 渲染深度
renderer.enable_depth_rendering()
renderer.update_scene(data, camera="onboard_camera")
depth = renderer.render().copy()  # shape: (120, 160)
renderer.disable_depth_rendering()
```

### 感知输出：TargetDetection

实际项目使用一个轻量 dataclass 表示检测结果，不做像素到世界坐标的完整变换（课程阶段只需要水平偏移和深度距离）：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class TargetDetection:
    visible: bool            # 是否检测到目标
    horizontal_offset: float # 水平偏移，归一化到 [-1, 1]（0 = 图像中心）
    distance: float          # 目标深度距离（m），未检测到时为 inf
    pixel_count: int         # 匹配像素数量
```

### 纯 numpy 颜色目标检测

```python
import numpy as np

def detect_colored_target(rgb: np.ndarray, depth: np.ndarray, color: str) -> TargetDetection:
    """用纯 numpy 通道比较检测彩色目标，无需 OpenCV。"""
    rgb = np.asarray(rgb, dtype=np.uint8)
    depth = np.asarray(depth, dtype=float)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or depth.shape != rgb.shape[:2]:
        raise ValueError("RGB 与深度图尺寸不匹配")

    # 通道索引：red=0, green=1, blue=2
    channels = {"red": 0, "green": 1, "blue": 2}
    if color not in channels:
        return TargetDetection(False, 0.0, float("inf"), 0)

    # 主通道值高、其他通道值低 → 颜色匹配
    primary = rgb[..., channels[color]].astype(int)
    others = np.delete(rgb.astype(int), channels[color], axis=2)
    secondary = np.max(others, axis=2)
    mask = (primary >= 160) & (secondary <= 85) & (primary >= secondary + 50)

    rows, cols = np.nonzero(mask)
    if cols.size == 0:
        return TargetDetection(False, 0.0, float("inf"), 0)

    # 水平偏移：归一化到 [-1, 1]，0 表示图像中心
    offset = 2.0 * float(np.mean(cols)) / max(1, rgb.shape[1] - 1) - 1.0

    # 深度：取匹配像素的中位数深度（抗噪声）
    valid_depth = depth[mask]
    valid_depth = valid_depth[np.isfinite(valid_depth) & (valid_depth > 0.0)]
    distance = float(np.median(valid_depth)) if valid_depth.size else float("inf")

    return TargetDetection(True, offset, distance, int(cols.size))
```

关键行设计原因：

- 纯 numpy 通道比较而非 OpenCV HSV：课程不依赖 `cv2`，只用 `numpy` 即可完成颜色阈值分割。条件 `primary >= 160` 和 `secondary <= 85` 是高饱和度的简化表达。
- `horizontal_offset` 归一化到 `[-1, 1]`：不依赖相机内参，直接用像素列的均值位置做归一化。对于导航任务，这足以判断"目标在左边还是右边"。
- `np.median(valid_depth)`：中位数比均值更抗深度图噪声和离群值（如目标边缘的混合像素）。
- 过滤无效深度 `np.isfinite(valid_depth) & (valid_depth > 0.0)`：深度图在天空、透明物体等区域会返回 inf 或 0，必须排除。

### 深度图噪声模型

真实深度相机（如 Intel RealSense）的噪声特征：

深度误差 sigma_d ≈ 0.001 * d^2（m）
d = 0.5 m → sigma ≈ 0.25 mm
d = 1.0 m → sigma ≈ 1.0 mm
d = 2.0 m → sigma ≈ 4.0 mm
- `$d` — 5.0 m → sigma ≈ 25 mm（精度显著下降）

**对 Upkie 的影响**：目标通常在 0.5-2.0 m 范围内，深度误差 0.25-4 mm，对于导航任务可以接受。

## 动手检查点

### 检查点 1：相机渲染

```powershell
python -c "
import mujoco, numpy as np
from upkie_mujoco_course.envs.standing_env import StandingEnv
env = StandingEnv()
r = mujoco.Renderer(env.runner.model, height=120, width=160)
r.disable_depth_rendering()
r.update_scene(env.runner.data, camera='onboard_camera')
rgb = r.render().copy()
print(f'RGB 形状: {rgb.shape}, 范围: [{rgb.min()}, {rgb.max()}]')
r.enable_depth_rendering()
r.update_scene(env.runner.data, camera='onboard_camera')
depth = r.render().copy()
print(f'深度形状: {depth.shape}, 范围: [{depth.min():.2f}, {depth.max():.2f}]')
r.close()
env.close()
"
```

预期：RGB 为 (120, 160, 3) uint8，深度为 (120, 160) float32。

### 检查点 2：目标检测

```powershell
python scripts/run_vla_lab.py --chapter 33
```

预期：检测到彩色目标，输出像素误差和深度距离指标。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 33
```

## 可视化证据

<!-- upkie-animation:33-evidence -->

在 `outputs/plots/checkpoint_33.png` 中绘制 2x2 图：

1. **左上**：RGB 图像 + 检测框。
2. **右上**：深度图（伪彩色）。
3. **左下**：检测到的目标中心像素的深度值分布（多次采样）。
4. **右下**：估计距离 vs 真实距离（0.5m 到 3.0m 范围）。

## 故障诊断挑战

<!-- upkie-animation:33-comparison -->

**破坏**：把相机内参的焦距 `fx` 设为真实值的 2 倍。

**第一处异常**：所有目标的估计距离都偏近 2 倍（因为 `X = (u-cx)*d/fx`，fx 大一倍则 X 坐标小一倍，但深度 d 不受影响）。水平位置估计错误，但深度正确。

**根因假设**：焦距决定了像素到角度的映射。焦距翻倍意味着每个像素对应的视角减半，导致水平/垂直位置计算错误。

**最小修复**：恢复正确的 `fx` 值。

**验证**：估计位置与真实位置误差 < 5%。

## 三档任务

### 基础任务

- 在 MuJoCo 中配置相机，渲染 RGB-D 图像。
- 用颜色阈值检测一个红色目标，估计其世界坐标。

### 岗位挑战

- 放置三个不同颜色的目标在不同距离处，同时检测并定位所有目标。
- 分析深度图噪声对距离估计精度的影响：在仿真中加入深度噪声，绘制 RMSE vs 噪声水平的曲线。

### 开放探索

- 比较颜色阈值检测和 YOLO 目标检测在 Upkie 场景中的精度和速度。
- 写一段 200 字分析：为什么具身机器人通常使用 RGB-D 而不是纯 RGB 相机？

## 复盘与面试

1. **深度图和 RGB 图的分辨率为什么通常不同？** 深度传感器（结构光或 ToF）的物理分辨率通常低于 RGB 传感器。需要配准（registration）把深度图对齐到 RGB 图的坐标系。

2. **深度图在什么情况下失效？** (a) 透明/反射物体（光被折射/反射）；(b) 室外强光（红外光被淹没）；(c) 太远（信号衰减）。在 MuJoCo 仿真中这些问题不存在，这就是 sim-to-real gap。

3. **从像素到世界坐标需要哪些信息？** (a) 像素坐标 (u,v)；(b) 该像素的深度 d；(c) 相机内参 (fx, fy, cx, cy)；(d) 相机外参（相机在世界坐标系中的位置和姿态）。

4. **为什么不用纯视觉 SLAM 代替深度相机？** SLAM 可以估计深度但计算量大、初始化慢。深度相机直接给出深度，实时性好。两者可以互补——SLAM 用于大尺度建图，深度相机用于近场避障。

## 下一关

关卡 `34`（语言任务与安全命令）会假设你已经能从图像中检测和定位目标。本关产出的视觉感知模块将成为下一关"语言条件导航"的感知输入——用户说"前往红色目标"，任务层解析出"红色"，感知层在图像中找到红色目标的位置。
