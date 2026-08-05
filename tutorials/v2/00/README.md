# 00 课程导航与岗位能力地图

> 建设状态：可执行
> 阶段：数学与工具
> 作品集目录：`outputs/portfolio/00`

## 岗位任务

你的第一个交付物不是代码，而是一张"能力地图"——你需要用文档和数据回答一个面试问题：
"这门课学完之后，你能做什么、用什么证据证明、在哪些场景下会失效？"

具体来说，你需要：

1. 理解 9 个阶段（数学与工具 → 机器人仿真 → 经典控制 → 状态估计与优化 → 学习控制 → 应用型 VLA → 工程部署 → 岗位毕业项目 → 硬件选修）之间的依赖关系。
2. 在 `outputs/portfolio/00/` 中放一份你自己的学习路线图（Markdown 或 SVG），标注每阶段的输入、输出和验收条件。
3. 能向面试官解释"为什么仿真错了后面全错"这条因果链。

## 学习目标

- **能理解**：用自己的话画出从 Python 环境到 PPO 训练到 VLA 部署的完整数据流，每个环节说清输入/输出形状。
- **能推导**：不需要公式——但能解释"为什么关卡顺序不可调换"，用前置依赖图证明。
- **能实现**：成功运行环境检查脚本，确认 Python 3.11 + MuJoCo + NumPy 可用。

## 前置关卡

无；这是课程入口。但你需要：

- 一台 Windows 机器（或 WSL2）
- Python 3.11 已安装
- 能打开 PowerShell 并执行命令

## 先观察现象

在运行任何脚本之前，先回答三个问题并写下你的猜测：

1. Upkie 机器人有几个关节？你能说出它们的名称吗？
2. `nq=13, nv=12, nu=6` 分别代表什么？为什么 nq 不等于 nv？
3. 一个轮足机器人保持平衡，需要哪些传感器数据？

写下答案后再往下看。答错没关系——这就是你的"基线"。

## 直觉与概念

<!-- upkie-animation:00-core -->

### 课程是什么

把这门课想象成一份"具身智能工程师的操作手册"。普通课程告诉你"什么是 LQR"，这门课要求你：

1. 手算 LQR 增益矩阵（关卡 17）
2. 在 MuJoCo 仿真里让 Upkie 用这个增益站起来（关卡 17）
3. 在域随机化后测试它还能不能站住（关卡 29）
4. 用残差 RL 补上 LQR 管不了的非线性部分（关卡 30）

每个关卡产出一个**可验证的交付物**，不是选择题答案。

