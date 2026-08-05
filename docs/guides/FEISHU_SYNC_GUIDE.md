# 飞书文档同步指南

## 推荐工作流

1. 在本地仓库修改 `tutorials/` 和 `docs/feishu/`。
2. 在本地运行对应 demo。
3. 截图或录制视频，保存到 `outputs/`。
4. 将 `docs/feishu/<chapter>.md` 复制到飞书。
5. 在飞书文档顶部注明对应 commit hash。
6. 如果飞书内容有修改，反向同步回仓库 Markdown。

## 每篇飞书文档建议标题

- 00 安装与环境检查
- 01 Upkie 模型审计
- 02 MuJoCo 基础
- 03 传统控制
- 04 控制接口
- 05 Gymnasium 环境封装
- 06 强化学习训练
- 07 鲁棒性与随机化
- 08 残差强化学习
- 09 替换机器人模型
- 10 高层指令接口

## 在飞书中记录代码版本

建议每篇文档顶部写：

```text
对应仓库 commit: <hash>
最后验证日期: <date>
运行环境: Windows + Python + MuJoCo
```

## 画板同步

写文档时，核心流程、系统架构、方案对比、能力分层等内容应优先规划为画板，不要只用文字或表格承载。**画板创作流程详见 `AGENTS.md` 「飞书画板（框架图）创作规范」章节**，要点如下：

- **图表类型路由**：思维导图、时序图、类图、饼图、甘特图走 Mermaid；流程图、树图、结构图、示意图等走 SVG。
- **SVG 创作流程**：写入 `./diagrams/YYYY-MM-DDTHHMMSS/diagram*.svg` → 用 `npx -y @larksuite/whiteboard-cli@^0.2.11` 渲染检查（必须 0 errors / 0 warnings）→ 导出 OpenAPI JSON → 用 `lark-cli docs +update --command block_insert_after --block-id <目标block>` 插入 `<whiteboard type="svg">完整SVG</whiteboard>`。
- **SVG 设计约束**：允许的元素与变换、禁用项、字体（Noto Sans SC）、连线（正交折线优先）等约束以 `AGENTS.md` 为准。
- **Mermaid 流程**：直接用 `lark-cli docs +update` 插入 `<whiteboard type="mermaid">代码</whiteboard>`。

修改画板后必须重新同步到飞书，避免飞书与仓库画板内容漂移。
