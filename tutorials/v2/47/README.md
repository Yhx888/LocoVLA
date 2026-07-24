# 47 代码评审、答辩与面试

> 建设状态：可执行
> 阶段：岗位毕业项目（oral_defense 毕业门槛）
> 作品集目录：`outputs/portfolio/47`

## 岗位任务

完成《代码评审、答辩与面试》岗位任务，把整个课程的控制、估计、RL、VLA、工程部署、安全、文档体系整理成可口头答辩的论证链，并用自动化代码评审给出可量化的可维护性证据。

你需要交付的不只是运行截图，而是可解释设计、固定配置、量化指标和失败分析。本关是毕业门槛 `oral_defense`，要求三件套齐备：自动化评审报告、答辩材料、面试题库。

验收边界：本关脚本只验证“答辩材料和代码评审工程是否就绪”。**课程工程就绪不等于学习者毕业**；学习者毕业必须经过仓库外部人工答辩。`engineering_47.json` 的 `passed=true`、本地签名文件或自动评审报告都不能自证真人答辩通过。

## 学习目标

- 能理解：用自己的话说明「代码评审 + 答辩 + 面试」解决什么工程问题——可解释性、可维护性、知识传承。
- 能推导：从指标定义出发解释 `review_pass` 的判定逻辑，不跳过覆盖率与静态告警的边界条件。
- 能实现：运行检查点，保存测试、日志、图表或视频三类证据，并写出可追溯的结果契约。

## 前置关卡

完成 `46`（故障演练）的证据验收，或通过先修诊断。本关把前 46 关的全部产物作为评审对象。

## 先观察现象

先看错误基线：故意在一个源文件里制造语法错误（例如删除一个冒号），再运行评审脚本，记录评审报告最先出现的异常字段。不要先读结论；先写下三个观察，再提出一个可被数据推翻的原因假设。

- 观察 1：语法错误会让 `syntax_errors` 从 0 变 1。
- 观察 2：`review_pass` 在 pytest-cov 未安装时立刻从 1 变 0。
- 观察 3：长行（>120 字符）会被计入 `static_warnings`，但不会单独让 `review_pass` 翻转。

## 直觉与概念

<!-- upkie-animation:47-core -->

毕业项目不是功能拼盘，而是一条从需求到证据、从故障到复盘的完整工程链。本关核心问题是：**如何用可测量证据判断「项目达到岗位可用」，而不是只在一次演示中碰巧工作？**

为什么需要代码评审和答辩？三个动机：

1. **可解释性**：答辩把「为什么选 PD→LQR→RL→VLA」压缩成一条论证链，让评审者在 3 分钟内理解每层设计的动机与局限。没有答辩，代码只是一堆能跑的函数。
2. **可维护性**：代码评审用覆盖率、复杂度、重复率、静态告警四类指标量化「代码是否易于维护」。指标不是装饰，而是后人接手时的健康体检表。
3. **知识传承**：面试题库把课程所有章节的关键决策沉淀成可自测的问答，新人通过自测就能快速建立全局认知，不必逆向工程代码。

本关的核心关系是把「主张」变成「证据」：

claim（主张）→ design reason（设计动机）→ experiment evidence（实验证据）→ limitation（局限性）→ improvement（改进方向）

阅读公式或契约时按七层顺序检查：直觉、符号、物理意义、设计动机、逐步推导、数值算例、代码映射。所有物理量使用 SI 单位；离散时间量必须说明采样周期。

适用范围是当前关卡声明的平衡点、约束和数据分布。接触丢失、传感器过期、动作饱和、输入超出训练分布或公式假设不成立时，必须进入诊断/安全路径，不能继续外推。

## 教科书级展开

### 1. 静态分析

静态分析不运行代码，只读源码文本，回答「代码本身有没有问题」。本关检查三项：

- **语法错误**：用 `py_compile.compile(..., doraise=True)` 编译每个文件。语法错误是最严重的问题——文件根本无法导入。
- **未使用的导入**：用 `ast` 解析出所有 `import` 绑定名，再用全文词边界匹配复核。只要绑定名在源码任意位置出现（含注释、字符串、类型注解），就视为已使用。这是保守策略，宁可漏报也不误报。
- **行长 > 120 字符**：逐行统计长度。长行降低可读性，但不影响正确性。

`warning_count = 未用导入数 + 长行数`，`static_warnings = 所有文件 warning_count 之和`。

### 2. 覆盖率统计

覆盖率回答「测试到底跑过了多少行代码」。本关调用 `pytest --cov=src/upkie_mujoco_course --cov-report=json`，从 JSON 报告里读 `totals.percent_covered`。

