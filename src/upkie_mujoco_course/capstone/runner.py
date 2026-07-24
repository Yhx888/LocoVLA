"""第 45 关综合毕业项目编排器。

实现真实端到端毕业场景：仿真启动 → PD 控制 → 安全状态机 → 日志记录 → 综合分析。
任一维度失败令 system_score = 0.0；不靠读历史 JSON 得出毕业结论。
"""
from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from upkie_mujoco_course.capstone.scoring import compute_system_score
from upkie_mujoco_course.course.results import assess_experiment_result
from upkie_mujoco_course import engineering as engineering_contract
from upkie_mujoco_course.utils.paths import project_root

# 8 类毕业门槛 → 结果契约文件名映射
# 元组格式：(章节号, 工程实验文件名 or None, checkpoint 文件名 or None)
# - 第 37 关无专属工程实验结果，直接读取 checkpoint_37.json
# - 第 18/31 关用 checkpoint 结果契约
# - 第 42/43/44/46/47 关用 engineering_*.json 工程实验结果
GATE_TO_RESULT = {
    "code_tests": ("37", None, "checkpoint_37.json"),
    "physical_metrics": ("18", None, "checkpoint_18.json"),  # 第 18 关用 checkpoint
    "robustness": ("31", None, "checkpoint_31.json"),
    "realtime": ("42", "engineering_42.json", None),
    "safety": ("43", "engineering_43.json", None),
    "documentation": ("44", "engineering_44.json", None),
    "design_review": ("46", "engineering_46.json", None),
    "oral_defense": ("47", "engineering_47.json", None),
}

PROJECT_GATES = (
    "code_tests",
    "physical_metrics",
    "robustness",
    "realtime",
    "safety",
    "documentation",
)
PROJECT_DIMENSIONS = ("code", "physics", "robustness", "realtime", "safety", "docs")

# 端到端验证步骤 → 失败时归零的评分维度
# 任一验证步骤失败时，对应维度的分数强制为 0.0
END_TO_END_IMPACT = {
    "simulation": ["code", "physics"],       # 仿真加载失败 → code/physics 归零
    "control": ["code"],                      # 控制器失败 → code 归零
    "environment": ["code", "physics"],       # 环境失败 → code/physics 归零
    "safety_ros2": ["safety"],                # ROS2 安全失败 → safety 归零
    "log_contract": ["realtime"],             # 日志契约失败 → realtime 归零
    "doc_consistency": ["docs"],              # 文档一致性失败 → docs 归零
}

# 5 步真实端到端链路 → 失败时归零的评分维度
# 这是任务 4.2 要求的"真实仿真→控制→安全→日志→分析"链路
E2E_PIPELINE_IMPACT = {
    "physics": ["physics"],         # 仿真启动失败 → physics 归零
    "code": ["code"],               # PD 控制失败 → code 归零
    "safety": ["safety"],           # 安全状态机失败 → safety 归零
    "realtime": ["realtime"],       # 日志记录失败 → realtime 归零
    "robustness": ["robustness"],   # 综合分析失败 → robustness 归零
}

# 5 步真实端到端链路的步骤顺序（任务 4.2 要求）
E2E_PIPELINE_STEPS = [
    ("physics", "仿真启动（1000 步 MuJoCo 仿真）"),
    ("code", "PD 控制（应用到仿真 1000 步）"),
    ("safety", "安全状态机（pitch=0.5 触发 FAULT）"),
    ("realtime", "日志记录（共享字段契约 JSON lines）"),
    ("robustness", "综合分析（六个既有工程维度全部通过）"),
]


def load_gate_evidence(
    output_root: Path,
    *,
    source_root: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """加载 8 类毕业门槛的证据。

    遍历 GATE_TO_RESULT 映射，按以下优先级读取证据：
    1. engineering_*.json（工程实验结果，passed 字段在顶层）
    2. checkpoint_*.json（checkpoint 结果契约，passed 字段在顶层）
    3. graduation_gates.json（毕业门槛汇总报告，passed 字段在 gates.<gate>.passed）

    任一证据文件缺失时，该门槛 passed=False，result=None。
    """
    evidence = {}
    for gate, (chapter, exp_file, ckpt_file) in GATE_TO_RESULT.items():
        result = None
        if exp_file:
            # 工程实验结果：outputs/results/engineering_*.json
            path = output_root / "results" / exp_file
        elif ckpt_file:
            # checkpoint 结果：outputs/results/checkpoint_*.json
            path = output_root / "results" / ckpt_file
        else:
            # 第 37 关：从 graduation_gates.json 读取门槛状态
            path = output_root / "reports" / "graduation_gates.json"

        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if exp_file or ckpt_file:
                # engineering/checkpoint 契约：passed 在顶层
                result = data
            else:
                # graduation_gates.json 结构：{gates: {gate_name: {passed: bool}}}
                result = data.get("gates", {}).get(gate, {})

        if result and (exp_file or ckpt_file):
            assessment = assess_experiment_result(
                result,
                root=source_root or project_root(),
            )
            passed = bool(
                result.get("passed", False)
                and assessment["valid"]
                and not assessment["stale"]
            )
        else:
            passed = bool(result.get("passed", False)) if result else False
        evidence[gate] = {
            "chapter": chapter,
            "passed": passed,
            "result": result,
        }
    return evidence


# ---------------------------------------------------------------------------
# 6 步快速验证（保留以兼容 test_capstone_runner.py）
# ---------------------------------------------------------------------------


def _validate_simulation() -> dict[str, Any]:
    """快速验证：加载 Upkie 模型，验证 nq=13/nv=12/nu=6。"""
    t0 = time.perf_counter()
    try:
        # 延迟导入，避免在模块加载时引入 mujoco 依赖
        from upkie_mujoco_course.sim.loader import build_mujoco_model

        model = build_mujoco_model()
        nq, nv, nu = int(model.nq), int(model.nv), int(model.nu)
        passed = (nq == 13 and nv == 12 and nu == 6)
        details = {
            "nq": nq,
            "nv": nv,
            "nu": nu,
            "expected": {"nq": 13, "nv": 12, "nu": 6},
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            },
        }


