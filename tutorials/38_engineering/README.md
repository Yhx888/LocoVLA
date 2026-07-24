# 38 C++、Eigen 与数值一致性

> 状态：已完成 Windows 工具链、CMake、CTest 与 1000 组 Python/C++ 数值一致性验收；第 38 关可执行。

## 岗位任务

你接到的不是“把 Python 翻译成 C++”，而是让同一状态误差在两种语言中得到可解释、单位一致、限幅一致的轮端力矩。任何一个符号变化都会让机器人向错误方向加速。

## 数据流

`[x误差, 速度误差, 俯仰误差, 俯仰角速度] -> Eigen::Vector4d -> 增益点积 -> 公共力矩 -> 左右轮符号映射 -> ±1 N·m 限幅`。

核心公式为：

\[
\tau = 2e_x + 0.8e_v + 3e_\theta + 0.8e_{\dot\theta}
\]

每个量第一次进入公式前必须换成 SI 单位。角度用 rad，角速度用 rad/s，位置用 m，输出用 N·m。该线性关系只在站立平衡点附近有效，接触丢失或俯仰误差超过 0.5 rad 时不能继续相信它。

## 检查点

```bash
cmake -S cpp -B build/cpp
cmake --build build/cpp
ctest --test-dir build/cpp --output-on-failure
```

故意错误：把右轮输出从 `-balance-yaw` 改成 `balance+yaw`。先用单元测试发现符号错误，再解释左右轮关节轴为什么相反。

基础任务是通过数值测试；岗位挑战是用 1000 个随机状态做 Python/C++ 最大绝对误差对比；开放探索是评估 `float` 与 `double` 对实时性和累计误差的影响。

作品集：`outputs/portfolio/38/numerical_parity_report.md`。