### 岗位能力地图

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 310 568" width="310" height="568" style="display:block">
<defs>
<marker id="cmap" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
</defs>
<rect x="40" y="10" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="30" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段0：数学与工具</text>
<text x="155.0" y="48" text-anchor="middle" fill="#64748b" font-size="10" font-family="inherit">手算与代码验证倒立摆基础模型</text>
<line x1="155" y1="62" x2="155" y2="72" stroke="#64748b" stroke-width="1.5" marker-end="url(#cmap)"/>
<rect x="40" y="72" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="92" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段1：机器人仿真</text>
<text x="155.0" y="110" text-anchor="middle" fill="#64748b" font-size="10" font-family="inherit">建立物理正确的 Upkie MuJoCo 数字样机</text>
<line x1="155" y1="124" x2="155" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#cmap)"/>
<rect x="40" y="134" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="154" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段2：经典控制</text>
<text x="155.0" y="172" text-anchor="middle" fill="#64748b" font-size="10" font-family="inherit">PD、LQR 与速度控制对比实验</text>
<line x1="155" y1="186" x2="155" y2="196" stroke="#64748b" stroke-width="1.5" marker-end="url(#cmap)"/>
<rect x="40" y="196" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="216" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段3：状态估计与优化</text>
<text x="155.0" y="234" text-anchor="middle" fill="#64748b" font-size="10" font-family="inherit">带噪声状态估计与受约束 MPC</text>
<line x1="155" y1="248" x2="155" y2="258" stroke="#64748b" stroke-width="1.5" marker-end="url(#cmap)"/>
<rect x="40" y="258" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="278" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段4：学习控制</text>
<text x="155.0" y="296" text-anchor="middle" fill="#64748b" font-size="10" font-family="inherit">可复现的 PPO 与残差控制基准</text>
<line x1="155" y1="310" x2="155" y2="320" stroke="#64748b" stroke-width="1.5" marker-end="url(#cmap)"/>
<rect x="40" y="320" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="340" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段5：应用型 VLA</text>
<text x="155.0" y="358" text-anchor="middle" fill="#64748b" font-size="10" font-family="inherit">语言条件视觉导航与稳定停车</text>
<line x1="155" y1="372" x2="155" y2="382" stroke="#64748b" stroke-width="1.5" marker-end="url(#cmap)"/>
<rect x="40" y="382" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="402" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段6：工程部署</text>
<text x="155.0" y="420" text-anchor="middle" fill="#64748b" font-size="10" font-family="inherit">将控制链路迁移到 C++ 与 ROS2</text>
<line x1="155" y1="434" x2="155" y2="444" stroke="#64748b" stroke-width="1.5" marker-end="url(#cmap)"/>
<rect x="40" y="444" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="464" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段7：岗位毕业项目</text>
<text x="155.0" y="482" text-anchor="middle" fill="#64748b" font-size="10" font-family="inherit">完整具身控制系统与岗位级作品集</text>
<line x1="155" y1="496" x2="155" y2="506" stroke="#64748b" stroke-width="1.5" marker-end="url(#cmap)"/>
<rect x="40" y="506" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="526" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段H：硬件选修（可选）</text>
<text x="155.0" y="544" text-anchor="middle" fill="#64748b" font-size="10" font-family="inherit">复刻并改进桌面轮足平衡机器人</text>
</svg>

箭头不是"建议先学"，而是"没有前者的输出，后者无法启动"。

### 为什么 nq ≠ nv

这是本关最重要的概念。`nq` 是广义坐标数（position），`nv` 是广义速度数（velocity）。

Upkie 的根部是自由关节（free joint），用四元数表示姿态。四元数有 4 个分量，但角速度只有 3 个分量（绕 x/y/z 轴的旋转速率），所以：

- `nq = 7（自由根部：3 平移 + 4 四元数）+ 6（6 个铰链关节）= 13`
- `nv = 6（自由根部：3 平移速度 + 3 角速度）+ 6（6 个铰链关节速度）= 12`

四元数比角速度多 1 个维度，这是 nq > nv 的根本原因。

## 教科书级展开

### 课程 Manifest 结构

课程元数据存储在 `configs/course/manifest.json`，由程序通过 `src/upkie_mujoco_course/course/manifest.py` 读取。

核心字段：

| 字段 | 含义 | 示例 |
|---|---|---|
| `stages[].id` | 阶段编号 | `"0"` 到 `"7"` + `"H"` |
| `stages[].title` | 阶段名称 | `"数学与工具"` |
| `stages[].project` | 阶段项目目标 | `"手算与代码验证倒立摆基础模型"` |
| `stages[].chapters` | 章节列表 | `[["00", "课程导航与岗位能力地图"], ...]` |

### Upkie 机器人速览

当前使用的 Upkie v2 模型（权威配置：`configs/robot/upkie.json`）：

| 参数 | 值 | 说明 |
|---|---|---|
| `nq` | 13 | 广义坐标维度 |
| `nv` | 12 | 广义速度维度 |
| `nu` | 6 | 执行器（控制输入）维度 |
| 关节 | 6 个 | left_hip, left_knee, left_wheel, right_hip, right_knee, right_wheel |
| 腿部执行器 | 4 个 | 位置控制，单位 rad |
| 轮端执行器 | 2 个 | 力矩控制，单位 N*m，范围 [-1.0, 1.0] |

### 关卡依赖关系

每个关卡的"前置关卡"不是随意指定的。依赖链的核心逻辑：

