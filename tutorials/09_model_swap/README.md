# 第9章：换一个机器人——模型替换

> 🎯 **本节目标**：学会如何替换机器人模型，理解可替换设计的重要性。

## 你将学到什么

完成本节后，你将能够：
- 理解如何通过 RobotSpec 替换机器人模型
- 掌握模型接口契约
- 为未来替换复杂模型做准备

## 为什么要学习模型替换？

在实际项目中，你可能需要：
- 在不同的机器人上复用代码
- 测试不同的机器人配置
- 为新机器人快速搭建控制框架

这就是**模型替换**的意义——设计可替换的接口，让代码更灵活。

## 第一步：理解 RobotSpec

RobotSpec 是机器人模型的"接口契约"，它定义了：
- base body name：基座名称
- wheel joint names：轮子关节名称
- leg joint names：腿部关节名称
- actuator names：执行器名称
- default pose：默认姿态

```powershell
type configs\robot\upkie.json
```

> 💡 **思考**：如果我要控制另一个机器人，需要修改哪些字段？

## 第二步：运行模型审计

```powershell
python scripts/01_check_model.py --config configs/robot/upkie.json
```

运行后，你会看到类似这样的输出：
```
模型审计完成: nq=6, nv=6, nu=6
报告: outputs/model_audit/upkie_model_report.md
```

> 🔍 **参数说明**：
> - `--config`：指定配置文件路径
> - 不同的配置文件对应不同的机器人模型

## 第三步：理解模型替换流程

1. **创建新的 URDF/MJCF 文件**：定义新机器人的几何和物理属性
2. **创建对应的 config JSON**：定义新机器人的接口参数
3. **运行模型审计验证**：确保模型能正确加载
4. **更新 joint/actuator 映射**：调整控制代码

## 第四步：探索代码

让我们看看 RobotSpec 是如何实现的：

```powershell
type src\upkie_mujoco_course\model\robot_spec.py
```

你会看到类似这样的代码：
```python
class RobotSpec:
    def __init__(self, config_path):
        # 加载配置
        self.config = load_config(config_path)
        # 解析关节和执行器
        self.wheel_joints = self.config["wheel_joints"]
        self.leg_joints = self.config["leg_joints"]
```

> 💡 **这就是可替换设计的核心**：通过配置文件定义接口，代码自动适配。

## 试试看：小挑战

1. **修改配置**：打开 `configs/robot/upkie.json`，修改 `wheel_joints` 字段，重新运行模型审计，看看输出有什么变化？

2. **阅读模型替换指南**：查看 `docs/MODEL_SWAP_GUIDE.md`，了解更多模型替换的细节。

3. **思考扩展**：如果我要控制一个四轮机器人，需要修改哪些配置？

## 常见问题

| 问题 | 解决方案 |
|---|---|
| RobotSpec 字段缺失 | 检查 config JSON 是否完整 |
| 模型加载失败 | 检查 URDF 路径是否正确 |

## 下一步

现在你已经学会了模型替换。下一章，我们将学习如何设计高层指令接口——这是通往 VLA（视觉-语言-动作）的第一步。

**预习问题**（带着这些问题进入下一章）：
- 什么是高层指令接口？
- 如何将自然语言转换为机器人动作？
- VLA 是什么？它能做什么？