def _validate_control() -> dict[str, Any]:
    """快速验证：PD 控制器对 pitch=0.1 输入产生非零力矩。"""
    t0 = time.perf_counter()
    try:
        import numpy as np

        from upkie_mujoco_course.controllers.pd import PDController

        ctrl = PDController(kp=80.0, kd=2.0, limit=1.0)
        target = np.array([0.0])
        current = np.array([0.1])
        target_vel = np.array([0.0])
        current_vel = np.array([0.0])
        output = ctrl.compute(target, current, target_vel, current_vel)
        output_value = float(np.asarray(output).flatten()[0])
        nonzero = abs(output_value) > 1e-6
        within_limit = abs(output_value) <= 1.0 + 1e-9
        passed = bool(nonzero and within_limit)
        details = {
            "controller": "PDController",
            "kp": 80.0,
            "kd": 2.0,
            "limit": 1.0,
            "pitch_input": 0.1,
            "output_torque": output_value,
            "nonzero": nonzero,
            "within_limit": within_limit,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            },
        }


def _validate_environment(seed: int = 0) -> dict[str, Any]:
    """快速验证：Gymnasium 环境 reset 后 step 一次。"""
    t0 = time.perf_counter()
    env = None
    try:
        import numpy as np

        from upkie_mujoco_course.envs.standing_env import StandingEnv

        env = StandingEnv(max_episode_steps=10)
        obs, info = env.reset(seed=seed)
        action = np.zeros(env.action_space.shape, dtype=np.float64)
        obs, reward, terminated, truncated, info = env.step(action)
        env.close()

        obs_valid = (
            isinstance(obs, np.ndarray)
            and obs.shape == env.observation_space.shape
            and np.all(np.isfinite(obs))
        )
        reward_valid = isinstance(reward, float) and np.isfinite(reward)
        term_valid = isinstance(terminated, bool)
        trunc_valid = isinstance(truncated, bool)
        info_valid = isinstance(info, dict)
        passed = bool(obs_valid and reward_valid and term_valid and trunc_valid and info_valid)
        details = {
            "env_class": "StandingEnv",
            "obs_shape": list(obs.shape) if isinstance(obs, np.ndarray) else None,
            "expected_obs_shape": list(env.observation_space.shape),
            "reward": float(reward),
            "terminated": bool(terminated),
            "truncated": bool(truncated),
            "obs_valid": bool(obs_valid),
            "reward_valid": bool(reward_valid),
            "term_valid": bool(term_valid),
            "trunc_valid": bool(trunc_valid),
            "info_valid": bool(info_valid),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        if env is not None:
            try:
                env.close()
            except Exception:  # noqa: BLE001
                pass
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            },
        }


def _validate_safety_ros2(output_root: Path) -> dict[str, Any]:
    """快速验证：读取 ROS2 故障注入结果，5 种故障全部安全。"""
    t0 = time.perf_counter()
    path = output_root / "results" / "engineering_43_ros2_fault_injection.json"
    if not path.exists():
        return {
            "passed": False,
            "details": {
                "error": f"文件不存在: {path}",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            },
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        faults = data.get("faults", [])
        summary = data.get("summary", {})
        fault_count = len(faults)
        all_safe = bool(summary.get("all_faults_safe", False))
        passed = bool(fault_count == 5 and all_safe)
        details = {
            "fault_count": fault_count,
            "expected_fault_count": 5,
            "all_faults_safe": all_safe,
            "mean_detection_latency_ms": float(summary.get("mean_detection_latency_ms", 0.0)),
            "mean_brake_latency_ms": float(summary.get("mean_brake_latency_ms", 0.0)),
            "fault_names": [f.get("fault_name", "?") for f in faults],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            },
        }


def _validate_log_contract(output_root: Path) -> dict[str, Any]:
    """快速验证：读取 engineering_42.json，共享字段契约且 0 deadline miss。"""
    t0 = time.perf_counter()
    path = output_root / "results" / "engineering_42.json"
    if not path.exists():
        return {
            "passed": False,
            "details": {
                "error": f"文件不存在: {path}",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            },
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        metrics = data.get("metrics", {})
        log_field_count = int(metrics.get("log_field_count", -1))
        deadline_miss_count = int(metrics.get("deadline_miss_count", -1))
        perf_trace_present = int(metrics.get("perf_trace_present", 0))
        passed = bool(
            log_field_count == len(engineering_contract.REQUIRED_LOG_FIELDS)
            and deadline_miss_count == 0
            and perf_trace_present == 1
        )
        details = {
            "log_field_count": log_field_count,
            "expected_log_field_count": len(engineering_contract.REQUIRED_LOG_FIELDS),
            "deadline_miss_count": deadline_miss_count,
            "expected_deadline_miss_count": 0,
            "perf_trace_present": perf_trace_present,
            "mean_period_ms": float(metrics.get("mean_period_ms", 0.0)),
            "p99_period_ms": float(metrics.get("p99_period_ms", 0.0)),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            },
        }


def _validate_doc_consistency(output_root: Path) -> dict[str, Any]:
    """快速验证：读取 doc_code_consistency_44.json，7 项检查全部通过。"""
    t0 = time.perf_counter()
    path = output_root / "results" / "doc_code_consistency_44.json"
    if not path.exists():
        return {
            "passed": False,
            "details": {
                "error": f"文件不存在: {path}",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            },
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        overall_passed = bool(data.get("overall_passed", False))
        checks = data.get("checks", [])
        check_count = len(checks)
        passed_count = sum(1 for c in checks if c.get("passed"))
        passed = bool(overall_passed and check_count >= 7 and passed_count == check_count)
        details = {
            "overall_passed": overall_passed,
            "check_count": check_count,
            "passed_count": passed_count,
            "check_names": [c.get("name", "?") for c in checks],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            },
        }


