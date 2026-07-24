# Upkie 本地交互式课程网站实施与交接计划

> **交给后续智能体：** 必须使用 `superpowers:executing-plans` 或 `superpowers:subagent-driven-development` 按阶段实施；任何功能代码开始前使用 `superpowers:test-driven-development`，宣称完成前使用 `superpowers:verification-before-completion`。前端视觉实现必须加载 `frontend-design`，浏览器验收必须加载 `playwright`。

**目标：** 在不重新生成课程正文的前提下，为现有 58 关 Upkie MuJoCo 课程建立本地单用户交互式学习网站，提供课程阅读、逐关动画、简化 3D、受控实验运行、证据查看与三层学习进度。

**架构：** React + Vite + TypeScript 负责桌面学习驾驶舱，FastAPI 直接复用现有 Python 课程契约并托管生产构建。课程正文只读取 `tutorials/v2/`，课程结构只读取 manifest，进度和运行产物只写入 `outputs/`。

**技术栈：** React、Vite、TypeScript、Motion、Three.js、React Three Fiber、React Markdown、KaTeX、Mermaid、Lucide、FastAPI、Pydantic、pytest、Vitest、Testing Library、Playwright。

---

## 0. 执行身份与分支

- **仓库：** `C:\HOME\Project\Bipedal-Wheel-robot-learning`
- **指定执行分支：** `tutorial-restructure/upkie-mujoco-course`
- **记录日期：** 2026-07-20
- **禁止擅自切换或新建分支。** 当前工作树包含大量既有未提交修改和实验产物；这些不是本任务可以清理、还原或覆盖的内容。
- 开始与每次提交前运行 `git branch --show-current`，结果必须是 `tutorial-restructure/upkie-mujoco-course`。
- 不使用 `git reset --hard`、`git checkout --` 或任何批量删除命令；不清理 `.claude/`、`.superpowers/`、`outputs/` 或其他未跟踪内容。
- 只暂存本任务明确修改的文件。提交信息、代码注释、界面文本和文档均使用中文。
- 当前 `.venv` 在本次交接检查中报告 Python 3.12.10，但 `pyproject.toml` 要求 `>=3.11,<3.12`。先运行 `py -0p` 查找 Python 3.11；不要静默使用 3.12，也不要未经确认覆盖现有 `.venv`。

## 1. 已锁定的产品决定

### 1.1 内容与事实来源

- `tutorials/v2/` 是 58 关正文的唯一来源，也是飞书 v2 教程的本地同步源。
- 网站不调用飞书 API，不重新生成、不改写、不复制正文；只做渲染和交互增强。
- `configs/course/manifest.json` 与 `src/upkie_mujoco_course/course/manifest.py` 是章节、先修、状态、命令和验收的权威来源。
- `configs/robot/upkie.json` 和模型契约是 3D 关节名称、方向、执行器语义与单位的权威来源。
- `outputs/` 保存阅读进度、运行历史、日志、图表、视频、结果和作品集；不增加数据库。

### 1.2 体验与范围

- 单用户、本机、桌面端；目标浏览器为最新版 Edge/Chrome。
- 小于 1180px 时右侧实验栏折叠；小于 1024px 显示桌面宽度提示，不开发移动端。
- 首页直接进入学习驾驶舱，不制作营销落地页。
- 章节页使用三栏：左侧课程树，中间学习区域，右侧实验与证据。
- 中间提供“学习 / 动画 / 结果”三个视图。
- 保留现有 `dashboard/app.py` Streamlit 仪表板，不删除、不改造成新站点。

### 1.3 三层进度

- 阅读层：达到正文底部并稳定停留后记录完成，同时保存最高阅读百分比。
- 自测层：三档任务和“复盘与面试”问题转为手动勾选；开放题不做伪自动评分。
- 实验层：只能由当前源码契约下 `acceptance_valid=true` 且 `passed=true` 的正式结果推导，前端和进度写接口不得直接设置。
- 三层都完成才判定整关完成并解锁下一关正式实验。
- 正文、动画和历史结果始终可浏览；未完成先修时只锁正式实验。
- 自测项 ID 使用 `chapter_id + 标准化文本 SHA-256 前 12 位`；教程问题变化时旧勾选自然失效。

