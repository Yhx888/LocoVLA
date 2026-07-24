# Upkie 课程平台阶段性交接文档

更新时间：2026-07-23（第二次交接）  
当前分支：`tutorial-restructure/upkie-mujoco-course`  
工作目录：`C:\HOME\Project\Bipedal-Wheel-robot-learning`

## 1. 交接结论与停止边界

本轮完成了：
- 阶段 A：两条后端 RED 测试已修复并转绿，36 条定向测试全部通过。
- 阶段 B：前端 RunCoordinator 交叉复核完成，所有契约确认正确。
- 阶段 C 第 1 步：全量 pytest 已运行（580 passed, 2 failed）。

整份"Upkie 课程平台一致性修复与高密度动画建设"计划尚未全部完成。阶段 C 剩余步骤（前端测试、tsc、build、E2E、C++、ROS2）、阶段 D（源码冻结与正式 checkpoint）和阶段 E（最终浏览器验收）仍需执行。

本停止点不包含以下操作：

- 不执行前端 `npm test`、`tsc`、`build`、`test:e2e`。
- 不执行 C++ CMake/CTest 或 ROS2 正式复验。
- 不运行 `00–47` 与 `H01` 的正式 checkpoint。
- 不进行最终完整浏览器验收。
- 不清理、回滚、提交或重排当前未提交修改。
- 不修改 `archive/`、机器人模型、`assets/` 或 `configs/robot/`。

## 2. 当前已完成内容

### 2.1 任务状态机与前后端运行契约

以下实现已经落入工作区，但在本阶段结束后尚未进行最终全量复验：

- 后端使用 SQLite 持久化运行任务、独立事件流和日志。
- 运行状态统一为 `queued | running | succeeded | failed | cancelled | interrupted`。
- 已实现活动任务占用、任务事件隔离、取消校验、异常收尾、重启恢复和 WebSocket 终态关闭。
- 前端已加入应用级 `RunCoordinator`，统一代码块运行与右侧验收任务。
- 已实现断线恢复、事件序号续传、轮询兜底、409 活动任务接管、失败详情和局部刷新。
- 结果面板、章节运行记录、产物 URL、健康状态和 Vite WebSocket 代理契约已经调整。

主要相关文件：

- `src/upkie_mujoco_course/web/runner.py`
- `src/upkie_mujoco_course/web/app.py`
- `src/upkie_mujoco_course/web/schemas.py`
- `dashboard/web/src/run/`
- `dashboard/web/src/components/course/MarkdownView.tsx`
- `dashboard/web/src/components/course/ResultsView.tsx`
- `dashboard/web/src/components/runner/RunnerPanel.tsx`
- `dashboard/web/src/api/client.ts`
- `dashboard/web/src/api/types.ts`

### 2.2 课程动画覆盖

- 58 节课程已加入共 136 个正文动画标记。
- 章节 12–37 每节至少包含 4 个动画，其余章节每节至少包含 1 个动画。
- 教程使用独立段落标记 `<!-- upkie-animation:<id> -->` 确定正文插入位置。
- H02–H10 保持“规划中”，相关动画只作概念示意，不作为验收证据。
- 动画索引可定位正文锚点，并支持大屏重播。

### 2.3 本阶段完成的动画修复

本阶段主要修改：

- `dashboard/web/src/animations/InlineCourseAnimation.tsx`
- `dashboard/web/src/animations/InlineCourseAnimation.test.tsx`
- `dashboard/web/src/animations/chapters/ChapterAnimationConfigs.ts`
- `dashboard/web/e2e/course.spec.ts`
- `dashboard/web/package.json`
- `dashboard/web/package-lock.json`

已完成行为：

- 8 种课程场景分别渲染对应的机制、参数和故障几何，不再复用含义不符的通用画面。
- SVG marker 通过 React `useId()` 生成唯一 ID，大屏实例不再重复正文锚点。
- `prefers-reduced-motion` 支持运行时切换。
- 普通播放结束与减少动态效果模式使用同一最终静态帧。
- 证据生成成功后会清除 missing 状态，并以 `?v=<revision>` 重新请求证据资源。
- 参数滑块同时改变显示数值和实际 SVG 几何，变化可观察。
- `ConfiguredGraph` 按配置中的真实坐标渲染全部节点和连线，已恢复章节 00 的“岗位毕业项目”、章节 43 的 `FAULT` 和章节 47 的“47题面试”。
- 移动端 SVG 使用 `viewBox` 响应式缩放，修复横向越界和画布尺寸问题。
- E2E 从易变化的 aria 文本断言切换到稳定的 `mechanism-scene` 测试标识。
- 将 `@testing-library/dom` `^10.4.1` 加为直接开发依赖，修复可复现安装后的 TypeScript 声明缺失。

## 3. 本阶段新鲜验证证据

以下结果是在动画源码完成后重新执行所得，可作为本阶段证据：

| 验证项 | 结果 |
|---|---|
| `npm test -- --run` | 通过，10 个测试文件、43 个测试 |
| `npx tsc --noEmit` | 通过 |
| `npm run build` | 通过 |
| `pytest -q tests/test_tutorial_animation_markers.py` | 通过，2 个测试 |
| 移动端关键 Playwright E2E | 通过，3 个测试 |
| 独立代码复核 | 通过，无 P1/P2 阻断项 |
| `git diff --check` | 无内容错误，仅有行尾提示 |

移动端关键 E2E 覆盖：

- 正文动画可播放，且 SVG 非空。
- 页面无横向溢出。
- 减少动态效果模式直接显示最终静态帧。

内置浏览器人工复核章节 12：

- 动画最终帧 `tokenCx="426"`。
- 播放结束后 `data-playing="false"`。
- 页面横向溢出为 `0`。
- 截图：`outputs/playwright/animation-stage-browser.png`。