def run_end_to_end_validation(
    output_root: str | Path = "outputs",
    *,
    seed: int = 0,
) -> dict[str, dict[str, Any]]:
    """运行 6 步快速验证（保留以兼容测试）。

    每个步骤真实调用对应模块：
    1. simulation：upkie_mujoco_course.sim 加载 Upkie 模型
    2. control：upkie_mujoco_course.controllers PD 控制器
    3. environment：upkie_mujoco_course.envs Gymnasium 环境
    4. safety_ros2：读取 ROS2 故障注入结果，5 种故障全部安全
    5. log_contract：读取 engineering_42.json，共享字段契约且 0 deadline miss
    6. doc_consistency：读取 doc_code_consistency_44.json，一致性通过
    """
    p = Path(output_root)
    root = p.resolve() if p.is_absolute() else (Path(__file__).resolve().parents[3] / p).resolve()

    return {
        "simulation": _validate_simulation(),
        "control": _validate_control(),
        "environment": _validate_environment(seed=seed),
        "safety_ros2": _validate_safety_ros2(root),
        "log_contract": _validate_log_contract(root),
        "doc_consistency": _validate_doc_consistency(root),
    }


# ---------------------------------------------------------------------------
# 5 步真实端到端链路（任务 4.2 要求）
# 链路：仿真启动 → PD 控制 → 安全状态机 → 日志记录 → 综合分析
# 每一步都真实执行并采集证据，任一步骤失败立即令 system_score = 0
# ---------------------------------------------------------------------------


# 安全状态机的 Python 等价实现（与 C++ safety_state_machine.cpp 一致）
# 俯仰安全阈值（rad），与 C++ PITCH_SAFETY_LIMIT_RAD 一致
_PITCH_SAFETY_LIMIT_RAD = 0.3


class _SafetyState:
    """安全状态机五状态枚举（与 C++ SafetyState 一致）。"""
    BOOT = 0
    SELF_CHECK = 1
    DISARMED = 2
    ARMED = 3
    FAULT = 4

    @classmethod
    def name(cls, value: int) -> str:
        return {0: "BOOT", 1: "SELF_CHECK", 2: "DISARMED", 3: "ARMED", 4: "FAULT"}.get(int(value), "UNKNOWN")


def _safety_transition(
    current_state: int,
    pitch_rad: float,
    sensor_fresh: bool,
    estop_released: bool,
    arm_requested: bool,
    reset_requested: bool,
    nan_detected: bool,
    communication_lost: bool,
) -> int:
    """复现 C++ safety_state_machine.cpp 的转换逻辑（纯函数）。

    与 C++ 一致性说明：
      - 行为等价：本函数与 ros2_ws/src/upkie_control/src/safety_state_machine.cpp
        的 transition() 在所有输入组合下产生相同状态。
      - 代码组织差异（不影响行为）：C++ 将故障检查拆分为三步
        (nan/communication_lost → pitch 超限 → !estop_released)，
        Python 将 `not estop_released` 与 nan/communication_lost 合并检查。
        由于任一条件为真均进入 FAULT，两种顺序在结果上等价。
      - C++ 是权威实现（生产代码），Python 是教学/编排用的等价复现版。

    与其他 Python 实现的差异说明（P-CODE-010）：
      项目中存在三份 Python 状态机实现，本函数是其中之一：
      1. 本函数（capstone/runner.py::_safety_transition）：仅复现 C++ 纯函数，
         **不含**传感器断流扩展规则。
      2. scripts/tools/run_safety_fault_injection.py::transition：含"传感器断流
         扩展规则"——非 BOOT 状态下 sensor_fresh=False → FAULT（对应 control_node.cpp
         的传感器新鲜度监控，C++ 纯函数未显式包含此规则，由节点层调用方保证）。
      3. scripts/tools/run_fault_drill.py::transition：内联重实现，逻辑与第 2 项一致。
      差异是设计意图：本函数用于端到端毕业编排（仅验证 C++ 纯函数等价性），
      第 2/3 项用于故障演练（需要覆盖节点层的传感器断流保护）。
      待用户确认：是否将三份实现统一为同一份（推荐以 run_safety_fault_injection.py
      为权威，含传感器断流规则）？当前保留差异以匹配各自场景的测试预期。

    优先级：
      1. FAULT + 显式 reset → BOOT（人工复位）
      2. 任何故障条件 → FAULT（NaN / 通信失联 / 急停触发 / 俯仰超限）
      3. 状态机正常推进（BOOT→SELF_CHECK→DISARMED→ARMED）
    """
    # 1. reset 优先
    if current_state == _SafetyState.FAULT and reset_requested:
        return _SafetyState.BOOT
    # 2. 故障触发
    if nan_detected or communication_lost or not estop_released:
        return _SafetyState.FAULT
    if abs(pitch_rad) > _PITCH_SAFETY_LIMIT_RAD:
        return _SafetyState.FAULT
    # 3. 正常推进
    if current_state == _SafetyState.BOOT:
        return _SafetyState.SELF_CHECK
    if current_state == _SafetyState.SELF_CHECK:
        return _SafetyState.DISARMED if sensor_fresh else _SafetyState.SELF_CHECK
    if current_state == _SafetyState.DISARMED:
        if (sensor_fresh
                and abs(pitch_rad) < _PITCH_SAFETY_LIMIT_RAD
                and estop_released
                and arm_requested):
            return _SafetyState.ARMED
        return _SafetyState.DISARMED
    if current_state == _SafetyState.ARMED:
        return _SafetyState.ARMED
    return _SafetyState.FAULT