### 1.4 代码运行

- 每个 `ready` 章节提供 `demo` 与 `full` 两种服务端预设。
- `full` 顺序运行 manifest 中的专属实验，再运行 `course_checkpoint`；只有它可以形成实验层完成证据。
- `demo` 使用短参数、smoke 配置或轻量入口；永不写成正式完成。
- PPO、VLA、实时实验补充明确的 `smoke/full` 参数；WSL2/ROS2 的 demo 只做环境诊断与已有证据预览。
- 浏览器只提交 `chapter_id + preset_id`；后端使用 `sys.executable` 和参数数组，不使用 shell，不接受任意命令。
- 单任务队列支持实时日志、刷新恢复、正常中断、超时终止和历史记录。
- `H02-H10` 保持 `planned`：可阅读和使用动画，正式运行按钮禁用。

### 1.5 动画与视觉

- 视觉方向：苹果式中性灰白、清晰黑色文字、蓝色主动作、绿色通过、橙色警告；统一圆角、克制阴影和有意义的状态动效。
- 使用 Lucide 图标；固定尺寸控件和动画画布，避免 hover、日志和动态文字引发布局跳动。
- 动画优先使用圆、线、箭头、状态块、曲线和固定坐标系；保留关键因果关系，不追求写实模型。
- 全局 Upkie 3D 使用盒体、圆柱、轮子、关节轴和标签，不加载复杂 STL。
- 动画支持播放、暂停、单步、复位、参数调节、文字化当前状态和 `prefers-reduced-motion`。

## 2. 公共接口与类型契约

### 2.1 HTTP 与 WebSocket

| 接口 | 行为 |
|---|---|
| `GET /api/health` | 返回 Python、核心依赖、MuJoCo、输出目录和可选外部环境诊断 |
| `GET /api/course` | 返回课程、阶段、章节摘要和总体进度 |
| `GET /api/chapters/{id}` | 返回章节元数据、Markdown、进度、运行预设和产物摘要 |
| `PUT /api/progress/{id}` | 只更新阅读百分比、阅读完成和自测项 ID |
| `POST /api/runs` | 接收 `chapter_id`、`preset_id`，创建受控任务 |
| `GET /api/runs` | 返回当前任务和按时间倒序的历史任务 |
| `GET /api/runs/{id}` | 返回单个任务及最后事件序号 |
| `POST /api/runs/{id}/cancel` | 只取消该任务启动的进程组 |
| `WS /api/runs/{id}/events?after={sequence}` | 续传 stdout、stderr 和状态事件 |
| `GET /api/artifacts/{path}` | 只读返回 `outputs/` 下白名单类型文件 |

### 2.2 固定类型

- `ChapterDto`：章节元数据、Markdown、先修、状态、三层进度、预设、产物。
- `ProgressRecord`：`reading_percent`、`reading_complete`、`self_check_ids`、只读 `experiment_accepted`、只读 `completed`。
- `RunPreset`：`id`、`label`、`mode`、`estimated_seconds`、`requires`、`counts_for_acceptance`、服务端命令步骤。
- `RunRecord`：`id`、章节、预设、`queued/running/succeeded/failed/cancelled`、时间戳、退出码、错误分类。
- `RunEvent`：递增 `sequence`、`timestamp`、`kind`、`stream`、`text` 和可选状态。
- `ArtifactDto`：相对路径、类型、大小、修改时间、只读 URL、证据有效性。

## 3. 文件边界

### 3.1 后端