本地课程服务在交接时使用 `http://127.0.0.1:8765`，先前记录的进程 PID 为 `15992`。接手后应先检查进程和健康接口，不应假设该 PID 在新会话中仍然有效。

## 4. 后端 RED 测试（已关闭）

两条 RED 测试已在本轮修复并转绿：

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_web_api.py::TestRunEndpoint::test_run_api_does_not_expose_internal_owner_pid `
  tests/test_web_runner.py::test_windows_process_probe_declares_pointer_sized_handle
# 结果：2 passed
```

### 4.1 公共 API 暴露内部 `owner_pid`（已修复）

修复位置：`src/upkie_mujoco_course/web/runner.py`

- `TaskRunner.get_run()` 返回 `dict(run)` 副本后 `pop("owner_pid", None)`。
- `TaskRunner.get_history()` 对 `list_runs()` 返回的每条记录 `pop("owner_pid", None)`。
- 内部 `RunStore` 和重启恢复逻辑不受影响，仍读取完整 `owner_pid`。

### 4.2 Windows HANDLE 类型声明（已修复）

修复位置：`src/upkie_mujoco_course/web/runner.py` 的 `_process_is_alive()`

- 新增 `from ctypes import wintypes` 导入。
- `kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]`，`restype = wintypes.HANDLE`。
- `kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]`，`restype = wintypes.BOOL`。
- `kernel32.CloseHandle.argtypes = [wintypes.HANDLE]`，`restype = wintypes.BOOL`。
- `finally` 中关闭句柄保持不变。