如果 `pytest-cov` 未安装，覆盖率返回 0.0 并标注「未安装 pytest-cov，跳过覆盖率分析」。此时 `review_pass` 的门槛从「覆盖率 ≥ 50%」降级为「无语法错误」——这是合理的降级：没有覆盖率工具时，至少要保证代码能编译。

### 3. 复杂度分析

复杂度回答「代码有多绕」。本关用 `ast` 统计每个文件的函数数、类数、最大嵌套深度。嵌套深度沿 `if/for/while/with/try/函数/类` 递增。最大嵌套深度越大，代码越难理解、越易出 bug。`avg_complexity` 是所有文件最大嵌套深度的平均值。

### 4. 重复代码检测

重复检测回答「有没有复制粘贴」。本关对每行做归一化（去注释、去首尾空白），用 MD5 哈希，统计出现在 ≥ 2 处的归一化行。`duplicate_percent = 重复行数 / 归一化行总数 × 100%`。重复率高说明该抽取公共函数。

### 5. review_pass 判定逻辑

pytest-cov 可用：  review_pass = (coverage >= 50%) AND (duplicate_percent <= 50%) AND (static_warnings <= 100) AND (syntax_errors == 0)
pytest-cov 不可用：review_pass = (syntax_errors == 0)

为什么这样设计？覆盖率工具可用时，我们追求完整的可维护性门槛；不可用时，退而求其次保证最基本的可编译性。教学项目含大量仿真脚本、ROS2 编排入口和样板代码（写 result/存 log/画图/写 portfolio），故覆盖率门槛设为 50%、重复率门槛设为 50%、静态告警上限 100。`review_pass` 是单一布尔门，把多个指标压成一个通过/不通过信号，便于仪表盘读取。

### 6. 答辩四要素

答辩材料（`docs/design/defense_material.md`）必须覆盖四节，缺一不可：

| 要素 | 回答的问题 | 课程对应 |
|---|---|---|
| 设计动机 | 为什么选这套技术栈？每层补足上层什么局限？ | PD→LQR→RL→VLA→C++/ROS2 |
| 实验证据 | 哪个测试证明这个能力达标？ | 8 类毕业门槛测试 |
| 局限性 | 这套方案在什么条件下会失效？ | 实时性、Sim2Real、单目感知 |
| 改进方向 | 失效后怎么改进？给具体技术路径 | 域随机化、DAgger、RT Linux |

数值算例：从配置中取一组实际参数，手算一个时间步，再与代码输出逐项对齐。若两者不同，优先检查单位、左右轮方向、平衡点和数组顺序。

## 三篇论文精读

精读不是摘抄摘要。每篇交付物都要回答六件事：论文解决什么问题、方法怎样工作、哪条公式或哪组实验支撑主张、方法在哪里失效、怎样映射到本项目、引用如何复核。编排脚本会把任务契约写到 `outputs/portfolio/47/paper_reading_tasks.json`，正文按其中的 `deliverable_path` 分别提交。

### 任务 1：轮式双足模型控制

- 论文：Zhao 等，*Design and Control of a Bio-inspired Wheeled Bipedal Robot*。
- 可验证标识：`arXiv:2308.13205`，入口 <https://arxiv.org/abs/2308.13205>。
- 问题：机器人改变机身高度和姿态时，怎样保持轮上平衡，同时满足全身动力学？
- 方法：画出高度可变轮式线性倒立摆、控制李雅普诺夫函数约束和全身控制之间的输入输出关系。
- 公式与实验：定位并解释 $\dot V \le -\gamma V$。写清 $V$、$\gamma$ 和控制输入的意义，再检查深蹲、速度跟踪、外部扰动实验各自支持哪项主张。
- 局限与映射：论文机器人不是 Upkie。至少列出机构、传感器、执行器或算力上的两项差异，并映射到第 17、19、24 关的状态顺序、轮端力矩约束和 MuJoCo 闭环指标。
- 交付物：`outputs/portfolio/47/papers/01_wheeled_biped_control.md`。

### 任务 2：并行强化学习

- 论文：Rudin 等，*Learning to Walk in Minutes Using Massively Parallel Deep Reinforcement Learning*。
- 可验证标识：`arXiv:2109.11978`，正式论文入口 <https://proceedings.mlr.press/v164/rudin22a.html>。
- 问题：大量并行环境怎样缩短训练时间，又不把训练速度误当成真实机器人性能？
- 方法：解释 on-policy 并行采样、PPO 更新和按策略表现调整地形难度的课程学习。
- 公式与实验：写出 PPO clipped objective，解释概率比、优势函数和裁剪范围；从论文记录并行规模、训练时间、仿真到真实迁移证据，注明表号或章节。
- 局限与映射：论文对象是 ANYmal，且使用 GPU 并行。说明为什么其分钟级训练结论不能直接外推到本项目，再映射到第 25-31 关的 PPO、域随机化、固定 seed 和独立评估。
- 交付物：`outputs/portfolio/47/papers/02_parallel_rl.md`。

