# 第2章：让机器人动起来——MuJoCo 仿真基础

> 🎯 **本节目标**：理解 MuJoCo 仿真的核心概念，让 Upkie 机器人在仿真中"站立"。

## 你将学到什么

完成本节后，你将能够：
- 理解 MjModel、MjData、qpos、qvel、ctrl 等核心概念
- 运行 MuJoCo 仿真步进
- 观察机器人的运动状态

## 什么是 MuJoCo？

MuJoCo 是一个物理仿真引擎，可以模拟机器人在真实世界中的运动。你可以把它想象成一个"虚拟物理实验室"，在里面你可以：
- 创建机器人模型
- 施加力和力矩
- 观察机器人的运动

## 第一步：运行仿真脚本

```powershell
python scripts/02_mujoco_step_demo.py --duration 3
```

运行后，会弹出 MuJoCo 可视化窗口，你可以看到 Upkie 机器人在原地站立 3 秒。

> 🖥️ **无图形界面环境**：如果你在远程服务器或无图形界面环境中运行，加 `--no-viewer`：
> ```powershell
> python scripts/02_mujoco_step_demo.py --duration 1 --no-viewer
> ```

## 第二步：理解仿真输出

运行后，你会看到类似这样的输出：
```
步进完成: sim_time=3.000s, obs_dim=12
```

> 🔍 **这些数字是什么意思？**
> - `sim_time=3.000s`：仿真运行了 3 秒
> - `obs_dim=12`：观测向量维度为 12（6 个关节位置 + 6 个关节速度）

## 第三步：理解核心概念

### MjModel 和 MjData

- **MjModel**：模型的只读定义，包含机器人结构、物理参数等
- **MjData**：仿真运行时的可变状态，包含关节位置、速度等

### 状态向量

- `qpos`：关节位置（6 个值）
- `qvel`：关节速度（6 个值）
- `ctrl`：控制输入（6 个值）

> 💡 **思考**：为什么状态向量是 12 维（6 qpos + 6 qvel），而不是 6 维？

## 第四步：探索代码

让我们看看仿真脚本是如何工作的：

```powershell
type scripts\02_mujoco_step_demo.py
```

你会看到类似这样的代码：
```python
# 加载模型
model = build_mujoco_model()

# 创建仿真数据
data = mujoco.MjData(model)

# 运行仿真步进
for _ in range(steps):
    mujoco.mj_step(model, data)
```

> 💡 **这就是仿真的核心**：加载模型 → 创建数据 → 步进仿真

## 试试看：小挑战

1. **修改仿真时长**：把 `--duration` 参数改成 5 或 10，观察机器人能站立多久？

2. **查看模型信息**：运行 `python scripts/01_check_model.py`，对比模型审计输出和仿真输出，看看有什么关联？

3. **探索其他参数**：运行 `python scripts/02_mujoco_step_demo.py --help`，看看还有哪些参数可以修改？

## 常见问题

| 问题 | 解决方案 |
|---|---|
| `mujoco 未安装` | 运行 `pip install -r requirements.txt` |
| 模型加载失败 | 检查 `assets/upkie/` 目录是否存在 |
| 窗口不显示 | 检查是否在图形界面环境中运行 |

## 下一步

现在你已经让机器人在仿真中"站立"了。下一章，我们将学习如何控制机器人的平衡——这是运动控制的基础。

**预习问题**（带着这些问题进入下一章）：
- 什么是 PD 控制？
- 如何让机器人从蹲姿站起？
- 什么是"轮式倒立摆"？