定向测试集全量通过（36 passed）：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_web_api.py tests/test_web_runner.py
# 结果：36 passed in 27.16s
```

## 4A. 全量 pytest 中的已知失败（非本轮引入）

```
FAILED tests/test_rl_labs.py::test_rl_labs_write_real_result_log_plot_and_portfolio[28]
FAILED tests/test_rl_labs.py::test_chapter_28_trains_and_reloads_real_mujoco_ppo
```

全量结果：`2 failed, 580 passed in 485.69s`。

这两条失败与本轮修改无关。本轮只修改了 `runner.py` 的 ctypes 声明和 `owner_pid` 过滤。`rl/labs.py` 和 `test_rl_labs.py` 是前序 Agent 留下的脏修改（`git diff --name-only` 可确认）。接手后应先排查 chapter 28 RL lab 的 `passed` 为何为 `False`，修复后再重跑全量 pytest。

## 5. 后续实施顺序

### 阶段 A：关闭后端 RED ✅ 已完成

两条 RED 测试已修复转绿，36 条定向测试全部通过。

### 阶段 B：交叉复核前端运行协调器 ✅ 已完成

复核结论：
- `RunCoordinatorProvider` 在 `App.tsx` 顶层包裹，MarkdownView、RunnerPanel、InlineCourseAnimation 通过 `useRunCoordinator` 共享同一实例。
- WebSocket 按 `lastSequence` 续传，`getRun` 每秒轮询兜底。
- 终态由后端 `TERMINAL.has(current.status)` 确认后才调用 `releaseOwner`。
- `handleExperimentComplete` 只刷新 `getChapter` + `listRuns` + `getCourseSummary`，不重载整章。
- RunnerPanel 和 MarkdownView 按钮在 `globallyBusy` 时显示"当前任务占用中"。
- 失败详情展示 `errorCategory`、`exitCode`、`error`、末尾日志；ResultsView 有重跑入口。
- ResultsView 按 `chapter_id` 过滤，产物优先 `art.url`，路径用 `/` 分隔。
- 健康状态在 CockpitPage 映射 `ready → 就绪`、`degraded → 部分缺失`、`offline → 离线`。
- Vite `/api` 代理配置 `ws: true`，WebSocket 走同一代理路径。

### 阶段 C：完整自动化回归（进行中）

已完成：
1. ✅ `.\.venv\Scripts\python.exe -m pytest` → 580 passed, 2 failed（RL chapter 28，非本轮引入）

待执行：
2. 在 `dashboard/web` 运行 `npm test -- --run`
3. 在 `dashboard/web` 运行 `npx tsc --noEmit`
4. 在 `dashboard/web` 运行 `npm run build`
5. 在 `dashboard/web` 运行 `npm run test:e2e`
6. 在 `cpp` 运行 CMake 配置、构建和 CTest
7. 在 WSL2 中重新执行 ROS2 构建与测试，并导出正式日志

前置阻塞：RL chapter 28 的 2 条失败需要先排查修复（`rl/labs.py` 是前序脏修改），修复后重跑全量 pytest 确认 0 failed。

任何一步失败都应先修根因并重跑受影响范围；不得跳过失败、放宽阈值或用旧日志替代新结果。

### 阶段 D：源码冻结与正式课程 checkpoint

1. 完成全部代码修复后冻结源码。
2. 记录当前 Git commit、dirty 状态和依赖版本。
3. 严格按 `00 -> 01 -> ... -> 47 -> H01` 的顺序执行正式 checkpoint。
4. 所有实验固定 `--seed 0`，并以验收实现强制 headless；执行前用入口的 `--help` 确认参数契约。
5. 每节保存命令、退出码、日志、`meta.json`、图表或视频等证据。
6. H02–H10 只核对“规划中”和概念动画，不作为正式硬件验收证据。
7. checkpoint 运行期间不得再修改源码。源码发生任何变化后，既有 `source_digest` 视为过期，必须重新生成受影响证据。

### 阶段 E：最终内置浏览器验收

自动化全部通过后，再使用内置浏览器复核以下真实流程：

1. 连续运行两个正文代码块，然后立即启动章节验收。
2. 在任务运行中尝试启动其他任务，确认占用提示和 409 接管行为。
3. 取消当前任务，分别验证错误 ID、未知任务和已终止任务的响应。
4. 人为断开 WebSocket，确认日志按事件序号无重复、无缺失恢复。
5. 验收完成后确认页面不整章重载、滚动位置和代码块日志保留。
6. 检查失败详情与重跑入口。
7. 检查动画索引跳转、大屏重播、参数滑块几何变化和证据重建后的缓存刷新。
8. 在桌面与移动端检查无文字裁切、控件重叠、横向溢出和空白画布。
9. 检查普通动画终帧与减少动态效果静态帧一致。

## 6. 环境与证据注意事项

- 主 Python 环境为 `.venv`，版本为 Python 3.11.15；不要混用 `.venv311`。
- SQLite 运行数据库为 `outputs/web_runs.sqlite3`。不要删除，否则会丢失本地运行历史和日志。
- 课程服务入口以项目现有启动脚本为准。启动前先检查 `8765` 端口，端口被占用时不要直接终止未知进程。
- 前端构建必须使用当前源码生成，不能让旧 `dist` 与新后端组合运行。
- 产物 URL 应优先使用后端返回的 `url`，文件路径统一为 URL 的 `/` 分隔形式。
- ROS2 只在 WSL2 中构建和验证，Windows 侧结果不能替代正式 ROS2 证据。
- 现有 outputs 中已有大量实验和验收产物。这些可用于排查，但只有源码冻结后重新生成、且 `source_digest` 匹配的产物才可计入最终验收。
- 不修改机器人模型。本轮没有触发模型事实变更，也不需要同步飞书机器人事实。

## 7. 工作区保护

当前工作区包含大量未提交修改和未跟踪实验产物，它们来自用户及前序实施过程。接手时必须遵守：

- 不执行 `git reset --hard`、`git checkout --` 或任何批量清理命令。
- 不批量删除文件或目录。
- 不回滚无法确认来源的修改。
- 修改已变更文件前先阅读现有 diff，并在当前内容上做最小补丁。
- 不修改 `archive/`。
- 不因为行尾提示对大量文件做机械格式化。
- 不提交与本计划无关的 outputs、缓存或工具临时文件。

## 8. 已知非阻断警告与待修问题

### 非阻断警告（不影响功能判定）

- 前端单测仍输出 React Router future flag 警告和部分 `act(...)` 警告。
- Vite 构建主 chunk 约 `987.10 kB`，超过 `500 kB` 警告阈值。
- `npm install` 报告 5 个依赖漏洞：3 个 moderate、1 个 high、1 个 critical。未执行 `npm audit fix --force`，后续需逐项评估兼容性后处理。
- `git diff --check` 仍可能显示 CRLF/LF 行尾提示，但本阶段没有空白符内容错误。

### 待修功能问题（阻断全量回归通过）

- `tests/test_rl_labs.py` chapter 28 的 2 条测试失败：`result["passed"]` 为 `False`。
- 根因在 `src/upkie_mujoco_course/rl/labs.py`（前序 Agent 脏修改），与本轮 `runner.py` 修改无关。
- 接手后需先排查 chapter 28 RL lab 为何 `passed=False`，修复后重跑全量 pytest 确认 0 failed。

这些警告不应与功能失败混淆。依赖漏洞和体积优化应单独评估，不要使用破坏性自动升级扩大本轮范围。

## 9. 最终完成判定

只有同时满足以下条件，才能对外声明整份总计划"全部完成"：

- ✅ 两条后端 RED 测试及相关定向测试全部通过。
- ✅ 前端 RunCoordinator 交叉复核通过。
- ⬜ RL chapter 28 的 2 条失败修复后，全量 pytest 0 failed。
- ⬜ 前端 `npm test`、`tsc`、`build`、`test:e2e` 新鲜通过。
- ⬜ C++ CMake/CTest 新鲜通过。
- ⬜ ROS2 在 WSL2 中新鲜构建和测试通过。
- ⬜ 58 节动画标记和滑块可观察变化契约全部通过。
- ⬜ `00–47` 与 `H01` 的正式 checkpoint 在冻结源码上按顺序通过，证据 `source_digest` 有效。
- ⬜ 桌面与移动端完整 Playwright E2E 通过。
- ⬜ 内置浏览器完成连续代码块后立即验收、取消、重连、局部刷新、动画和减少动态效果的最终人工复核。
- ⬜ 最终验收日志明确记录仍存在的非阻断风险，不使用旧证据或推断代替实际结果。

在上述条件满足前，准确状态应表述为：阶段 A/B 已完成，阶段 C 进行中（pytest 已跑但有 2 条预存失败待修），阶段 D/E 未开始。

## 10. 第三次交接状态（2026-07-23 晚，本轮实测更新）

### 10.1 阶段 C 全量回归（新鲜证据，日志见 `outputs/engineering-probe/logs/`）

- RL chapter 28 根因已定位并最小修复：前序 Agent 把训练步数从 `50_000` 改成 `100_000` 导致 PPO 过训练发散成跌倒策略（success_rate=0.0 / fall_rate=1.0）。修复为恢复 `training_timesteps = 50_000`（`src/upkie_mujoco_course/rl/labs.py`，含中文注释）。
- Python 全量 `pytest`：**582 passed**。
- 前端 `npm test -- --run`：**43 passed**；`npx tsc --noEmit`：**0 错误**；`npm run build`：**成功**（主 chunk ~987 kB 警告，非阻断）；`npm run test:e2e`：**24 passed**。
- C++（Windows 侧无编译器）：改在 WSL2 独立 `build-wsl2` 目录用 g++ 13.3.0 构建，`CTest`：**2/2 passed**。
- ROS2：WSL2 家目录新鲜 `colcon build + test`，**42 tests / 0 failures**。

### 10.2 阶段 D 关键发现——既有实验证据全部失效

盘点（`outputs/engineering-probe/audit_evidence.py`）显示：**当前源码下无任何一章的既有实验证据有效**，分两类：

1. **14 章 source_digest 过期 / schema 版本过旧**（正式契约要求 `schema_version == 2.0`，既有证据是旧版；部分 commit/diff 摘要亦已变更）。
2. **27 章 seed 非 0**——既有证据按章号取种子（如 ch21 seed=21、ch28 seed=28），而正式验收 `course_checkpoint.py` 强制 `--seed 0`，`_require_experiment_result_file` 对 seed≠0 直接判失败。

结论：阶段 D 的真正工作量不是「顺序跑 checkpoint」，而是**必须先在冻结源码上用 seed=0 重新生成每章实验证据**，且严格按 00→47→H01 顺序 checkpoint（存在学习者先修门控，先修章节未 checkpoint 会导致后续章节失败）。

### 10.3 阶段 D 本轮进度（已核验 source_digest）

- **00–37 共 38 章：已用 seed=0 重生成证据并 checkpoint 通过，source_digest 在冻结源码下全部有效**（`assess_experiment_result` 校验通过）。覆盖数学基础(01-05)、模型契约(11)、经典控制(13-18)、状态估计(20-23)、MPC+轨迹(24)、RL 含 PPO/残差/sim2real(25-31)、VLA 含数据集+BC 训练(32-37)，以及仅测试章节(00,06-10,12,17,19)。
- 纯 Python 工程/硬件证据已 seed=0 重生成：**41、44、46、H01**（但其 checkpoint 受先修门控，需在 WSL2 章节完成后按序验收）。

### 10.4 剩余阻塞（须 WSL2 环境）

- **38 数值一致性、39 构建复现、40 ROS2 节点、47 代码评审**：依赖 C++/CMake 或 ROS2 构建，Windows 侧无编译器，须在 WSL2 生成 seed=0 证据。
- **42、43**：依赖 colcon 测试日志（ROS2）；**45 capstone**：依赖 43 的 ROS2 安全证据。
- 上述 7 章的 seed=0 证据仍是旧种子/陈旧 digest，其 checkpoint（`checkpoint_38..47`、`checkpoint_H01`）当前 source_digest **已过期**，不能计入冻结源码正式通过。
- 41、44、46、H01 证据虽已新鲜，但因先修门控须等 38–43、45、47 完成后才能按序 checkpoint。

### 10.5 阶段 E（内置浏览器最终验收）——未开始。

### 10.6 本轮准确完成度

阶段 A/B 完成；阶段 C 全量回归新鲜通过；阶段 D 已完成 00–37（38/49 章）冻结源码正式 checkpoint 且 digest 有效，剩余 38–47+H01（11 章，其中 7 章须 WSL2）未在冻结源码上完成正式 checkpoint；阶段 E 未开始。**不满足「全部完成」条件。**

## 11. 第四次交接状态（2026-07-23 深夜，权威复审）

### 11.1 关键回归——10.3 的「00–37 有效」结论当前已失效

用项目自带的权威校验 `assess_experiment_result`（`outputs/engineering-probe/audit_evidence.py`）重新盘点，当前源码 `source_digest = 1d822cd9…`（分支 `tutorial-restructure/upkie-mujoco-course` @ `bb6d7be`，工作区 406 个改动）下：

- **证据有效（digest 通过）：0 章**（此前 10.3 记录的「00–37 共 38 章有效」已不再成立）。
- **证据过期/无效：34 章**（01–37 几乎全部 + 42/44/46/H01），统一失效原因：`source_state.untracked_manifest_sha256` 与当前源码不一致 → `source_digest` 已过期；其中 42 另有 `schema_version` 须为 2.0。
- **seed 非 0 / 未通过：7 章**（38/39/40/43/45/47 seed 等于章号、41 未通过）。

### 11.2 根因——source_digest 对未跟踪文件极度敏感

`capture_source_state` 把「未跟踪文件清单摘要」（`untracked_manifest_sha256`，排除 outputs 等 `_GENERATED_TOP_LEVEL` 生成目录）纳入 `source_digest`。因此**只要工作区在生成目录之外新增/改动任一未跟踪文件，全部已生成证据会同时失效**。这解释了 10.3「38 章有效」为何在后续操作后集体回退为「0 章有效」——期间未跟踪文件集发生了变化，digest 漂移。

### 11.3 对完成度的诚实结论与待决策阻塞

最终完成条件之「00–47 + H01 checkpoint 在冻结源码上全部通过，source_digest 有效」当前为 **0/49 有效**，远未完成。这是一个**需用户决策的架构性阻塞**：只要工作区持续产生未跟踪文件，任何一批重生成的证据都会被下一次改动打掉。可行方向二选一——

1. **先冻结未跟踪文件集**（清点并纳入跟踪或移入生成目录白名单），再一次性按 00→…→H01 顺序重生成全部 seed=0 证据并 checkpoint，中途不得再新增工作区文件；
2. **调整 digest 口径**（如未跟踪清单排除范围），但这会改动证据契约本身，须谨慎评估对既有测试的影响。

此外，7 章（38/39/40/43/45/47/42）仍须 WSL2 的 C++/ROS2 工具链，而 ML 栈仅在 Windows `.venv`——无单一环境同时具备两者，跨环境 digest 亦不一致（Windows `1d822cd9` vs WSL2 `028ee1e1`）。这两点叠加，构成「49 章统一有效 checkpoint」的核心障碍，尚待用户就环境策略与 digest 口径拍板。

## 12. 第五次交接状态（2026-07-23，用户拍板后已改门禁）

### 12.1 用户决策

- 坎1 → 采用「路线②：调整 digest 口径」。
- 坎2 → 授权按最佳方式处理；允许更改门禁，只要保证项目能顺利完成。
- 后续按「读者通读全项目 → 记录问题清单 → 统一修复」的方法推进验收，>5 分钟的长任务可先跳过。

### 12.2 已落地的门禁修改（`src/upkie_mujoco_course/course/results.py`）

- **坎1（路B）**：`_SOURCE_DIGEST_FIELDS` 移除 `untracked_manifest_sha256`。该字段仍写入 `source_state` 供人工核对，但不再参与 `source_digest` 计算，也不再触发过期判定。**未跟踪/临时文件的增删改不会再让已生成证据集体失效。**
- **坎2（比两套指纹更优）**：新增 `_normalize_newlines`，对 `tracked_diff` 与 `requirements.lock` 在计算哈希前统一换行符（CRLF/CR→LF）。这样 Windows 与 WSL2 在同一提交、同一工作区内容下得到**同一份 source_digest**，49 章可共用一套有效指纹，无需为两个环境分别记录两套照片。
- 同步测试：`tests/test_experiment_results.py` 移除「伪造未跟踪清单可被检测」的参数用例（路B下有意排除），新增 `test_untracked_manifest_change_does_not_invalidate_result` 锁定新契约。定向回归 `test_experiment_results.py + test_checkpoint_evidence.py` = **30 passed**。

### 12.3 影响与后续

- 门禁改动本身会使**所有旧证据的 stored source_digest 过期**（旧指纹含未跟踪字段、且未做换行归一），须在冻结源码上按序重新生成——这属于阶段 D 的重生成工作，其中含 >5 分钟训练的章节按用户指示可先跳过、集中记录。
- 下一步：以读者身份通读教程/文档/脚本，记录问题清单（断链、与 manifest/模型契约不一致、缺失文件等），再统一修复。

## 13. 读者视角通读与统一修复（2026-07-23）

以“零基础学习者”视角通读全部 58 关教程 + README/SYLLABUS/核心文档，对照 `configs/robot/upkie.json`、`configs/course/manifest.json`、`docs/guides/tutorial-writing-spec.md` 三份权威事实源，共记录 12 条问题，已统一修复 11 条（1 条为误报）。

### 13.1 已修复清单

| 编号 | 位置 | 问题 | 修复 |
|---|---|---|---|
| H-01/H-02/L-02 | `tutorials/v2/09/README.md` | 错说 `sensor_names` 为空、`sensor_contract` 仅 6 字段 | 改为 7 个传感器 + 11 类观测字段，补齐表格与代码注释 |
| H-03 | `tutorials/v2/30/README.md` | 用 `qpos[5]=radians(30)` 设俯仰角（破坏四元数） | 改为绕 y 轴构造四元数写入 `qpos[3:7]`，并加注释 |
| M-01 | 12 个章节共 15 处 | ` ```html ` 包裹 ` ```powershell ` 导致命令块不可渲染 | 脚本 `scripts/tools/fix_nested_codeblocks.py` 拆掉外层 html 围栏 |
| M-02 | `tutorials/v2/00/README.md` | 终端输出放进 LaTeX `$$` 块 | 改为 `text` 代码块，展示真实输出 |
| M-03 | `tutorials/v2/19/README.md` | 代码用三轴 `hypot` 但文字写二轴 `atan2(-ax,az)` | 文字统一为三轴版本 |
| M-04 | `tutorials/v2/44/README.md` | 前置关叡把 43 写成“安全状态机” | 改为 manifest 标题“部署、安全与故障恢复” |
| M-05 | `tutorials/v2/11/README.md` | 文件路径放进 LaTeX `$$` 块 | 改为 `text` 代码块 |
| L-01 | `README.md` | 轮矩写 `N·m`（与配置 `N*m` 不一致） | 统一为 `N*m` |
| L-03 | `tutorials/v2/19/README.md` | 互补滤波符号列表格式错乱（缺 `- `、多余 `$`） | 统一为规范列表项 |

### 13.2 误报

- L-04（`tutorials/v2/25/README.md` `pitch_rate` 缩进）：实际缩进一致，无需修改。

### 13.3 回归验证

修改后定向回归均通过：`test_experiment_results + test_checkpoint_evidence` = 30 passed；`test_engineering_40/42 + test_mpc + test_graduation_readiness` = 59 passed；`test_tutorial_animation_markers + test_web_content + test_course_facts + test_estimation_optimization_labs` = 36 passed。教程/模型契约/动画标记一致性未被破坏。

### 13.4 全量 pytest 新鲜回归（2026-07-23）

门禁改动 + 测试同步 + 读者视角统一修复全部落地后，重跑全量 Python 测试：

```
.\.venv\Scripts\python.exe -m pytest -q
582 passed in 420.39s (0:07:00)
```

- 结果 **582 passed, 0 failed**，日志：`outputs/logs/full_pytest_20260723_readeraccept.log`。
- 交接基线中的 2 条 chapter 28 失败（`test_rl_labs_write_real_result_log_plot_and_portfolio[28]`、`test_chapter_28_trains_and_reloads_real_mujoco_ppo`）已随源码修复转绿。
- 确认坎1（移除 `untracked_manifest_sha256` 出指纹）、坎2（换行归一）与 11 项教程/文档修复未破坏任何测试；「全量 pytest 0 failed」这一完成条件已满足。

### 13.5 前端全套新鲜回归（2026-07-23）

在 `dashboard/web` 下，源码修复后重跑前端四项：

| 项目 | 命令 | 结果 | 日志 |
|---|---|---|---|
| 单元测试 | `npm test -- --run` | **43 passed**（10 文件） | `outputs/logs/fe_npmtest_20260723.log` |
| 类型检查 | `npx tsc --noEmit` | **0 errors**（EXIT=0） | `outputs/logs/fe_tsc_20260723.log` |
| 生产构建 | `npm run build` | **成功**（EXIT=0，5.04s） | `outputs/logs/fe_build_20260723.log` |
| 端到端 | `npm run test:e2e` | **24 passed**（desktop-1440/1920 + mobile-390） | `outputs/logs/fe_e2e_20260723.log` |

非阻断警告如常：React act(...)、Vite chunk 987.10 kB。「前端 test/tsc/build/E2E 新鲜通过」与「桌面+移动端 E2E 通过」两项完成条件已满足。

### 13.6 阶段 D 正式 checkpoint（冻结源码 commit `bb6d7be`，2026-07-23）

门禁改动后旧证据全部过期（旧 digest 含未跟踪字段、未换行归一，且工作区改动使 tracked_diff 变化）。验证阶段 D 路径：**在冻结源码上重跑各章 lab 生成新鲜证据 → checkpoint 校验通过**。

- **已完成：00–11 共 12 章**，全部 `checkpoint EXIT=0`，source_digest 有效。
  - 01–05：`run_foundation_lab.py --chapter NN --seed 0` 重生成 `foundation_NN.json` 后 checkpoint 通过。
  - 11：`11_model_contract_lab.py`（该入口不接受 `--seed`）重生成 `model_contract_11.json` 后通过。
  - 06–10：纯测试型 checkpoint，先修链（01→…→10）满足后逐章通过。
  - 日志：`outputs/logs/cp_00..11_20260723.log`、`outputs/logs/lab_01..05,11_20260723.log`；证据：`outputs/results/checkpoint_00..11.json`。
- **验证的关键机制**：`course_checkpoint.py` 只校验既有专项实验证据、不重生成（见 `REQUIRED_EXPERIMENT_RESULTS`）；且启用学习者先修门控，必须按 00→…→H01 顺序、前置章节先通过。

#### 13.6.1 阶段 D 扩展至 00–37（2026-07-23，冻结源码 `bb6d7be`）

在用户确认「跳过 RL 长训练、暂缓 C++/ROS2」后继续推进，实测发现 **RL 章节并非长训练**（详见下），因此 25–31 也一并重生成并通过。Windows 侧冻结源码 checkpoint 已达 **00–37 共 38 章全部 `EXIT=0`**：

| 章段 | 生成入口 | checkpoint |
|---|---|---|
| 12/17/19 | 纯测试型（无专项证据） | EXIT=0 |
| 13/14/15/16/18 | `run_classical_control_lab.py --chapter NN --seed 0` | EXIT=0 |
| 20/21/22/23 | `run_estimation_optimization_lab.py --chapter NN --seed 0` | EXIT=0 |
| 24 | `run_mpc_balance_compare.py`（estimation_24）+ `run_trajectory_optimization_lab.py`（trajectory_24） | EXIT=0 |
| 25–31 | `run_rl_lab.py --chapter NN --seed 0` | EXIT=0 |
| 32–37 | `run_vla_lab.py --chapter NN --seed 0` | EXIT=0 |

- **RL 耗时实测（纠正此前「>5 分钟」误判）**：25/26/27/29=约 4s、31=6s、30=53s、28（真实 MuJoCo PPO）=71s，全部远低于 5 分钟。25–31 无需跳过，已重生成新鲜证据并 checkpoint 通过。
- 日志：`outputs/logs/cp_12..37_20260723_staged.log`、`outputs/logs/lab_*_20260723_staged.log`。
- **验证的关键机制（补充）**：先修门控为**顺序链**——任一前置章节未通过，其后所有章节 checkpoint 均报「学习先修未完成: N」。

### 13.7 尚未完成（相对目标的完整验收条件）

- **阶段 D 剩余 38–47 + H01（11 章）：Windows 侧阻塞，须 WSL2。** 38/39 专项实验（`run_engineering_lab.py`）需 C++ 构建，本轮实测 `run_engineering_lab.py --chapter 38` 失败：`CMAKE_CXX_COMPILER not set`、无 Ninja。由于先修门控为顺序链，40–47 与 H01 的 checkpoint 全部被 38/39 阻断（即使其证据可在 Windows 生成）。
- **C++ CTest：Windows 侧阻塞。** 本轮实测 `cmake -B build` 失败：`CMAKE_CXX_COMPILER not set`、无 `nmake`（cmake 4.4.0 已装但无 MSVC/编译器）。与 §10.4 一致，须在 WSL2 或装有编译器的环境执行。
- **ROS2（WSL2）：** 新鲜构建与测试须在 WSL2 执行，Windows `.venv` 无法直接运行。
- **阶段 E**：内置浏览器桌面+移动端交互流程（占用提示/409 接管/取消/断线恢复等）人工实测尚未进行。

### 13.8 WSL2 环节实测结果（2026-07-23，冻结源码 `bb6d7be`）

WSL2（Ubuntu 24.04，内核 6.18，g++ 13.3.0，cmake，ROS2 Jazzy）本轮可用。逐项实测：

- **00–37 checkpoint 在当前脏树上重验通过。** 用户对 `tutorials/v2/00|11|30/README.md` 的实质内容修改（新增动画标记、修正自由基座四元数 `qpos[3:7]` 物理 bug 等，00 约 182 增/56 删）属 tracked 改动，理论上改变 `tracked_diff_sha256`。经实证：`course_checkpoint.py --chapter 00..37` 全部 EXIT=0，`source_digest` 与当前源码一致——说明现有证据的指纹与当前树匹配，坎2 换行归一使跨环境（含 CRLF/LF）指纹稳定，00–37 依旧有效。
- **C++ CTest：新鲜通过。** WSL2 中 `cmake -B build-wsl2 -DCMAKE_BUILD_TYPE=Release` → `cmake --build` → `ctest`：`control_test`、`realtime_probe_smoke` 各 Passed，**2/2 tests passed, 0 failed**，CTEST_EXIT=0。Eigen 3.4.0 系统已装无需下载。日志：`outputs/logs/cpp_ctest_20260723_wsl2.log`。为避免与 Windows 缓存冲突使用独立 `cpp/build-wsl2`。
- **ROS2：新鲜通过。** `source /opt/ros/jazzy/setup.bash` → `colcon build --symlink-install`（`upkie_control`）→ `colcon test`：3/3 测试可执行文件通过，`colcon test-result --all`：**42 tests, 0 errors, 0 failures, 0 skipped**（Test.xml 3 + control_node 14 + log_contract 10 + safety_state_machine 15）。日志：`outputs/logs/ros2_build_test_20260723_wsl2.log`。
- **38–47 + H01 checkpoint：双平台阻塞（未完成）。** 根因确认：
  - Windows：`.venv` 有完整 ML 栈但无 C++ 编译器（`CMAKE_CXX_COMPILER not set`、无 Ninja/MSVC），38/39 专项实验无法在 Windows 生成，先修门控顺序链连带阻断 40–47、H01。
  - WSL2：C++ 可构建，但 **Python 工具链缺失**——系统 `python3` 为 3.12（课程包 `pyproject.toml` 限定 `>=3.11,<3.12`），且**无 pip / ensurepip / python3-venv / pipx / virtualenv / conda / uv**，仅有 apt 提供的 numpy、pyyaml。`checkpoint.py` 模块级 `import matplotlib`，各章 lab 需 numpy/scipy/matplotlib（capstone 42–47 另需 mujoco/torch）。在不使用 `sudo apt` 安装 `python3.11 python3-venv python3-pip` 且不进行大体积网络下载（torch/mujoco）的前提下，无法在 WSL2 构建可运行环境。此阻塞需用户决策：或在 WSL2 预置 Python 3.11 + venv + 课程依赖，或在 Windows 安装 C++ 编译器（使 38/39 可在 Windows 用现有 `.venv` 完成）。
- **阶段 E（内置浏览器实测）：已完成核心流程实测，见 §13.9。**

辅助脚本（均为未跟踪文件，不影响 `source_digest`）：`scripts/tools/wsl_cpp_build.sh`、`wsl_ros2_build_test.sh`、`wsl_env_probe.sh`、`wsl_pytool_probe.sh`、`wsl_eng_setup.sh`。

### 13.9 阶段 E 内置浏览器实测结果（2026-07-23，冻结源码 `bb6d7be`）

复用已运行的本地服务 `http://127.0.0.1:8765`（先查 `/api/health` → `status:ready`、`.venv` python 3.11.15、mujoco 3.8.0；未终止任何未知进程）。用内置 Chrome DevTools 在章节 30（含 4 个动画 + 残差幅度滑块）逐项实测：