- `src/upkie_mujoco_course/web/app.py`：FastAPI 工厂、路由挂载、生产静态托管。
- `src/upkie_mujoco_course/web/schemas.py`：全部 Pydantic 请求与响应类型。
- `src/upkie_mujoco_course/web/content.py`：manifest、Markdown、自测项和章节 DTO 聚合。
- `src/upkie_mujoco_course/web/progress_store.py`：三层进度读写与完成判定。
- `src/upkie_mujoco_course/web/presets.py`：结构化预设加载、manifest 命令校验和 argv 生成。
- `src/upkie_mujoco_course/web/runner.py`：单任务队列、子进程组、日志事件、取消与恢复。
- `src/upkie_mujoco_course/web/artifacts.py`：`outputs/` 产物索引、MIME 白名单和路径安全。
- `src/upkie_mujoco_course/web/diagnostics.py`：Python 3.11、依赖、MuJoCo 和外部工具诊断。
- `configs/course/web_run_presets.json`：每个 ready 章节的 demo 元数据与受控 argv；full 命令仍来自 manifest。
- `scripts/run_course_web.py`：最薄启动入口，不承载业务逻辑。

### 3.2 前端

- `dashboard/web/`：独立 Vite React TypeScript 工程。
- `src/api/`：固定 DTO 和 API/WebSocket 客户端。
- `src/pages/`：驾驶舱、章节页和不支持宽度提示。
- `src/components/course/`：课程树、Markdown、进度、自测和结果视图。
- `src/components/runner/`：预设切换、运行、取消、日志和证据面板。
- `src/animations/primitives/`：固定画布、坐标轴、向量、曲线、时间线、状态图、控制条。
- `src/animations/chapters/`：每关一个懒加载组件；不得用同一模板只替换标题。
- `src/three/UpkieModel.tsx`：只使用稳定几何体的简化交互 3D。

## 4. 分阶段实施清单

### 阶段 1：基线、依赖和 API 类型

- [ ] 阅读根目录 `AGENTS.md`、本文件、`docs/guides/CONTINUATION_HANDOFF.md`、manifest、机器人配置和现有 dashboard 数据模块。
- [ ] 记录 `git status --short` 与 `py -0p`，确认分支和 Python 3.11 路径；不清理现有工作树。
- [ ] 先新增失败测试，覆盖六个 DTO 的必需字段、枚举值和实验完成字段只读语义。
- [ ] 增加 FastAPI/uvicorn 运行依赖及前端依赖；保持项目 Python 版本约束不变。
- [ ] 实现 `schemas.py`，运行 `pytest tests/test_web_schemas.py -q`，预期全部通过。
- [ ] 只暂存本阶段文件并提交中文提交信息。

### 阶段 2：课程、Markdown、进度和产物

- [ ] 先测试 58 个章节均能通过 API 聚合，正文路径必须位于 `tutorials/v2/`。
- [ ] 测试自测哈希稳定、正文变化导致旧自测失效、实验字段不能由 PUT 写入。
- [ ] 测试产物路径穿越、符号链接越界、非白名单扩展名和 `outputs/` 外路径全部返回拒绝。
- [ ] 实现 `content.py`、`progress_store.py`、`artifacts.py`，复用现有 `CourseProgress`、`dashboard_data` 与结果契约。
- [ ] 运行新增后端测试和现有 `tests/test_course_manifest.py tests/test_dashboard_data.py`。

### 阶段 3：运行预设、任务队列和诊断

- [ ] 为每个 ready 章节建立 demo 配置；full 流程从 manifest checkpoints 派生，不复制命令事实。
- [ ] 为 RL/VLA/实时入口补充 `--profile smoke|full` 或等价受控参数，并保持教程原命令语义不变。
- [ ] 先测试未知章节、planned 章节、未知预设、shell 元字符、越界脚本和输出越界均被拒绝。
- [ ] 使用假的短命令测试状态机、事件序号、stdout/stderr、刷新恢复、超时和取消。
- [ ] Windows 使用独立进程组；取消先正常中断，等待后只终止目标任务，不终止站点或其他 Python 进程。
- [ ] 诊断必须把当前 Python 3.12 判为不兼容，并给出 Python 3.11 修复建议；WSL2/ROS2 缺失属于章节能力缺失，不阻止普通章节阅读。
- [ ] 运行 `pytest tests/test_web_presets.py tests/test_web_runner.py tests/test_web_diagnostics.py -q`。

