# 34 语言任务与安全命令

> 建设状态：可执行
> 阶段：应用型 VLA
> 作品集目录：`outputs/portfolio/34`

## 岗位任务

你的交付物是一份"语言条件控制验证报告"：设计一个语言解析模块，把自然语言指令（如"前往红色目标"、"停车"、"驶向蓝色目标"）转换为结构化的动作命令，并在安全层的保护下执行。面试官会问："你怎么确保语言模型不会生成危险的指令？如果解析出错了，安全层能兜住吗？"

具体交付：

1. 一个语言解析器的代码：把字符串指令转换为 `{verb, target, parameters}` 结构。
2. 一张安全命令分类表：哪些命令可以直接执行，哪些需要安全层审核。
3. 一段端到端演示：输入"前往红色目标" → 解析 → 感知定位 → 安全过滤 → 执行。

## 学习目标

- **能理解**：解释为什么语言指令必须经过结构化解析才能传给控制层，以及为什么不能把原始文本直接传给神经网络策略。
- **能推导**：从语言指令到控制指令的完整变换链，每一步的输入/输出格式。
- **能实现**：实现一个简单但完整的语言条件控制管线。

## 前置关卡

完成 `33`（RGB-D 相机与目标检测）的证据验收。你需要理解：

- 目标检测和距离估计的输出格式
- 分层架构中任务层和规划层的接口
- 安全层的拦截机制

## 先观察现象

**错误基线实验**：不做语言解析，直接把指令文本传给 RL 策略。

```python
# 假设策略接受文本输入（实际上大多数 RL 策略不接受）
instruction = "go to the red target"
action = policy.predict(instruction)  # 这行代码会报错
```

**记录观察**：RL 策略的输入是数值向量，不能直接处理文本。需要一个解析步骤把文本转换为数值特征。

## 直觉与概念

<!-- upkie-animation:34-intuition -->

### 语言解析：从"说人话"到"说机器话"

人类说"去红色目标那里停下来"，机器人需要理解：

1. **动词**：去（移动）+ 停（到达后停止）
2. **目标**：红色（需要视觉搜索）
3. **条件**：到达后（需要距离判断）

语言解析器的工作就是把这个模糊的人类表达转换为精确的结构化命令：

```python
{
    "verb": "navigate",
    "target_color": "red",
    "stop_at_target": True,
    "source_text": "前往红色目标那里停下来",
}
```

### 安全命令分类

| 命令类型 | 安全等级 | 处理方式 | 示例 |
|---|---|---|---|
| 停止 | 最高 | 立即执行，跳过所有层 | "停车"、"停止" |
| 速度指令 | 中 | 经过安全层审核 | "向前走"、"速度 0.5" |
| 导航指令 | 中 | 经过规划层 + 安全层 | "前往红色目标" |
| 配置指令 | 低 | 只在初始化时执行 | "切换模式" |

**核心原则**：停止命令必须绕过所有中间层，直接切断控制输出。这是硬编码的安全机制，不能被任何学习模块覆盖。

## 教科书级展开

<!-- upkie-animation:34-parameter -->

### 语言解析器设计

实际项目使用一个函数（而非类）和一个不可变 dataclass：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TaskInstruction:
    """结构化任务指令。"""
    verb: str              # "navigate" 或 "unknown"
    target_color: str      # "red", "blue", "green" 或 "unknown"
    stop_at_target: bool   # 是否在目标处停车
    source_text: str       # 原始文本


def parse_task_instruction(text: str) -> TaskInstruction:
    """把课程范围内的自然语言任务解析为结构化命令。"""
    normalized = text.strip().lower()

    # 颜色别名：支持中英文
    color_aliases = {
        "red": ("red", "红", "红色"),
        "blue": ("blue", "蓝", "蓝色"),
        "green": ("green", "绿", "绿色"),
    }
    target_color = next(
        (color for color, aliases in color_aliases.items()
         if any(alias in normalized for alias in aliases)),
        "unknown",
    )

    # 导航动词：支持中英文关键词
    navigate = any(word in normalized for word in (
        "前往", "驶向", "到", "navigate", "go to", "approach"))
    # 停车关键词
    stop = any(word in normalized for word in (
        "停车", "停下", "停止", "stop"))

    return TaskInstruction(
        verb="navigate" if navigate else "unknown",
        target_color=target_color,
        stop_at_target=stop,
        source_text=text,
    )