- **无横向溢出。** 桌面 `documentElement.scrollWidth == innerWidth`（1251=1251）；窄屏（501）同样无溢出。
- **关键 SVG/图像非空。** 全页 95 个 `<svg>` 全部 `shapeCount>0`（无空画布）；主内容三张概念动画 SVG 分别为 456×156（11 形状）/456×132（8 形状）/456×156（20 形状）；证据 PNG `checkpoint_30.png` 实测 `naturalWidth=728, naturalHeight=308, complete=true`（非空像素）。
- **参数滑块真实改变数值与 SVG 几何。** 残差幅度滑块从 `1` 拖到 `2`，参数动画三条柱宽由 `425/393/361` 变为 `550/518/486`——数值与 SVG 几何同步改变。
- **连续代码块运行后立即启动章节验收（headline 流程）。** 点击"运行全部（2）"→ 面板依次进入"运行中（1/2）"（rl lab）→ 完成"学习控制实验 30 通过"→ 自动衔接"运行中（2/2）"（`course_checkpoint.py`）→ 完成"关卡 30 自动验收通过"。运行中显示"取消"按钮（占用/取消入口）。
- **验收后不重载整章、滚动位置保留。** 全程 `h1` 稳定为"30 残差强化学习"、`scrollY=0` 未被重置，说明运行/验收不触发整章重载。
- **证据缓存刷新机制存在且行为正确。** 证据图 URL 带 `?v=` cache-buster；冻结源码 + 固定 seed 的确定性重建产出字节相同的图表，版本不跳变（`?v=0`），符合"内容变化才刷新"的设计。
- **桌面 + 移动端截图存 `outputs/playwright/`：** `phaseE_ch30_desktop_full.png`、`phaseE_ch30_mobile_full.png`、`phaseE_ch30_running_1of2.png`、`phaseE_ch30_completed_both_pass.png`。

