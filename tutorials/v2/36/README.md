# 36 行为克隆与视觉语言融合

> 建设状态：可执行
> 阶段：应用型 VLA
> 作品集目录：`outputs/portfolio/36`

## 岗位任务

你的交付物是一份"行为克隆训练报告"：用关卡 35 的真实示范训练一个融合视觉、语言和本体感觉的策略，分别报告独立 seed 划分下的训练/验证误差，并保存供第 37 关真实闭环调用的统一 checkpoint。面试官会问："你的 BC 策略在开环模仿上误差很小，为什么闭环运行时仍可能偏离专家轨迹？你怎么验证这个风险？"

具体交付：

1. 一个训练好的 BC 策略模型（`outputs/checkpoints/vla_bc_policy.npz`）。
2. 一张训练集 vs 验证集 MSE 对比图。
3. 一段证据说明：数据来自 6 个真实示范、训练/验证 seed 独立，且 checkpoint 保存/加载往返误差为 0。

## 学习目标

- **能理解**：解释行为克隆的损失函数 `L = E[||pi_theta(o, l) - a_expert||^2]` 的含义，以及开环误差和闭环误差为什么差距很大。
- **能推导**：从模仿学习的泛化界出发，推导 BC 策略的闭环性能上界与 episode 长度 T 的关系。
- **能实现**：用 numpy 实现岭回归行为克隆，在示范数据上求解解析解权重。

## 前置关卡

完成 `35`（示范数据与脚本专家）的证据验收。你需要理解：

- 示范数据的格式（RGB + 深度 + 本体感觉 + 动作 + 指令）
- 分布偏移问题的理论背景
- numpy 基础（矩阵运算、线性代数）

## 先观察现象

**错误基线实验**：只训练开环模仿精度，不测试闭环性能。

```python
# 训练：用岭回归求解开环模仿的最优权重
policy = BehaviorCloningPolicy.fit(episodes, ridge=1e-4)

# 只检查开环误差
open_loop_mse = evaluate_open_loop(policy, episodes)
print(f"开环 MSE: {open_loop_mse:.6f}")
# 问题：开环误差很小，但闭环运行时误差累积
```

**记录观察**：开环 MSE 可能只有 0.001，但闭环运行时 100 步后累积误差达到 1.0——机器人偏离轨迹很远。

## 直觉与概念

<!-- upkie-animation:36-intuition -->

### 行为克隆：照着做

行为克隆（Behavior Cloning, BC）是最直接的模仿学习方法：

输入: 观测 o（图像 + 本体感觉）+ 语言指令 l
输出: 动作 a
目标: 让 a 尽可能接近专家动作 a_expert

它本质上是一个**监督学习问题**——只不过标签是专家的动作而不是图像分类的标签。

### 开环 vs 闭环误差

**开环**：给定专家的状态，预测动作并比较。

$$
for each (s, a_{\text{expert}}) in dataset:
    a_{\text{pred}} = pi_{\text{\theta}}(s)
    error += \lVert a_{\text{pred}} - a_{\text{expert}}\lVert ^2
$$

**闭环**：让策略自己运行，与专家的轨迹比较。

s = s_0
for t in range(T):
a = pi_theta(s)
- `$s` — env.step(a)  # 用策略的动作推进状态
error += ||s - s_expert[t]||^2

**关键区别**：开环用的是专家的状态（总是在正确轨迹上），闭环用的是策略自己的状态（可能偏离轨迹）。闭环误差 ≈ 开环误差 × T^2（二次累积）。

## 教科书级展开

<!-- upkie-animation:36-parameter -->

### 行为克隆损失函数

**公式**：

$$
L_{BC}(\theta) = E_{(o,l,a) ~ D} [ \lVert pi_{\text{\theta}}(o, l) - a\lVert ^2 ]
$$

**符号拆解**：

| 符号 | 含义 | 维度 |
|---|---|---|
| `theta` | checkpoint 参数：岭回归权重 + 可选训练样本缓存 | 权重 22 x 6 |
| `o` | 观测（RGB-D 经感知压缩 + 本体感觉） | 特征 22 维 |
| `l` | 语言指令（经解析器提取颜色） | 颜色 one-hot 3 维 |
| `a` | 专家动作 | 6 |
| `pi_theta` | 样本 checkpoint 走局部 1-NN；旧权重 checkpoint 走线性兼容 | 6 维动作 |
| `D` | 示范数据集 | N episodes |