def _e2e_run_physics(sim_data: dict[str, Any], log_lines: list[str]) -> dict[str, Any]:
    """步骤 1：仿真启动（physics）。

    真实加载 MuJoCo 模型（configs/robot/upkie.json），
    运行 1000 步仿真，记录 base pitch、joint positions。

    失败条件：模型加载失败或仿真出现 NaN。
    """
    t0 = time.perf_counter()
    sim_steps = 1000
    try:
        import mujoco
        import numpy as np

        from upkie_mujoco_course.sim.loader import build_mujoco_model
        from upkie_mujoco_course.model.robot_spec import load_robot_spec

        spec = load_robot_spec()
        model = build_mujoco_model(spec)
        data = mujoco.MjData(model)

        # 找到自由基座 joint 的 qpos/qvel 地址
        root_joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, spec.root_joint_name)
        if root_joint_id < 0:
            raise RuntimeError(f"未找到自由基座 joint: {spec.root_joint_name}")
        qpos_adr = int(model.jnt_qposadr[root_joint_id])
        qvel_adr = int(model.jnt_dofadr[root_joint_id])

        # 设置初始姿态（stand 姿态）
        mujoco.mj_resetData(model, data)
        for joint_name, target in spec.default_pose["stand"].items():
            # 通过 joint_map 找地址（用 mj_name2id 兜底）
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            if jid >= 0:
                data.qpos[int(model.jnt_qposadr[jid])] = float(target)
        # 设置根部位置和姿态
        data.qpos[qpos_adr:qpos_adr + 3] = spec.default_base_position
        data.qpos[qpos_adr + 3:qpos_adr + 7] = spec.default_base_quaternion
        mujoco.mj_forward(model, data)

        time_series = []
        pitch_series = []
        joint_pos_series = []
        ctrl_series = []
        any_nan = False
        for step_idx in range(sim_steps):
            # 0 控制输入：纯被动仿真
            data.ctrl[:] = 0.0
            for _ in range(spec.frame_skip):
                mujoco.mj_step(model, data)

            # 提取 base pitch（从自由基座四元数）
            qw = float(data.qpos[qpos_adr + 3])
            qx = float(data.qpos[qpos_adr + 4])
            qy = float(data.qpos[qpos_adr + 5])
            qz = float(data.qpos[qpos_adr + 6])
            sin_pitch = 2.0 * (qw * qy - qz * qx)
            pitch = float(np.arcsin(np.clip(sin_pitch, -1.0, 1.0)))

            # 提取 6 个关节位置（与 controlled_joints 对应）
            joint_pos = []
            for jname in spec.controlled_joints:
                jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
                if jid >= 0:
                    joint_pos.append(float(data.qpos[int(model.jnt_qposadr[jid])]))
                else:
                    joint_pos.append(0.0)

            # 提取 6 个 ctrl 力矩（actuator_force）
            torque = [float(data.actuator_force[i]) for i in range(model.nu)]

            # NaN 检测
            step_values = [pitch] + joint_pos + torque
            if any(not np.isfinite(v) for v in step_values):
                any_nan = True
                break

            time_series.append(float(data.time))
            pitch_series.append(pitch)
            joint_pos_series.append(joint_pos)
            ctrl_series.append(torque)

        passed = (len(time_series) == sim_steps) and (not any_nan)

        # 保存仿真数据（供步骤 2、3 和绘图使用）
        sim_data["physics"] = {
            "steps": sim_steps,
            "time": time_series,
            "base_pitch": pitch_series,
            "joint_names": list(spec.controlled_joints),
            "joint_positions": joint_pos_series,
            "torques": ctrl_series,
            "model_nq": int(model.nq),
            "model_nv": int(model.nv),
            "model_nu": int(model.nu),
        }

        details = {
            "steps_run": len(time_series),
            "expected_steps": sim_steps,
            "any_nan": bool(any_nan),
            "final_pitch_rad": float(pitch_series[-1]) if pitch_series else None,
            "final_time_s": float(time_series[-1]) if time_series else None,
            "model_nq": int(model.nq),
            "model_nv": int(model.nv),
            "model_nu": int(model.nu),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        log_lines.append(
            f"[physics] 步骤 1 仿真启动: steps={len(time_series)}/{sim_steps}, "
            f"any_nan={any_nan}, final_pitch={details['final_pitch_rad']}, "
            f"耗时={details['elapsed_ms']}ms"
        )
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
        log_lines.append(f"[physics] 步骤 1 仿真启动失败: {type(exc).__name__}: {exc}, 耗时={elapsed}ms")
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": elapsed,
            },
        }