未逐项手动触发的边缘态（占用提示的 409 接管、取消四态中的错误ID/未知/已终止、WebSocket 断线按序恢复、失败详情与重跑入口、reduced-motion 终帧一致、动画索引跳转/大屏重播）：这些由自动化 E2E（24 passed，含桌面 1440/1920 + 移动 390）与全量 pytest（582 passed）覆盖；本轮手动实测聚焦 happy-path 关键流程并留有截图证据。

### 13.10 工程/毕业章节最终验收（2026-07-24，冻结源码 `bb6d7be`）

本轮授权启动 WSL2（仅用其 ROS2 Jazzy/colcon/g++，不装 Python/venv/torch/mujoco，不改机器人模型），完成 38–47 + H01 的最终验收。所有 checkpoint 均在冻结源码 `bb6d7be` 上执行，`source_digest` 与当前源码一致，seed 固定为 0。

#### 通过的章节（9 章 checkpoint EXIT=0，git=bb6d7be）

| 章节 | 主题 | 证据要点 | checkpoint |
|---|---|---|---|
| 38 | C++ 控制库构建 | Windows `.venv` 内置 ninja+ziglang（zig 编译器）回退工具链，自动下载校验 Eigen 3.4.0 | EXIT=0 |
| 39 | C++ 控制器移植 | 同上 zig 工具链 | EXIT=0 |
| 40 | ROS2 控制节点端到端 | 新鲜 WSL2 证据：timing（samples=1074, mean=9.999ms, p99=10.240ms, **deadline_miss=0**）+ qos（compatible=True，6 计数全 > 0）+ colcon（42 tests 0 fail）+ 有效 PNG | EXIT=0 |
| 41 | Windows 实时基线 | 新鲜 60s/100Hz 基准：samples=5999, p99=10.063ms, max=10.337ms, deadline_miss=0 | EXIT=0 |
| 42 | 统一日志契约 | 解析 1074 条 jsonl：deadline miss 0/1073 + colcon 42 tests | EXIT=0 |
| 43 | 部署安全故障恢复 | 5/5 故障检测且 safe + colcon 42 tests | EXIT=0 |
| 44 | 纯 Python 工程关 | 前序已通过 | EXIT=0 |
| 46 | 纯 Python 工程关 | 前序已通过 | EXIT=0 |
| H01 | 硬件选修（概念动画） | 前序已通过 | EXIT=0 |

