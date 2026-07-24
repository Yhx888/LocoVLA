# 第4章：封装控制接口——让代码更易用

> 🎯 **本节目标**：理解控制接口的设计，学会如何封装控制器让代码更易于使用。

## 你将学到什么

完成本节后，你将能够：
- 理解 action space 的重要性
- 掌握不同的控制接口类型
- 实现 action filter 和 saturation

## 为什么要封装控制接口？

想象一下，你写了一个 PD 控制器。现在你想：
- 让其他人也能用这个控制器
- 在不同的机器人上复用这个控制器
- 对控制输出进行裁剪和滤波

这就是**控制接口封装**的意义。

## 第一步：运行 LQR 控制脚本

```powershell
python scripts/03_run_lqr_balancer.py
```

运行后，你会看到类似这样的输出：
```
LQR 输出: [0.0]
```

> 🔍 **为什么输出是 [0.0]？**
> 因为状态为零时，控制量也为零（符合预期：静止状态不需要修正）。

## 第二步：理解控制接口类型

### 力矩控制（Torque Control）
直接控制关节的力矩输出。

### 位置目标控制（Position Target Control）
控制关节的目标位置。

### 速度目标控制（Velocity Target Control）
控制关节的目标速度。

> 💡 **思考**：为什么轮子用速度控制，而髋关节用位置控制？

## 第三步：理解 Action 处理

### Action Scaling（动作缩放）
将策略输出的动作缩放到实际范围。

### Action Clipping（动作裁剪）
将动作裁剪到有效范围内，防止超出限制。

### Low-pass Filter（低通滤波器）
平滑控制输出，减少抖动。

## 第四步：探索代码

让我们看看控制接口是如何实现的：

```powershell
type src\upkie_mujoco_course\envs\action_adapter.py
```

你会看到类似这样的代码：
```python
def adapt_action(action, spec):
    # 缩放
    scaled = action * spec.action_scale
    # 裁剪
    clipped = np.clip(scaled, spec.ctrlrange[:, 0], spec.ctrlrange[:, 1])
    return clipped
```

> 💡 **这就是控制接口封装的意义**：让控制器更易于使用，同时保证安全性。

## 试试看：小挑战

1. **查看其他控制器**：`src/upkie_mujoco_course/controllers/` 目录下还有哪些控制器？它们分别做什么？

2. **修改动作缩放**：打开 `configs/env/standing.json`，找到 `action_scale` 字段，修改它的值，观察控制效果变化。

3. **理解饱和**：什么是 saturation？为什么需要它？

## 常见问题

| 问题 | 解决方案 |
|---|---|
| 动作超出限制 | 检查 `action_adapter.py` 中的裁剪逻辑 |
| 控制不平滑 | 检查 `action_filter.py` 中的低通滤波器实现 |

## 下一步

现在你已经理解了控制接口的封装。下一章，我们将学习如何构建 Gymnasium 环境，为强化学习做准备。

**预习问题**（带着这些问题进入下一章）：
- 什么是 Gymnasium？
- 为什么要构建 Gymnasium 环境？
- 什么是 observation space 和 action space？