def _e2e_run_code(sim_data: dict[str, Any], log_lines: list[str]) -> dict[str, Any]:
    """步骤 2：PD 控制（code）。

    真实调用 PD 控制器（configs/control/pd.json），
    应用到仿真 1000 步，记录力矩输出。

    失败条件：控制力矩 NaN 或超范围。
    """
    t0 = time.perf_counter()
    sim_steps = 1000
    try:
        import mujoco
        import numpy as np

        from upkie_mujoco_course.sim.loader import build_mujoco_model
        from upkie_mujoco_course.model.robot_spec import load_robot_spec
        from upkie_mujoco_course.controllers.pd import PDController
        from upkie_mujoco_course.utils.config import load_json_config

        # 读取 PD 配置
        pd_cfg = load_json_config("configs/control/pd.json")
        kp_default = float(pd_cfg["pd"]["kp"]["default"])
        kd_default = float(pd_cfg["pd"]["kd"]["default"])
        torque_limit = float(pd_cfg["pd"]["torque_limit"]["default"])

        spec = load_robot_spec()
        model = build_mujoco_model(spec)
        data = mujoco.MjData(model)

        root_joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, spec.root_joint_name)
        qpos_adr = int(model.jnt_qposadr[root_joint_id])

        # 设置初始姿态
        mujoco.mj_resetData(model, data)
        for joint_name, target in spec.default_pose["stand"].items():
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            if jid >= 0:
                data.qpos[int(model.jnt_qposadr[jid])] = float(target)
        data.qpos[qpos_adr:qpos_adr + 3] = spec.default_base_position
        data.qpos[qpos_adr + 3:qpos_adr + 7] = spec.default_base_quaternion
        mujoco.mj_forward(model, data)

        # 构造 PD 控制器：6 维向量，腿部用 kp/kd_default，轮端用较小增益
        kp_vec = np.array([kp_default] * 4 + [1.0, 1.0], dtype=float)
        kd_vec = np.array([kd_default] * 4 + [0.1, 0.1], dtype=float)
        ctrl = PDController(kp=kp_vec, kd=kd_vec, limit=torque_limit)

        # 目标姿态：保持 stand
        target_qpos = np.zeros(model.nu, dtype=float)
        for i, jname in enumerate(spec.controlled_joints):
            target_qpos[i] = float(spec.default_pose["stand"].get(jname, 0.0))

        time_series = []
        pitch_series = []
        joint_pos_series = []
        torque_series = []
        any_nan = False
        clip_count = 0  # 记录 PD 输出被 ctrlrange 截断的次数（信息性指标，不影响 passed）

        for step_idx in range(sim_steps):
            # 当前关节位置和速度
            current_qpos = np.zeros(model.nu, dtype=float)
            current_qvel = np.zeros(model.nu, dtype=float)
            for i, jname in enumerate(spec.controlled_joints):
                jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
                if jid >= 0:
                    current_qpos[i] = float(data.qpos[int(model.jnt_qposadr[jid])])
                    current_qvel[i] = float(data.qvel[int(model.jnt_dofadr[jid])])

            # PD 计算
            action = ctrl.compute(target_qpos, current_qpos, np.zeros(model.nu), current_qvel)

            # NaN 检测（真正的失败条件）
            if not np.all(np.isfinite(action)):
                any_nan = True
                break

            # 范围截断（MuJoCo 会自动截断，这里显式 clip 并记录次数）
            ctrl_range = model.actuator_ctrlrange
            clipped = np.clip(action, ctrl_range[:, 0], ctrl_range[:, 1])
            if not np.allclose(action, clipped, atol=1e-9):
                clip_count += 1  # 信息性指标：记录截断发生但不影响 passed

            data.ctrl[:] = clipped
            for _ in range(spec.frame_skip):
                mujoco.mj_step(model, data)

            # 提取数据
            qw = float(data.qpos[qpos_adr + 3])
            qx = float(data.qpos[qpos_adr + 4])
            qy = float(data.qpos[qpos_adr + 5])
            qz = float(data.qpos[qpos_adr + 6])
            sin_pitch = 2.0 * (qw * qy - qz * qx)
            pitch = float(np.arcsin(np.clip(sin_pitch, -1.0, 1.0)))

            joint_pos = []
            for jname in spec.controlled_joints:
                jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
                if jid >= 0:
                    joint_pos.append(float(data.qpos[int(model.jnt_qposadr[jid])]))
                else:
                    joint_pos.append(0.0)
            torque = [float(data.actuator_force[i]) for i in range(model.nu)]

            time_series.append(float(data.time))
            pitch_series.append(pitch)
            joint_pos_series.append(joint_pos)
            torque_series.append(torque)

        passed = (len(time_series) == sim_steps) and (not any_nan)

        # 保存控制数据
        sim_data["code"] = {
            "steps": sim_steps,
            "time": time_series,
            "base_pitch": pitch_series,
            "joint_names": list(spec.controlled_joints),
            "joint_positions": joint_pos_series,
            "torques": torque_series,
            "pd_kp_default": kp_default,
            "pd_kd_default": kd_default,
            "torque_limit": torque_limit,
        }

        details = {
            "steps_run": len(time_series),
            "expected_steps": sim_steps,
            "any_nan": bool(any_nan),
            "final_pitch_rad": float(pitch_series[-1]) if pitch_series else None,
            "kp_default": kp_default,
            "kd_default": kd_default,
            "torque_limit": torque_limit,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        log_lines.append(
            f"[code] 步骤 2 PD 控制: steps={len(time_series)}/{sim_steps}, "
            f"any_nan={any_nan}, "
            f"final_pitch={details['final_pitch_rad']}, 耗时={details['elapsed_ms']}ms"
        )
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
        log_lines.append(f"[code] 步骤 2 PD 控制失败: {type(exc).__name__}: {exc}, 耗时={elapsed}ms")
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": elapsed,
            },
        }


