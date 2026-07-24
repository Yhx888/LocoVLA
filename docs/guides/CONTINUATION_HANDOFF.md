# 课程重构交接状态

最后审计：2026-07-18（`final_acceptance_20260718_006` 已完成）。本文件是后续工具继续工作的权威起点，只记录已验证事实。`ready` 表示关卡已有可执行入口，**不等于课程验收完成或学习者已经毕业**。

## 先读什么

1. `AGENTS.md`：语言、安全、历史快照和飞书规则。
2. `docs/guides/tutorial-writing-spec.md`：小白教学、公式、可视化、日志、测试和故障注入规范。
3. `configs/course/manifest.json` 与 `src/upkie_mujoco_course/course/manifest.py`：58 关清单与 `ready/planned` 状态。
4. `configs/robot/upkie.json` 与 `src/upkie_mujoco_course/model/contract.py`：机器人 v2 物理契约。
5. `outputs/results/`、`outputs/logs/`、`outputs/plots/`、`outputs/portfolio/`：实验事实证据。
6. `outputs/reports/graduation_gates.json`：毕业门槛汇总，当前不能单独作为毕业完成证明。

## 不可违反的边界

- 永远使用中文；按当前工具环境和已加载技能的规范执行。
- 不改 `archive/v1-current-learning/`，不批量删除文件，不使用 `git reset --hard` 或 `git checkout --`。
- 当前工作树很脏，包含用户和既有代理的修改及未跟踪实验产物；不得还原、清理或覆盖它们。
- 用 `apply_patch` 修改文件；未获用户许可不提交、推送或创建 PR。
- 没有视觉、日志、自动测试和可追溯结果契约的实验，不得标为完成；不得虚构指标或把测试模板当作实机/ROS2 运行证据。

## 机器人 v2 物理契约

- `nq=13, nv=12, nu=6`，根部为自由基座 `root`。
- 腿部为位置控制，单位 `rad`；左右轮为 `[-1, 1] N*m` 力矩控制，绝不能退回速度控制。
- 改模型后先运行 `python scripts/11_model_contract_lab.py`，再同步教程和飞书事实。

## 当前审计结论

- 可信验收模型已重建：结果契约校验源码摘要、dirty 状态、依赖锁、证据内容和先修关系；本地自动评审不能把 `learner_graduated` 判为真。
- 目标高度奖励、MPC 约束失败语义、模型替换契约和 ROS2 传感器安全链已修复。ext4 路径已有一次 fresh ROS2/colcon 证据：`34 tests`、0 error、0 failure；`/mnt/c` 直挂构建残留仍不可用。
- 第 21 关已接入 MuJoCo IMU/编码器、EKF/UKF 和控制器观测链：raw/EKF/UKF RMSE 为 `0.0343/0.0112/0.0108 rad`，301 步闭环存活。
- 第 28 关已用 50000 步真实 PPO 替换代理实验：10/10 存活，最大俯仰 `0.307 rad`，相对零动作平均回报提高 `220.38`。
- 第 30 关已用 10000 步真实残差 PPO 替换随机残差：`10 N` 配对扰动下回报差 `+4.257`，成功率 1.0、跌倒率 0。
- 第 35-37 关已形成真实 MuJoCo RGB-D 示范、BC checkpoint 和三色闭环：成功率 1.0、碰撞率 0、BC 推理 9260 次。
- Python 3.11.15 完整基线最新一次为 `464 passed in 348.69s`；课程事实检查和模型审计同时通过。最终结果目录为 `outputs/final_acceptance_20260718_006`，源码摘要以其中的 `source_state.json` 为准，避免 tracked 文档自引用摘要。
- 从空输出目录按 00-47 顺序重跑后，共 89 份结构化结果均为 `schema_version=2.0`、`passed=true`、`acceptance_valid=true`、`stale=false`，且绑定同一源码摘要；C++/CTest、WSL2/colcon、ROS2 安全、MPC/EKF/UKF、PPO、残差 PPO、BC-VLA 和故障演练均有新证据。
- 飞书 00-47 文档已存在；文件夹中共 48 篇正文已逐章回读；课程主页 revision 57 已更新为 `course_build_ready=true`、`learner_graduated=false`，并明确自动评审不能替代仓库外部真人答辩。

学习者毕业需要仓库外部人工答辩。本仓库只能判断课程工程是否具备可复现入口和证据，不能用自动代码评审替代真人答辩。

## 推荐执行顺序

1. 后续任何源码或教程修改都必须重新采集 `capture_source_state()`，并重新生成与当前源码摘要一致的证据；不得合并 `_001`-`_005` 分段调试产物。
2. 需要复核时，以 `outputs/final_acceptance_20260718_006` 为基线，从 00 到 47 顺序执行必修实验和 checkpoint；硬件选修 H01-H10 不属于本轮阻断项。
3. 重新验收必须执行完整 pytest、课程事实、模型、C++/CTest 和 WSL2/colcon，并逐项检查 `acceptance_valid=true`、`stale=false`。
4. 飞书 00-47 正文已完成逐章回读；若正文或源码改变，必须重新同步并回读主页。仓库外部人工答辩状态始终单独记录。

## 基础验证命令

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\tools\check_course_facts.py
.\.venv\Scripts\python.exe scripts\graduation_readiness.py
```

在 Ubuntu 中：

```bash
source /opt/ros/jazzy/setup.bash
cd /mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/ros2_ws
colcon --log-base ~/upkie-ros2-build/log build --symlink-install --build-base ~/upkie-ros2-build/build --install-base ~/upkie-ros2-build/install
source ~/upkie-ros2-build/install/setup.bash
```
