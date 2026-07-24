#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 47 关实验编排入口：自动化代码评审→写结果契约。

调用 ``scripts/tools/run_code_review.py`` 对 ``src/upkie_mujoco_course/``
与 ``scripts/`` 做静态分析、覆盖率、复杂度、重复检测，生成
``outputs/reports/code_review_47.md`` 与指标契约，再据此汇总 metrics 写出
统一结果契约（``outputs/results/engineering_47.json``）与 portfolio 报告。

通过条件（动态，取决于 pytest-cov 是否可用）：
- pytest-cov 可用：review_pass == 1 且 coverage_percent >= 50
- pytest-cov 不可用：review_pass == 1（review_pass 此时等价于无语法错误）

用法：
    python scripts/run_engineering_lab_47.py [--output-root outputs]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.course.results import write_experiment_result  # noqa: E402

REVIEW_SCRIPT = ROOT / "scripts" / "tools" / "run_code_review.py"
_REVIEW_TIMEOUT_SECONDS = 660

PAPER_READING_TASKS = [
    {
        "title": "Design and Control of a Bio-inspired Wheeled Bipedal Robot",
        "citation_id": "arXiv:2308.13205",
        "verification_url": "https://arxiv.org/abs/2308.13205",
        "problem": "轮式双足在改变机身高度和姿态时，怎样同时保持轮上平衡与全身动力学一致？",
        "method": "梳理高度可变轮式线性倒立摆、控制李雅普诺夫函数约束与全身控制的分层关系。",
        "formula_or_experiment": "定位 CLF 下降条件，解释 V_dot <= -gamma V 的变量与适用条件；复核深蹲、速度跟踪和扰动实验各自支持什么主张。",
        "limitations": "区分论文机器人与 Upkie 的机构、传感器和算力差异，列出至少两项不能直接迁移的假设。",
        "project_mapping": "映射到第 17、19、24 关的 LQR/MPC 平衡状态、轮端力矩约束和 MuJoCo 闭环指标。",
        "deliverable_path": "outputs/portfolio/47/papers/01_wheeled_biped_control.md",
    },
    {
        "title": "Learning to Walk in Minutes Using Massively Parallel Deep Reinforcement Learning",
        "citation_id": "arXiv:2109.11978",
        "verification_url": "https://proceedings.mlr.press/v164/rudin22a.html",
        "problem": "大规模并行仿真如何缩短腿式运动策略训练时间，同时维持真实机器人迁移能力？",
        "method": "分析并行 on-policy 训练、PPO 采样设置和按表现调节难度的课程学习。",
        "formula_or_experiment": "写出 PPO clipped objective，逐项解释概率比和优势；从论文实验表中记录并行规模、训练时间与真实迁移证据。",
        "limitations": "论文对象是 ANYmal 且依赖 GPU 并行；说明这些结果为何不能直接证明当前 CPU MuJoCo Upkie 策略达标。",
        "project_mapping": "映射到第 25-31 关的 PPO 配置、域随机化、课程难度、固定 seed 和训练/评估分离。",
        "deliverable_path": "outputs/portfolio/47/papers/02_parallel_rl.md",
    },
    {
        "title": "RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control",
        "citation_id": "arXiv:2307.15818",
        "verification_url": "https://proceedings.mlr.press/v229/zitkovich23a.html",
        "problem": "怎样把视觉语言预训练知识接入机器人动作预测，并检验新物体、新场景和新指令下的泛化？",
        "method": "梳理机器人轨迹与视觉语言数据共同微调、动作离散为 token、闭环执行与受控分布偏移评估。",
        "formula_or_experiment": "写出动作 token 的负对数似然目标，并从论文评估中选一组已见/未见条件对照，说明指标能证明和不能证明什么。",
        "limitations": "RT-2 的机械臂数据、模型规模和算力不等于 Upkie；重点分析动作 token、延迟和安全停机的迁移边界。",
        "project_mapping": "映射到第 32-37 关的视觉输入、语言命令、BC/VLA 闭环、停止命令与低层安全控制。",
        "deliverable_path": "outputs/portfolio/47/papers/03_rt2_vla.md",
    },
]

_CPP_BUILD_COMMAND = (
    "cmake -S outputs/portfolio/47/cpp -B outputs/portfolio/47/cpp/build "
    "&& cmake --build outputs/portfolio/47/cpp/build"
)

