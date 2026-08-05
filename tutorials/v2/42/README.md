# 42 日志、测试与性能分析

> 建设状态：可执行  
> 阶段：工程部署  
> 作品集目录：`outputs/portfolio/42`

## 岗位任务

在 ROS2 Jazzy 控制节点中实现 9 字段统一日志契约（JSON lines），通过 ament_cmake_gtest 验证字段完整性、时间戳单调性和失效字段拒绝，采集 10 秒稳态日志验证 100Hz 周期 deadline。你需要交付的不只是运行截图，而是可解释设计、固定配置、量化指标和失败分析。

## 学习目标

- 能理解：用自己的话说明"统一日志契约"解决什么工程问题——可观测性（知道系统在做什么）、可审计性（事后能追责）、可复现性（能用日志重放实验）。
- 能推导：从 9 个字段的物理含义和单位出发，解释 timestamp_ns 单调性为什么是硬约束，deadline 12ms 判定线从何而来。
- 能实现：运行检查点，保存测试、日志、图表三类证据，并能解释失效字段拒绝机制的退出码语义。

## 前置关卡

完成 `41` 的证据验收，或通过先修诊断。第 41 关建立了 100Hz 控制循环的时延基线，本关在此基础上为该循环加上可观测的日志层。

## 先观察现象

先看错误基线：关闭或故意破坏本关关键环节，记录机器人姿态、接触、动作和日志最先出现的异常。不要先读结论；先写下三个观察，再提出一个可被数据推翻的原因假设。

**观察示例**：
1. 删除日志中一条记录的 `timestamp_ns` 字段后，分析脚本立即退出码 1，不生成任何图表。
2. 把两条日志的时间戳颠倒后，分析脚本报告"第 2 行：时间戳乱序"并拒绝继续。
3. 正常日志 3034 行中，跳过前 1000 行预热后，稳态段 2033 个周期零 deadline miss。

## 直觉与概念

<!-- upkie-animation:42-core -->

工程部署关注接口、时间、故障和复现。平均能跑不等于最坏情况安全。

本关核心问题是：**如何用可测量证据判断"日志契约"已经达到岗位可用，而不是只在一次演示中碰巧工作？**

### 为什么需要统一日志契约

机器人控制系统的调试和验收依赖三类证据：日志（发生了什么）、测试（能否重复判定）、可视化（趋势和分布）。如果每次实验的日志格式都不一样——字段名不同、单位混乱、时间戳缺失——那么：

- **可观测性丧失**：无法在故障发生后回溯"当时控制循环周期是多少"，因为日志里根本没记录。
- **可审计性丧失**：无法证明"这次测试和上次测试用的是同一套控制律"，因为日志里没有 git commit。
- **可复现性丧失**：无法用日志重放实验，因为缺少状态、动作和配置的完整快照。

统一日志契约的本质是：**把"可观测、可审计、可复现"从口号变成可机器校验的硬约束**。9 个字段不是随便选的，而是覆盖了"何时（timestamp_ns）、哪次实验（episode_id）、哪个版本（git_commit）、什么状态（pitch_rad/pitch_rate_rad_s）、什么动作（raw/clamped_torque）、安全与否（safety_flag）、周期多长（loop_cycle_ms）"的完整闭环。

## 教科书级展开

### 9 字段统一日志契约

每行日志是一个 JSON 对象（JSON lines 格式，每行一条），包含恰好 9 个字段：

timestamp_ns          : 整数，纳秒级时间戳，必须单调非降
episode_id            : 整数，实验 episode 编号
git_commit            : 字符串，代码版本 commit hash
pitch_rad             : 浮点数，俯仰角（rad）
pitch_rate_rad_s      : 浮点数，俯仰角速度（rad/s）
raw_torque_common_nm  : 浮点数，限幅前力矩（N·m）
clamped_torque_common_nm : 浮点数，限幅后力矩（N·m）
safety_flag           : 整数，安全状态标志（0=正常, 1=协方差无效, 2=力矩饱和, 3=FAULT 状态）
loop_cycle_ms         : 浮点数，本帧控制循环周期（ms）

