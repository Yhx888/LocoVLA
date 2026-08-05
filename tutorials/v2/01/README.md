# 01 Python 科学计算环境

> 建设状态：可执行  
> 阶段：数学与工具  
> 作品集目录：`outputs/portfolio/01`

## 岗位任务

你刚接手一段姿态估计代码。它能运行，却偶尔把机器人控制器送进 `NaN`：有人把角度写成整数数组，有人把 `(时间, 特征)` 的轴放反，还有人混用了度和弧度。

本关交付一份可审查的科学计算环境证据，证明你能：

- 确认 Python、NumPy 和项目环境来自预期解释器；
- 读懂数组的 `shape`、`dtype` 和单位；
- 用向量化计算构造俯仰角与俯仰角速度；
- 在数据进入控制器前发现 `NaN`、无穷大和形状错误。

## 学习目标

- **理解**：说清列表、NumPy 数组、样本轴和特征轴的区别。
- **推导**：从“变化量除以时间”得到离散速度的单位。
- **实现**：运行本关实验，生成结果、日志、曲线和作品集索引。

## 前置关卡

完成 `00` 的导航诊断即可。若你已经熟悉虚拟环境和 NumPy，可直接运行本关检查点；不能解释输出字段时仍需阅读本章。

## 先观察现象

下面三段代码都“像是数组”，但工程语义完全不同：

```python
angle_a = np.array([0, 0.1, 0.2], dtype=int)       # 小数被截断
angle_b = np.array([[0.0, 0.1, 0.2]])             # shape=(1, 3)
angle_c = np.array([0.0, np.nan, 0.2])            # 含非有限值
```

先不要急着修。分别预测：第二个样本是什么、控制器会读到几个特征、数值微分后会出现什么。岗位诊断的第一步不是“换个参数”，而是确认数据契约。

## 直觉与概念

<!-- upkie-animation:01-core -->

### Python 环境是什么

大白话说，环境就是“这次运行究竟使用哪一个 Python，以及它能找到哪一组库”。同一台电脑可以有多个 Python；`pip install` 成功不代表课程脚本使用了那个环境。

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 883.2 82" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="20" y="18" width="88" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="64.0" y="39" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">课程命令</text>
<line x1="108" y1="34" x2="130" y2="34" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="130" y="18" width="129" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="194.5" y="38" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="194.5" dy="0">.venv Python</tspan>
<tspan x="194.5" dy="22">解释器</tspan>
</text>
<line x1="259" y1="44" x2="281" y2="44" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="281" y="18" width="107" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="334.3" y="39" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">NumPy 数组</text>
<line x1="388" y1="34" x2="410" y2="34" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="410" y="18" width="148" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="483.7" y="39" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">形状与有限值检查</text>
<line x1="558" y1="34" x2="580" y2="34" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="580" y="18" width="133" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="646.2" y="39" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">控制或估计算法</text>
<line x1="713" y1="34" x2="735" y2="34" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="735" y="18" width="128" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="799.0" y="39" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">日志 图表 测试</text>
</svg></div>

### ndarray 是什么

`ndarray` 是“同一种数据类型组成的规则多维表格”。对课程中的状态时间序列，统一约定：

- `$shape` — (样本数 N, 每个样本的特征数 D)

例如 201 个时刻，每个时刻保存 `[time, pitch, pitch_rate]`，形状就是 `(201, 3)`。`axis=0` 沿时间走，`axis=1` 在同一时刻选择特征。

## 教科书级展开

### 1. 数据表与单位

记第 `k` 个样本为：

$$
x_{k} = [t_{k}, theta_{k}, omega_{k}]
$$

| 符号 | 含义 | SI 单位 |
|---|---|---|
| `t_k` | 第 k 个采样时刻 | s |
| `theta_k` | 俯仰角 | rad |
| `omega_k` | 俯仰角速度 | rad/s |
| `N` | 样本总数 | 1 |
| `D` | 每个样本的特征数，本例为 3 | 1 |

二维数组 `X` 的第 `k` 行就是 `x_k`。因此 `X[k, 1]` 是第 `k` 个时刻的俯仰角，不是第 1 条轨迹。

### 2. 从连续速度到离散差分

连续角速度定义为：

$$
\omega(t) = d \theta(t) / dt
$$

采样周期为 `Delta t` 时，中心差分使用前后两个样本：

$$
omega_{k} \approx  (theta_{k+1} - theta_{k-1}) / (2 \Delta t)
$$

单位检查：分子是 `rad`，分母是 `s`，结果必然是 `rad/s`。如果代码输出仍标成 `rad`，即使曲线看起来平滑，物理语义也是错的。

本关信号为 `theta(t)=sin(2 pi t)`，解析导数是 `2 pi cos(2 pi t)`。实验使用 201 个样本覆盖 2 秒，`Delta t=0.01 s`。固定运行得到中心区域最大误差：

0.0041333542482888674 rad/s

误差来自离散近似，不是随机噪声。减小采样周期通常会降低截断误差，但过小会放大浮点舍入和传感器噪声，不能无限减小。

### 3. 代码映射

```python
time = np.linspace(0.0, 2.0, 201)
angle = np.sin(2.0 * np.pi * time)
numerical_rate = np.gradient(angle, time)
table = np.column_stack((time, angle, numerical_rate))

assert table.shape == (201, 3)
assert np.isfinite(table).all()
```

`column_stack` 明确把三个一维特征放到列方向。最后两行是进入控制算法前的最低成本防线。

### 假设、适用范围与失效条件

