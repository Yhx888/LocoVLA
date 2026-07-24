# 第10章：用语言控制机器人——高层指令接口

> 🎯 **本节目标**：理解高层指令接口的设计，为接入 VLA（视觉-语言-动作）做准备。

## 你将学到什么

完成本节后，你将能够：
- 理解 command stub 与 VLA/VLM/LLM 的关系
- 实现键盘/脚本命令接口
- 为未来接入大模型做准备

## 什么是高层指令接口？

想象一下，你对机器人说"向前走"，它就能自动执行相应的动作。这就是**高层指令接口**的意义。

> 💡 **类比**：高层指令就像"遥控器"，你按"前进"按钮，机器人就知道该怎么动。

## 第一步：运行命令演示脚本

```powershell
python scripts/10_run_command_demo.py --text "go forward"
```

运行后，你会看到类似这样的输出：
```
站立命令: MotionCommand(forward_velocity=0.0, yaw_rate=0.0, height=0.0, source='script:stand')
前进命令: MotionCommand(forward_velocity=0.2, yaw_rate=0.0, height=0.0, source='script:forward')
语言命令: MotionCommand(forward_velocity=0.2, yaw_rate=0.0, height=0.0, source='language_stub')
```

> 🔍 **这些输出是什么意思？**
> - `forward_velocity`：前进速度
> - `yaw_rate`：转向速率
> - `height`：身体高度
> - `source`：命令来源

## 第二步：理解命令接口架构

```text
文本/键盘/脚本命令
        ↓
HighLevelCommand
        ↓
mode, velocity, yaw_rate, height
        ↓
classic controller / RL policy / residual policy
        ↓
MuJoCo robot
```

> 💡 **这就是从语言到动作的转换过程**：文本 → 命令 → 控制参数 → 机器人动作

## 第三步：理解 Language Stub

当前的 Language Stub 只做规则映射，未来可替换为 VLA/VLM/LLM：

- "go forward slowly" → vx = 0.2
- "turn left" → yaw_rate = 0.5
- "stop" → vx = 0.0, yaw_rate = 0.0

```powershell
type src\upkie_mujoco_course\commands\language_stub.py
```

> 🤔 **思考**：如果我要支持更多命令，需要修改哪些代码？

## 第四步：探索代码

让我们看看高层指令接口是如何实现的：

```powershell
type src\upkie_mujoco_course\commands\command_types.py
```

你会看到类似这样的代码：
```python
class MotionCommand:
    forward_velocity: float
    yaw_rate: float
    height: float
    source: str
```

> 💡 **这就是命令接口的核心**：定义标准化的命令格式，方便扩展。

## 试试看：小挑战

1. **添加新命令**：修改 `language_stub.py`，添加一个新的命令映射，如 "dance" → 特殊动作。

2. **查看帮助信息**：运行 `python scripts/10_run_command_demo.py --help`，看看还有哪些参数可以使用。

3. **思考 VLA 接入**：如果要接入大语言模型，需要设计什么样的接口？

## 常见问题

| 问题 | 解决方案 |
|---|---|
| 命令无法识别 | 检查 `language_stub.py` 中的命令映射 |
| 控制不响应 | 检查命令格式是否正确 |

## 恭喜完成所有课程！

你已经完成了 Upkie MuJoCo 运动控制课程的所有内容！

### 你学到了什么

- **第0-2章**：环境搭建、模型审计、MuJoCo 仿真基础
- **第3-4章**：经典控制（PD/LQR）、控制接口封装
- **第5-6章**：Gymnasium 环境、强化学习训练
- **第7-8章**：鲁棒性与域随机化、残差 RL
- **第9-10章**：模型替换、高层指令接口

### 下一步学习建议

1. **深入学习强化学习**：尝试更复杂的任务，如行走、跑步
2. **学习 VLA（视觉-语言-动作）**：将视觉和语言模型接入机器人控制
3. **尝试真实机器人**：将仿真中学习的策略迁移到真实机器人
4. **参与开源项目**：为 MuJoCo、Gymnasium 等项目贡献代码

### 继续学习资源

- [MuJoCo 官方文档](https://mujoco.readthedocs.io/)
- [Gymnasium 官方文档](https://gymnasium.farama.org/)
- [Stable-Baselines3 文档](https://stable-baselines3.readthedocs.io/)
- [Spinning Up in Deep RL](https://spinningup.openai.com/)

祝你在机器人控制和 VLA 的学习之路上一切顺利！🚀