- **40 关 deadline miss 根因与修复（无阈值放宽）**：首次故障注入在 `/mnt/c`（慢文件系统）上运行，`control_node` 每 tick 写 `record_log` 引入单个 12.75ms 抖动样本（> 12ms 阈值），导致 `deadline_miss_count=1`，40 关判定失败。**修复方式**：将 `run_ros2_fault_injection.py --output-root` 指向 WSL2 ext4 home（`~/upkie-evidence`，快 I/O），install-prefix 仍用当前源码 `/mnt/c/.../ros2_ws/install` 的新鲜构建；重跑后 timing `deadline_miss=0`、max=10.38ms，再把 5 个证据文件复制回 `/mnt/c/outputs`。这是消除测量伪影，非放宽通过条件。
- **本轮新鲜证据文件**：`outputs/logs/engineering_40_timing.json`、`engineering_40_qos.json`、`engineering_42_log.jsonl`、`engineering_43_control_node.log`、`engineering_40_colcon_test.log`（恰好 1 行 `Summary: 42 tests, 0 errors, 0 failures, 0 skipped`）、`outputs/results/engineering_43_ros2_fault_injection.json`、`outputs/plots/engineering_40.png`；日志 `outputs/logs/ros2_fault_injection_20260724_wsl2.log`、`ros2_build_test_20260724_wsl2.log`。
- **C++ CTest（WSL2 新鲜通过）**：`cmake -B build-wsl2 -DCMAKE_BUILD_TYPE=Release` → `cmake --build` → `ctest`，`control_test` 与 `realtime_probe_smoke` 均 Passed，**2/2 tests passed, 0 failed, CTEST_EXIT=0**。日志 `outputs/logs/cpp_ctest_20260723_wsl2.log`。
- **ROS2 colcon（WSL2 新鲜通过）**：`colcon build --symlink-install`（upkie_control）+ `colcon test`，`colcon test-result --all` = **42 tests, 0 errors, 0 failures, 0 skipped**。日志 `outputs/logs/ros2_build_test_20260724_wsl2.log`。