### 阶段 4：FastAPI 应用和统一启动

- [ ] 先用 TestClient 覆盖所有 HTTP 接口、404、409 先修锁定、422 请求错误和 WebSocket 续传。
- [ ] 实现 API 路由和应用生命周期；站点退出时取消仍由站点持有的任务。
- [ ] 实现生产静态文件托管及 SPA fallback，但 `/api`、`/ws` 和不存在产物不能回退到 `index.html`。
- [ ] `scripts/run_course_web.py` 完成诊断、选择空闲端口、启动服务和打开浏览器。
- [ ] 运行后端 Web 测试与现有课程测试，确认未破坏 Streamlit 仪表板。

### 阶段 5：前端驾驶舱与课程阅读

- [ ] 使用 `frontend-design` 实现已确认的苹果式视觉系统，定义颜色、圆角、阴影、间距、固定面板尺寸和减少动态效果。
- [ ] 建立三栏布局、课程树、继续学习、环境状态、阶段进度和章节路由。
- [ ] 实现 React Markdown、GFM、KaTeX 和 Mermaid；代码块只展示服务端已注册运行入口，不把代码文本作为命令执行。
- [ ] 实现阅读底部检测、自测项勾选和三层进度展示。
- [ ] 实现“学习 / 动画 / 结果”标签与右侧实验面板；日志区域固定高度并可滚动。
- [ ] Vitest 覆盖导航、Markdown、公式、Mermaid、自测、先修锁定、运行错误和窗口宽度提示。

### 阶段 6：任务交互与结果查看

- [ ] 实现 demo/full 分段控制、预计耗时、依赖提示、运行与取消按钮。
- [ ] WebSocket 断线后使用最后 `sequence` 续传，刷新后恢复当前任务。
- [ ] 失败界面按环境缺失、先修锁定、命令失败、超时、取消、产物缺失显示中文动作建议。
- [ ] 结果视图展示 JSON 指标、图片、SVG、视频、Markdown 和原始日志；过期证据显式标记且不计完成。
- [ ] 使用真实轻量章节完成一次 demo 与 full 集成测试，确认只有 full 有效验收会更新实验层。

### 阶段 7：动画基础设施与简化 3D

- [ ] 使用固定 `aspect-ratio` 和容器尺寸实现动画画布、播放控制和几何原语。
- [ ] 所有参数输入提供边界、单位、复位值和文字化当前状态。
- [ ] `UpkieModel` 只使用盒体、圆柱和轮子；从后端契约读取六个关节、左右轮方向和执行器语义。
- [ ] 3D 支持旋转、缩放、关节选择、标签开关和相机复位；加载失败显示静态结构图。
- [ ] Playwright 验证画布非空像素、相机取景、交互后布局不变和减少动态效果。

### 阶段 8：逐关动画

- [ ] `00-11`：课程依赖地图、数组形状、复现链、坐标变换、线性化、滤波、步进、运动树、姿态、执行器/传感器、摩擦接触、模型契约。
- [ ] `12-24`：反馈、PID 饱和、倒立摆受力、极点/时域/频域、可控性、LQR、命令混合、互补滤波、Kalman、EKF/UKF、辨识、QP、MPC。
- [ ] `25-37`：Gym 状态转移、奖励拆解、策略梯度、PPO 裁剪、随机化、残差控制、Sim2Real、分层任务、RGB-D、语言安全、示范数据、行为克隆、VLA 失败分析。
- [ ] `38-47`：数值一致性、CMake 依赖、ROS2 话题、抖动分布、日志时间线、安全状态机、需求追踪、项目全链路、故障时间线、代码质量证据。
- [ ] `H01-H10`：BOM、装配公差、供电安全、FOC、编码器展开、IMU 融合、舵机几何、实机安全门、WebSocket 新鲜度、Sim2Real 参数覆盖。
- [ ] 每关拥有独立组件、暂停/单步/复位和至少一个有教学意义的参数交互。
- [ ] 注册表测试必须精确覆盖 manifest 的 58 个章节；缺少、多余或重复 ID 均失败。