数学（矩阵、微积分、概率）
↓ 提供计算工具
仿真（MuJoCo 状态、模型加载）
↓ 提供物理正确的数字样机
经典控制（PD、LQR）
↓ 提供线性控制器基线
状态估计（滤波、辨识）
↓ 提供噪声下的真实状态
学习控制（PPO、残差 RL）
↓ 提供非线性策略
VLA（视觉、语言、行为克隆）
↓ 提供多模态决策
部署（C++、ROS2）
↓ 提供生产级系统

## 动手检查点

### 检查点 1：环境确认

```powershell
.\.venv\Scripts\Activate.ps1
```

```powershell
python --version
```

<div style="font-size:13px;color:#666;margin-top:4px">预期：Python 3.11.x</div>

```powershell
python -c "import mujoco; print(mujoco.__version__)"
```

<div style="font-size:13px;color:#666;margin-top:4px">预期：3.x.x</div>

```powershell
python -c "import numpy; print(numpy.__version__)"
```

<div style="font-size:13px;color:#666;margin-top:4px">预期：2.x.x</div>

### 检查点 2：模型审计

```powershell
python scripts/01_check_model.py
```

预期输出包含：

```text
nq = 13
nv = 12
nu = 6
joints: ['left_hip', 'left_knee', 'left_wheel', 'right_hip', 'right_knee', 'right_wheel']
```

如果看到 `ModuleNotFoundError`，说明虚拟环境没有激活或依赖没装。

确认参数后，可以打开 MuJoCo 可视化窗口直观观察机器人模型：

```powershell
python scripts/00_view_model.py --duration 3.0
```

这会打开一个 3D 窗口，显示 Upkie 在重力作用下的自由运动。如果只想在终端验证模型能正常步进（例如无图形界面的服务器），添加 `--no-viewer` 参数：

```powershell
python scripts/00_view_model.py --no-viewer
```

### 检查点 3：Manifest 加载

```powershell
python -c "import sys; sys.path.insert(0, 'src'); from upkie_mujoco_course.course.manifest import load_course_manifest; m = load_course_manifest(); print(f'{len(m[\"stages\"])} stages, {sum(len(s[\"chapters\"]) for s in m[\"stages\"])} chapters')"
```

