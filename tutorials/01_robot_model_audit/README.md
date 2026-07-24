# 第1章：认识你的机器人——模型审计

> 🎯 **本节目标**：学会检查机器人模型的"身体结构"，就像医生给病人做体检一样。

## 你将学到什么

完成本节后，你将能够：
- 理解为什么控制机器人前要先"审计"模型
- 看懂模型审计报告中的关键信息
- 知道如何检查关节、执行器等组件

## 为什么要"审计"模型？

想象一下，你要控制一个机器人。但在你开始写代码之前，你需要知道：

- 这个机器人有哪些关节？
- 每个关节叫什么名字？
- 关节的活动范围是多少？
- 用什么执行器来驱动这些关节？

如果这些信息搞错了，你的控制代码就会失败。这就是**模型审计**的意义。

## 第一步：运行模型审计脚本

```powershell
python scripts/01_check_model.py
```

运行后，你会看到类似这样的输出：
```
模型审计完成: nq=6, nv=6, nu=6
报告: outputs/model_audit/upkie_model_report.md
```

> 🔍 **这些数字是什么意思？**
> - `nq=6`：机器人有 6 个关节位置（qpos）
> - `nv=6`：机器人有 6 个关节速度（qvel）
> - `nu=6`：机器人有 6 个执行器（actuators）

## 第二步：查看审计报告

脚本运行后，会在 `outputs/model_audit/` 目录下生成报告。打开看看：

```powershell
type outputs\model_audit\upkie_model_report.md
```

你会看到 Upkie 机器人的详细信息。让我们一起看看这些信息代表什么：

### 关节（Joints）

报告中列出了所有关节：
- `left_hip`：左髋关节
- `left_knee`：左膝关节
- `left_wheel`：左轮
- `right_hip`：右髋关节
- `right_knee`：右膝关节
- `right_wheel`：右轮

> 💡 **思考**：为什么是这 6 个关节？如果我想让机器人走路，还需要其他关节吗？

### 执行器（Actuators）

执行器是驱动关节的"肌肉"。报告中列出了：
- 4 个位置执行器（hip 和 knee）：控制关节角度
- 2 个速度执行器（wheel）：控制轮子转速

> 🤔 **问题**：为什么髋关节和膝关节用位置执行器，而轮子用速度执行器？

## 第三步：探索配置文件

现在让我们看看配置文件是如何定义这些信息的：

```powershell
type configs\robot\upkie.json
```

你会看到类似这样的内容：
```json
{
  "name": "upkie",
  "controlled_joints": ["left_hip", "left_knee", "left_wheel", "right_hip", "right_knee", "right_wheel"],
  "position_actuators": [...],
  "velocity_actuators": [...]
}
```

> 💡 **这就是"模型审计"的意义**：在控制机器人之前，先要了解它的"身体结构"。

## 试试看：小挑战

1. **修改配置**：打开 `configs/robot/upkie.json`，找到 `timestep` 字段，把它改成 `0.001`，然后重新运行 `python scripts/01_check_model.py`，看看输出有什么变化？

2. **查看其他配置**：`configs/` 目录下还有哪些配置文件？它们分别控制什么？

## 常见问题

| 问题 | 解决方案 |
|---|---|
| `KeyError: joint not found` | joint name 不匹配，检查 `configs/robot/upkie.json` |
| `ValueError: actuator mismatch` | actuator 数量不对，重新运行模型审计 |

## 下一步

现在你已经了解了机器人的"身体结构"。下一章，我们将学习如何让这个机器人在仿真环境中"动起来"。

**预习问题**（带着这些问题进入下一章）：
- MuJoCo 是什么？它能做什么？
- 仿真环境和真实世界有什么区别？
- 如何让机器人在仿真中"站立"？
