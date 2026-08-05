# 教程参考答案撰写 · 交接文件

> 更新时间：2026-07-29
> 任务来源：计划《课程答案折叠与AI助教》（`C:\Users\YHX\AppData\Roaming\Qoder\SharedClientCache\cache\plans\课程答案折叠与AI助教_task-bd9.md`，禁止编辑计划文件本身）
> 本文件目的：让下一个会话/接手者无需重读全部历史即可继续撰写答案。

## 一、任务全貌

为 `tutorials/v2/` 全部 58 关的「复盘与面试」小节补齐参考答案，写入 qa 注释块，供前端 QaAnswerBox 组件渲染（答题区直接可见 + 参考答案独立折叠 + AI 评分）。

功能代码（前端 tokenizer、QaAnswerBox、后端 AI 模块、测试）**均已完成并验证**，剩余工作只有答案内容撰写。

## 二、qa 块格式约定（必须严格遵守）

```markdown
1. 问题文本？

<!-- upkie-qa:{章节号}-q{序号} -->
答案正文
<!-- /upkie-qa -->
```

- ID 全课程唯一，形如 `28-q1`、`H01-q2`，必须与所在章节号一致。
- 迁移类章节：原文是 `**粗体问题？** 内联答案` 格式，需拆成「编号问题 + qa 块」，原答案要点全部保留并扩写。
- 撰写类章节：原文只有编号问题列表，答案从零撰写。
- 格式门禁：`powershell -Command "Set-Location 'c:\HOME\Project\Bipedal-Wheel-robot-learning'; .venv\Scripts\python -m pytest tests/test_tutorial_qa_format.py -q"`（校验注释成对闭合、ID 唯一且与章节号一致）。每写完 2~3 章跑一次。

## 三、答案写作规范

- 中文，300~500 字/题。
- 必须引用该章正文的具体数值/命令/阈值（先 Grep 章节 README 抓关键事实再写，不许编造）。
- 交叉引用相关章节（如 32↔34 分层安全、29↔31 域随机化、27↔28 方差与 clip）。
- 面试视角：不止答对，还要给出工程判断框架和常见误区。
- **写完必须逐字检查 diff 中的中文笔误**——本任务已多次踩坑（历史笔误：惄惄/碋巧/兕底/疾75%/钢性/撨满/遮缩 等，均为输出时的错别字），发现立即用 SearchReplace 修复。

## 四、进度状态

| 批次 | 范围 | 状态 |
|------|------|------|
| batch1 | 00~05 | ✅ 完成 |
| batch2 | 06~18 | ✅ 完成 |
| batch3 | 19~31 | ✅ 完成 |
| batch4 | 32~47 | ✅ 完成 |
| batch5 | H01~H10 | ✅ 完成 |

**全部 58 关答案撰写已完成（2026-07-29）。**

### 最终验证结果

1. **完整性核查**：Grep 统计 `tutorials/v2/` 下所有 README.md 的 `upkie-qa:` 块数量，58 章全部 ≥4 个 qa 块，无遗漏。
2. **格式门禁**：`pytest tests/test_tutorial_qa_format.py -q` → **4 passed**（全部批次写入后多次运行，结果一致）。
3. **全局笔误扫描**：Grep 历史已知错字（碋巧/钢性/兕底/撨满/遮缩/惄惄）→ 0 匹配；重复字模式（的的/了了/是是/在在/做做/运运/控控/检检/查查）→ 仅 3 处「饱和和…」合法用法，无笔误。
4. **前端渲染抽查**（playwright-cli，课程 Web http://127.0.0.1:8765）：
   - `/chapter/35`：4 道题渲染为答题区 + 独立折叠「参考答案」按钮；点击展开后答案完整显示（含 inline code 渲染），无裸露 HTML 注释。截图：`%TEMP%\opencode\qa-render-ch35.png`
   - `/chapter/40`：4 个「参考答案」按钮确认。截图：`%TEMP%\opencode\qa-render-ch40.png`
   - `/chapter/H01`：4 个「参考答案」按钮确认。截图：`%TEMP%\opencode\qa-render-chH01.png`

## 五、batch4 章节明细（已完成）

已确认分类（原文已核对）：

- **35 章（迁移，4题）**：数据质量 vs 数量 / 分布偏移 / 数据覆盖度 / 脚本专家局限。
- **36 章（迁移，4题）**：开环误差小闭环差 / 视觉语言融合 / 确定性 vs 随机性输出 / BC 能否超过专家。
- **37 章（迁移，4题）**：三种泛化层次 / 失败分析第一个可观测信号 / OOD 精度召回权衡（误报率 <5%）/ 从失败中学习（DAgger）。
- **38 章（撰写，4题）**：关键假设与失效信号 / 接口单位限幅设计 / 三份可复现证据 / 指标退化 20% 排查顺序。
- **39 章（撰写，4题）**：FetchContent vs find_package / PUBLIC vs PRIVATE 传播 / 跨平台 C++17 排查顺序 / 构建产物目录管理与 git hash。
- **40~43 章（迁移，各4题）**：原文为缩进答案要点格式，已拆成编号问题 + qa 块并扩写。40=ROS2 QoS/executor/colcon/lifecycle；41=jitter/调度/mutex/deadline miss；42=9字段日志契约/timestamp_ns/三份证据/P99退化；43=五状态安全状态机/PITCH_SAFETY_LIMIT_RAD/力矩门控/故障注入。
- **44~47 章（迁移，各4题）**：原文为缩进答案要点格式。44=文档代码一致性/FMEA/接口覆盖；45=min评分/木桶原理/8类门槛；46=4大类9种故障/fault→symptom→evidence链路；47=review_pass判定/pytest-cov降级/静态分析。

## 六、batch5（H01~H10，已完成）

- **H01（撰写，4题）**：固定commit审计 / 根许可证vs单文件头 / README覆盖率vs BOM完整率 / 采购冻结保护。审计对象 commit `19a012ec`，7个候选BOM项，MIT头比例0.0。
- **H02~H10（撰写，各4题）**：均为规划中状态，通用四问模板（假设/设计/证据/排查），答案基于各章核心关系撰写：H02=clearance=hole-shaft；H03=P=UI限流；H04=tau≈Kt×Iq FOC；H05=omega=unwrap(delta_theta)/dt；H06=互补滤波alpha融合；H07=servo→joint→leg_height；H08=tau_safe=estop·rate_limit(low_pass(tau_raw))；H09=valid=sequence∧timestamp∧bounded；H10=sim distribution covers hardware uncertainty。

## 七、操作要点（踩坑记录）

1. 章节目录是纯数字/H编号：`tutorials\v2\28\README.md`、`tutorials\v2\H01\README.md`。
2. `build\oss-snapshot\` 是构建副本，**不要编辑**。
3. SearchReplace 的 original_text 必须与当前文件逐字一致（含全角/半角、粗体星号），写入前先 Grep 当前原文，不要凭记忆。
4. 每次写入后检查工具返回的 diff，重点查错别字；同文件多处修复合并为一次调用。
5. 全部批次完成后：跑完整 `pytest tests/test_tutorial_qa_format.py`，再用浏览器（course web，路由 `/chapter/{NN}`）抽查渲染，然后才能认定任务完成。
6. 全部批次已完成，batch4/batch5 均标记 COMPLETE。本交接文件仅作历史记录，不再有后续撰写工作。