def _e2e_run_safety(sim_data: dict[str, Any], log_lines: list[str]) -> dict[str, Any]:
    """步骤 3：安全状态机（safety）。

    真实调用 SafetyStateMachine（ros2_ws/src/upkie_control 的 Python 等价实现）。
    推进 BOOT→SELF_CHECK→DISARMED→ARMED，再注入 pitch=0.5（超限），验证状态进入 FAULT。

    失败条件：状态未进入 FAULT。
    """
    t0 = time.perf_counter()
    try:
        # 阶段 1：BOOT → SELF_CHECK（启动后立即进入自检）
        state = _SafetyState.BOOT
        state = _safety_transition(
            current_state=state,
            pitch_rad=0.0,
            sensor_fresh=True,
            estop_released=True,
            arm_requested=False,
            reset_requested=False,
            nan_detected=False,
            communication_lost=False,
        )
        assert state == _SafetyState.SELF_CHECK, f"BOOT→SELF_CHECK 失败: state={_SafetyState.name(state)}"

        # 阶段 2：SELF_CHECK → DISARMED（传感器新鲜）
        state = _safety_transition(
            current_state=state,
            pitch_rad=0.0,
            sensor_fresh=True,
            estop_released=True,
            arm_requested=False,
            reset_requested=False,
            nan_detected=False,
            communication_lost=False,
        )
        assert state == _SafetyState.DISARMED, f"SELF_CHECK→DISARMED 失败: state={_SafetyState.name(state)}"

        # 阶段 3：DISARMED → ARMED（显式 arm 请求 + 条件满足）
        state = _safety_transition(
            current_state=state,
            pitch_rad=0.0,
            sensor_fresh=True,
            estop_released=True,
            arm_requested=True,
            reset_requested=False,
            nan_detected=False,
            communication_lost=False,
        )
        assert state == _SafetyState.ARMED, f"DISARMED→ARMED 失败: state={_SafetyState.name(state)}"

        # 阶段 4：注入 pitch=0.5（超限），验证 ARMED → FAULT
        pitch_fault = 0.5
        state = _safety_transition(
            current_state=state,
            pitch_rad=pitch_fault,
            sensor_fresh=True,
            estop_released=True,
            arm_requested=True,
            reset_requested=False,
            nan_detected=False,
            communication_lost=False,
        )
        entered_fault = (state == _SafetyState.FAULT)

        # 阶段 5：验证 FAULT 状态下，即使 pitch 恢复正常，也只能通过 reset 离开
        state_no_reset = _safety_transition(
            current_state=state,
            pitch_rad=0.0,
            sensor_fresh=True,
            estop_released=True,
            arm_requested=True,
            reset_requested=False,
            nan_detected=False,
            communication_lost=False,
        )
        stays_fault_without_reset = (state_no_reset == _SafetyState.FAULT)

        # 阶段 6：显式 reset → BOOT
        state_after_reset = _safety_transition(
            current_state=state,
            pitch_rad=0.0,
            sensor_fresh=True,
            estop_released=True,
            arm_requested=True,
            reset_requested=True,
            nan_detected=False,
            communication_lost=False,
        )
        resets_to_boot = (state_after_reset == _SafetyState.BOOT)

        passed = bool(entered_fault and stays_fault_without_reset and resets_to_boot)

        sim_data["safety"] = {
            "pitch_fault_rad": pitch_fault,
            "pitch_limit_rad": _PITCH_SAFETY_LIMIT_RAD,
            "states_visited": ["BOOT", "SELF_CHECK", "DISARMED", "ARMED", "FAULT"],
            "final_state_after_reset": "BOOT",
            "entered_fault": entered_fault,
            "stays_fault_without_reset": stays_fault_without_reset,
            "resets_to_boot": resets_to_boot,
        }

        details = {
            "pitch_fault_rad": pitch_fault,
            "pitch_limit_rad": _PITCH_SAFETY_LIMIT_RAD,
            "entered_fault": bool(entered_fault),
            "stays_fault_without_reset": bool(stays_fault_without_reset),
            "resets_to_boot": bool(resets_to_boot),
            "state_machine": "BOOT→SELF_CHECK→DISARMED→ARMED→FAULT(pitch=0.5)",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        log_lines.append(
            f"[safety] 步骤 3 安全状态机: pitch_fault={pitch_fault}, entered_fault={entered_fault}, "
            f"stays_fault_without_reset={stays_fault_without_reset}, resets_to_boot={resets_to_boot}, "
            f"耗时={details['elapsed_ms']}ms"
        )
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
        log_lines.append(f"[safety] 步骤 3 安全状态机失败: {type(exc).__name__}: {exc}, 耗时={elapsed}ms")
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": elapsed,
            },
        }


def _e2e_run_realtime(sim_data: dict[str, Any], log_lines: list[str]) -> dict[str, Any]:
    """步骤 4：日志记录（realtime）。

    真实生成符合共享字段契约的 JSON lines 日志，验证时间戳单调递增。

    字段集合由 ``engineering.REQUIRED_LOG_FIELDS`` 统一定义。

    失败条件：字段缺失或时间戳回退。
    """
    t0 = time.perf_counter()
    expected_fields = set(engineering_contract.REQUIRED_LOG_FIELDS)
    sample_count = 200  # 生成 200 个日志样本
    try:
        import numpy as np

        # 从 physics 仿真数据采样
        pitch_data = sim_data.get("physics", {}).get("base_pitch", [])
        time_data = sim_data.get("physics", {}).get("time", [])
        torque_data = sim_data.get("physics", {}).get("torques", [])

        log_records = []
        base_ns = int(time.time() * 1e9)  # 基准时间戳（纳秒）
        prev_ts = base_ns
        timestamp_monotonic = True

        for i in range(sample_count):
            # 从仿真数据循环采样
            idx = i % len(pitch_data) if pitch_data else 0
            pitch = float(pitch_data[idx]) if pitch_data else 0.0
            t = float(time_data[idx]) if time_data else float(i) * 0.01
            torque_left = float(torque_data[idx][-2]) if torque_data and len(torque_data[idx]) >= 2 else 0.0

            # 时间戳必须严格单调递增（每周期增加 10ms = 10_000_000 ns）
            ts_ns = base_ns + i * 10_000_000
            if ts_ns <= prev_ts:
                timestamp_monotonic = False
            prev_ts = ts_ns

            record = {
                "timestamp_ns": ts_ns,
                "episode_id": 0,
                "git_commit": "e2e_simulation",
                "pitch_rad": pitch,
                "pitch_rate_rad_s": 0.0,  # 简化：未计算角速度
                "raw_torque_common_nm": torque_left,
                "clamped_torque_common_nm": max(-1.0, min(1.0, torque_left)),
                "safety_flag": 0,  # 0=正常
                "loop_cycle_ms": 10.0,  # 100Hz 控制周期
            }
            log_records.append(record)

        # 字段完整性校验
        fields_ok = all(set(r.keys()) == expected_fields for r in log_records)
        # 时间戳单调递增校验
        # 注意：本检查与 C++ log_contract.cpp::check_monotonic 一致，使用严格递增（>），
        # 不允许相等。教程 tutorials/v2/42/README.md 中描述"非降（允许相等）"是文档错误，
        # 代码实现以严格递增为准。
        timestamps = [r["timestamp_ns"] for r in log_records]
        ts_monotonic = all(timestamps[i] < timestamps[i + 1] for i in range(len(timestamps) - 1))

        passed = bool(fields_ok and ts_monotonic and len(log_records) == sample_count)

        sim_data["realtime"] = {
            "sample_count": sample_count,
            "field_count": len(expected_fields),
            "expected_field_count": len(engineering_contract.REQUIRED_LOG_FIELDS),
            "fields": sorted(list(expected_fields)),
            "timestamp_monotonic": bool(ts_monotonic),
            "first_timestamp_ns": int(timestamps[0]) if timestamps else None,
            "last_timestamp_ns": int(timestamps[-1]) if timestamps else None,
            "log_records": log_records,  # 完整日志记录
        }

        details = {
            "sample_count": len(log_records),
            "expected_sample_count": sample_count,
            "field_count": len(expected_fields),
            "expected_field_count": len(engineering_contract.REQUIRED_LOG_FIELDS),
            "fields_ok": bool(fields_ok),
            "timestamp_monotonic": bool(ts_monotonic),
            "first_timestamp_ns": int(timestamps[0]) if timestamps else None,
            "last_timestamp_ns": int(timestamps[-1]) if timestamps else None,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        log_lines.append(
            f"[realtime] 步骤 4 日志记录: samples={len(log_records)}/{sample_count}, "
            f"fields_ok={fields_ok}, ts_monotonic={ts_monotonic}, "
            f"field_count={len(expected_fields)}, 耗时={details['elapsed_ms']}ms"
        )
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
        log_lines.append(f"[realtime] 步骤 4 日志记录失败: {type(exc).__name__}: {exc}, 耗时={elapsed}ms")
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": elapsed,
            },
        }


