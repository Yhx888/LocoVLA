# 28 PPO 训练与诊断

> 建设状态：可执行
> 阶段：学习控制
> 作品集目录：`outputs/portfolio/28`

## 岗位任务

你的交付物是一份"PPO 训练诊断报告"：用 PPO 算法训练 Upkie 平衡策略，记录完整的训练曲线、超参数选择和诊断分析。面试官会问："PPO 的 clip 机制是什么？你怎么知道训练是否正常？什么时候该停止训练？"

具体交付：

1. 一个训练 50,000 步、可重载的轮端力矩 PPO checkpoint 及 sidecar 元数据。
2. 一张固定 10 回合评估图：零动作、经典控制和 PPO 回报，以及 PPO 最大俯仰误差。
3. 一段分析，解释 clip ratio、GAE 与当前固定评估指标的边界；训练内部 loss 可在 TensorBoard 查看，但不是本关固定 result 的字段。

## 学习目标

- **能理解**：解释 PPO 的核心创新——用 clip 约束限制策略更新幅度，防止策略崩溃。
- **能推导**：从策略梯度定理出发，推导 PPO 的 clipped surrogate objective，不跳步。
- **能实现**：用 `stable-baselines3` 的 PPO 训练 Upkie，并解读 TensorBoard 日志。

## 前置关卡

完成 `27`（MDP 与策略梯度）的证据验收。你需要理解：

- 策略梯度定理和 REINFORCE 算法
- 优势函数 A(s,a) = Q(s,a) - V(s) 的含义
- GAE（Generalized Advantage Estimation）的基本思想

## 先观察现象

**错误基线实验**：用极大的学习率训练 PPO，观察策略崩溃。

```python
import sys
sys.path.insert(0, 'src')
from stable_baselines3 import PPO
from upkie_mujoco_course.envs.standing_env import WheelTorqueStandingEnv

env = WheelTorqueStandingEnv(max_episode_steps=200)

# 故意用极大学习率
model = PPO("MlpPolicy", env, learning_rate=0.1, verbose=1)
model.learn(total_timesteps=5000)
env.close()
```

**记录观察**：

1. policy loss 剧烈振荡（不收敛）
2. KL divergence 很大（策略更新幅度过大）
3. episode reward 不上升甚至下降
4. 这就是 PPO 的 clip 机制要防止的问题

## 直觉与概念

<!-- upkie-animation:28-intuition -->

### PPO 的直觉：不要走太远

想象你在山顶上找最低点（优化策略）：

- **REINFORCE**：每步走固定距离——可能一步跨过山谷到另一座山上
- **TRPO**（Trust Region Policy Optimization）：限制每步不超过一个信任区域——安全但计算贵
- **PPO**：用 clip 近似 TRPO——简单且有效

PPO 的核心思想：**新策略和旧策略不能差太多**。如果新策略想做的改变太大，就把它裁剪到允许范围内。

### clip 机制

ratio = pi_new(a|s) / pi_old(a|s)
$$
L_{\text{clip}} = min(ratio \cdot A, clip(ratio, 1-\epsilon, 1+\epsilon) \cdot A)
$$

当 `ratio > 1 + epsilon`（新策略太想做这个动作了）→ clip 到 `1 + epsilon`
当 `ratio < 1 - epsilon`（新策略太不想做这个动作了）→ clip 到 `1 - epsilon`

这保证了策略更新不会一次改变太多。

## 教科书级展开

<!-- upkie-animation:28-parameter -->

### PPO 目标函数推导

**从策略梯度出发**：

$$
grad J(\theta) = E[grad \log pi_{\text{\theta}}(a|s) \cdot A(s,a)]
$$

**重要性采样**（用旧策略的数据估计新策略的梯度）：

$$
grad J(\theta) = E_{pi_{\text{old}}}[ (pi_{\text{\theta}}(a|s) / pi_{\text{old}}(a|s)) \cdot grad \log pi_{\text{\theta}}(a|s) \cdot A(s,a) ]
              = E_{pi_{\text{old}}}[ grad (pi_{\text{\theta}}(a|s) / pi_{\text{old}}(a|s)) \cdot A(s,a) ]