<div style="font-size:13px;color:#666;margin-top:4px">预期输出类似：9 stages, 58 chapters（含硬件选修）</div>

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 00
```

## 可视化证据

在 `outputs/portfolio/00/` 中创建你的学习路线图，至少包含：

1. **阶段依赖图**：9 个阶段的有向图，标注每阶段的输入/输出。
2. **能力清单**：列出你期望在课程结束时能做到的 5 件事。
3. **基线自评**：对上述 5 件事，用 1-5 分评估你当前的水平。

可视化建议：用 Mermaid 语法写依赖图，后续关卡会教你用飞书画板做更专业的版本。

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 310 442" width="310" height="442" style="display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
</defs>
<rect x="40" y="10" width="230" height="38" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="34" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段0: 数学与工具</text>
<line x1="155" y1="48" x2="155" y2="58" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="40" y="58" width="230" height="38" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="82" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段1: 机器人仿真</text>
<line x1="155" y1="96" x2="155" y2="106" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="40" y="106" width="230" height="38" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="130" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段2: 经典控制</text>
<line x1="155" y1="144" x2="155" y2="154" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="40" y="154" width="230" height="38" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="178" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段3: 状态估计</text>
<line x1="155" y1="192" x2="155" y2="202" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="40" y="202" width="230" height="38" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="226" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段4: 学习控制</text>
<line x1="155" y1="240" x2="155" y2="250" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="40" y="250" width="230" height="38" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="274" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段5: 应用型VLA</text>
<line x1="155" y1="288" x2="155" y2="298" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="40" y="298" width="230" height="38" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="322" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段6: 工程部署</text>
<line x1="155" y1="336" x2="155" y2="346" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="40" y="346" width="230" height="38" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="370" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段7: 毕业项目</text>
<line x1="155" y1="384" x2="155" y2="394" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="40" y="394" width="230" height="38" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="418" text-anchor="middle" fill="#1e293b" font-size="12" font-family="inherit">阶段H: 硬件选修（可选）</text>
</svg></div>

## 故障诊断挑战

**破坏**：把 `configs/course/manifest.json` 中某个阶段的 `chapters` 字段改为空数组 `[]`。

**预期第一处异常**：Manifest 加载代码在解析该阶段时会报告 `chapters` 为空，或者下游依赖该阶段章节数的代码输出 `0 chapters`。

**最小修复**：恢复被清空的 `chapters` 数组。

**验证方法**：重新运行 Manifest 加载命令，确认章节总数恢复。

**为什么不能放宽阈值**：如果你把"允许 0 章节"当作正常状态，后续所有依赖该阶段的学习路径都会静默消失，你甚至不知道自己漏学了什么。

## 三档任务

### 基础任务

- 运行三个检查点，截图保存预期输出。
- 在 `outputs/portfolio/00/` 创建 `roadmap.md`，包含阶段依赖图和个人能力基线。

### 岗位挑战

- 阅读 `configs/robot/upkie.json`，手动计算 nq 和 nv，写出每一步的推导过程。
- 解释为什么轮端执行器用力矩控制（N*m）而不是速度控制（rad/s），从物理直觉和控制理论两个角度回答。

### 开放探索

- 在网上搜索 2-3 个其他双足或轮足机器人项目（如 Cassie、Digit、Unitree H1），比较它们的关节配置与 Upkie 的差异。
- 写一篇 200 字短文：为什么 Upkie 适合作为教学平台而不是这些更复杂的机器人？

## 复盘与面试

1. 本关最关键的假设是什么？

<!-- upkie-qa:00-q1 -->
假设你的环境（Python 3.11 + MuJoCo）已正确配置。失效时的第一个信号是 `import mujoco` 报错或版本号不匹配。后续所有关卡的脚本、测试和验收都建立在这个假设之上，所以本关才把「环境检查通过」作为硬性验收条件，而不是可选项。
<!-- /upkie-qa -->

2. 为什么 nq > nv？

<!-- upkie-qa:00-q2 -->
四元数用 4 个数表示 3 自由度的旋转，多出的 1 维被「长度必须等于 1」的归一化约束消掉。因此广义坐标 `qpos` 里自由基座占 7 维（3 平移 + 4 四元数），而广义速度 `qvel` 里只占 6 维（3 线速度 + 3 角速度），所以 nq=13 比 nv=12 多 1。面试时画一个单位球面就能解释清楚：四元数被限制在球面上，真正的自由度只有 3 个。
<!-- /upkie-qa -->

3. 为什么关卡顺序不可调换？

<!-- upkie-qa:00-q3 -->
因为每个关卡的输出是下一个关卡的输入：环境检查产出可用的仿真器，建模关卡产出经验证的机器人模型，控制关卡再在这个模型上设计控制器。如果跳过仿真直接学 PPO，你训练出来的策略会在一个物理错误的模型上运行，得到的奖励曲线再好看也无法迁移到真实机器人上。
<!-- /upkie-qa -->

4. 你能用哪三份证据证明环境可用？

<!-- upkie-qa:00-q4 -->
(a) `python --version` 输出 3.11.x；(b) `import mujoco` 成功并输出版本号；(c) `scripts/01_check_model.py` 正确输出 nq=13, nv=12, nu=6。三份证据分别覆盖解释器版本、依赖安装和模型加载三个层次，缺一不可：前两项通过只能说明库装好了，只有第三项能证明机器人模型本身可以被正确解析。
<!-- /upkie-qa -->

## 下一关

关卡 `01`（Python 科学计算环境）会假设你已经能激活虚拟环境并运行基本 Python 命令。本关的 Manifest 理解和环境检查能力是后续所有关卡的基础——如果环境配错了，后面每一步的输出都不可信。
