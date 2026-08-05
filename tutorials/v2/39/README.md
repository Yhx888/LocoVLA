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

<!-- upkie-qa:39-q1 -->
`find_package` 适合系统级、版本稳定的库（比如本关的 `Eigen3::Eigen`）：它依赖用户机器上已安装的包，构建速度快、不引入网络依赖，但要求每台开发机和 CI 都预先装好正确版本。`FetchContent` 适合内部库或需要锁定特定 commit 的依赖：它在配置阶段自动下载源码并加入构建树，版本完全由 `CMakeLists.txt` 控制，复现性更强，代价是首次配置需要网络、构建时间增加。本关的岗位挑战就是让你把 Eigen3 从 `find_package` 切换为 `FetchContent`，记录构建时间变化和 `INTERFACE_INCLUDE_DIRECTORIES` 传播差异——这个实验的价值不在于"哪个更好"，而在于让你理解两种方式的传播行为是否一致。组合策略：内部库用 `FetchContent`（版本锁定、不依赖系统环境），系统级库用 `find_package`（利用系统优化、减少下载体积），两者在 CMake 目标层面都通过 `target_link_libraries` 统一接入，下游代码不需要知道依赖从哪来。CMake 解析失败时第一个要查的变量是 `CMAKE_PREFIX_PATH`——它决定 `find_package` 在哪些目录搜索，大多数"找不到包"的错误都是这个变量没设或设错了；其次是 `CMAKE_CXX_COMPILER`（第 38 关的工具链诊断），确认编译器本身可用。常见误区是在 `find_package` 失败后立刻换 `FetchContent` 而不查 `CMAKE_PREFIX_PATH`，这样掩盖了环境配置问题，换台机器还会再遇到。
<!-- /upkie-qa -->

2. `target_include_directories` 设为 `PUBLIC` 与 `PRIVATE` 时，对下游 `target_link_libraries` 的传播行为有什么区别？请用一个编译错误示例说明把本该 `PRIVATE` 的头文件误设为 `PUBLIC` 的后果。

<!-- upkie-qa:39-q2 -->
`PUBLIC` 表示"这个 include 路径既是我的实现需要，也是调用方使用我的接口时需要"——它会通过 `target_link_libraries` 传播给所有链接这个目标的目标。`PRIVATE` 表示"只有我自己编译时需要，调用方不需要"——不传播。本关正文的核心契约就是：`include/` 是调用方可以依赖的承诺（`PUBLIC`），`src/` 是实现细节（`PRIVATE`），测试只能通过公共接口使用库。编译错误示例：如果把 `upkie_course_control` 的 `target_include_directories` 从 `PUBLIC` 改为 `PRIVATE`（本关故障注入 `-DUPKIE_COURSE_EXPOSE_PUBLIC_HEADERS=OFF` 就是做这件事），库本身仍能编译（因为 `PRIVATE` 路径对自己可见），但 `control_test` 在 `#include "upkie_course/control.hpp"` 时报 `No such file or directory`——这正是目标可见性契约在工作，故障构建被正确拒绝。反过来，把本该 `PRIVATE` 的 `src/` 目录误设为 `PUBLIC` 的后果更隐蔽：下游代码会意外地能 `#include` 实现细节头文件，形成对内部实现的依赖，一旦你重构 `src/` 的文件结构，所有下游代码都会编译失败——这比立刻报错更危险，因为问题被推迟到了最糟糕的时机。面试时的判断框架：问自己"调用方需要这个头文件才能用我的接口吗"，需要就 `PUBLIC`，不需要就 `PRIVATE`，没有中间地带。常见误区是"全部设 `PUBLIC` 以防万一"——这会让依赖图变成一团乱麻，本关要求依赖图至少包含 3 个真实目标（`control_test`、`control_probe`、`upkie_course_control`），清晰的 `PUBLIC`/`PRIVATE` 划分是依赖图可读的前提。
<!-- /upkie-qa -->

3. 同事在 Ubuntu GCC 12 上编译通过，你在 Windows MSVC 上报 C++17 标准相关错误。你会按什么顺序排查 `CMAKE_CXX_STANDARD`、编译器 flag、ABI 兼容性和 CMake generator 差异？