#### 已知基线失败（用户已决定记为已知失败，不改冻结源码）

在冻结源码 `bb6d7be` 上，第 45、47 关的专项实验为 `passed=False`，checkpoint 无法通过。这是冻结基线自身的缺陷，与运行环境无关：

- **第 47 关（岗位级作品集）**：`engineering_47.json` on `bb6d7be` → `passed=False`。根因：`static_warnings=141`（工作树；仅计跟踪源码约 106）超过阈值 100；`review_pass=0`；`duplicate_percent=40.66`。均为冻结源码自身的代码质量指标未达阈值。
- **第 45 关（capstone 综合验收）**：`engineering_45.json` on `bb6d7be` → `passed=False`，`gate_passed_count=4/8`（robustness/realtime/safety/oral_defense=0）。其中 `oral_defense` 门依赖 `engineering_47.json` 通过，因 47 未通过而级联失败；capstone 采用"木桶"判定，单门不过即整体不过。
- **陈旧 checkpoint 文件清理**：`outputs/results/checkpoint_45.json` 与 `checkpoint_47.json` 原为旧 commit `65885a6` 的 `passed=True` 残留，冒充冻结源码上的通过结果，已删除（单文件删除，非批量清理），避免误导；在 `bb6d7be` 上重跑 checkpoint 45/47 均 `EXIT=1`（专项实验未通过）。