$$

**问题**：当 `pi_theta` 远离 `pi_old` 时，ratio 可能极大或极小，导致梯度爆炸。

**PPO 的解决**：

$$
L_{\text{CLIP}}(\theta) = E[ min(r_{t}(\theta) \cdot A_{t}, clip(r_{t}(\theta), 1-eps, 1+eps) \cdot A_{t}) ]
$$
其中 r_t(theta) = pi_theta(a_t | s_t) / pi_old(a_t | s_t)

**为什么用 min？**

- 当 A > 0（好动作）：ratio 越大越好，但 clip 限制了最大值 → min 选择 clip 后的值
- 当 A < 0（坏动作）：ratio 越小越好，但 clip 限制了最小值 → min 选择 clip 后的值

min 确保目标函数是 A 和 clip 的保守估计——宁可低估改进，也不冒过大更新的风险。

### GAE（Generalized Advantage Estimation）

**公式**：

- `$delta_t` — r_t + gamma * V(s_{t+1}) - V(s_t)          # TD 误差
A_t = sum_{l=0}^{T-t} (gamma * lambda)^l * delta_{t+l}  # GAE

**符号拆解**：

| 符号 | 含义 | 典型值 |
|---|---|---|
| `gamma` | 折扣因子 | 0.99 |
| `lambda` | GAE 衰减因子 | 0.95 |
| `delta_t` | 单步 TD 误差 | 实时计算 |
| `V(s)` | 价值函数估计 | 神经网络输出 |

**设计动机**：lambda 控制偏差-方差权衡。

- `lambda = 0`：A_t = delta_t（一步 TD），偏差大（V 估计不准时），方差小
- `lambda = 1`：A_t = 蒙特卡洛回报 - V(s_t)，偏差小，方差大
- `lambda = 0.95`：折中选择，实践中最常用

### 数值算例

gamma = 0.99, lambda = 0.95
- `$r` — [1, 1, 1, 1, 1]（5 步奖励）
- `$V` — [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]（价值估计）
$$
delta_{0} = 1 + 0.99 \cdot 0.6 - 0.5 = 1.094
delta_{1} = 1 + 0.99 \cdot 0.7 - 0.6 = 1.093
delta_{2} = 1 + 0.99 \cdot 0.8 - 0.7 = 1.092
\dots
$$
A_0 = delta_0 + 0.99*0.95*delta_1 + (0.99*0.95)^2*delta_2 + ...
= 1.094 + 0.9405*1.093 + 0.8844*1.092 + ...
≈ 1.094 + 1.028 + 0.966 + ... （指数衰减求和）

### 当前训练环境：只学习两轮力矩

`WheelTorqueStandingEnv` 继承通用站立环境，但把策略动作空间缩成 2 维：左右轮的归一化力矩。环境内部再构造完整 6 维动作，四个腿部位置通道保持中立站姿，两个轮端通道由 PPO 输出。

PPO action shape = (2,)
-> left_wheel_motor, right_wheel_motor
full action shape = (6,)
-> four leg channels remain neutral
-> two wheel channels receive PPO action

这就是“纯 PPO”的准确含义：轮端平衡力矩从零学习，不叠加 `WheelBalancerController`；它不是让 PPO 同时从零学习四条腿的站姿。

### Upkie 代码映射