CPP_ALGORITHM_ROUTE = [
    {
        "milestone": "M1-滑动统计",
        "algorithm_problem": "在线计算最近 N 个控制周期的 RMSE、最大值和 P99，不保存无限历史。",
        "data_structures": ["std::deque", "std::vector", "双端单调队列"],
        "source_path": "outputs/portfolio/47/cpp/01_rolling_metrics.cpp",
        "test_path": "outputs/portfolio/47/cpp/tests/01_rolling_metrics_test.cpp",
        "check_command": (
            f"{_CPP_BUILD_COMMAND} && ctest --test-dir outputs/portfolio/47/cpp/build "
            "-R rolling_metrics --output-on-failure"
        ),
        "acceptance": "空输入、窗口为 1、重复值和 10000 点流式输入全部通过；窗口内存为 O(N)。",
        "evidence_paths": [
            "outputs/portfolio/47/cpp/01_rolling_metrics.cpp",
            "outputs/portfolio/47/cpp/logs/01_rolling_metrics.txt",
        ],
    },
    {
        "milestone": "M2-先修关系图",
        "algorithm_problem": "验证课程先修图无环，并输出 00-47 的一种合法拓扑顺序。",
        "data_structures": ["std::unordered_map", "std::vector", "std::queue", "Kahn 拓扑排序"],
        "source_path": "outputs/portfolio/47/cpp/02_prerequisite_graph.cpp",
        "test_path": "outputs/portfolio/47/cpp/tests/02_prerequisite_graph_test.cpp",
        "check_command": (
            f"{_CPP_BUILD_COMMAND} && ctest --test-dir outputs/portfolio/47/cpp/build "
            "-R prerequisite_graph --output-on-failure"
        ),
        "acceptance": "正常 DAG、孤立节点、重复边和人工环四类用例通过，并能报告构成环的节点。",
        "evidence_paths": [
            "outputs/portfolio/47/cpp/02_prerequisite_graph.cpp",
            "outputs/portfolio/47/cpp/logs/02_prerequisite_graph.txt",
        ],
    },
    {
        "milestone": "M3-受限网格规划",
        "algorithm_problem": "在带障碍和风险代价的二维网格上求最低代价路径，禁止穿越安全区。",
        "data_structures": ["std::priority_queue", "std::unordered_map", "Dijkstra", "父节点回溯"],
        "source_path": "outputs/portfolio/47/cpp/03_grid_planner.cpp",
        "test_path": "outputs/portfolio/47/cpp/tests/03_grid_planner_test.cpp",
        "check_command": (
            f"{_CPP_BUILD_COMMAND} && ctest --test-dir outputs/portfolio/47/cpp/build "
            "-R grid_planner --output-on-failure"
        ),
        "acceptance": "可达、不可达、起终点相同和高风险绕行用例通过；输出路径每一步相邻且总代价可复算。",
        "evidence_paths": [
            "outputs/portfolio/47/cpp/03_grid_planner.cpp",
            "outputs/portfolio/47/cpp/logs/03_grid_planner.txt",
        ],
    },
    {
        "milestone": "M4-实验调度",
        "algorithm_problem": "在总时长预算内选择互不冲突的实验，使证据价值总和最大。",
        "data_structures": ["std::vector", "std::lower_bound", "动态规划", "解路径回溯"],
        "source_path": "outputs/portfolio/47/cpp/04_experiment_scheduler.cpp",
        "test_path": "outputs/portfolio/47/cpp/tests/04_experiment_scheduler_test.cpp",
        "check_command": (
            f"{_CPP_BUILD_COMMAND} && ctest --test-dir outputs/portfolio/47/cpp/build "
            "-R experiment_scheduler --output-on-failure"
        ),
        "acceptance": "空集合、单实验、全部冲突和贪心失败反例通过；返回最优值及可复核的实验编号。",
        "evidence_paths": [
            "outputs/portfolio/47/cpp/04_experiment_scheduler.cpp",
            "outputs/portfolio/47/cpp/logs/04_experiment_scheduler.txt",
        ],
    },
]


def validate_paper_reading_tasks(tasks: list[dict[str, object]]) -> bool:
    required = {
        "title",
        "citation_id",
        "verification_url",
        "problem",
        "method",
        "formula_or_experiment",
        "limitations",
        "project_mapping",
        "deliverable_path",
    }
    identifiers = [str(task.get("citation_id", "")) for task in tasks]
    return bool(
        len(tasks) >= 3
        and len(set(identifiers)) == len(tasks)
        and all(required <= task.keys() for task in tasks)
        and all(all(task.get(field) for field in required) for task in tasks)
        and all(str(task["verification_url"]).startswith("https://") for task in tasks)
        and all(str(task["deliverable_path"]).startswith("outputs/portfolio/47/") for task in tasks)
    )


def validate_cpp_algorithm_route(route: list[dict[str, object]]) -> bool:
    required = {
        "milestone",
        "algorithm_problem",
        "data_structures",
        "source_path",
        "test_path",
        "check_command",
        "acceptance",
        "evidence_paths",
    }
    return bool(
        len(route) >= 4
        and all(required <= item.keys() for item in route)
        and all(item.get("data_structures") for item in route)
        and all(str(item["source_path"]).endswith(".cpp") for item in route)
        and all(str(item["test_path"]).endswith(".cpp") for item in route)
        and all(
            any(tool in str(item["check_command"]) for tool in ("g++", "cmake", "ctest"))
            for item in route
        )
        and all(
            all(
                str(path).startswith("outputs/portfolio/47/")
                for path in item["evidence_paths"]
            )
            for item in route
        )
    )