阅读契约时按七层顺序检查：

1. **直觉**：9 个字段覆盖"何时、哪个版本、什么状态、什么动作、安全吗、多快"六个维度。
2. **符号**：`timestamp_ns` 的 `_ns` 后缀明确单位是纳秒；`_rad`、`_rad_s`、`_nm` 后缀分别声明弧度、弧度每秒、牛·米。
3. **物理意义**：`pitch_rad` 是机身俯仰角，0 表示直立；`raw_torque_common_nm` 是 PD 控制器算出的力矩，`clamped_torque_common_nm` 是限幅到 ±1 N·m 后的实际输出。
4. **设计动机**：同时记录限幅前后力矩，可以诊断"力矩饱和是否导致失控"；记录 `git_commit` 可以追溯"这次实验用的是哪个版本的代码"。
5. **逐步推导**：从 PD 控制律 `τ = Kp·pitch + Kd·pitch_rate` 出发，`raw_torque` 是公式直接输出，`clamped_torque` 是 `clip(raw, -1, 1)`，两者之差就是饱和量。
6. **数值算例**：pitch=0.1 rad, pitch_rate=0, Kp=3.0, Kd=0.8 → raw_torque=0.3 N·m, clamped_torque=0.3 N·m（未饱和）；若 pitch=0.5 rad → raw_torque=1.5 N·m, clamped_torque=1.0 N·m（饱和 0.5 N·m）。
7. **代码映射**：`scripts/tools/analyze_engineering_42_logs.py` 的 `REQUIRED_FIELDS` 元组定义了这 9 个字段，`parse_log_lines` 函数逐行校验。

### JSON lines 格式

每行一个独立 JSON 对象，用换行符分隔：

```json
{"timestamp_ns": 1000000000, "episode_id": 0, "git_commit": "abc1234", "pitch_rad": 0.1, "pitch_rate_rad_s": 0.0, "raw_torque_common_nm": 0.3, "clamped_torque_common_nm": 0.3, "safety_flag": 0, "loop_cycle_ms": 10.0}
{"timestamp_ns": 1010000000, "episode_id": 0, "git_commit": "abc1234", "pitch_rad": 0.09, "pitch_rate_rad_s": -0.5, "raw_torque_common_nm": 0.27, "clamped_torque_common_nm": 0.27, "safety_flag": 0, "loop_cycle_ms": 10.0}
```

选择 JSON lines 而非单个 JSON 数组的原因：流式写入（控制节点每帧追加一行，不需要在结束时合并）、容错性（一行损坏不影响其他行解析）、可增量分析（可以用 `head`/`tail` 截取片段）。

### timestamp_ns 单调性

`timestamp_ns` 必须单调非降（允许相等，不允许倒退）。原因：

- **物理约束**：时间不会倒流。如果日志中出现时间戳倒退，说明数据链路出现异常（重放、缓冲区乱序、多线程竞争）。
- **周期计算依赖**：周期 = `curr_timestamp - prev_timestamp`。如果时间戳倒退，周期为负数，统计无意义。
- **校验规则**：`curr < prev` 视为乱序，立即退出码 1，报告行号和前后值。相等（`curr == prev`）允许，视为零周期。

### safety_flag 四值语义

0 = 正常（NORMAL）            控制循环正常运行，力矩正常输出
1 = 协方差无效（COV_INVALID）  pitch==0 且 IMU 协方差检测无效
2 = 力矩饱和（TORQUE_SAT）    |raw_torque| > 1.0，执行器限幅触发
3 = FAULT 状态（FAULT）       安全状态机进入 FAULT，力矩门控关闭

`safety_flag` 是安全状态机（第 43 关）的可观测投影。在本关的稳态日志中，`safety_flag` 全程为 0（正常）。

### deadline 判定

