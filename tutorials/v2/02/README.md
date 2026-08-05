# 02 Git 与可复现实验

> 建设状态：可执行  
> 阶段：数学与工具  
> 作品集目录：`outputs/portfolio/02`

## 岗位任务

同事交给你一条“训练效果很好”的曲线，却没有 commit、seed 和配置。你无法判断它来自当前代码、旧模型还是一次偶然的随机初始化。

本关要建立最小可复现实验契约：任何结果都必须能追溯到代码版本、配置、随机种子、指标、原始日志和图表。交付物不是一句“我跑过了”，而是一份别人能重新执行的证据索引。

## 学习目标

- **理解**：区分工作区、提交、配置、随机种子和实验结果的职责。
- **推导**：解释为什么相同 seed 只保证随机源一致，不自动保证所有计算确定性。
- **实现**：生成两条相同 seed 的完全一致轨迹，并用哈希证明字节级一致。

## 前置关卡

完成 `01`，能够确认解释器、数组形状、数据类型和有限性。若这些信息不稳定，Git 记录再完整也无法复现实验。

## 先观察现象

下面三条实验声明，哪一条能被审查？

1. “昨天跑得挺稳，图在聊天记录里。”
2. “使用 PPO，seed 大概是 0，代码应该没改。”
3. “commit、配置、seed、指标、日志和图表路径都写入结果 JSON。”

只有第三条建立了从结论返回原始证据的路径。截图可以展示现象，但无法证明代码版本和参数。

## 直觉与概念

<!-- upkie-animation:02-core -->

### Git 不是云盘

Git 保存的是有结构的代码历史。commit 是一次带唯一标识的代码快照；工作区中的未提交修改不属于该快照。实验结果记录 commit 后，还必须记录工作区是否有额外修改。

### seed 是随机数发生器的起点

伪随机数不是“真正随意”，而是确定算法生成的序列。相同算法、相同 seed 和相同调用顺序会产生相同序列；调用次数变化，后续值也会变化。

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 200" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="16" y="12" width="130" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="81.0" y="33" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">Git commit</text>
<rect x="156" y="12" width="120" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="216.0" y="33" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">配置文件</text>
<rect x="296" y="12" width="100" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="346.0" y="33" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">seed</text>
<rect x="436" y="12" width="140" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="506.0" y="32" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="506.0" dy="0">软件与硬件</tspan>
<tspan x="506.0" dy="22">环境</tspan>
</text>
<polyline points="81,44 81,68 596,68" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="216,44 216,68 596,68" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="346,44 346,68 596,68" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="506,64 506,68 596,68" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="596" y1="68" x2="596" y2="80" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="536" y="80" width="120" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="596.0" y="101" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">实验身份</text>
<line x1="596" y1="112" x2="596" y2="130" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="110" y="130" width="58" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="139.0" y="151" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">运行</text>
<line x1="168" y1="146" x2="290" y2="146" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="290" y="130" width="93" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="336.6" y="150" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="336.6" dy="0">指标 日志</tspan>
<tspan x="336.6" dy="22">图表 视频</tspan>
</text>
<line x1="383" y1="146" x2="470" y2="146" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="470" y="130" width="103" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="521.5" y="151" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">作品集证据</text>
</svg></div>

## 教科书级展开

### 1. 可复现实验的七个字段

experiment = code + config + seed + environment + data + metrics + artifacts

| 字段 | 回答的问题 | 本项目位置 |
|---|---|---|
| code | 运行的是哪一版代码 | `git_commit` |
| config | 控制器、环境和训练参数是什么 | `config` |
| seed | 随机序列从哪里开始 | `seed` |
| environment | Python 与依赖版本是什么 | 日志或锁定依赖 |
| data | 输入数据或场景是什么 | 数据集元数据 |
| metrics | 如何量化好坏 | `metrics` |
| artifacts | 原始证据在哪里 | `plots/videos/logs` |

