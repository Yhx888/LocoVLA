# 45 综合毕业项目

> 建设状态：可执行  
> 阶段：岗位毕业项目  
> 作品集目录：`outputs/portfolio/45`

## 岗位任务

完成《综合项目》岗位任务：编排“仿真→控制→安全→日志→分析”全链路。第 45 关用 `project_score = min(code, physics, robustness, realtime, safety, docs)` 验收本关开始前已经具备的六个工程维度；同时保留八维 `system_score`，报告第 46/47 关尚未完成时的课程就绪度。你需要交付的不只是运行截图，而是可解释设计、固定配置、量化指标和失败分析。

验收边界：`project_score` 只决定第 45 关工程项目是否通过；`system_score` 只表示八维本地课程证据是否齐备。两者都不是对学习者本人的毕业认证。**课程工程就绪不等于学习者毕业**；学习者毕业必须通过仓库外部人工答辩，本地 JSON、自动代码评审或 checkpoint 均不能代替外部评审者的判断。

## 学习目标

- 能理解：用自己的话说明 `system_score = min()` 评分逻辑解决什么工程问题，为什么取最小值而不是平均值。
- 能推导：从木桶原理出发解释 min 操作的物理含义，不跳过符号含义。
- 能实现：运行 `scripts/run_capstone_project.py`，保存测试、日志、结果契约三类证据。
- 能诊断：删除某个结果契约后，能预测并验证 system_score 的变化。

## 前置关卡

完成 `44` 的证据验收（系统设计与接口文档），或通过先修诊断。本关汇总第 18/31/37/42/43/44 关证据，并预期第 46/47 关完成。

## 先观察现象

先看错误基线：删除某个已通过关卡的结果契约（例如 `outputs/results/engineering_42.json`），再运行本关脚本，观察 `system_score` 和 `dimension_scores` 的变化。不要先读结论；先写下三个观察，再提出一个可被数据推翻的原因假设。

## 直觉与概念

<!-- upkie-animation:45-core -->

毕业项目不是功能拼盘，而是一条从需求到证据、从故障到复盘的完整工程链。

本关核心问题是：**如何用可测量证据判断"系统已经达到岗位可用"，而不是只在一次演示中碰巧工作？**

答案是用"木桶原理"：系统的整体质量由最短的板决定。`system_score = min(所有维度)` 正是这个原理的数学表达——任何一个维度不通过，整体评分就是 0。

### 为什么取 min（木桶原理）

用大白话说：一个机器人如果代码测试全过、物理指标达标、鲁棒性过关，但实时性不达标（控制循环超时），那它在真实部署中照样会摔倒。安全无短板，所以取最小值。

拆解字母：
- `min`：取最小值函数，输入一组数，返回其中最小的一个。
- 8 个维度各输出 0.0（不通过）或 1.0（通过）。
- `system_score` = 这 8 个数里的最小值。

Upkie 实例：假设第 45 关六个工程维度全通过，而第 46/47 关尚未运行，那么 `project_score = 1.0`，第 45 关可以通过；八维 `system_score = 0.0`，表示全课程工程证据尚未齐备。外部人工答辩仍未发生，因此学习者毕业状态仍为假。

为什么有用：min 操作确保了"全链路无短板"的验收语义，防止用高维度分数掩盖低维度缺陷。

## 教科书级展开

### 核心关系

project_score = min(code, physics, robustness, realtime, safety, docs)
system_score = min(code, physics, robustness, realtime, safety, docs, design_review, oral_defense)

按七层顺序检查：

#### 1. 直觉

8 个维度的评分像 8 块木板围成一个木桶。木桶能装多少水，不取决于最高的板，而取决于最矮的板。`min` 就是找最矮的那块板。

#### 2. 符号拆解

