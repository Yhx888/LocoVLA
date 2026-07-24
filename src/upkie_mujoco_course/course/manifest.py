"""统一课程清单。"""

from __future__ import annotations

from upkie_mujoco_course.utils.config import load_json_config


READY_CHAPTERS = {
    "00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24",
    "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "H01",
}

FOUNDATION_TASKS = {
    "01": "审计 Python 科学计算环境，并用数组与数值微分验证姿态信号的数据形状、单位和有限性。",
    "02": "建立包含 commit、配置、seed、哈希和原始结果的可复现实验记录。",
    "03": "验证 Upkie 坐标变换，并用 SVD 与对称矩阵特征分解量化重构误差、条件数和主方向。",
    "04": "比较非线性摆与线性化有效区，并用中心差分审计二次型矩阵梯度。",
    "05": "从带噪俯仰角信号中恢复趋势，量化滤波降噪收益和响应滞后。",
}

MODEL_CONTRACT_TASK = "审计候选机器人是否满足自由基座、状态维度、关节映射、轮端力矩、传感器字段和采样周期契约。"

CLASSICAL_TASKS = {
    "13": "比较有无抗积分饱和的 PID，在相同限幅下量化恢复速度和积分累积。",
    "14": "建立轮式倒立摆俯仰动力学，量化小角度线性化范围和轮端力矩作用。",
    "15": "把极点实部、阻尼比、时域收敛和频率增益联系到同一组可视化证据。",
    "16": "建立四状态线性模型，用可控矩阵和可观矩阵判断状态能否被驱动和重建。",
    "18": "将速度、偏航率和高度命令映射为受限动作，并在 MuJoCo 闭环中验证跟踪和安全边界。",
}

ESTIMATION_TASKS = {
    "20": "用线性 Kalman 滤波器融合带噪俯仰测量，报告 RMSE 和协方差收敛。",
    "21": "融合 MuJoCo IMU 与轮编码器，同步比较 EKF/UKF，并让 UKF 估计进入平衡控制闭环。",
    "22": "用训练/测试分离的最小二乘辨识恢复轮式倒立摆的局部动力学系数。",
    "23": "求解带轮端边界和耦合约束的凸二次规划，报告约束残差和代价。",
    "24": "在同一双积分器问题上比较直接配点与单次打靶，并用受约束 MPC 完成 MuJoCo 闭环。",
}

RL_TASKS = {
    "25": "验证 Gymnasium 契约：observation/action shape、seed 复现性、step 时长均值/最值。",
    "26": "拆解奖励与终止/截断信号：在中性动作下量化各项奖励均值与方差。",
    "27": "在可解析的一维高斯策略上比较 REINFORCE 样本梯度、解析梯度和价值基线，证明无偏性并量化降方差收益。",
    "28": "训练并重载 50000 步轮矩 PPO，用固定 10 回合报告回报、存活率、跌倒率和俯仰安全边界。",
    "29": "对域随机化字段采样分布做覆盖率/均值/方差验证，避免“名义上随机化实际固定”。",
    "30": "训练 10000 步轮端残差 PPO，在相同 10 N 扰动和 seed 下与经典基线配对比较回报与安全指标。",
    "31": "用同一经典控制器在标称与随机化 MuJoCo 分布上进行固定种子配对评估，报告回报差、成功率、失败记录与 bootstrap 置信区间。",
}

VLA_TASKS = {
    "32": "量化高层任务→低层命令延迟与越权命令拒绝率，证明安全层级分离有效。",
    "33": "在合成 RGB-D 上运行颜色目标检测，报告像素质心误差、目标像素数与深度均值/方差。",
    "34": "把自然语言指令解析为结构化 target/verb/stop 契约，量化命中率与越权拒绝率。",
    "35": "生成三色真实 MuJoCo RGB-D 示范集，验证高层命令 npz 契约与训练/验证 seed。",
    "36": "在真实示范上拟合行为克隆策略，报告 train/val 损失并保存统一 checkpoint。",
    "37": "加载 BC checkpoint 运行三色 MuJoCo 闭环与紧急停止，报告成功、碰撞、停车、姿态和推理指标。",
}