**设计动机**：MSE 用来量化连续动作的模仿误差。训练阶段仍计算岭回归权重，保证旧 checkpoint 和无样本路径可以执行；当前统一 checkpoint 同时保存训练特征与动作，正常推理采用局部 1-NN 动作检索，直接返回特征空间中最近示范的动作。

### 视觉语言融合架构

课程阶段使用**可解释特征**代替 CNN，所有特征都来自已有的感知、语言和本体感觉模块输出：

输入特征提取（每步 22 维）:
1. detection.visible       → 1 维 (0/1)
2. detection.horizontal_offset → 1 维 [-1, 1]
3. min(detection.distance, 10.0) → 1 维 [0, 10]
4. color == "red"          → 1 维 (0/1)
5. color == "green"        → 1 维 (0/1)
6. color == "blue"         → 1 维 (0/1)
7. proprioception[:15]     → 15 维 (本体感觉前 15 维，不足则补零)
8. bias                    → 1 维 (常数 1.0)
融合:
features = [visible, offset, distance, r, g, b, prop0, ..., prop14, 1.0]
normalized = (features - feature_mean) / feature_scale
nearest = argmin(||training_features - normalized||_2)
action = clip(training_actions[nearest], -1, 1)

**设计动机**：特征全部来自可解释的模块输出，不直接把原始像素送进策略。1-NN 让本课程的小数据 checkpoint 精确复用最接近的已验证示范动作；代价是分布外泛化能力有限，所以第 37 关必须做真实闭环评估。

### 行为克隆策略代码

```python
def predict(self, rgb, depth, proprioception, instruction):
    features = _features(rgb, depth, proprioception, instruction)  # (22,)
    if (
        self.training_features is not None
        and self.training_actions is not None
        and self.feature_mean is not None
        and self.feature_scale is not None
    ):
        normalized = (features - self.feature_mean) / self.feature_scale
        distances = np.linalg.norm(self.training_features - normalized, axis=1)
        nearest = np.argpartition(distances, 0)[:1]
        inverse_distance = 1.0 / np.maximum(distances[nearest], 1e-6)
        action = np.average(
            self.training_actions[nearest], axis=0, weights=inverse_distance,
        )
    else:
        action = features @ self.weights  # 兼容线性权重路径
    return np.clip(action, -1.0, 1.0)
```

关键行设计原因：

- 当前统一 checkpoint 带训练样本，因此进入局部 1-NN 动作检索分支；只有旧 checkpoint 或手工构造的无样本策略才进入 `features @ weights` 兼容路径。
- `_features()` 固定为 22 维：感知 3 维、颜色 3 维、本体感觉 15 维、偏置 1 维；权重矩阵固定为 22 x 6。
- `.npz` 保存权重、归一化训练特征、训练动作、特征均值和尺度；加载使用 `allow_pickle=False`。

### 训练过程

```python
from upkie_mujoco_course.vla.behavior_cloning import BehaviorCloningPolicy
from upkie_mujoco_course.vla.contracts import load_episode
from pathlib import Path

# 加载示范数据
dataset_dir = Path("outputs/datasets/vla")
episodes = [load_episode(p) for p in sorted(dataset_dir.glob("*.npz"))]

# 训练：一步解析解（无迭代、无学习率、无 epoch）
policy = BehaviorCloningPolicy.fit(episodes, ridge=1e-4)

# 保存 checkpoint
output = policy.save("outputs/checkpoints/vla_bc_policy.npz")
print(f"训练完成: {len(episodes)} 条示范, checkpoint={output}")

# 验证保存/加载往返一致性
reloaded = BehaviorCloningPolicy.load("outputs/checkpoints/vla_bc_policy.npz")
max_diff = float(np.max(np.abs(reloaded.weights - policy.weights)))
print(f"checkpoint 往返最大误差: {max_diff:.2e}")  # 预期: 0.0
```

关键设计原因：

- 岭回归解析解保留为兼容线性权重路径；当前带样本 checkpoint 的实际动作由局部 1-NN 决定。两条路径都不需要反向传播，但不能把线性权重误写成当前闭环的唯一推理方式。
- `ridge=1e-4` 正则化强度：值太大会欠拟合（权重被压得太小），值太小会过拟合（权重对训练数据噪声敏感）。`1e-4` 是一个合理的默认值。
- 保存/加载往返验证：确保 checkpoint 文件没有精度损失。`np.savez_compressed` 使用无损压缩，往返误差应为 0。