漏掉任一字段都不一定让结果立刻错误，但会缩短证据的可追溯链。

### 2. 相同 seed 为什么产生相同序列

把伪随机数发生器抽象成状态更新：

s_(k+1) = F(s_k)
r_k = G(s_k)

`s_0` 由 seed 初始化。若两次运行的 `s_0` 相同，且每一步调用 `F`、`G` 的顺序相同，则所有 `r_k` 相同。

本关固定 `seed=0` 生成 128 个标准正态样本。真实结果：

same_seed_max_difference = 0.0
different_seed_mean_difference = 1.0563434493906498
trace_sha256_length = 64

`same_seed_max_difference=0` 表示数组逐元素一致；SHA-256 再把整个字节序列压缩成 64 位十六进制指纹。哈希相同是强证据，但不能说明算法“效果好”，只说明输入序列一致。

### 3. seed 的适用边界

固定 seed 仍可能无法完全复现，常见原因包括：

- 多线程调度顺序不同；
- GPU 算子使用非确定性实现；
- 库版本或底层 BLAS 不同；
- 输入数据顺序或预处理变化；
- 工作区有未提交修改；
- 代码中存在时间、网络或系统熵输入。

所以 seed 是必要条件，不是充分条件。

### 假设、适用范围与失效条件

- 假设使用同一种随机数发生器、相同库版本和相同调用顺序；
- 本关只验证 CPU 上 NumPy 随机序列的字节级一致，不代表 GPU 训练逐位确定；
- commit 只描述已提交代码，工作区修改、外部数据和环境版本必须另行记录；
- 哈希用于识别输入是否一致，不能证明指标正确或算法安全；
- 依赖并发、网络、系统时间或未固定数据顺序时，本契约不足以保证完全复现。

### 4. 代码映射

```python
first = seeded_normal_trace(seed=0, size=128)
repeated = seeded_normal_trace(seed=0, size=128)
different = seeded_normal_trace(seed=1, size=128)

same_difference = np.max(np.abs(first - repeated))
digest = hashlib.sha256(first.tobytes()).hexdigest()
```

统一结果由 `write_experiment_result` 写入，它会自动加入创建时间、commit、通过条件和每项检查结果。

## 动手检查点

先观察当前代码身份：

```powershell
git rev-parse --short HEAD
git status --short
```

`git status --short` 有输出并不等于实验无效，但必须承认当前结果包含未提交修改，不能把它错误归因于已有 commit。

运行专属实验：

```powershell
python scripts/run_foundation_lab.py --chapter 02 --seed 0
```

再运行关卡验收：

```powershell
python scripts/course_checkpoint.py --chapter 02
```

应生成：

- `outputs/results/foundation_02.json`
- `outputs/logs/foundation_02.json`
- `outputs/plots/foundation_02.png`
- `outputs/portfolio/02/evidence.json`
- `outputs/results/checkpoint_02.json`

常见失败一：相同 seed 仍不同。检查是否复用了同一个随机数发生器并在中间多调用了一次。  
常见失败二：结果里 commit 是 `unknown`。确认命令从 Git 仓库根目录运行，且系统能找到 `git`。

## 可视化证据

`outputs/plots/foundation_02.png` 中两条 `seed=0` 轨迹应完全重合，`seed=1` 明显不同。重合曲线是视觉证据；SHA-256 和差异指标是日志证据；自动测试是重复判定。

通过本关后，你获得的是第一个可放进作品集的“实验身份卡”：任何人都能沿 `evidence.json -> result -> log/plot` 返回原始事实。

## 故障诊断挑战

分别运行：

```powershell
python scripts/run_foundation_lab.py --chapter 02 --seed 0
python scripts/run_foundation_lab.py --chapter 02 --seed 1
```

