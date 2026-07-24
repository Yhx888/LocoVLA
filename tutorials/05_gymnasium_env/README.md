# 第5章：构建强化学习环境——Gymnasium

> 🎯 **本节目标**：理解 Gymnasium 环境接口，学会构建强化学习环境。

## 你将学到什么

完成本节后，你将能够：
- 理解 reset、step、observation_space、action_space、reward 和 termination
- 构建自定义 Gymnasium 环境
- 使用 check_env 验证环境

## 什么是 Gymnasium？

Gymnasium 是一个强化学习环境标准库。它定义了一套标准接口，让不同的环境可以被统一使用。

> 💡 **类比**：想象 Gymnasium 是一个"游戏手柄标准"，所有游戏都用同一个手柄操作。

## 第一步：运行环境检查脚本

```powershell
python scripts/05_check_gym_env.py
```

运行后，你会看到类似这样的输出：
```
Gymnasium 环境检查通过
```

> ⚠️ **可能出现的警告**：
> - `WARN: For Box action spaces, we recommend using a symmetric and normalized space` — 建议动作空间归一化
> - `WARN: A Box observation space minimum value is -infinity` — 观测空间无下界
> - `WARN: A Box observation space maximum value is -infinity` — 观测空间无上界
>
> 这些警告是正常的，不影响功能。

## 第二步：理解 Gymnasium 核心接口

### reset()
重置环境，返回初始 observation。

### step(action)
执行动作，返回 (observation, reward, terminated, truncated, info)。

### observation_space
观测空间定义，描述环境返回的状态。

### action_space
动作空间定义，描述智能体可以采取的动作。

> 💡 **思考**：为什么需要定义 observation_space 和 action_space？

## 第三步：理解 Reward 设计

### Standing Reward
保持站立的奖励。

### Velocity Tracking
速度跟踪的奖励。

### Regularization
正则化惩罚，防止动作过大。

## 第四步：探索代码

让我们看看 Gymnasium 环境是如何实现的：

```powershell
type src\upkie_mujoco_course\envs\standing_env.py
```

你会看到类似这样的代码：
```python
class StandingEnv(gymnasium.Env):
    def reset(self):
        # 重置环境
        ...
        return observation, info
    
    def step(self, action):
        # 执行动作
        ...
        return observation, reward, terminated, truncated, info
```

> 💡 **这就是 Gymnasium 环境的核心**：实现 reset 和 step 方法。

## 试试看：小挑战

1. **查看其他环境**：`src/upkie_mujoco_course/envs/` 目录下还有哪些环境？它们分别做什么？

2. **修改奖励函数**：打开 `src/upkie_mujoco_course/rewards/standing.py`，修改奖励权重，观察训练效果变化。

3. **理解终止条件**：什么是 termination？什么是 truncation？它们有什么区别？

## 常见问题

| 问题 | 解决方案 |
|---|---|
| observation shape 不匹配 | 检查 `envs/observation.py` |
| reward 返回 NaN | 检查 reward 函数 |

## 下一步

现在你已经构建了 Gymnasium 环境。下一章，我们将学习如何使用强化学习训练策略。

**预习问题**（带着这些问题进入下一章）：
- 什么是强化学习？
- 什么是 PPO 算法？
- 如何训练一个强化学习策略？