### 闭环性能上界

**定理**（Ross et al., 2011）：

$$
J(pi_{\text{expert}}) - J(pi_{\text{\theta}}) \le  O(T^2 * \epsilon + T * \sqrt(\epsilon))
$$
- `$T` — episode 长度
- `$epsilon` — 开环单步模仿误差

**物理意义**：即使开环误差 epsilon 很小（比如 0.01），如果 episode 很长（T=1000），闭环性能差距可以达到 `1000^2 * 0.01 = 10000`。这就是为什么 BC 策略在长 episode 中容易失败。

## 动手检查点

### 检查点 1：BC 训练

```powershell
python scripts/36_train_behavior_cloning.py --dataset-dir outputs/datasets/vla --output outputs/checkpoints/vla_bc_policy.npz
```

预期：

行为克隆训练完成: episodes=6 checkpoint=outputs/checkpoints/vla_bc_policy.npz

### 检查点 2：统一训练实验

```powershell
python scripts/run_vla_lab.py --chapter 36
```

预期：输出训练集/验证集损失比和 checkpoint 往返一致性指标。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 36
```

## 可视化证据

<!-- upkie-animation:36-evidence -->

专属实验把训练/验证 MSE 对比写入 `outputs/plots/vla_36.png`，统一 checkpoint 另保存关卡级汇总证据：

图中只有训练集与验证集两根 MSE 柱。岭回归无迭代曲线；示范数量和 checkpoint 往返误差从 `outputs/results/vla_36.json` 复核，真实闭环轨迹留到第 37 关验证。

## 故障诊断挑战

<!-- upkie-animation:36-comparison -->

**破坏**：在训练数据中把语言标签全部替换为空字符串（去掉语言信息）。

**第一处异常**：策略在训练集上的 loss 下降正常（因为它仍然可以模仿动作），但在评估时对不同指令的响应完全相同——策略忽略了语言输入，只根据视觉和本体感觉决策。

**根因假设**：没有语言信息，策略无法区分"前往红色目标"和"前往蓝色目标"，只能学到一种平均行为。

**最小修复**：恢复正确的语言标签。

**验证**：策略对不同指令产生不同的运动方向。

## 三档任务

### 基础任务

- 训练 BC 策略，记录开环和闭环性能。
- 做消融实验：分别去掉视觉、语言、本体感觉输入，比较性能。

### 岗位挑战

- 实现 DAgger 的一轮迭代：用 BC 策略闭环运行，收集新的状态-动作对（由专家标注），加入数据集后重新训练。
- 比较 DAgger 前后的闭环性能改善。

### 开放探索

- 研究 Diffusion Policy（扩散策略）如何建模动作分布的多模态性。
- 写一段 200 字分析：BC 策略和 RL 策略在实际部署中应该怎样结合？

## 复盘与面试

1. 开环误差小但闭环性能差，怎么解释？

<!-- upkie-qa:36-q1 -->
开环测试时，策略每一步看到的都是专家的"正确"状态，预测动作和专家动作比较，误差自然小——本关的错误基线实验里开环 MSE 可以低到 0.001。但闭环时策略用自己的动作推进状态，一旦某步预测有微小偏差，状态就偏离了专家轨迹，进入训练数据从未覆盖的区域，下一步预测误差更大，偏离进一步加剧，形成正反馈循环。本关正文给出的定量关系是：闭环误差 ≈ 开环误差 × T²（Ross et al., 2011 的泛化界 `J(pi_expert) - J(pi_theta) <= O(T² × epsilon + T × sqrt(epsilon))`）。代入具体数字：epsilon=0.01、T=1000 时，性能差距上界可达 10000 量级，这就是为什么 BC 策略在长 episode 中容易彻底失败。工程上的验证方法：本关检查点 2 要求同时报告开环 MSE 和闭环成功率，两者差距越大说明分布偏移越严重。面试时如果被问"怎么缓解"，标准答案有三条：增加训练数据覆盖度（第 35 章）、用 DAgger 在线收集策略自己的状态重新标注、缩短 episode 长度或分段控制。常见误区是看到开环误差小就认为策略可用——开环指标只能证明策略"在专家轨迹附近"模仿得好，不能证明闭环稳定性。
<!-- /upkie-qa -->

2. 为什么融合视觉和语言？

<!-- upkie-qa:36-q2 -->
纯视觉策略能感知环境（目标在哪里、距离多远），但不能理解语言指令——不知道该去红色目标还是蓝色目标；纯语言策略能解析指令，但没有环境感知——知道"去红色目标"却不知道红色目标在哪个方向。两者融合才能实现"语言条件导航"：听到指令 → 确定目标颜色 → 视觉定位目标 → 生成导航动作。本关的融合架构是 22 维可解释特征：感知 3 维（`detection.visible`、`horizontal_offset` [-1,1]、`min(distance, 10.0)`）、颜色 one-hot 3 维（red/green/blue，来自语言解析器）、本体感觉前 15 维、偏置 1 维，权重矩阵固定 22×6。这个设计的关键决策是不直接把原始像素送进策略，而是用已有感知模块的输出作为特征——课程阶段追求可解释性，每个特征维度都有明确物理含义，面试时能逐维解释"这 22 个数字分别代表什么"。生产系统通常用 CNN 或 ViT 直接从像素提取特征，泛化能力更强，但可解释性差、需要大量数据。常见误区是认为"融合就是简单拼接"——实际上特征归一化（`(features - feature_mean) / feature_scale`）和动作限幅（`clip(action, -1, 1)`）是融合管线里不可省略的步骤，否则不同量纲的特征会主导距离计算，1-NN 检索结果会被本体感觉的大数值特征支配。
<!-- /upkie-qa -->

3. BC 策略的输出应该是确定性还是随机性？

<!-- upkie-qa:36-q3 -->
确定性输出（直接输出动作均值）实现简单，本关的 1-NN 检索就是确定性路径：找到特征空间最近的示范，直接返回其动作，`clip` 到 [-1, 1]。问题是多模态场景下会取平均——比如训练数据里"遇到岔路口"有时向左有时向右，确定性策略可能输出"直走"（两个方向的均值），哪个都不对。随机性输出（输出高斯分布的均值和方差，采样得到动作）能表达这种不确定性，但训练更复杂，需要最大化对数似然而不是最小化 MSE，评估时也要用多次采样的期望而不是单次预测。本关课程阶段选择确定性 1-NN 有明确的工程理由：只有 6 条示范，数据量太小，拟合分布参数没有统计意义；1-NN 精确复用最接近的已验证示范动作，在小数据下比参数化模型更稳健。代价是分布外泛化能力有限，所以第 37 关必须做真实闭环评估来量化这个风险。面试时的判断框架：数据量少（<100 条）→ 确定性/最近邻；数据量充足且场景多模态 → 随机性策略（高斯或 Diffusion Policy）；安全关键场景 → 随机性策略 + 安全层过滤极端采样。常见误区是在小数据上强行拟合高斯分布，方差估计不稳定，反而比确定性输出更差。
<!-- /upkie-qa -->

4. BC 策略能超过专家吗？

<!-- upkie-qa:36-q4 -->
不能——这是 BC 的理论上限决定的。BC 的损失函数 `L_BC(theta) = E[||pi_theta(o,l) - a||²]` 本质上是在最小化与专家动作的 MSE，最优解就是专家本身，不可能比专家更好。本关的 1-NN 实现更直观：策略的动作永远来自训练集里某条示范的 `training_actions`，不可能产生训练数据里没有的动作，上限就是示范数据里最好的那条轨迹。要超过专家有三条路：一是 RL 微调（在 BC 预训练基础上用环境奖励继续优化，第 25~31 章的 PPO 就是这条路）；二是更好的示范数据（用更优的专家或人类示范替换脚本专家，第 35 章讨论了脚本专家的次优性）；三是集成多个专家（取多个专家动作的加权组合，可能比单个专家更稳健）。面试时如果被追问"那 BC 还有什么价值"，答案是：BC 不需要环境奖励函数、训练快（本关岭回归是解析解，无迭代、无学习率、无 epoch）、可复现（checkpoint 往返误差为 0，`allow_pickle=False` 保证安全加载），适合作为冷启动基线和安全约束下的初始策略。常见误区是把 BC 当成最终方案——BC 是起点不是终点，生产系统通常需要 BC + RL 微调的组合。
<!-- /upkie-qa -->

## 下一关

关卡 `37`（闭环泛化与失败分析）会假设你已经有一个训练好的 BC 策略。本关产出的策略将成为下一关"系统级评估"的被测对象——你需要在多种场景下量化策略的泛化能力和失败模式。