### 任务 3：视觉语言动作模型

- 论文：Brohan、Zitkovich 等，*RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control*。
- 可验证标识：`arXiv:2307.15818`，正式论文入口 <https://proceedings.mlr.press/v229/zitkovich23a.html>。
- 问题：视觉语言预训练知识怎样进入机器人动作预测，泛化又怎样被受控实验检验？
- 方法：解释机器人轨迹与视觉语言数据共同微调、动作离散为 token、闭环执行和分布偏移评估。
- 公式与实验：写出动作 token 的负对数似然目标 $L=-\sum_t\log p(a_t\mid o_{\le t},l)$，并选一组已见/未见条件对照，区分“语义泛化”与“低层控制稳定”。
- 局限与映射：RT-2 的机械臂数据、模型规模和推理算力都不等于 Upkie。重点分析动作 token、控制延迟和停止命令边界，映射到第 32-37 关的 BC/VLA 闭环与低层安全控制。
- 交付物：`outputs/portfolio/47/papers/03_rt2_vla.md`。

每份精读卡最后附一张“论文主张 → 论文证据 → 本项目对应实验 → 尚未验证”的四列表。引用标识和实验位置必须可回到原文复核；没有读到的内容写“未核验”，不能依据二手摘要补齐。

## C++ 算法训练路线

这条路线不是刷题清单，而是四个可编译、可测试、能进入作品集的里程碑。每一阶段都要提交 `.cpp` 源码、独立测试、构建输出和失败复盘。任务契约位于 `outputs/portfolio/47/cpp_algorithm_route.json`。

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 250.95 330" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="20" y="10" width="211" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="125.5" y="30" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="125.5" dy="0">M1 滑动窗口</tspan>
<tspan x="125.5" dy="22">deque / 单调队列</tspan>
</text>
<line x1="140" y1="62" x2="140" y2="72" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="20" y="72" width="211" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="125.5" y="92" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="125.5" dy="0">M2 先修图</tspan>
<tspan x="125.5" dy="22">哈希表 / 拓扑排序</tspan>
</text>
<line x1="140" y1="124" x2="140" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="20" y="134" width="211" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="125.5" y="154" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="125.5" dy="0">M3 网格规划</tspan>
<tspan x="125.5" dy="22">堆 / Dijkstra</tspan>
</text>
<line x1="140" y1="186" x2="140" y2="196" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="20" y="196" width="211" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="125.5" y="216" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="125.5" dy="0">M4 实验调度</tspan>
<tspan x="125.5" dy="22">二分 / 动态规划</tspan>
</text>
<line x1="140" y1="248" x2="140" y2="258" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="20" y="258" width="211" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="125.5" y="278" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="125.5" dy="0">CTest 日志 + 复杂度说明</tspan>
<tspan x="125.5" dy="22">+ 失败复盘</tspan>
</text>
</svg></div>

| 里程碑 | 明确问题 | 数据结构与算法 | 验收重点 |
|---|---|---|---|
| M1 滑动统计 | 最近 $N$ 个控制周期的 RMSE、最大值、P99 | `std::deque`、单调队列、滑动窗口 | 空输入、$N=1$、重复值、10000 点流式输入；内存 $O(N)$ |
| M2 先修关系图 | 检查课程先修图是否有环并输出合法顺序 | `unordered_map`、`queue`、Kahn 拓扑排序 | DAG、孤立点、重复边、人工环；环节点可定位 |
| M3 受限网格规划 | 障碍和风险代价下求最低代价路径 | `priority_queue`、Dijkstra、父节点回溯 | 可达、不可达、同起终点、高风险绕行；总代价可复算 |
| M4 实验调度 | 时间预算内选择互不冲突实验，使证据价值最大 | `vector`、`lower_bound`、动态规划、回溯 | 空集合、全冲突、贪心失败反例；返回最优值和实验编号 |

源码放在 `outputs/portfolio/47/cpp/`，测试放在其 `tests/` 子目录。每完成一个里程碑，运行任务契约中的 `check_command`；命令通过后，把 CTest 输出保存到相应 `logs/*.txt`。只给出时间复杂度不算通过，还要用测试覆盖边界输入，并在复盘中说明一次失败如何定位。

四个里程碑的节奏是：先写失败测试，再实现最小正确版本，最后才优化复杂度。M1 和 M2 证明基础数据结构与图算法；M3 检查堆、最短路和安全约束；M4 检查动态规划建模。最终答辩随机抽取一个里程碑，要求在十分钟内解释状态、循环不变量、复杂度和一个失败用例。