ENGINEERING_TASKS = {
    "38": "用真实 CMake 构建和 CTest 运行 C++ 轮端控制器，并以固定种子的 1000 组输入验证 Python/C++ 数值一致性。",
    "39": "生成 CMake 依赖图，完成干净构建，并通过关闭公共头文件导出复现和定位接口边界故障。",
    "40": "在 WSL2/ROS2 Jazzy 中构建 colcon 工作区，运行控制节点，验证 /imu -> /wheel_torque 话题链路、QoS 与 100 Hz 行为。",
    "41": "在 60 秒、100 Hz 的真实 C++ 控制循环中比较 Windows 默认和 1 ms 定时器分辨率，量化周期抖动与 deadline miss。",
    "42": "在 ROS2 Jazzy 控制节点中实现 9 字段统一日志契约（JSON lines），通过 ament_cmake_gtest 验证字段完整性、时间戳单调性和失效字段拒绝，采集 10 秒稳态日志验证 100Hz 周期 deadline。",
    "43": "实现五状态安全状态机（BOOT→SELF_CHECK→DISARMED→ARMED→FAULT）纯函数，集成 /estop、/arm、/reset 服务和 /safety_state 话题，通过 13 个 gtest 和 5 种故障注入演练验证安全状态转换和力矩门控。",
    "44": "编写系统设计文档（需求→接口→风险→验证证据四层链路）和接口契约文档（话题/服务/参数/QoS/单位/限幅/坐标系），通过自动化评审报告验证文档覆盖率 100%。",
    "45": "编排综合项目（仿真→控制→安全→日志→分析全链路），用 project_score 验收第 45 关六个既有工程维度，并用 system_score 单独报告含第 46/47 关在内的八维课程就绪度。",
    "46": "执行综合故障演练（4 大类 9 种故障：传感器/执行器/通信/软件），生成故障时间线图和实验报告（fault → symptom → evidence → root cause → corrective action），验证检测覆盖率 100%。",
    "47": "执行自动化代码评审（静态分析、覆盖率、复杂度、重复检测），编写答辩材料（设计动机、实验证据、局限性、改进方向）和面试题库（47 题），验证项目可解释性和可维护性。",
}

HARDWARE_TASKS = {
    "H01": "锁定外部仓库 revision，审计根许可证、源码文件头与 README BOM 证据，并在信息不完整时明确冻结采购。",
}


