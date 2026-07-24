# 已知问题

> 最后审计日期：2026-07-18
> 本清单对照 `docs/guides/CONTINUATION_HANDOFF.md`「已完成的验收缺口」移除已解决问题，仅保留当前真实未决事项。

## 1. 硬件选修 H01-H10 不在本轮验收范围

- 用户已明确允许忽略硬件选修，因此 H01-H10 的状态不阻断必修 00-47 收口。
- 授权未明确的 CAD、PCB 资料不复制到课程仓库；真实硬件能力也不能由 MuJoCo 或桌面测试外推。

## 2. WSL2/ROS2 构建产物残留

- `ros2_ws/build`、`ros2_ws/install`、`ros2_ws/log` 是首次在 `/mnt/c/...` 直接运行 `colcon build --symlink-install` 的**失败尝试残留**（ament 生成 stamp 文件时返回 `Operation not permitted`），不能作为第 40 关证据，也不能 `source install/setup.bash`。
- ext4 路径 `~/upkie-ros2-build/` 已完成一次 fresh 构建与测试，记录为 `34 tests`、0 error、0 failure；最终 00-47 链仍须把对应原始日志绑定到同一源码摘要的新输出根。
- 当前可工作的构建方式见 `docs/guides/WSL2_ROS2_SETUP.md`。

## 3. 实机部署与 Sim2Real 待启动

- 课程目前以 MuJoCo 仿真为主线，不接真实硬件。
- 域随机化、Sim2Real 验证、真实 Upkie 部署等内容尚未在课程中实机落地。

## 4. 必修 00-47 的 fresh 全链路证据仍待最终生成

- 第 26 关高度奖励已改为相对 `target_standing_height` 的误差项，并已有定向测试；不再属于已知缺陷。
- 已有 `_001` 等分段运行产物，但其源码摘要不统一，且旧的 41/43/44 结果没有登记本次图表，不能拼接成完整验收。最终验收必须在源码稳定后，从唯一空输出目录依次运行 00-47。
- 在 fresh 运行、完整 pytest、模型审计、C++/CTest 和 WSL2/ROS2 验证全部完成前，只能表述为「实现与定向回归就绪」，不能表述为「全量验收完成」。

## 5. 飞书正文仍待最终逐章回读

- 指定飞书文件夹已经存在 00-47 文档。第 45 关 revision 7 与课程主页 revision 39 已独立回读；主页已撤销旧测试数和自动毕业结论，并明确 `learner_graduated=false`。
- 本地 `tutorials/v2/00-47` 是同步源。其余章节仍须逐章回读版本、公式、命令和画板，未回读前不得标记为远端全量验收完成。

## 6. 学习者毕业不能由仓库自动签发

- `graduation_gates.json` 只能汇总可自动核验的工程证据，不能把自动代码评审伪装成口头答辩，也不能把 `learner_graduated` 判为真。
- 旧报告中任何 `overall_passed=true` 或“口头答辩通过”字段均是过期产物，不得引用；冻结源码后必须重新生成 schema 2.0 报告。
- 学习者毕业必须由仓库外部人工答辩判定。当前项目收口目标是证明「课程工程可复现并具备答辩入口」，不是签发学习者毕业结论。
- C++/ROS2 仅支持在 WSL2 Ubuntu 24.04 + ROS2 Jazzy 验证；Windows 原生 ROS2 与真实机器人部署不在本轮支持范围。