| 符号 | 含义 | 取值 |
|---|---|---|
| `code` | 代码测试维度 | 0.0 或 1.0 |
| `physics` | 物理控制指标维度 | 0.0 或 1.0 |
| `robustness` | 鲁棒性维度 | 0.0 或 1.0 |
| `realtime` | 实时性维度 | 0.0 或 1.0 |
| `safety` | 安全性维度 | 0.0 或 1.0 |
| `docs` | 文档维度 | 0.0 或 1.0 |
| `design_review` | 设计评审维度 | 0.0 或 1.0 |
| `oral_defense` | 口头答辩维度 | 0.0 或 1.0 |
| `min(...)` | 取最小值 | 0.0 或 1.0 |
| `project_score` | 第 45 关工程项目评分 | 0.0 或 1.0 |
| `system_score` | 八维课程工程就绪度 | 0.0 或 1.0 |

每个维度映射到一类毕业门槛，对应一个关卡的结果契约。

#### 3. 物理意义

`min` 操作的物理含义是"最弱环节决定整体"。在工程系统中，这对应"单点故障"原则：一个环节失效，整个系统失效。轮足机器人如果安全机制不工作（safety=0），即使其他维度全满分，也不允许部署。

#### 4. 设计动机

为什么不用平均值？因为平均值会掩盖缺陷。如果 7 个维度通过、1 个维度失败，平均值 = 7/8 = 0.875，看起来"差不多通过了"，但实际上存在一个未闭环的风险。`min` 操作确保了零容忍语义：全过才是过。

#### 5. 逐步推导

```
输入：8 个维度的评分，每个为 0.0 或 1.0
步骤1：收集所有维度评分 → [code, physics, robustness, realtime, safety, docs, design_review, oral_defense]
步骤2：取最小值 → min([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0]) = 0.0
步骤3：判定第 45 关 → project_score >= 1.0 ? 通过 : 不通过
```

#### 6. 数值算例

下面是“第 46/47 关证据缺失”时的教学算例，不代表当前工作区状态：

- `$code` — 1.0  (第 37 关 checkpoint_37.json passed=true)
- `$physics` — 1.0  (第 18 关 checkpoint_18.json passed=true)
- `$robustness` — 1.0  (第 31 关 checkpoint_31.json passed=true)
- `$realtime` — 1.0  (第 42 关 engineering_42.json passed=true)
- `$safety` — 1.0  (第 43 关 engineering_43.json passed=true)
- `$docs` — 1.0  (第 44 关 engineering_44.json passed=true)
- `$design_review` — 0.0 (第 46 关 engineering_46.json 不存在)
- `$oral_defense` — 0.0 (第 47 关 engineering_47.json 不存在)
system_score = min(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0) = 0.0
project_score = min(1.0, 1.0, 1.0, 1.0, 1.0, 1.0) = 1.0

这个算例中第 45 关的 `project_score` 为 `1.0`，而 `system_score` 为 `0.0`，因为第 46/47 关证据尚未生成。即使八个维度后来都得到 `1.0`，也只表示课程工程证据齐备；学习者毕业仍由仓库外部人工答辩单独判定。

#### 7. 代码映射

评分逻辑在 `src/upkie_mujoco_course/capstone/scoring.py`：

```python
def compute_system_score(evidence):
    dimension_scores = {}
    for dim, gate in DIMENSION_TO_GATE.items():
        ev = evidence.get(gate, {})
        dimension_scores[dim] = 1.0 if ev.get("passed", False) else 0.0
    system_score = min(dimension_scores.values()) if dimension_scores else 0.0
    return {"system_score": system_score, "dimension_scores": dimension_scores}
```

### 8 类毕业门槛映射

| 门槛 | 关卡 | 评分维度 | 证据文件 |
|---|---|---|---|
| code_tests | 37 | code | `outputs/results/checkpoint_37.json` |
| physical_metrics | 18 | physics | `outputs/results/checkpoint_18.json` |
| robustness | 31 | robustness | `outputs/results/checkpoint_31.json` |
| realtime | 42 | realtime | `outputs/results/engineering_42.json` |
| safety | 43 | safety | `outputs/results/engineering_43.json` |
| documentation | 44 | docs | `outputs/results/engineering_44.json` |
| design_review | 46 | design_review | `outputs/results/engineering_46.json` |
| oral_defense | 47 | oral_defense | `outputs/results/engineering_47.json` |