<!-- upkie-qa:39-q3 -->
按"从最可能到最不可能"的顺序：第一步查 `CMAKE_CXX_STANDARD`。这是最常见的根因——GCC 12 默认开启 C++17（甚至 C++20），而 MSVC 默认是 C++14，如果 `CMakeLists.txt` 里没有显式设置 `set(CMAKE_CXX_STANDARD 17)` 和 `set(CMAKE_CXX_STANDARD_REQUIRED ON)`，MSVC 就会用旧标准编译，报出"不支持 if constexpr"或"structured bindings"之类的错误。第二步查编译器 flag：MSVC 的 `/std:c++17` 和 GCC 的 `-std=c++17` 语法不同，如果有人在 `CMAKE_CXX_FLAGS` 里硬编码了 GCC 风格的 flag，MSVC 会忽略或报错；正确做法是只用 `CMAKE_CXX_STANDARD`，让 CMake 自动翻译成各编译器的正确 flag。第三步查 CMake generator 差异：本关正文提到 Ninja 是默认生成器，Windows 上如果回退到 Visual Studio 生成器，多配置构建（Debug/Release）的行为和单配置的 Ninja 不同，某些 `target_compile_definitions` 可能只在特定配置下生效。第四步才查 ABI 兼容性：GCC 和 MSVC 的 C++ ABI 本来就不兼容（name mangling、异常处理、STL 实现都不同），但这通常表现为链接错误而不是编译错误，而且本关的依赖（Eigen3）是纯头文件库，不涉及 ABI 问题。面试时的判断框架：跨平台编译错误的排查顺序是"标准设置 → flag 语法 → 生成器行为 → ABI"，绝大多数问题在前两步就能解决。常见误区是一看到 MSVC 报错就去查 ABI，浪费了时间还找不到根因。
<!-- /upkie-qa -->

4. 构建产物散落在 `build/` 多个子目录时，如何用 `CMAKE_RUNTIME_OUTPUT_DIRECTORY` 和 `CMAKE_ARCHIVE_OUTPUT_DIRECTORY` 统一管理？如果 CI 要求每次构建产物路径带 git hash，你会在 CMake 层还是 CI 脚本层实现？为什么？

<!-- upkie-qa:39-q4 -->
在 `CMakeLists.txt` 顶层设置 `set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)` 和 `set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)`，所有可执行文件（`control_test`、`control_probe`）和静态库（`upkie_course_control`）就会分别集中到 `build/bin/` 和 `build/lib/`，不再散落在各子目录。多配置生成器（Visual Studio）还需要额外设置 `CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG` 等 per-configuration 变量，否则产物会跑到 `build/bin/Debug/` 子目录。git hash 路径应该在 CI 脚本层实现，不在 CMake 层。理由：CMake 的职责是描述"怎么构建"，不应该感知"在哪台机器、哪个 commit 上构建"——把 `execute_process(COMMAND git rev-parse HEAD ...)` 写进 `CMakeLists.txt` 会让每次配置都依赖 git 可执行文件，在没有 `.git` 目录的源码包（比如 `FetchContent` 下载的 tarball）里直接失败。正确做法是 CI 脚本在调用 CMake 前把 hash 作为参数传入：`cmake -DCMAKE_RUNTIME_OUTPUT_DIRECTORY=build/${GIT_HASH}/bin ..`，或者在 CI 脚本里构建完成后把产物复制到带 hash 的目录。本关的构建可复现性报告（`outputs/portfolio/39/build_reproducibility_report.md`）和依赖图（`outputs/reports/engineering_39_dependencies.dot`）就是这套思路的体现：构建系统只负责生成正确的产物，证据归档和路径管理由外部脚本（`run_engineering_lab.py`）负责。面试时的判断框架：凡是"环境相关"的信息（git hash、机器名、时间戳）都不应该硬编码进构建系统，而应该作为参数注入。常见误区是在 CMake 里调用 git 命令——这会让构建系统变得脆弱且难以测试。
<!-- /upkie-qa -->

## 下一关

下一关 `40` 会把本关结果作为输入，而不是重新开始。
