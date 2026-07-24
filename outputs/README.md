# outputs

本目录保存课程运行时生成的 checkpoint、TensorBoard 日志、实验结果、图表、视频和作品集证据。

- 固定实验可以覆盖同名结果文件，但不得手工修改指标或 `passed` 状态。
- 历史实验产物可用于对照；dashboard 会把旧源码摘要标记为 `legacy` 或 `stale`。
- 最终验收从空的临时输出目录执行，不能依赖这里已有的 JSON。
- 大型模型、视频和训练日志默认不提交 Git。