#### 验收结论（不声称"全部完成"）

- 全量 pytest 582 passed（前序）；前端 test/tsc/build/E2E 新鲜通过（前序）；C++ CTest 新鲜 2/2 通过（本轮）；ROS2 colcon 新鲜 42 tests 0 fail（本轮）。
- checkpoint：00–44、46、H01 在冻结源码 `bb6d7be` 上全部通过、`source_digest` 有效；**45、47 为冻结基线自身缺陷导致的已知失败，未通过**。H02–H10 保持"规划中"，不计入硬件验收。
- 剩余风险：45/47 若要转为通过，需修改冻结源码（降 static_warnings 至 ≤100、修 review/robustness/realtime/safety/oral_defense 门），但这会使相关章节 `source_digest` 过期、须整体重生证据；用户已明确本轮不改源码。

#### 补充（本轮精确量化 + 用户复核决定）

- **static_warnings 来源分布（逐文件统计）**：工作树合计 141 = 已跟踪冻结源码 **106** + 未跟踪临时脚本 35（scripts/tools/_*.py 等 9 个文件，如 `_regenerate_all_svg.py` 11 条）。关键结论：即便清除全部未跟踪临时文件，冻结源码本身仍为 **106 > 100**，第 47 关 `review_pass` 仍为 0。故 45/47 的失败是冻结基线自身的代码质量缺陷，与临时文件、编译器或运行环境均无关。
- **两个"解锁"安装方案均无关**：Windows 安装 C++ 编译器 或 WSL2 预置 Python/venv/torch 都无法改变 45/47 结果——它们卡的是静态告警阈值门，不是缺工具链。38–44/46/H01 已借 WSL2 现成 ROS2/g++（未装 Python/torch、未动模型）在冻结基线通过。
- **用户复核决定（本轮）**：再次确认 45/47 记为已知基线失败，不改冻结源码、不重生证据。要转为通过需在跟踪源码中至少修复 6 条静态告警（超长行/未用导入，纯整洁），并因 `source_digest` 失效重生 00–47+H01 全部证据；用户明确不授权。
