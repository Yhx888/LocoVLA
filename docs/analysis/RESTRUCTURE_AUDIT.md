# 项目重构审计

## 当前结论

- v1 已归档到 `archive/v1-current-learning/`。
- v2 课程已成为根目录的主项目结构。
- Upkie 原始描述包保留在 `assets/upkie/upkie_description/`，不破坏 `package://upkie_description/...` 引用。
- 项目结构：`src/`、`scripts/`、`configs/`、`tests/`、`tutorials/`、`docs/feishu/`、`outputs/`。

## 历史问题（已解决）

- 旧仓库按 Phase 1/2/3 横向组织，课程主线不够聚焦 → 已重构为 00-10 章节纵向课程。
- 文档与脚本入口绑定不强 → 每章教程都有对应的 scripts/ 入口。
- 缺少统一配置、模型映射、Gymnasium 环境和测试清单 → 已建立完整的 src/ 代码库。
- 飞书同步流程、Git 回滚流程和 GitHub 发布流程不完整 → 已有 docs/ 指南。