控制循环目标周期 10ms（100Hz），deadline 判定线 12ms（`DEADLINE_MS = 12.0`）。周期超过 12ms 视为 deadline miss。判定线留 2ms 余量的原因：操作系统调度抖动、ROS2 wall_timer 精度、WSL2 跨文件系统开销。

本关采集的 10 秒稳态日志（跳过前 1000 行预热后）共 2033 个周期样本：
- 均值 10.000 ms
- P99 10.269 ms
- 最大 10.433 ms
- deadline miss 0 次

适用范围是当前关卡声明的平衡点、约束和数据分布。接触丢失、传感器过期、动作饱和、输入超出训练分布或公式假设不成立时，必须进入诊断/安全路径，不能继续外推。

## 动手检查点

### 1. 运行日志分析实验

> **日志文件来源**：`outputs/logs/engineering_42_log.jsonl` 由 ROS2 Jazzy 控制节点在 100Hz 控制循环中实时采集生成（每帧追加一行 JSON）。如果你的环境尚未配置 ROS2 控制节点，可以用以下 Python 命令生成一份符合 9 字段契约的模拟日志用于分析练习：
> ```powershell
> python -c "import json, time; fields = ['timestamp_ns','episode_id','git_commit','pitch_rad','pitch_rate_rad_s','raw_torque_common_nm','clamped_torque_common_nm','safety_flag','loop_cycle_ms']; base = int(time.time()*1e9); lines = [json.dumps(dict(zip(fields, [base+i*10_000_000, 0, 'sim', 0.01, 0.0, 0.3, 0.3, 0, 10.0]))) for i in range(1000)]; open('outputs/logs/engineering_42_log.jsonl','w').write('\n'.join(lines)+'\n'); print(f'已生成 {len(lines)} 行模拟日志')"
> ```

```powershell
python scripts/run_engineering_lab_42.py --log-path outputs/logs/engineering_42_log.jsonl
```

该命令调用 `scripts/tools/analyze_engineering_42_logs.py` 解析 JSON lines 日志，生成周期延迟直方图和状态-力矩时间序列，合并 C++ 端 GoogleTest 统计，最终写出结果契约 `outputs/results/engineering_42.json`。

### 2. 运行关卡自动验收

```powershell
python scripts/course_checkpoint.py --chapter 42
```

命令必须从项目根目录运行，原始输出写入 `outputs/`，不能手工改写成"更好看"的结果。