### min 操作的物理含义

`min` 是一个非线性操作，它确保了"与"语义：所有维度通过 ⟺ system_score = 1.0。这等价于逻辑与（AND）操作：

system_score = 1.0 ⟺ code ∧ physics ∧ robustness ∧ realtime ∧ safety ∧ docs ∧ design_review ∧ oral_defense

适用范围是当前关卡声明的 8 类毕业门槛。接触丢失、传感器过期、动作饱和、输入超出训练分布或公式假设不成立时，必须进入诊断/安全路径，不能继续外推。

## 动手检查点

```powershell
python scripts/run_capstone_project.py --output-root outputs
```

预期结果：脚本读取当前本地工程证据，同时计算 `project_score` 与 `system_score`，写出 `outputs/results/engineering_45.json` 和 `outputs/portfolio/45/engineering_45_report.md`。第 45 关只以 `project_score >= 1.0` 判定；分数取决于证据内容、源码摘要和端到端检查，不能预设为 0 或 1，也不输出学习者毕业结论。命令必须从项目根目录运行，原始输出写入 `outputs/`，不能手工改写成“更好看”的结果。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 45
```

## 可视化证据

脚本生成的 portfolio 报告 `outputs/portfolio/45/engineering_45_report.md` 包含 8 维度评分明细表，直观展示每个维度的通过状态和得分。

视觉只回答"发生了什么"，日志给出时间与数值，测试负责可重复判定；三者缺一不可。本关的证据是结果契约 `engineering_45.json`，它汇总了 8 类门槛状态。

## 故障诊断挑战

故意制造一个与"综合毕业项目"直接相关的错误：

1. 备份某个已通过关卡的结果契约（例如 `outputs/results/engineering_42.json`）
2. 删除该文件
3. 重新运行 `python scripts/run_capstone_project.py`
4. 观察 `project_score` 从 1.0 降为 0.0，`dimension_scores.realtime` 从 1.0 降为 0.0；若第 46/47 关尚未完成，`system_score` 会继续保持 0.0
5. 恢复文件，重新运行，确认指标恢复

按"现象 → 第一处异常证据 → 根因假设 → 最小验证 → 修复后对比"记录，不允许通过放宽阈值隐藏失败。

## 三档任务

- **基础任务**：在固定配置下运行 `scripts/run_capstone_project.py`，解释每个输出字段（project_score、system_score、dimension_scores、gate_passed_count）。
- **岗位挑战**：在当前源码状态下重新生成 8 个维度的本地证据，解释每个维度为何通过或失败；不得用旧结果文件预设 `system_score`。
- **开放探索**：在 `scoring.py` 的 `DIMENSION_TO_GATE` 中添加一个新维度（例如 `energy_efficiency`），先写假设（新维度如何影响 system_score），再用同一评估协议公平比较。

## 复盘与面试

1. 本关最关键的假设是什么？失效时第一个可观测信号是什么？
   - 假设：8 类门槛的证据文件路径和 `passed` 字段结构正确。失效信号：`dimension_scores` 中某个维度意外为 0.0。
2. 为什么用 min 而不是平均值或加权和？
   - min 确保"全链路无短板"的零容忍语义；平均值会掩盖缺陷，加权和需要主观设定权重。
3. 你能用哪三份证据证明结果可复现？
   - `engineering_45.json`（结果契约）、`engineering_45_e2e_run.log`（真实链路日志）、`portfolio/45/engineering_45_report.md`（评分明细）。
4. 如果 system_score 突然从 1.0 降为 0.0，你先查哪个维度？为什么？
   - 先查 `dimension_scores` 中值为 0.0 的维度，再追溯该维度对应的关卡结果契约是否被删除或 `passed` 字段是否变为 false。

## 下一关

下一关 `46` 提供故障演练与设计评审的本地工程证据，第 `47` 关提供代码评审和答辩材料。两关的自动结果可以支持“课程工程就绪”判断，但学习者毕业仍需仓库外部人工答辩。