### 阶段 9：端到端验收和交付

- [ ] Playwright 在 `1440x900`、`1920x1080` 覆盖打开站点、恢复阅读、切换动画、运行 demo/full、取消、查看产物和完成三层进度。
- [ ] 截图检查文字、箭头、公式、曲线、按钮、日志和 3D 不重叠、不溢出、不引发布局跳动。
- [ ] 运行前端单元测试、TypeScript 检查、生产构建和 Playwright。
- [ ] 使用 Python 3.11 运行完整 `pytest`；若耗时测试需要数分钟，等待完成，不以局部测试代替完整回归。
- [ ] 更新 README 的网站启动命令、依赖说明和 Streamlit 兼容入口。
- [ ] 启动最终本地服务器并向用户提供实际 URL；确认浏览器控制台无错误。

## 5. 必须通过的命令

根据最终前端脚本名称保持以下等价命令：

```powershell
git branch --show-current
py -3.11 -m pytest -q
npm --prefix dashboard/web run test
npm --prefix dashboard/web run typecheck
npm --prefix dashboard/web run build
npm --prefix dashboard/web run test:e2e
py -3.11 scripts/run_course_web.py
```

预期结果：分支名称正确；全部 pytest 和前端测试通过；生产构建成功；两个桌面视口端到端测试通过；启动命令输出可访问的本地 URL。

## 6. 明确不做

- 不开发账号、数据库、云同步、多人任务隔离或移动端。
- 不提供任意终端、在线代码编辑器或浏览器实时 MuJoCo。
- 不重新生成课程正文，不把飞书作为运行时依赖。
- 不把 demo、历史结果、过期结果或动画数据冒充正式验收证据。
- 不修改 `archive/v1-current-learning/`，不删除现有 Streamlit 入口。
- 不为了网站顺手重构无关控制器、课程算法或实验代码。

## 7. 接手智能体短提示词

```text
请接手实现 Upkie 本地交互式课程网站。仓库为 C:\HOME\Project\Bipedal-Wheel-robot-learning，必须继续使用分支 tutorial-restructure/upkie-mujoco-course，禁止切换分支、清理或还原当前大量未提交修改。先完整阅读 AGENTS.md、docs/superpowers/plans/2026-07-20-upkie-local-course-web-handoff.md 和 docs/guides/CONTINUATION_HANDOFF.md，再检查 git status、py -0p、manifest、机器人契约和现有测试。严格按交接文档分阶段 TDD 实施，每阶段只修改和暂存本任务文件；不要重新生成 tutorials/v2 正文。前端必须使用 frontend-design，端到端验证使用 playwright，执行计划使用 superpowers:executing-plans 或 superpowers:subagent-driven-development，完成声明前使用 superpowers:verification-before-completion。持续工作到全部后端、前端、58 关动画、生产构建、完整 pytest 和 Playwright 验收通过，并启动本地服务器向用户提供实际 URL；遇到现有脏工作树时保护并兼容，不得覆盖用户修改。
```

## 8. 完成定义

只有同时满足以下条件才可以宣称交付完成：

- 58 关正文都从本地教程读取，58 个动画注册完整，`H02-H10` 保持 planned。
- 三层进度、先修锁定、demo/full、任务取消、日志恢复和产物安全均按契约工作。
- 简化 3D 和所有动画在两个桌面视口无空白、错位、遮挡和布局跳动。
- 完整 Python 与前端测试、生产构建和 Playwright 全部通过。
- 现有 Streamlit 与课程测试没有回归。
- 已在指定分支启动可用站点，并给出实际访问 URL 和未解决限制。