```python
import sys
sys.path.insert(0, 'src')
from stable_baselines3 import PPO
from upkie_mujoco_course.envs.standing_env import WheelTorqueStandingEnv
from upkie_mujoco_course.rl.train_sb3 import train_ppo_standing

# 方式 1：使用项目训练入口（推荐）
# 训练入口内部创建 WheelTorqueStandingEnv(max_episode_steps=200)，
# 读取 configs/rl/ppo_standing.json 中的超参数，
# 保存 zip 与可审计 sidecar
path = train_ppo_standing(total_timesteps=50000, seed=28, profile="reference")

# 方式 2：手动创建环境和模型（用于理解训练流程）
env = WheelTorqueStandingEnv(max_episode_steps=200)

# PPO 超参数（smoke 档位，用于快速验证）
model = PPO(
    "MlpPolicy",
    env,
    learning_rate=3e-4,        # 学习率
    n_steps=16,                # 每次更新的采样步数（smoke 档位）
    batch_size=8,              # mini-batch 大小
    gamma=0.99,                # 折扣因子
    seed=0,
    verbose=0,
    tensorboard_log="./outputs/tensorboard",
)

# reference 档位超参数（正式训练）：
# n_steps=1024, batch_size=64, total_timesteps=50000

# 训练
model.learn(total_timesteps=50000)
model.save("./outputs/checkpoints/ppo_standing_latest.zip")
env.close()
```

手动 `model.save()` 只用于理解 SB3，本身不会生成本项目要求的 sidecar，也不会自动嵌入 `training_mode`。要得到能被 `evaluate_policy` 验证的 checkpoint，必须使用 `train_ppo_standing()` 项目入口。

关键行设计原因：

- `n_steps=16`（smoke）/ `n_steps=1024`（reference）：每次更新前的采样步数。smoke 档位用极小值快速验证流程，reference 档位用较大值保证优势估计质量。
- `gamma=0.99`：折扣因子，与 PPO 论文默认值一致。
- `WheelTorqueStandingEnv(max_episode_steps=200)`：策略动作维度为 2，评估器根据 checkpoint 元数据重建同一种环境，避免用 6 动作环境错误加载。
- 训练入口同时保存 `ppo_standing_latest.zip` 与 `ppo_standing_latest.metadata.json`。sidecar 中必须有 `training_mode=wheel_torque`、步数、seed 和 profile；zip 内也嵌入同一训练模式。

### 固定实验的真实评估

第 28 关专属实验使用训练 seed `28`，随后以 seed `280-289` 重载同一 checkpoint 评估 10 回合：

training_mode=wheel_torque
training_timesteps=50000
zero_return_mean=137.8792638944778
classic_return_mean=399.35648451522866
ppo_return_mean=358.25532205584386
ppo_return_improvement_over_zero=220.37605816136607
ppo_success_rate=1.0
ppo_fall_rate=0.0
ppo_max_abs_pitch_rad=0.3074230982798487
checkpoint_reloaded=1.0

PPO 明显优于零动作并完成 10 回合，但平均回报仍低于经典控制器。因此本关证明“轮矩 PPO 已学会在当前 200 步标称任务中存活”，不证明它优于经典控制。

## 动手检查点

### 检查点 1：PPO 训练

```powershell
python scripts/06_train_ppo_standing.py --total-timesteps 50000 --profile reference --mode full_action --seed 28
```

预期输出：

训练完成，模型保存到: outputs/checkpoints/ppo_standing_latest.zip

`--mode full_action` 是当前 CLI 的兼容名称；实际调用的 `train_ppo_standing()` 使用 `WheelTorqueStandingEnv`，sidecar 中权威模式是 `wheel_torque`。不要凭 CLI 标签猜动作维度。

### 检查点 2：策略评估

```powershell
python scripts/08_eval_policy.py --episodes 10 --model outputs/checkpoints/ppo_standing_latest.zip --mode rl
```

预期：模型元数据通过校验，并在每个最多 200 步的回合中返回回报。固定第 28 关证据要求 10/10 回合走到截断、跌倒率为 0、最大俯仰误差不超过 `0.35 rad`。

### 专属实验与统一验收

```powershell
python scripts/run_rl_lab.py --chapter 28
python scripts/course_checkpoint.py --chapter 28
```

## 可视化证据

<!-- upkie-animation:28-evidence -->

固定证据为：

