# H01 复刻范围、许可证与 BOM 审计

目标载体为 [Micro-Wheeled_leg-Robot](https://github.com/MuShibo/Micro-Wheeled_leg-Robot)。本关只读审计公开资料；不复制 CAD、PCB 或其他授权未明确资产，也不因 README 提到器件就下单。

运行：

```powershell
python scripts/run_hardware_audit.py --chapter H01
python scripts/course_checkpoint.py --chapter H01
```

当前审计锁定 commit `19a012ec8ee8b4f981aab887409a64b8dff37725`：默认分支为 `master`，根目录没有统一许可证，README 识别 7 个候选 BOM 项，三个源码文件头抽样未检出 MIT 许可证。审计通过的含义是采购冻结被正确执行，不是获得授权或允许上电。

每个 BOM 项必须再补齐型号、数量、替代料、供应商、单价、机械接口、供电需求和证据链接。当前缺少这些可采购字段，且舵机未被 README 精确提及，因此冻结整套采购。许可证范围在作者明确前，仅链接原仓库并保留审计日志。

故障挑战：将根许可证缺失手工改成“已存在”，但不改变文件树。日志会与真实文件树矛盾；应修复计算逻辑，而不是放宽冻结条件。
