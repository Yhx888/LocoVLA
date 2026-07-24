# H01 复刻范围、许可证与 BOM 审计

> 建设状态：可执行  
> 阶段：硬件选修（独立于毕业项目）  
> 作品集目录：`outputs/portfolio/H01`

## 岗位任务

在采购、加工或复刻一个开源轮足项目之前，先回答三件事：资产能否合法参考，BOM 是否足以实际下单，资料缺口会不会直接转化为供电、装配或安全风险。本关以 [Micro-Wheeled_leg-Robot](https://github.com/MuShibo/Micro-Wheeled_leg-Robot) 为只读审计对象，不复制 CAD、PCB 或授权不明确的资产。

本关的“通过”表示审计脚本能够把不充分证据识别出来并冻结采购；它绝不表示该仓库已获得统一授权，也不表示机器人可以上电。

## 学习目标

- 区分仓库根许可证、单文件许可头、README 描述和可采购 BOM 的法律与工程含义。
- 用固定 commit 而非浮动分支名保存审计证据。
- 将每个 BOM 条目标记为“README 已提及”“README 未提及”或“实际目录未找到”。
- 在型号、数量、供应商、接口或许可缺失时做出可复核的采购冻结结论。

## 前置关卡

这是高级选修的起点，不依赖 `47` 毕业项目。实机经验者可跳过基础电子知识，但不能跳过许可、供电和采购边界审计。

## 先观察现象

```powershell
python scripts/run_hardware_audit.py --chapter H01
```

本次真实远程快照锁定为 commit `19a012ec8ee8b4f981aab887409a64b8dff37725`，默认分支为 `master`。审计发现根目录没有 `LICENSE`、`COPYING` 或 `NOTICE`；README 覆盖 7 个候选 BOM 项中的 6 个，源码抽样 3 个文件的 MIT 文件头比例为 `0.0`。因此采购冻结，不能将历史印象或单个文件的旧许可说法当作当前证据。

## 直觉与概念

<!-- upkie-animation:h01-core -->

README 像一张愿望清单，BOM 像可下单的工程合同，许可证则限定你能如何使用资料。三者不是同一件事。一个“ESP32”字样没有型号、数量、接口电平、供应商和替代料，就不能让采购人员安全下单；一个源码文件出现许可头，也不能自动授权同仓库中的 CAD 或 PCB。

## 教科书级展开

审计对象可写为：

审计结论 = commit + 根许可证 + 源码许可抽样 + BOM 证据 + 采购风险

其中 commit 是不可变的 Git 标识，不带物理单位；BOM 的数量单位是 `pcs`，价格应是货币/pcs，电池电压是 `V`，电流是 `A`。本关没有假设“缺少许可证就一定侵权”，它只说明授权范围不明确，课程只能链接原仓库而不能复制未明确资产。失效条件包括仓库后续更新、GitHub API 不可用、README 改写或审计样本不足；任一情况都必须重新锁定 revision。

`fetch_repository_snapshot()` 依次读取仓库元数据、分支 commit、递归文件树、README 和三个源码文件头。`audit_repository_snapshot()` 查找根许可证名、计算源码 MIT 头比例，并将 PCB、ESP32、L6234PD013TR、AS5600、MPU6050、舵机、GH1.25 写成差异表。代码不会下载或导入 CAD/PCB，只记录路径和文本证据。

本次指标为：根许可证缺失 `1.0`、BOM 项数 `7.0`、采购冻结 `1.0`。README 覆盖率约为 `0.8571428571428571`，但这不是 BOM 完整率，因为实际下单字段仍然缺失。将 `0.857` 写成“85.7% 可以采购”是错误推论。

## 动手检查点

```powershell
python scripts/run_hardware_audit.py --chapter H01
python scripts/course_checkpoint.py --chapter H01
```

预期生成 `outputs/logs/hardware_H01.json`、`outputs/plots/hardware_H01.png`、`outputs/results/hardware_H01.json` 和 `outputs/portfolio/H01/evidence.json`。自动验收检查根许可证缺失被正确识别、至少识别 6 个候选 BOM 项，并确认采购冻结没有被绕过。

## 可视化证据

`outputs/plots/hardware_H01.png` 显示 README 对每个候选项的提及情况；日志保留 commit、许可矩阵、BOM 差异和冻结原因；`tests/test_hardware_audit.py` 用注入快照验证缺少根许可证时一定不能放行。图表回答“提到了什么”，日志回答“依据哪个版本”，测试回答“下次是否仍会冻结”。

## 故障诊断挑战

故意把 `root_license_present=False` 改成 `True`，但保持根目录文件树不变。现象是采购冻结会被错误放宽；第一处异常证据是日志中的许可证字段与 `root_paths` 矛盾。最小修复是恢复从文件树计算许可证，而不是手工填布尔值。

另一个常见错误是把 README 中的“舵机”同义词或图片说明误当成精确型号。应记录原始文本、型号、数量、连接器、供电电压和证据 URL；缺一项即保留冻结。

## 三档任务

- 基础任务：复现快照并解释三个通过条件为何都指向“停止采购”。
- 岗位挑战：为每个 BOM 项补充型号、数量、替代料、单价、供应风险和证据链接，再重新审计。
- 开放探索：若项目作者补充根许可证，先复核授权覆盖的资产类别，再决定是否解除哪一部分冻结；不要把软件许可外推到 CAD/PCB。

## 复盘与面试

1. 为什么固定 commit 比默认分支更适合审计？
2. 根许可证缺失和单文件许可头分别意味着什么？
3. README 覆盖率为什么不能替代 BOM 完整率？
4. 采购冻结如何保护后续 FOC、IMU 和上电安全工作？

## 下一关

`H02` 只在许可和 BOM 范围被明确后进入机械加工与装配公差；本关留下的冻结证据必须随项目而非被删除。