1. `outputs/plots/rl_28.png`：左图比较零动作、经典控制和重载 PPO 的逐回合回报；右图显示 10 回合 PPO 最大俯仰误差及 `0.35 rad` 门槛；
2. `outputs/logs/rl_28.json`：训练模式、checkpoint 路径和 30 条原始评估记录；
3. `outputs/results/rl_28.json`：训练步数、回报改善、成功/跌倒率、俯仰边界和重载检查；
4. `outputs/portfolio/28/evidence.json`：作品集索引。

TensorBoard 仍可用于观察 loss、entropy 与 KL，但不能把一次未保存的界面读数写成固定 result 事实。

## 故障诊断挑战

<!-- upkie-animation:28-comparison -->

**破坏**：把 `clip_range` 从 0.2 改为 2.0（几乎不 clip）。

> **说明**：本项目使用 SB3 的 PPO 默认值（`clip_range=0.2`, `ent_coef=0.0`），未在配置文件中显式设置这些超参数。下面的诊断实验通过手动覆盖默认值来观察参数影响。

**第一处异常**：`approx_kl` 急剧增大（超过 0.5），策略在某次更新后崩溃——episode reward 突然下降到初始水平，且无法恢复。

**根因假设**：clip_range = 2.0 意味着允许策略概率比在 [-1, 3] 范围内变化，这基本上没有约束。一次过大的策略更新可能让策略进入无法恢复的差状态。

**最小修复**：恢复 `clip_range = 0.2`。

**验证**：`approx_kl` 回到 0.01 级别，训练曲线恢复正常。

## 三档任务

### 基础任务

- 用 reference 参数训练轮矩 PPO 50000 步，保存 zip、sidecar 和评估证据。
- 解释为什么 PPO 优于零动作但仍低于经典控制器。

### 岗位挑战

- 做超参数扫描：`learning_rate = {1e-4, 3e-4, 1e-3}` × `clip_range = {0.1, 0.2, 0.3}`，共 9 组。
- 用表格记录每组的最终性能和训练稳定性，找出最佳组合。

### 开放探索

- 比较 PPO 和 SAC（Soft Actor-Critic）在 Upkie 平衡任务上的训练效率。
- 写一段 200 字分析：为什么 PPO 在机器人控制中比 DQN 更常用？

## 复盘与面试

1. PPO 的 clip 解决了什么问题？

<!-- upkie-qa:28-q1 -->
防止策略单次更新过大。REINFORCE 和 vanilla policy gradient 对更新幅度没有任何约束：一批碰巧的高优势样本可以把策略参数推出很远，而策略一旦变得面目全非，它采集到的新数据也随之变差，形成“坏策略→坏数据→更坏策略”的正反馈，崩溃后往往无法恢复——这对在线采样的 RL 尤其致命，因为没有旧数据可以回退。PPO 的做法是把新旧策略的概率比 `r = pi_new(a|s)/pi_old(a|s)` 限制在 `[1-clip_range, 1+clip_range]` 内：当比值超出区间时，目标函数取截断后的保守值，梯度不再鼓励继续偏离，相当于在旧策略周围划了一个信任域。这是 TRPO 用二阶 KL 约束实现的同一思想的一阶廉价版本，代价是约束只是近似的（所以还要监控 `approx_kl` 做交叉验证）。从 27 关的视角看，clip 处理的是方差问题的另一面：基线降低单步梯度估计的方差，clip 限制方差残留部分对参数的单次破坏力，两者配合才让在线策略优化变得可用。调试时的对应信号是 `clip_fraction`：它记录多大比例的样本触发了截断，长期过高说明学习率或 `clip_range` 与当前任务不匹配。
<!-- /upkie-qa -->

2. entropy 下降太快说明什么？

