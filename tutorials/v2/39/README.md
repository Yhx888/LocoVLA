# 39 CMake 与工程结构

> 建设状态：可执行  
> 阶段：工程部署  
> 作品集目录：`outputs/portfolio/39`

## 岗位任务

把“我电脑能编译”变成同事能复现的工程证据：生成 CMake 目标依赖图，运行干净构建和 CTest，并在不改控制器源码的前提下关闭公共头文件导出，证明测试目标会正确地拒绝接口边界错误。

完成《CMake 与工程结构》岗位任务，并用实验数据解释结果。 你需要交付的不只是运行截图，而是可解释设计、固定配置、量化指标和失败分析。

## 学习目标

- 能理解：用自己的话说明“CMake 与工程结构”解决什么工程问题。
- 能推导：从假设和单位出发解释本关核心关系，不跳过符号含义。
- 能实现：运行检查点，保存测试、日志、图表或视频三类证据。

## 前置关卡

完成 `38` 的证据验收，或通过先修诊断。

## 先观察现象

先看错误基线：关闭或故意破坏本关关键环节，记录机器人姿态、接触、动作和日志最先出现的异常。不要先读结论；先写下三个观察，再提出一个可被数据推翻的原因假设。

## 直觉与概念

<!-- upkie-animation:39-core -->

`include/` 是调用方可以依赖的承诺，`src/` 是实现细节，测试只能通过公共接口使用库。CMake 的依赖图应明确包含 `control_test`、`control_probe`、`upkie_course_control` 和 `Eigen3::Eigen`。如果把公共头文件改为 `PRIVATE`，库本身仍能编译，但调用方应在包含 `upkie_course/control.hpp` 时失败；这正是目标可见性契约在工作。

工程部署关注接口、时间、故障和复现。平均能跑不等于最坏情况安全。

本关核心问题是：**如何用可测量证据判断“CMake 与工程结构”已经达到岗位可用，而不是只在一次演示中碰巧工作？**

## 教科书级展开

核心关系：

source -> target -> dependency -> test

阅读公式或契约时按七层顺序检查：直觉、符号、物理意义、设计动机、逐步推导、数值算例、代码映射。所有物理量使用 SI 单位；离散时间量必须说明采样周期。该关系默认模型字段、坐标方向和执行器语义与 `configs/robot/upkie.json` 一致。

适用范围是当前关卡声明的平衡点、约束和数据分布。接触丢失、传感器过期、动作饱和、输入超出训练分布或公式假设不成立时，必须进入诊断/安全路径，不能继续外推。

数值算例从配置中取一组实际参数，手算一个时间步，再与代码输出逐项对齐。若两者不同，优先检查单位、左右轮方向、平衡点和数组顺序。

## 动手检查点

```powershell
python scripts/run_engineering_lab.py --chapter 39
```

通过时会写入 `outputs/results/engineering_39.json`、构建日志、`outputs/reports/engineering_39_dependencies.dot`、可视化和 `outputs/portfolio/39/build_reproducibility_report.md`。验收要求是基线 CTest 通过、故障构建被拒绝、依赖图至少包含 3 个真实目标。故障注入只使用 `-DUPKIE_COURSE_EXPOSE_PUBLIC_HEADERS=OFF`，不允许手改源码或放宽编译错误。

```powershell
python scripts/course_checkpoint.py --chapter 39
```

预期结果：专属实验成功、结果契约与当前源码状态一致时，checkpoint 校验基线 CTest、故障构建拒绝和依赖图证据后通过；构建失败或证据版本过期时应明确拒绝。命令必须从项目根目录运行，原始输出写入 `outputs/`，不能手工改写成“更好看”的结果。

## 可视化证据

图表同时展示基线 CTest、故障构建拒绝和 CMake 依赖目标数量；DOT 文件保留实际 target 边。图表说明验收是否覆盖，DOT 文件说明覆盖的是哪些工程边界，失败构建日志说明第一处异常来自哪里。

至少生成 `outputs/plots/checkpoint_39.png`。控制类优先画状态与力矩时间序列；学习类画奖励分解和评估分布；感知类保留 RGB、深度与检测叠加；工程类画延迟分布和故障时间线。

视觉只回答“发生了什么”，日志给出时间与数值，测试负责可重复判定；三者缺一不可。

## 故障诊断挑战

若错误提示 `upkie_course/control.hpp: No such file or directory`，先验证 `target_include_directories` 的 `PUBLIC`/`PRIVATE` 传播属性，而不是向全局编译器参数添加随机 include 路径。若 CMake 找不到生成器或编译器，回到第 38 关的工具链诊断，不把环境问题误判为代码问题。

故意制造一个与“CMake 与工程结构”直接相关的错误。按“现象 -> 第一处异常证据 -> 根因假设 -> 最小验证 -> 修复后对比”记录，不允许通过放宽阈值隐藏失败。

## 三档任务

- 基础任务：在干净构建（删除 `build/` 后重新 `cmake --build`）下通过全部 CTest，并能逐条解释 `CMakeLists.txt` 中每个 `target_link_libraries` 的 `PUBLIC`/`PRIVATE` 选择理由。
- 岗位挑战：将 Eigen3 从 `find_package` 切换为 `FetchContent` 引入，记录构建时间变化、下载体积和 `INTERFACE_INCLUDE_DIRECTORIES` 传播差异；再故意把 `control_test` 对 `upkie_course_control` 的链接改为 `PRIVATE`，用编译错误截图证明接口边界被正确执行。
- 开放探索：新增一个只依赖头文件的 `upkie_course_control_lite` 库（`INTERFACE` library），对比它与原库在编译时间、链接产物大小和下游可见性三方面的差异，先写假设再实验验证。

## 复盘与面试

1. `FetchContent` 和 `find_package` 各自适用于什么场景？如果你的项目同时依赖一个内部库和一个系统级库，你会怎么组合？CMake 解析失败时第一该查哪个变量？
2. `target_include_directories` 设为 `PUBLIC` 与 `PRIVATE` 时，对下游 `target_link_libraries` 的传播行为有什么区别？请用一个编译错误示例说明把本该 `PRIVATE` 的头文件误设为 `PUBLIC` 的后果。
3. 同事在 Ubuntu GCC 12 上编译通过，你在 Windows MSVC 上报 C++17 标准相关错误。你会按什么顺序排查 `CMAKE_CXX_STANDARD`、编译器 flag、ABI 兼容性和 CMake generator 差异？
4. 构建产物散落在 `build/` 多个子目录时，如何用 `CMAKE_RUNTIME_OUTPUT_DIRECTORY` 和 `CMAKE_ARCHIVE_OUTPUT_DIRECTORY` 统一管理？如果 CI 要求每次构建产物路径带 git hash，你会在 CMake 层还是 CI 脚本层实现？为什么？

## 下一关

下一关 `40` 会把本关结果作为输入，而不是重新开始。