```

关键行设计原因：

- 使用函数而非类：课程阶段的解析器没有状态，函数比类更简洁。`@dataclass(frozen=True)` 确保解析结果不可变，避免下游模块意外修改。
- 支持中英文关键词："前往"、"驶向"、"到"覆盖中文导航意图，"navigate"、"go to"、"approach"覆盖英文。注意："去"不在关键词列表中（太模糊，可能误匹配）。
- `target_color` 默认为 `"unknown"`：如果指令中没有颜色信息（如"向前走"），返回 `unknown` 而非 `None`，下游代码不需要处理空值。
- 停止判断独立于导航判断：一条指令可以同时包含导航和停止（如"前往红色目标并停车"），两者互不干扰。

### 端到端管线

```python
class LanguageConditionedController:
    """语言条件控制器。"""

    def __init__(self, detector, planner,
                 safety_filter, low_level_ctrl):
        self.detector = detector
        self.planner = planner
        self.safety = safety_filter
        self.controller = low_level_ctrl
        self.current_command = None

    def process_instruction(self, text: str):
        """处理新的语言指令。"""
        cmd = parse_task_instruction(text)

        # 非导航指令不执行
        if cmd.verb != "navigate":
            self.current_command = None
            return {"action": "rejected", "reason": "未知指令"}

        self.current_command = cmd
        return {"action": "command_accepted", "command": cmd}

    def step(self, rgb, depth, state):
        """每个规划周期调用一次。"""
        if self.current_command is None:
            return self.controller.compute(state)  # 默认平衡

        cmd = self.current_command

        if cmd.verb == "navigate" and cmd.target_color != "unknown":
            # 感知：检测目标
            target = self.detector.detect(
                rgb, depth, color=cmd.target_color)

            if target is None:
                return self.controller.compute(state)  # 没找到，保持平衡

            # 规划：生成速度指令
            v_ref = self.planner.compute_velocity(
                target, state)

            # 安全检查
            v_safe = self.safety.filter(v_ref, state)

            # 到达检测：stop_at_target 标志决定是否停车
            if cmd.stop_at_target and target["distance"] < 0.3:
                self.current_command = None
                v_safe = 0.0

            return self.controller.compute(state, v_ref=v_safe)

        return self.controller.compute(state)
```

## 动手检查点

### 检查点 1：语言解析

```powershell
python -c "
from upkie_mujoco_course.vla.language import parse_task_instruction
tests = ['前往红色目标', '驶向蓝色目标并停车', 'Navigate to the green target', 'do nothing here']
for t in tests:
    cmd = parse_task_instruction(t)
    print(f'{t} -> verb={cmd.verb}, color={cmd.target_color}, stop={cmd.stop_at_target}')
"
```

预期：每条指令都被正确解析为结构化 `TaskInstruction`。

### 检查点 2：端到端演示

```powershell
python scripts/run_vla_lab.py --chapter 34
```

预期：输出语言解析命中率和安全拒绝率指标。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 34
```

## 可视化证据

<!-- upkie-animation:34-evidence -->

在 `outputs/plots/checkpoint_34.png` 中绘制：

1. **时间线**：从语言输入到机器人开始移动的延迟分解（解析 + 感知 + 规划 + 控制）。
2. **轨迹图**：Upkie 在三种指令下的运动轨迹。

## 故障诊断挑战

<!-- upkie-animation:34-comparison -->

**破坏**：在语言解析器中去掉停止命令的特殊处理——让它走正常的动词匹配流程。

**第一处异常**：当用户说"紧急停止"时，解析器可能匹配到"停"→ verb="stop"，但也可能因为"紧急"这个词干扰匹配（取决于实现），导致停止命令延迟执行或不被识别。

**根因假设**：停止命令必须是无条件的、最高优先级的。任何前置条件或解析逻辑都可能引入延迟或失败。

**最小修复**：恢复停止命令的独立检查（在所有其他解析之前）。

**验证**：无论输入什么文本，只要包含"停"，立即返回停止命令。

## 三档任务

### 基础任务

- 实现语言解析器，测试 10 种不同的中文指令。
- 在仿真中运行"前往红色目标"任务，记录端到端延迟。

### 岗位挑战

- 设计一个"指令冲突解决器"：当用户连续发出"向前走"和"停止"时，系统应该在多长时间内响应停止？
- 在感知模块加入 20% 的漏检率，测试导航任务的成功率退化。

### 开放探索

- 研究 CLIP 和 Flamingo 等多模态模型如何处理语言+视觉任务。
- 写一段 200 字分析：规则解析器和 LLM 解析器在安全性上的根本区别是什么？

## 复盘与面试

1. **为什么停止命令必须特殊处理？** 因为它是安全关键命令。任何其他逻辑（感知、规划）都可能出错或延迟，但停止命令必须在毫秒内响应。这是硬编码的安全底线。

2. **为什么不用 LLM 做语言解析？** 可以，但 LLM 有延迟（100ms-1s）和不确定性（可能输出危险指令）。在安全关键的机器人系统中，确定性的小模型（规则或小型分类器）更可靠。LLM 适合做高层任务分解，不适合做安全关键指令。

3. **解析出错了怎么办？** 安全层兜底。即使解析器把"去悬崖"解析为"向前移动"，安全层会在机器人接近边缘时拦截。这是分层架构的核心优势——每一层都可以独立提供安全保障。

4. **端到端延迟是多少？** 解析 1ms + 感知 100ms + 规划 30ms + 控制 2ms = 约 133ms。这意味着从说话到机器人开始动需要约 133ms。

## 下一关

关卡 `35`（示范数据与脚本专家）会假设你已经有一个可工作的语言条件控制器。本关产出的控制器将成为下一关"脚本专家"的基础——用这个控制器生成高质量的示范数据，用于训练行为克隆策略。