- 采样时刻严格递增，本实验是等间隔 `0.01 s`；
- 角度使用弧度，时间使用秒；
- 数组全部为浮点数且没有缺测；
- `np.gradient` 的端点精度低于内部中心差分，所以验收排除首尾样本；
- 非等间隔采样必须传入真实时间数组，不能假设固定 `Delta t`。

## 动手检查点

先运行专属实验：

```powershell
python scripts/run_foundation_lab.py --chapter 01 --seed 0
```

真实典型输出：

sample_count: 201
feature_count: 3
finite_ratio: 1.0
derivative_max_error_rad_s: 0.0041333542482888674

再运行自动验收：

```powershell
python scripts/course_checkpoint.py --chapter 01
```

通过后应得到：

- `outputs/results/foundation_01.json`
- `outputs/logs/foundation_01.json`
- `outputs/plots/foundation_01.png`
- `outputs/portfolio/01/evidence.json`
- `outputs/results/checkpoint_01.json`

常见失败一：`ModuleNotFoundError`。先检查 `python -c "import sys; print(sys.executable)"` 是否指向项目 `.venv`。  
常见失败二：误差超过阈值。先检查样本数、时间范围和是否把角度改成了度。

## 可视化证据

打开 `outputs/plots/foundation_01.png`。蓝色角度曲线和橙色数值角速度的周期相同，相位相差约四分之一周期。图表只证明“形状随时间怎样变化”；日志负责证明版本、形状和数据类型；测试负责证明同一算法能重复通过。

本关的正向里程碑不是“安装成功”，而是你已经能在算法运行前审计第一条数据边界。

## 故障诊断挑战

运行下面的故障样例：

```powershell
python -c "import numpy as np; x=np.array([0.0,np.nan,0.2]); assert np.isfinite(x).all(), '检测到非有限姿态数据'"
```

按以下顺序记录：

1. 现象：断言失败，而不是控制器稍后随机崩溃；
2. 第一处异常证据：`x[1]` 为 `NaN`；
3. 根因假设：上游除零、缺测或非法类型转换；
4. 最小验证：打印产生 `x[1]` 的输入，不要先删除断言；
5. 修复后对比：`finite_ratio` 必须回到 `1.0`。

## 三档任务

- **基础任务**：解释 `(201, 3)` 中两个数字分别代表什么，并通过本关实验。
- **岗位挑战**：把采样数改为 101 和 401，比较数值微分误差，同时保持 2 秒时长不变。
- **开放探索**：比较前向差分、中心差分和 `np.gradient` 的端点行为，写出选择理由。

## 复盘与面试

1. 为什么 `shape=(3, 201)` 不能在不改下游代码的情况下等价替换 `(201, 3)`？

<!-- upkie-qa:01-q1 -->
两者的数据内容相同，但轴的含义完全不同：`(201, 3)` 是「201 个时刻、每时刻 3 个通道」，`(3, 201)` 是「3 个通道、每通道 201 个时刻」。下游代码里所有按轴操作都绑定了这个约定：例如 `data[i]` 取第 i 个时刻、`data.mean(axis=0)` 求时间平均、切片 `data[:, 0]` 取第一个通道。换成 `(3, 201)` 后这些操作语义全部错位，但很多地方不会报错（广播机制会「好心」地把形状凑对），只会静默地算出错误结果，这比直接报错更危险。
<!-- /upkie-qa -->

2. `dtype=int` 为什么会让小角度数据静默损坏？

<!-- upkie-qa:01-q2 -->
整型数组存不了小数：往 `dtype=int` 的数组里写入 0.05 rad，会被截断成 0。平衡控制中的俯仰角通常只有 ±0.1 rad 量级，全部会变成 0，控制器从此「看不见」偏角。更隐蔽的是这个过程不报错也不警告，程序照常运行，只是结果全错——所以叫「静默损坏」。防御方式是创建数组时显式声明 `dtype=np.float64`，并在测试里断言 dtype。
<!-- /upkie-qa -->

3. `np.isfinite` 能发现什么，不能发现什么？

<!-- upkie-qa:01-q3 -->
能发现：`NaN` 和 `±inf`，也就是除零、`0/0`、溢出、未初始化内存等产生的「非法数值」。不能发现：数值合法但语义错误的问题，最典型的是单位错误——把 30° 当成 30 rad 存进去，`np.isfinite` 依然全部返回 True，因为 30 是一个完全合法的浮点数。所以数值健康检查只是底线，单位和量级还需要额外的范围断言（例如俯仰角应在 ±π 以内）来把关。
<!-- /upkie-qa -->

4. 采样周期减半后，数值微分的截断误差和噪声敏感性分别怎样变化？

<!-- upkie-qa:01-q4 -->
两者向相反方向变化，这是一对经典权衡：

- 截断误差变小：中心差分的截断误差是 $O(\Delta t^2)$，$\Delta t$ 减半后截断误差约降为原来的 1/4。
- 噪声敏感性变大：差分公式要除以 $\Delta t$（或 $2\Delta t$），测量噪声幅度不变时，除以更小的数会把噪声放大约 2 倍。

所以「采样越快越好」对带噪声的真实传感器不成立：实际工程中要在截断误差和噪声放大之间选折中的 $\Delta t$，或先滤波再差分。
<!-- /upkie-qa -->

## 下一关

下一关 `02` 会把本关的数组、版本和结果进一步封装成可复现实验记录。你将证明“同一 seed 得到同一原始序列”，而不是只说“我的电脑上能运行”。