def write_learning_task_contracts(output_root: Path) -> tuple[Path, Path]:
    """写出论文精读和 C++ 路线契约，返回两个文件路径。"""

    learning_root = output_root / "portfolio" / "47"
    learning_root.mkdir(parents=True, exist_ok=True)
    paper_tasks_path = learning_root / "paper_reading_tasks.json"
    cpp_route_path = learning_root / "cpp_algorithm_route.json"
    paper_tasks_path.write_text(
        json.dumps(PAPER_READING_TASKS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    cpp_route_path.write_text(
        json.dumps(CPP_ALGORITHM_ROUTE, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return paper_tasks_path, cpp_route_path


def _write_review_plot(metrics: dict[str, float], path: Path) -> None:
    """生成代码评审指标可视化图表。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 设置中文字体
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False

    labels = [
        "覆盖率 (%)",
        "平均嵌套深度",
        "重复率 (%)",
        "静态告警",
        "语法错误",
    ]
    values = [
        metrics.get("coverage_percent", 0.0),
        metrics.get("avg_complexity", 0.0),
        metrics.get("duplicate_percent", 0.0),
        metrics.get("static_warnings", 0.0),
        metrics.get("syntax_errors", 0.0),
    ]
    colors = ["#17745a" if v == 0 or (i == 0 and v >= 50) else "#d36b27" for i, v in enumerate(values)]

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(labels, values, color=colors)
    ax.set_xlabel("数值")
    ax.set_title("第 47 关代码评审指标")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _resolve_output_root(value: str, source_root: Path) -> Path:
    """将输出根目录解析为绝对路径，相对路径相对于源码根。"""
    p = Path(value)
    return p.resolve() if p.is_absolute() else (source_root / p).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="运行第 47 关代码评审实验")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--source-root", default=str(ROOT))
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    output_root = _resolve_output_root(args.output_root, source_root)
    paper_tasks_valid = validate_paper_reading_tasks(PAPER_READING_TASKS)
    cpp_route_valid = validate_cpp_algorithm_route(CPP_ALGORITHM_ROUTE)
    paper_tasks_path, cpp_route_path = write_learning_task_contracts(output_root)

    # 1. 调用代码评审脚本（在仓库根目录执行）
    # run_code_review.py 固定写入 ROOT/outputs/reports/，故指标从此处读取
    # 安全措施：输出写入日志文件，超时保护，不在内存中无限 capture_output
    cmd = [
        sys.executable,
        str(REVIEW_SCRIPT),
        "--output-root",
        str(output_root),
    ]
    review_log = output_root / "logs" / "engineering_47_review.log"
    review_log.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(review_log, "w", encoding="utf-8") as log_f:
            proc = subprocess.run(
                cmd, cwd=str(ROOT),
                stdout=log_f, stderr=subprocess.STDOUT,
                timeout=_REVIEW_TIMEOUT_SECONDS,
            )
    except subprocess.TimeoutExpired:
        print(
            f"[FAIL] 代码评审超时（>{_REVIEW_TIMEOUT_SECONDS}s），已终止",
            file=sys.stderr,
        )
        return 1
    if proc.returncode != 0:
        print(
            f"[FAIL] 代码评审失败（退出码 {proc.returncode}），详见 {review_log}",
            file=sys.stderr,
        )
        return proc.returncode

    # 2. 读取指标契约（固定路径，与 run_code_review.py 输出一致）
    metrics_path = output_root / "reports" / "code_review_47_metrics.json"
    report_path = output_root / "reports" / "code_review_47.md"
    if not metrics_path.exists():
        print(f"[FAIL] 指标契约未生成：{metrics_path}", file=sys.stderr)
        return 1
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    review_metrics: dict[str, float] = {k: float(v) for k, v in payload["metrics"].items()}
    pytest_cov_available: bool = bool(payload.get("pytest_cov_available", False))

    # 3. 汇总 metrics（六项核心指标）
    metrics: dict[str, float] = {
        "module_count": review_metrics["module_count"],
        "coverage_percent": review_metrics["coverage_percent"],
        "avg_complexity": review_metrics["avg_complexity"],
        "duplicate_percent": review_metrics["duplicate_percent"],
        "static_warnings": review_metrics["static_warnings"],
        "coverage_test_passed": review_metrics["coverage_test_passed"],
        "review_pass": review_metrics["review_pass"],
        "paper_reading_task_count": float(len(PAPER_READING_TASKS)),
        "paper_reading_tasks_valid": float(paper_tasks_valid),
        "cpp_algorithm_milestone_count": float(len(CPP_ALGORITHM_ROUTE)),
        "cpp_algorithm_route_valid": float(cpp_route_valid),
    }

    # 4. 动态构造通过条件
    # pytest-cov 可用：要求 review_pass == 1 且 coverage_percent >= 50
    # pytest-cov 不可用：仅要求 review_pass == 1（review_pass 此时为「无语法错误」）
    # 说明：static_warnings（长行+未用导入）作为信息性指标写入报告，不作为硬门槛，
    #       因为部分文件（如 checkpoint.py）按项目约束禁止修改且天然含长行。
    if pytest_cov_available:
        pass_conditions = {
            "review_pass": {"operator": "==", "value": 1},
            "coverage_percent": {"operator": ">=", "value": 50},
        }
        gate_desc = "review_pass == 1 且 coverage_percent >= 50"
    else:
        pass_conditions = {
            "review_pass": {"operator": "==", "value": 1},
        }
        gate_desc = "review_pass == 1（pytest-cov 未安装，门槛降级为无语法错误）"
    pass_conditions.update(
        {
            "coverage_test_passed": {"operator": "==", "value": 1},
            "paper_reading_task_count": {"operator": ">=", "value": 3},
            "paper_reading_tasks_valid": {"operator": "==", "value": 1},
            "cpp_algorithm_milestone_count": {"operator": ">=", "value": 4},
            "cpp_algorithm_route_valid": {"operator": "==", "value": 1},
        }
    )

    # 5. 写结果契约
    result_path = output_root / "results" / "engineering_47.json"
    plot_path = output_root / "plots" / "engineering_47_code_review.png"

    # 生成代码评审指标可视化图表
    _write_review_plot(metrics, plot_path)

    write_experiment_result(
        result_path,
        chapter_id="47",
        seed=args.seed,
        config={
            "review_script": str(REVIEW_SCRIPT.relative_to(ROOT)),
            "report_path": str(report_path.relative_to(ROOT)),
            "pytest_cov_available": pytest_cov_available,
            "defense_material": "docs/design/defense_material.md",
            "interview_qa_bank": "docs/design/interview_qa_bank.md",
            "paper_reading_tasks": str(paper_tasks_path),
            "cpp_algorithm_route": str(cpp_route_path),
        },
        metrics=metrics,
        pass_conditions=pass_conditions,
        plots=[str(plot_path)],
        logs=[str(report_path)],
        root=source_root,
    )

    # 6. 写 portfolio 报告
    portfolio = output_root / "portfolio" / "47" / "engineering_47_report.md"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        "# 第 47 关代码评审、答辩与面试报告\n\n"
        "## 评审摘要\n\n"
        "| 指标 | 数值 |\n"
        "|---|---|\n"
        f"| 模块数 | {int(metrics['module_count'])} |\n"
        f"| 覆盖率 | {metrics['coverage_percent']:.1f}% |\n"
        f"| 平均最大嵌套深度 | {metrics['avg_complexity']:.2f} |\n"
        f"| 重复代码比例 | {metrics['duplicate_percent']:.2f}% |\n"
        f"| 静态告警数（未用导入 + 长行） | {int(metrics['static_warnings'])} |\n"
        f"| 语法错误数 | {int(review_metrics.get('syntax_errors', 0))} |\n"
        f"| 评审通过（review_pass） | {int(metrics['review_pass'])} |\n\n"
        "## 通过条件\n\n"
        f"- 门槛：`{gate_desc}`\n"
        f"- 结果契约 `passed` = 评审门槛全部满足\n\n"
        "## 答辩与面试材料\n\n"
        "- 答辩材料：`docs/design/defense_material.md`（设计动机/实验证据/局限性/改进方向）\n"
        "- 面试题库：`docs/design/interview_qa_bank.md`（47+ 题含参考答案）\n\n"
        "## 论文精读与 C++ 算法路线\n\n"
        f"- 论文精读任务：`{paper_tasks_path}`（{len(PAPER_READING_TASKS)} 篇）\n"
        f"- C++ 算法路线：`{cpp_route_path}`（{len(CPP_ALGORITHM_ROUTE)} 个里程碑）\n"
        f"- 定义校验：论文={paper_tasks_valid}，C++={cpp_route_valid}\n\n"
        "## 证据文件\n\n"
        f"- 代码评审报告：`outputs/reports/code_review_47.md`\n"
        f"- 指标契约：`outputs/reports/code_review_47_metrics.json`\n"
        f"- 结果契约：`{result_path}`\n",
        encoding="utf-8",
    )

    print(f"[OK] 第 47 关结果契约：{result_path}")
    print(f"[OK] portfolio：{portfolio}")
    print(f"[OK] 评审门槛：{gate_desc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
