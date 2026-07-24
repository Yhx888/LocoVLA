# 更新日志

## 2026-07-17

- **重新验收并纠正完成判定**：废止「自动 graduation gates 8/8 等于学习者毕业」的旧结论；仓库只核验课程工程就绪，学习者毕业必须由仓库外部人工答辩判定。
- **可信证据契约升级到 2.0**：结果与 checkpoint 校验源码摘要、dirty 状态、依赖锁摘要、相对证据路径、指标、checks 和先修关系，并增加伪 JSON、空作品集、旧提交与缺少专属实验的拒绝测试。
- **必修控制与安全缺陷修复**：修正目标高度奖励；MPC 不可行时显式失败并加入 MuJoCo 闭环；EKF/UKF 接入 MuJoCo IMU 与编码器；ROS2 禁止无 IMU 或无效协方差时 arm，并补齐偏航与运行时安全阈值。
- **真实学习控制与 VLA 闭环**：第 28 关使用 PPO 训练与评估，第 30 关使用残差 PPO 和基线对照，第 35-37 关形成 MuJoCo RGB-D 示范、BC checkpoint、三色任务与紧急停止闭环。
- **非硬件原始缺口补齐**：加入 SVD、特征值分解、矩阵求导、变分法、HJB、Pontryagin、KKT/对偶、直接配点、打靶法、三篇论文精读与可追踪 C++ 算法训练路线。
- **验收仍在收口**：最终 00-47 fresh 证据、完整回归、C++/ROS2 实际运行和飞书逐章回读完成前，不宣称全量验收完成。

## 2026-07-16

- **课程 v2 全量补齐**：58 关（00-47 + H01-H10）清单成型，21 关教程正文按 `tutorial-writing-spec.md` 重写（每关 ≥ 150 行，含独有故障诊断挑战）。
- **11 关独立实验证据生成**：RL（25/26/28/29/30）+ VLA（32-37）的 result/log/plot/portfolio 齐全。
- **24 MPC 深度补齐**：4 状态线性 MPC + LQR vs MPC vs 受限 MPC 对照 + 伴随法梯度 + 3 个新测试。
- **第 47 关代码评审**：pytest-cov 已安装，真实覆盖率 77.89%，`review_pass=1`；递归保护 + 排除自身 + 超时 + 日志写入文件，修复内存爆炸问题。
- **第 40 关检查点断裂修复**：补齐 TEST_TARGETS、入口脚本和证据，实测通过。
- **第 45 关检查点断裂修复**：三重证据齐全，实测通过。
- **manifest.py 入口路由修正**：40-47 关指向正确的独立脚本。
- **飞书 v0.4.0 同步完成**：`lark-cli docs +update --command overwrite --as user`，回读确认。
- **仪表盘 Playwright 截图更新**：桌面 + 移动端（2026-07-16）。
- **WSL2 + ROS2 Jazzy + colcon 已安装**：构建产物在 `~/upkie-ros2-build/`；首次在 `/mnt/c/...` 直接 `colcon build` 失败的残留位于 `ros2_ws/{build,install,log}`，不能作为通过证据。

## 2026-06-26

- 飞书教学文档信息密度优化（v1 时代，仅作历史参考；详见 `docs/analysis/COURSE_OPTIMIZATION_SUMMARY.md`）。

## 2026-05-30

- 初始化 v2 Upkie MuJoCo 教程项目
- 搭建完整项目结构，包含 Gymnasium 环境和 RL 训练框架
