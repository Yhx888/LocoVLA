# 第0章：搭建你的第一个机器人仿真环境

> 🎯 **本节目标**：用 10 分钟搭建环境，运行你的第一个机器人仿真程序。

## 你将学到什么

完成本节后，你将能够：
- 在自己电脑上运行 MuJoCo 仿真
- 看到 Upkie 机器人在屏幕上"站立"
- 理解这个课程的整体结构

## 开始之前

你需要：
- Windows 电脑（本课程基于 Windows 开发）
- Python 基础（会写 `print("hello")` 就够了）
- 好奇心 🧐

## 第一步：创建虚拟环境

> 💡 **为什么要虚拟环境？**
> 想象一下，你的电脑是一个大厨房。虚拟环境就是给你分配的一个专属小厨房，你在里面放什么工具都不会影响别人。

打开 PowerShell，进入项目目录，运行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

激活后，你的命令行前面会出现 `(.venv)`，就像这样：
```
(.venv) PS C:\HOME\Project\Bipedal-Wheel-robot-learning>
```

> 🤔 **思考**：如果关掉终端再打开，`.venv` 还在吗？答案是：还在！但需要重新激活。

## 第二步：安装依赖

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

> ⏳ **等待时间**：安装可能需要几分钟，取决于你的网速。可以先看看 `requirements.txt` 里面有什么：
> ```powershell
> type requirements.txt
> ```
> 你会看到 `mujoco`、`gymnasium`、`torch` 等，这些是我们后面会用到的工具。

## 第三步：验证安装

```powershell
python --version
python -m pip list | findstr mujoco
```

你应该看到 Python 版本 >= 3.10，以及 mujoco 已安装。

> ❓ **如果版本低于 3.10 怎么办？**
> 去 [python.org](https://www.python.org/downloads/) 下载最新版本，安装时记得勾选 "Add Python to PATH"。

## 第四步：运行你的第一个仿真脚本

```powershell
python scripts/01_check_model.py
```

运行后，你会看到类似这样的输出：
```
模型审计完成: nq=6, nv=6, nu=6
报告: outputs/model_audit/upkie_model_report.md
```

> 🔍 **这些数字是什么意思？**
> - `nq=6`：机器人有 6 个关节位置（qpos）
> - `nv=6`：机器人有 6 个关节速度（qvel）
> - `nu=6`：机器人有 6 个执行器（actuators）
>
> 现在不需要完全理解，后面会详细讲解。

## 第五步：查看生成的报告

脚本运行后，会在 `outputs/model_audit/` 目录下生成报告。打开看看：

```powershell
type outputs\model_audit\upkie_model_report.md
```

你会看到 Upkie 机器人的详细信息：有哪些关节、哪些执行器、它们的参数是什么。

> 💡 **这就是"模型审计"的意义**：在控制机器人之前，先要了解它的"身体结构"。

## 试试看：小挑战

现在你已经成功运行了第一个脚本，试试这个小挑战：

1. **修改配置**：打开 `configs/robot/upkie.json`，找到 `timestep` 字段，把它改成 `0.001`，然后重新运行 `python scripts/01_check_model.py`，看看输出有什么变化？

2. **查看其他配置**：`configs/` 目录下还有哪些配置文件？它们分别控制什么？

## 常见问题

| 问题 | 解决方案 |
|---|---|
| `ModuleNotFoundError: No module named 'mujoco'` | 依赖没装好，重新运行 `pip install -r requirements.txt` |
| `FileNotFoundError` | 检查是否在项目根目录，运行 `dir assets\upkie\` 看看文件是否存在 |
| PowerShell 提示"无法加载文件，因为在此系统上禁止运行脚本" | 以管理员身份运行 `Set-ExecutionPolicy RemoteSigned` |

## 下一步

恭喜！你已经成功搭建了环境，运行了第一个仿真脚本。

下一章，我们将深入学习**模型审计**——了解如何系统地检查一个机器人模型的各个组成部分。

**预习问题**（带着这些问题进入下一章）：
- 一个机器人模型包含哪些关键信息？
- 为什么要"审计"模型？直接用不行吗？
- 如果我要控制机器人的轮子，我需要知道什么？