<!-- upkie-qa:28-q2 -->
说明策略过早收敛：探索不足，很可能陷入局部最优。entropy 衡量动作分布的随机程度：高斯策略下它直接对应输出标准差的大小。训练初期策略应保持较高熵广泛尝试，随着价值估计变准再逐步收窄；如果 entropy 在回报还很低时就快速坠落，意味着策略过早把概率质量集中到少数动作上，后续采样几乎不再产生新信息，即使存在更好的策略方向也没有样本能揭示它。对 Upkie 平衡任务的典型症状是：策略迅速锁定某种“勉强不倒”的保守姿态，回报卡在平台期再也上不去。解决方案有两个旋钮：增大 `ent_coef`，在损失函数里提高熵奖励的权重，直接惩罚过早收窄；或增大 `clip_range`，允许每次更新走得更远，让策略有机会跳出当前局部区域。但要注意反向误判：entropy 下降本身是训练正常推进的标志，健康的曲线应该是“先高后缓降最后企稳”；真正的问题信号是“下降速度与回报改善不匹配”——熵已探底而回报仍差。诊断时应把 entropy 曲线与 episode_reward、`approx_kl` 对照着读，而不是单看一条曲线下结论，这正是本关训练诊断方法的核心：指标之间互相交叉验证。
<!-- /upkie-qa -->

3. `approx_kl` 一直很小（< 0.001）说明什么？

<!-- upkie-qa:28-q3 -->
说明策略几乎没有更新。`approx_kl` 估计每轮优化前后新旧策略的 KL 散度，它持续接近零意味着参数更新对动作分布几乎没产生影响，训练在空转。可能的原因有三类，需要逐一排查。其一，学习率太小：梯度方向对但步长微不足道，验证方法是把学习率提高一个量级看 `approx_kl` 是否随之上升。其二，优势函数接近零：可能是价值函数拟合得很准且策略已局部最优（良性，配合回报平台和低 entropy 可确认收敛）；也可能是奖励尺度过小或归一化后优势被压平（病态，检查奖励各分量量级和 advantage 的标准差）。其三，网络容量不足：网络已饱和，梯度在参数空间里推不动分布，需要加宽加深网络验证。与它对称的危险信号是 `approx_kl` 过大（如 > 0.05）：说明 clip 机制已兑不住信任域承诺，策略正在大步跳变，有崩溃风险。所以健康区间是“小但不接近零”，它应该和 `clip_fraction`、entropy、回报曲线一起读：`approx_kl` 小 + 回报仍在涨→正常稳健训练；`approx_kl` 小 + 回报停滞 + entropy 仍高→学习信号不足，要从奖励和优势估计入手查原因。
<!-- /upkie-qa -->

4. 什么时候该停止训练？

<!-- upkie-qa:28-q4 -->
本关给出的可操作判据是：当 episode_reward 在最近 20% 的训练步数中改善不足 5%，且 entropy 已稳定在低值（< 0.5）时，就应该停止。这个双条件设计有明确分工：回报条件确认“性能已进入平台”，但单凭它不够——回报曲线可能只是暂时停滞，策略还在探索；entropy 条件确认“策略已停止探索、分布已收窄”，两者同时成立才能判定训练真正收敛而非暂停。继续训练的代价不只是浪费计算：长时间在同一分布上更新还可能过拟合到当前环境的特定噪声模式，降低策略鲁棒性，甚至因偏差累积导致晚期崩溃。工程实践上还应补两道保险：定期保存 checkpoint 并用固定 seed 的评估回合（而非训练回报）做最终选型，因为训练期回报含探索噪声，与贪婪策略的真实性能有系统差异；停止判据写进实验配置而非临时目测，保证不同实验间可比。反面模式也要警惕：仅因“曲线还在动”就无限延长训练，或仅因预算耗尽就在震荡期强行截断——前者没有停止准则，后者拿到的是未收敛的随机快照。这套判据也是 29 关域随机化实验的前提：只有标准环境下训练稳定收敛的策略，才有资格进入随机化训练。
<!-- /upkie-qa -->

## 下一关

关卡 `29`（域随机化与鲁棒性）会假设你已经有一个在标准环境中表现良好的 PPO 策略。本关产出的训练诊断方法将成为下一关评估"域随机化后策略是否仍然有效"的核心工具——如果策略在标准环境中都不稳定，域随机化只会让问题更严重。