def load_course_manifest() -> dict:
    raw = load_json_config("configs/course/manifest.json")
    chapters: list[dict] = []
    previous_id: str | None = None
    for stage in raw["stages"]:
        stage_previous_id = None if stage["id"] == "H" else previous_id
        for chapter_id, title in stage["chapters"]:
            status = "ready" if chapter_id in READY_CHAPTERS else "planned"
            task = FOUNDATION_TASKS.get(chapter_id)
            if chapter_id == "11":
                task = MODEL_CONTRACT_TASK
            if chapter_id in CLASSICAL_TASKS:
                task = CLASSICAL_TASKS[chapter_id]
            if chapter_id in ESTIMATION_TASKS:
                task = ESTIMATION_TASKS[chapter_id]
            if chapter_id in RL_TASKS:
                task = RL_TASKS[chapter_id]
            if chapter_id in VLA_TASKS:
                task = VLA_TASKS[chapter_id]
            if chapter_id in HARDWARE_TASKS:
                task = HARDWARE_TASKS[chapter_id]
            if chapter_id in ENGINEERING_TASKS:
                task = ENGINEERING_TASKS[chapter_id]
            if task is None:
                task = f"完成《{title}》岗位任务，并用实验数据解释结果。"
            command = f"python scripts/course_checkpoint.py --chapter {chapter_id}"
            if chapter_id in FOUNDATION_TASKS:
                lab_command = f"python scripts/run_foundation_lab.py --chapter {chapter_id}"
            elif chapter_id == "11":
                lab_command = "python scripts/11_model_contract_lab.py"
            elif chapter_id in CLASSICAL_TASKS:
                lab_command = f"python scripts/run_classical_control_lab.py --chapter {chapter_id}"
            elif chapter_id in ESTIMATION_TASKS:
                lab_command = (
                    "python scripts/run_trajectory_optimization_lab.py"
                    if chapter_id == "24"
                    else f"python scripts/run_estimation_optimization_lab.py --chapter {chapter_id}"
                )
            elif chapter_id in RL_TASKS:
                lab_command = f"python scripts/run_rl_lab.py --chapter {chapter_id}"
            elif chapter_id in VLA_TASKS:
                lab_command = f"python scripts/run_vla_lab.py --chapter {chapter_id}"
            elif chapter_id in HARDWARE_TASKS:
                lab_command = f"python scripts/run_hardware_audit.py --chapter {chapter_id}"
            elif chapter_id in ENGINEERING_TASKS:
                # 40-47 关各有独立入口脚本；38/39 使用 run_engineering_lab.py
                _eng_independent = {
                    "40": "python scripts/run_engineering_lab_40.py",
                    "41": "python scripts/run_engineering_lab_41.py",
                    "42": (
                        "python scripts/run_engineering_lab_42.py "
                        "--log-path outputs/logs/engineering_42_log.jsonl"
                    ),
                    "43": "python scripts/run_engineering_lab_43.py",
                    "44": "python scripts/run_engineering_lab_44.py",
                    "45": "python scripts/run_capstone_project.py",
                    "46": "python scripts/run_engineering_lab_46.py",
                    "47": "python scripts/run_engineering_lab_47.py",
                }
                lab_command = _eng_independent.get(
                    chapter_id,
                    f"python scripts/run_engineering_lab.py --chapter {chapter_id}",
                )
            else:
                lab_command = None
            lab_commands = [lab_command] if lab_command else []
            if chapter_id == "24":
                lab_commands.insert(0, "python scripts/run_mpc_balance_compare.py")
            acceptance = "命令、测试和可视化证据全部通过，且能解释关键设计选择。"
            portfolio = f"outputs/portfolio/{chapter_id}"
            checkpoints = []
            for experiment_command in lab_commands:
                checkpoints.append(
                    {
                        "id": (
                            "model_contract_lab"
                            if chapter_id == "11"
                            else "classical_control_lab"
                            if chapter_id in CLASSICAL_TASKS
                            else "estimation_optimization_lab"
                            if chapter_id in ESTIMATION_TASKS
                            else "rl_lab"
                            if chapter_id in RL_TASKS
                            else "vla_lab"
                            if chapter_id in VLA_TASKS
                            else "hardware_audit"
                            if chapter_id in HARDWARE_TASKS
                            else "engineering_lab"
                            if chapter_id in ENGINEERING_TASKS
                            else "foundation_lab"
                        ),
                        "command": experiment_command,
                        "acceptance": "专属实验结果通过，并生成原始日志与可视化图表。",
                    }
                )
            checkpoints.append(
                {
                    "id": "automatic_acceptance",
                    "command": command,
                    "acceptance": acceptance,
                }
            )
            chapter = {
                "id": chapter_id,
                "stage": stage["id"],
                "stage_title": stage["title"],
                "title": title,
                "task": task,
                "mission": task,
                "commands": lab_commands + [command],
                "command": command,
                "checkpoints": checkpoints,
                "acceptance": acceptance,
                "visualizations": [
                    f"outputs/plots/model_contract_11.png"
                    if chapter_id == "11"
                    else f"outputs/plots/classical_{chapter_id}.png"
                    if chapter_id in CLASSICAL_TASKS
                    else f"outputs/plots/estimation_{chapter_id}.png"
                    if chapter_id in ESTIMATION_TASKS
                    else f"outputs/plots/rl_{chapter_id}.png"
                    if chapter_id in RL_TASKS
                    else f"outputs/plots/vla_{chapter_id}.png"
                    if chapter_id in VLA_TASKS
                    else f"outputs/plots/hardware_{chapter_id}.png"
                    if chapter_id in HARDWARE_TASKS
                    else f"outputs/plots/engineering_{chapter_id}.png"
                    if chapter_id in ENGINEERING_TASKS
                    else f"outputs/plots/foundation_{chapter_id}.png"
                    if chapter_id in FOUNDATION_TASKS
                    else f"outputs/plots/checkpoint_{chapter_id}.png"
                ],
                "portfolio": portfolio,
                "artifact": portfolio,
                "tutorial": f"tutorials/v2/{chapter_id}/README.md",
                "prerequisites": [] if stage_previous_id is None else [stage_previous_id],
                "status": status,
                "completion": {
                    "status": status,
                    "required_evidence": ["test", "log", "visual"],
                },
            }
            chapters.append(chapter)
            stage_previous_id = chapter_id
        previous_id = stage_previous_id
    return {"title": raw["title"], "version": raw["version"], "stages": raw["stages"], "chapters": chapters}
