# 第8章：传统控制 + 强化学习——残差 RL

> 🎯 **本节目标**：理解残差强化学习，学会将传统控制与强化学习结合。

## 你将学到什么

完成本节后，你将能够：
- 理解传统控制 + RL 融合路线
- 实现残差控制器
- 对比 classic、RL、residual 三种策略

## 什么是残差 RL？

残差 RL 是一种将传统控制与强化学习结合的方法。它的核心思想是：

```
u_final = u_classic + scale * u_rl
```

其中：
- `u_classic`：传统控制器输出（如 PD、LQR）
- `u_rl`：强化学习策略输出
- `scale`：缩放系数

> 💡 **类比**：想象你在开车。传统控制器是你的"基本驾驶技能"，强化学习是你的"应急反应"。残差 RL 就是在基本驾驶的基础上，根据情况做出微调。

## 第一步：运行评估脚本

```powershell
python scripts/08_eval_policy.py --episodes 1
```

运行后，你会看到类似这样的输出：
```
评估 returns: [396.7200000000013]
```

## 第二步：理解残差 RL 的优势

### 为什么用残差 RL？

1. **更稳定**：传统控制器提供基础稳定性
2. **更高效**：RL 只需要学习残差部分
3. **更安全**：可以限制 RL 的输出范围

### 残差 RL 公式

```text
u_classic = PD / LQR / wheel balancer
u_rl = policy(obs)
u_final = clip(u_classic + scale * u_rl)
```

## 第三步：探索代码

让我们看看残差控制器是如何实现的：

```powershell
type src\upkie_mujoco_course\controllers\residual.py
```

你会看到类似这样的代码：
```python
class ResidualController:
    def compute(self, state):
        # 传统控制器输出
        u_classic = self.classic_controller.compute(state)
        # RL 策略输出
        u_rl = self.policy(state)
        # 残差组合
        u_final = u_classic + self.scale * u_rl
        return np.clip(u_final, self.ctrlrange[:, 0], self.ctrlrange[:, 1])
```

## 试试看：小挑战

1. **对比三种策略**：分别运行 classic、RL、residual 三种策略，对比它们的性能。

2. **调整残差缩放**：修改 `scale` 参数，观察控制效果变化。

3. **理解残差限制**：为什么要限制 RL 的输出范围？

## 常见问题

| 问题 | 解决方案 |
|---|---|
| 残差太大 | 减小 `scale` 参数 |
| 控制不平滑 | 增加训练时间，让 RL 策略更稳定 |

## 下一步

现在你已经理解了残差 RL。下一章，我们将学习如何替换机器人模型。

**预习问题**（带着这些问题进入下一章）：
- 什么是 RobotSpec？
- 如何设计可替换的机器人模型接口？
- 为什么要保留模型可替换边界？