## 动手检查点

```powershell
python scripts/run_engineering_lab_47.py
python scripts/course_checkpoint.py --chapter 47
```

预期结果：生成五类产物——
- `outputs/reports/code_review_47.md`：人类可读评审报告
- `outputs/reports/code_review_47_metrics.json`：机器可读指标契约
- `outputs/results/engineering_47.json`：课程工程结果契约（`passed=true` 只表示本地自动条件满足）
- `outputs/portfolio/47/paper_reading_tasks.json`：三篇论文精读任务契约
- `outputs/portfolio/47/cpp_algorithm_route.json`：四阶段 C++ 算法路线契约

命令必须从项目根目录运行，原始输出写入 `outputs/`，不能手工改写成「更好看」的结果。

## 可视化证据

代码评审报告（`outputs/reports/code_review_47.md`）是本关的核心可视化证据。它用表格列出每个文件的语法错误、未用导入、长行、函数数、类数、最大嵌套深度，并在摘要表给出模块数、覆盖率、平均复杂度、重复比例、静态告警数、评审通过。

工程类评审没有时间序列图，报告本身就是证据：日志给出文件级数值，测试负责可重复判定 `review_pass`，两者缺一不可。

## 故障诊断挑战

故意制造一个与「代码评审」直接相关的错误：

1. **现象**：临时删除 `tests/` 下某个测试文件，重新运行评审。
2. **第一处异常证据**：如果安装了 pytest-cov，覆盖率会下降；未安装时，`static_warnings` 与 `review_pass` 不变（因为门槛已降级为无语法错误）。
3. **根因假设**：覆盖率统计依赖测试存在；删除测试减少了被覆盖的行。
4. **最小验证**：恢复测试文件，覆盖率回升。
5. **修复后对比**：记录删除前后的 `coverage_percent` 差值。

按「现象 → 第一处异常证据 → 根因假设 → 最小验证 → 修复后对比」记录，不允许通过放宽阈值隐藏失败。

## 三档任务

- **基础任务**：在固定环境下运行 `python scripts/run_engineering_lab_47.py`，解释结果契约的每个输出字段（模块数、覆盖率、avg_complexity、duplicate_percent、static_warnings、review_pass），并说明它为何不能替代外部人工答辩。
- **岗位挑战**：安装 pytest-cov 后重跑，确认覆盖率门槛（≥50%）生效；同时完成三篇精读卡和 M1-M4 C++ 里程碑，确保每份材料都能从引用标识、源码和 CTest 日志回到原始证据。
- **开放探索**：给评审脚本添加一个新指标（如圈复杂度 McCabe、`# noqa` 违规数、TODO/FIXME 计数），先写假设（这个指标能暴露什么问题），再用同一评审协议公平比较添加前后的报告差异。

## 复盘与面试

1. 本关最关键的假设是什么？失效时第一个可观测信号是什么？
   - 假设：源码能被 `py_compile` 编译且 `ast` 解析。失效信号：`syntax_errors > 0`，`review_pass` 立即翻为 0。
2. 为什么 `review_pass` 在 pytest-cov 未安装时降级为「无语法错误」？有哪些可替代方案？
   - 因为覆盖率工具不可用时无法度量测试覆盖，退而保证最基本的可编译性。替代：用纯 `coverage.py`（不依赖 pytest-cov）、或把门槛改为「测试全部通过」。
3. 你能用哪三份证据证明结果可复现？
   - (1) 代码评审报告 Markdown，(2) 指标契约 JSON（含 git_commit、metrics），(3) 结果契约 `engineering_47.json`（含 pass_conditions 与 checks）。
4. 如果 `static_warnings` 突然上升 50%，你先查模型、数据、控制还是部署？为什么？
   - 先查部署——新增依赖、合并的长行、自动生成代码最易引入长行告警；其次查是否有大段复制粘贴导致重复率上升。控制与模型变化一般不直接影响静态指标。

## 证据文件

- 评审脚本：`scripts/tools/run_code_review.py`
- 编排入口：`scripts/run_engineering_lab_47.py`
- 测试：`tests/test_code_review.py`
- 答辩材料：`docs/design/defense_material.md`
- 面试题库：`docs/design/interview_qa_bank.md`（62 题含参考答案）
- 评审报告：`outputs/reports/code_review_47.md`
- 结果契约：`outputs/results/engineering_47.json`
- 论文任务：`outputs/portfolio/47/paper_reading_tasks.json`
- C++ 路线：`outputs/portfolio/47/cpp_algorithm_route.json`
- 作品集：`outputs/portfolio/47/evidence.json`

## 下一关

下一关 `H01` 会把本关结果作为输入，而不是重新开始。