### 3. 运行 Python 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_engineering_42.py
```

测试覆盖：正常日志生成两张图表、缺失字段被拒绝、时间戳乱序被拒绝、JSON 解析失败被拒绝、编排入口写出结果契约。

## 可视化证据

至少生成以下两张图表：

1. **周期延迟直方图**（`outputs/plots/engineering_42_latency_histogram.png`）：横轴周期（ms），纵轴频次；标注均值、P99、deadline 三条竖线。直方图回答"周期分布是否集中、有没有长尾"。

2. **状态-力矩时间序列**（`outputs/plots/engineering_42_state_torque_timeseries.png`）：双 y 轴，左轴画 pitch_rad 和 pitch_rate_rad_s，右轴画 raw_torque 和 clamped_torque，safety_flag 变化点用橙色虚线标注。时间序列回答"状态和动作是否耦合、限幅是否触发"。

视觉只回答"发生了什么"，日志给出时间与数值，测试负责可重复判定；三者缺一不可。

## 故障诊断挑战

**场景**：故意删除一条日志中的 `timestamp_ns` 字段，确认分析脚本的失效拒绝机制。

**现象**：分析脚本退出码 1，不生成任何图表。

**第一处异常证据**：stderr 输出 `第 1 行：缺少字段 timestamp_ns`。

**根因假设**：`parse_log_lines` 函数对每行做字段完整性校验，`REQUIRED_FIELDS` 中的 9 个字段缺一不可。

**最小验证**：运行 `tests/test_engineering_42.py::test_missing_timestamp_rejected`，确认退出码 1 且错误消息包含"缺少字段 timestamp_ns"。

**修复后对比**：恢复 `timestamp_ns` 字段后，分析脚本退出码 0，正常生成两张图表。

按"现象 -> 第一处异常证据 -> 根因假设 -> 最小验证 -> 修复后对比"记录，不允许通过放宽阈值隐藏失败。

## 三档任务

- **基础任务**：在固定 seed 下通过本关检查点（`tests/test_engineering_42.py` 全部通过），并解释每个输出字段的物理含义和单位。
- **岗位挑战**：在 ROS2 Jazzy 中采集 10 秒稳态日志（100Hz × 10s = 1000 帧），通过 `--warmup-skip` 剔除启动瞬态后，报告 mean/P99/max 周期和 deadline miss 数。本关实际采集 3034 行，跳过前 1000 行预热后稳态段 2033 个周期零 miss。
- **开放探索**：在 9 字段契约中添加一个新字段（如 `battery_voltage_v`），先写假设"该字段能帮助诊断什么故障"，再修改 `REQUIRED_FIELDS` 和分析脚本，用同一评估协议验证假设。

## 复盘与面试

1. 本关最关键的假设是什么？失效时第一个可观测信号是什么？

<!-- upkie-qa:42-q1 -->
最关键的假设是：9 字段契约完整即足以复现控制行为。这 9 个字段（`timestamp_ns`、`episode_id`、`git_commit`、`pitch_rad`、`pitch_rate_rad_s`、`raw_torque_common_nm`、`clamped_torque_common_nm`、`safety_flag`、`loop_cycle_ms`）覆盖了"何时、哪个版本、什么状态、什么动作、安全吗、多快"六个维度，缺任何一个都无法事后重建当时的控制决策。这个假设失效时，第一个可观测信号不是机器人行为异常，而是分析脚本退出码 1——`parse_log_lines` 函数对每行做字段完整性校验，`REQUIRED_FIELDS` 中的 9 个字段缺一不可，缺失任何一个立即拒绝继续分析，不生成任何图表。本关的故障诊断挑战就是验证这个机制：删除一条日志的 `timestamp_ns` 字段后，stderr 输出"第 1 行：缺少字段 timestamp_ns"，退出码 1；把两条日志时间戳颠倒后，报告"第 2 行：时间戳乱序"并拒绝继续。这种"宁可拒绝分析也不接受不完整数据"的设计是刻意的：一份有缺失字段的日志给出的分析结论比没有分析更危险，因为它看起来有数据支撑但实际上基于不完整信息。面试时的判断框架：日志契约的价值不在于"记录了什么"，而在于"拒绝记录什么"——失效拒绝机制比字段本身更重要。常见误区是"日志越详细越好"，实际上字段越多契约越脆弱，9 个字段是在"足够复现"和"容易维护"之间的平衡点。
<!-- /upkie-qa -->

2. 为什么当前接口、单位和限幅这样设计？有哪些可替代方案？

<!-- upkie-qa:42-q2 -->
`timestamp_ns` 用纳秒整数而非毫秒，是因为 100 Hz 控制循环的周期是 10 ms，毫秒精度下相邻帧时间戳差仅为 10，统计粒度严重不足——P99 和均值的差异（本关实测：均值 10.000 ms、P99 10.269 ms、最大 10.433 ms）在毫秒精度下完全无法分辨，纳秒精度才能捕捉到 0.269 ms 的 P99 偏移。字段名后缀（`_rad`、`_rad_s`、`_nm`）是单位声明的一部分，避免"这个 0.1 是弧度还是度"的歧义。同时记录 `raw_torque_common_nm` 和 `clamped_torque_common_nm` 的设计动机是诊断力矩饱和：两者之差就是饱和量，本关数值算例里 pitch=0.5 rad 时 raw=1.5 N·m、clamped=1.0 N·m（Kp=3.0），饱和 0.5 N·m 这个信息在只有 clamped 的日志里完全丢失。`safety_flag` 的四值语义（0=正常、1=协方差无效、2=力矩饱和、3=FAULT）是第 43 关安全状态机的可观测投影，本关稳态日志里全程为 0。替代方案：用 ROS2 内置的 `time_msg`（sec+nsec 双字段）代替单整数纳秒，语义更标准，但 JSON lines 里单整数更易解析、更易用 `head`/`tail` 截取片段做增量分析。常见误区是"单位写在文档里就够了"——文档会过期，字段名后缀不会，把单位编码进字段名是最持久的防歧义手段。
<!-- /upkie-qa -->

3. 你能用哪三份证据证明结果可复现？

<!-- upkie-qa:42-q3 -->
三份证据对应三类验收需求，缺一不可。第一份是结果契约 `outputs/results/engineering_42.json`：包含 `git_commit`（代码版本）和 seed（随机种子），让别人能在完全相同的代码版本和随机条件下重跑实验；这是可审计性的基础——没有 git_commit，"上次实验用的是哪个版本的控制律"就无法追溯。第二份是原始日志 `outputs/logs/engineering_42_log.jsonl`：3034 行 JSON lines，每行 9 个字段，是实验的完整原始记录；跳过前 1000 行预热后，稳态段 2033 个周期的均值 10.000 ms、P99 10.269 ms、最大 10.433 ms、deadline miss 0 次——这些数字都可以从原始日志重新计算验证，不依赖任何中间处理结果。第三份是可视化图表：周期延迟直方图（`engineering_42_latency_histogram.png`，标注均值/P99/deadline 三条竖线）和状态-力矩时间序列（`engineering_42_state_torque_timeseries.png`，双 y 轴，safety_flag 变化点用橙色虚线标注）；图表回答"分布形状是否正常、有没有长尾"，这是纯数字无法直观传达的。三份证据的分工：JSON 契约给出机器可读的通过/失败判定，原始日志给出可重算的数值，图表给出人类可审查的趋势。面试时的判断框架：如果面试官问"你怎么证明这不是碰巧通过"，答案是固定 git_commit + 固定 seed + 原始日志可重算。常见误区是只交图表——图表不能重算，原始日志才能让别人验证你的 P99 数字没有算错。
<!-- /upkie-qa -->

4. 如果指标退化 20%（如 P99 从 10.3ms 升到 12.4ms），你先查模型、数据、控制还是部署？为什么？

<!-- upkie-qa:42-q4 -->
先查部署，而且这个判断几乎是确定的。理由：P99 从 10.269 ms 升到 12.4 ms 已经超过了 deadline 判定线 12 ms（`DEADLINE_MS = 12.0`，留 2 ms 余量），这意味着控制循环的实时性恶化，而不是控制律本身出了问题。控制律是 PD 点积（`τ = Kp·pitch + Kd·pitch_rate`，Kp=3.0、Kd=0.8），计算量是纳秒级的，不可能贡献毫秒级的延迟退化；模型和数据更不相关——本关没有训练任何模型。最可能的根因是部署环境变化：WSL2 的调度抖动（WSL2 的时钟中断和 Windows 主机共享，主机负载高时 WSL2 进程会被延迟调度）、CPU 频率降频（`cpufreq` 从 `performance` 切到 `powersave`，空闲时降频导致唤醒延迟）、或者后台进程抢占（防病毒扫描、Windows Update）。排查步骤：先重跑 `python scripts/run_engineering_lab_42.py` 确认退化是否可复现，再看 `loop_cycle_ms` 的直方图是整体右移（系统性延迟，指向 CPU 降频）还是出现长尾（偶发抢占，指向后台进程），最后检查运行环境的 CPU 频率设置和后台进程列表。面试时的判断框架：延迟退化的排查顺序是"环境 → 调度 → 代码"，控制律代码在延迟分析里几乎永远是最后才查的。常见误区是一看到 P99 变大就去调控制参数，完全忽略了运行环境这个最可能的根因。
<!-- /upkie-qa -->

## 下一关

下一关 `43` 会把本关的 `safety_flag` 字段升级为完整的五状态安全状态机，实现故障检测和力矩门控。