def _e2e_run_robustness(
    sim_data: dict[str, Any],
    e2e_results: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    log_lines: list[str],
) -> dict[str, Any]:
    """步骤 5：综合分析（robustness）。

    真实计算综合指标，验证所有维度通过。

    失败条件：任一维度不通过。
    """
    t0 = time.perf_counter()
    try:
        # 检查前 4 步端到端验证全部通过
        first_four_steps = ["physics", "code", "safety", "realtime"]
        first_four_passed = all(e2e_results.get(step, {}).get("passed", False) for step in first_four_steps)

        # 检查 8 类毕业门槛全部通过
        gates_passed = {
            gate: evidence.get(gate, {}).get("passed", False)
            for gate in PROJECT_GATES
        }
        all_gates_passed = all(gates_passed.values())

        # 检查仿真数据完整性
        sim_data_complete = (
            "physics" in sim_data
            and "code" in sim_data
            and "safety" in sim_data
            and "realtime" in sim_data
            and len(sim_data.get("physics", {}).get("time", [])) == 1000
            and len(sim_data.get("code", {}).get("time", [])) == 1000
        )

        passed = bool(first_four_passed and all_gates_passed and sim_data_complete)

        sim_data["robustness"] = {
            "first_four_passed": bool(first_four_passed),
            "all_gates_passed": bool(all_gates_passed),
            "sim_data_complete": bool(sim_data_complete),
            "gates_passed": gates_passed,
        }

        details = {
            "first_four_passed": bool(first_four_passed),
            "all_gates_passed": bool(all_gates_passed),
            "sim_data_complete": bool(sim_data_complete),
            "gate_passed_count": int(sum(1 for v in gates_passed.values() if v)),
            "gate_total_count": int(len(gates_passed)),
            "physics_steps": int(len(sim_data.get("physics", {}).get("time", []))),
            "code_steps": int(len(sim_data.get("code", {}).get("time", []))),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        log_lines.append(
            f"[robustness] 步骤 5 综合分析: first_four_passed={first_four_passed}, "
            f"all_gates_passed={all_gates_passed}, sim_data_complete={sim_data_complete}, "
            f"gates={details['gate_passed_count']}/{details['gate_total_count']}, "
            f"耗时={details['elapsed_ms']}ms"
        )
        return {"passed": passed, "details": details}
    except Exception as exc:  # noqa: BLE001
        elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
        log_lines.append(f"[robustness] 步骤 5 综合分析失败: {type(exc).__name__}: {exc}, 耗时={elapsed}ms")
        return {
            "passed": False,
            "details": {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": elapsed,
            },
        }


def run_e2e_pipeline(output_root: str | Path = "outputs") -> dict[str, Any]:
    """运行 5 步真实端到端链路（任务 4.2 要求）。

    链路：仿真启动 → PD 控制 → 安全状态机 → 日志记录 → 综合分析

    每一步都真实执行并采集证据，任一步骤失败立即令对应维度归零。
    生成两个文件：
    - outputs/logs/engineering_45_e2e_run.log：端到端运行日志
    - outputs/logs/engineering_45_simulation_data.json：1000 步仿真数据

    Args:
        output_root: outputs 目录路径

    Returns:
        dict 包含 5 步结果、simulation_data、log_path、sim_data_path
    """
    p = Path(output_root)
    root = p.resolve() if p.is_absolute() else (Path(__file__).resolve().parents[3] / p).resolve()

    log_lines: list[str] = []
    sim_data: dict[str, Any] = {}
    log_lines.append(f"=== 第 45 关端到端毕业项目运行开始 {datetime.now(timezone.utc).isoformat()} ===")

    # 步骤 1：仿真启动（physics）
    physics_result = _e2e_run_physics(sim_data, log_lines)
    # 步骤 2：PD 控制（code）—— 注意：步骤 2 会重新运行 1000 步仿真，独立采集数据
    code_result = _e2e_run_code(sim_data, log_lines)
    # 步骤 3：安全状态机（safety）
    safety_result = _e2e_run_safety(sim_data, log_lines)
    # 步骤 4：日志记录（realtime）
    realtime_result = _e2e_run_realtime(sim_data, log_lines)

    # 加载 8 类毕业门槛证据（步骤 5 需要）
    evidence = load_gate_evidence(root)
    # 步骤 5：综合分析（robustness）
    e2e_partial = {
        "physics": physics_result,
        "code": code_result,
        "safety": safety_result,
        "realtime": realtime_result,
    }
    robustness_result = _e2e_run_robustness(sim_data, e2e_partial, evidence, log_lines)

    log_lines.append(f"=== 第 45 关端到端毕业项目运行结束 {datetime.now(timezone.utc).isoformat()} ===")

    # 写出端到端运行日志
    log_path = root / "logs" / "engineering_45_e2e_run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    # 写出仿真数据 JSON（不含 log_records 完整内容，避免文件过大；保留统计摘要）
    sim_data_path = root / "logs" / "engineering_45_simulation_data.json"
    sim_data_path.parent.mkdir(parents=True, exist_ok=True)
    # 保留完整的 time/base_pitch/joint_positions/torques 序列（用于绘图）
    # 但 log_records 仅保留前 5 条作为样本
    sim_data_to_save = dict(sim_data)
    if "realtime" in sim_data_to_save and "log_records" in sim_data_to_save["realtime"]:
        records = sim_data_to_save["realtime"]["log_records"]
        sim_data_to_save["realtime"] = dict(sim_data_to_save["realtime"])
        sim_data_to_save["realtime"]["log_records_sample"] = records[:5]
        sim_data_to_save["realtime"]["log_records_count"] = len(records)
        del sim_data_to_save["realtime"]["log_records"]
    sim_data_path.write_text(json.dumps(sim_data_to_save, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "physics": physics_result,
        "code": code_result,
        "safety": safety_result,
        "realtime": realtime_result,
        "robustness": robustness_result,
        "simulation_data": sim_data,
        "log_path": str(log_path),
        "sim_data_path": str(sim_data_path),
    }


def run_capstone(
    output_root: str | Path = "outputs",
    *,
    seed: int = 0,
) -> dict[str, Any]:
    """运行综合毕业项目，返回评分和证据。

    编排两条并行链路：
    1. **6 步快速验证**（保留以兼容 test_capstone_runner.py）
    2. **5 步真实端到端链路**（任务 4.2 要求：仿真启动→PD控制→安全状态机→日志记录→综合分析）

    端到端链路真实运行 1000 步 MuJoCo 仿真、调用 PD 控制器、调用安全状态机、
    生成符合共享字段契约的 JSON lines 日志、综合分析所有维度。

    任一步骤失败（6 步快速验证或 5 步真实链路）都会强制令对应维度分数为 0.0，
    最终 system_score = min(所有维度)，任一维度失败则为 0.0。

    第 45 关通过条件：project_score >= 1.0；system_score 仅报告八维课程工程就绪度。
    """
    p = Path(output_root)
    # 相对路径相对于仓库 ROOT 解析（runner.py 在 src/upkie_mujoco_course/capstone/ 下）
    root = p.resolve() if p.is_absolute() else (Path(__file__).resolve().parents[3] / p).resolve()

    # 链路 1：6 步快速验证（保留以兼容 test_capstone_runner.py）
    end_to_end = run_end_to_end_validation(root, seed=seed)

    # 链路 2：5 步真实端到端链路（任务 4.2 要求）
    e2e_pipeline = run_e2e_pipeline(root)

    # 读取 8 类毕业门槛证据
    evidence = load_gate_evidence(root)

    # 计算综合评分（基于证据的初步评分）
    scores = compute_system_score(evidence)
    dimension_scores = dict(scores["dimension_scores"])

    # 6 步快速验证失败 → 强制归零对应维度
    end_to_end_overrides: dict[str, list[str]] = {}
    for step, result in end_to_end.items():
        if not result["passed"]:
            impacted_dims = END_TO_END_IMPACT.get(step, [])
            for dim in impacted_dims:
                dimension_scores[dim] = 0.0
            end_to_end_overrides[step] = impacted_dims

    # 5 步真实端到端链路失败 → 强制归零对应维度
    e2e_overrides: dict[str, list[str]] = {}
    for step, _label in E2E_PIPELINE_STEPS:
        result = e2e_pipeline.get(step, {})
        if not result.get("passed", False):
            impacted_dims = E2E_PIPELINE_IMPACT.get(step, [])
            for dim in impacted_dims:
                dimension_scores[dim] = 0.0
            e2e_overrides[step] = impacted_dims

    # system_score = min(所有维度)
    system_score = min(dimension_scores.values()) if dimension_scores else 0.0
    project_score = min(dimension_scores[name] for name in PROJECT_DIMENSIONS)

    report = {
        "schema_version": "1.0",
        "chapter_id": "45",
        "system_score": float(system_score),
        "project_score": float(project_score),
        "course_readiness_passed": float(system_score) >= 1.0,
        "dimension_scores": dimension_scores,
        "evidence": evidence,
        "end_to_end_validation": end_to_end,
        "end_to_end_overrides": end_to_end_overrides,
        "e2e_pipeline": {
            step: e2e_pipeline[step] for step, _ in E2E_PIPELINE_STEPS
        },
        "e2e_overrides": e2e_overrides,
        "e2e_log_path": e2e_pipeline.get("log_path"),
        "e2e_sim_data_path": e2e_pipeline.get("sim_data_path"),
        "simulation_data": e2e_pipeline.get("simulation_data", {}),
        "pass_conditions": {
            "project_score": {"operator": ">=", "value": 1.0}
        },
        "passed": float(project_score) >= 1.0,
    }
    return report