第二次会覆盖默认结果路径，这是有意设计的诊断任务。比较两次终端指标并回答：为什么 `same_seed_max_difference` 仍为 0，而生成的轨迹哈希会变化？因为每次实验内部都比较“当前 seed 与其重复运行”，但实验之间的 seed 不同。

岗位记录中必须把 seed 当作实验主键的一部分；需要并存多个 seed 时，应使用不同输出目录或在上层批量评估中保存每个 episode。

## 三档任务

- **基础任务**：运行 seed 0 实验，解释统一结果 JSON 的每个一级字段。
- **岗位挑战**：连续运行 seed 0、1、2，建立对比表，不能只挑最好的一次。
- **开放探索**：调查 PyTorch 确定性设置，区分 CPU、CUDA 和 MuJoCo 中仍可能存在的非确定来源。

## 复盘与面试

1. commit 相同是否保证结果相同？为什么不保证？

<!-- upkie-qa:02-q1 -->
不保证。commit 只锁定了代码本身，而结果还取决于代码之外的因素：依赖库版本（NumPy/MuJoCo 升级可能改变数值细节）、随机种子、配置文件、命令行参数、操作系统与硬件（不同 CPU 的浮点运算顺序可能不同）、以及工作区里未提交的修改。所以可复现实验要同时记录 commit + 依赖版本 + seed + 完整配置，缺一不可。
<!-- /upkie-qa -->

2. seed 相同是否保证多线程训练逐位一致？为什么？

<!-- upkie-qa:02-q2 -->
不保证。seed 只能固定随机数生成器的输出序列，但多线程/多进程环境下各线程的执行顺序由操作系统调度决定，每次运行都可能不同：谁先拿到任务、梯度以什么顺序累加都会变。而浮点加法不满足结合律（$(a+b)+c \ne a+(b+c)$），累加顺序不同就会产生逐位差异，并在长训练中被逐步放大。GPU 的非确定性算子也是同类来源。因此多线程训练只能期望统计意义上的可复现（曲线趋势一致），而不是逐位一致。
<!-- /upkie-qa -->

3. 为什么截图不能替代原始 JSON 和日志？

<!-- upkie-qa:02-q3 -->
截图只是结果的「渲染」，不是结果本身：(a) 不可机读，无法用脚本重新校验或对比两次实验；(b) 信息有损，看不到完整精度的数值、运行参数和环境信息；(c) 无法验证来源，截图可以被裁剪、修改，也可能来自另一次运行。原始 JSON 和日志则包含完整数值与实验身份（commit、seed、配置），可以被程序重新验证。截图可以作为辅助展示，但证据链的根必须是机读文件。
<!-- /upkie-qa -->

4. 工作区有未提交修改时，怎样诚实记录实验身份？

<!-- upkie-qa:02-q4 -->
在实验记录里同时写入 commit 哈希和「工作区是否干净」的标记（如 `git status --porcelain` 是否为空，或记录 `dirty=true`），最好连同 `git diff` 的内容或其哈希一起保存。这样任何人看到记录就知道：这次结果对应的代码 = 某 commit + 某些未提交修改，而不是假装结果来自干净的 commit。更规范的做法是：重要实验前先提交，让工作区保持干净。
<!-- /upkie-qa -->

5. 哈希相同能证明什么，不能证明什么？

<!-- upkie-qa:02-q5 -->
能证明：两份文件的字节内容逐位相同（碰撞概率可忽略），例如两次运行产出的数据完全一致、文件在传输中未被篡改。不能证明：内容本身是「正确」的——如果算法有 bug，两次运行会稳定地产出同样错误的结果，哈希依然相同。换句话说，哈希验证的是「一致性/完整性」，不是「正确性」；正确性需要独立的验证手段（解析解、物理量纲检查、测试）来背书。
<!-- /upkie-qa -->

## 下一关

下一关 `03` 使用本关的固定配置和证据格式，处理机器人软件中最常见的几何错误：同一个点在机身坐标系和世界坐标系中为什么会有不同数字。
