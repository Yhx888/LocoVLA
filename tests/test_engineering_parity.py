"""测试工程对等（engineering.parity）数值一致性。

覆盖场景：
- parse_probe_output 解析 C++ 探针输出
- reference_control Python 参考控制器输出
- 数值对等性容差检查
"""
import numpy as np
import pytest
import runpy

from upkie_mujoco_course.engineering import lab as engineering_lab
from upkie_mujoco_course.engineering.parity import parse_probe_output
from upkie_mujoco_course.engineering.parity import reference_control
from upkie_mujoco_course.engineering.lab import _dependency_targets
from upkie_mujoco_course.course.checkpoint import _markdown_portfolio_is_substantive


def test_reference_control_matches_documented_gain_and_wheel_signs():
    state = np.array([[0.1, 0.2, -0.05, 0.4]])
    actual = reference_control(state, yaw=np.array([0.4]), limit=np.array([1.0]))

    assert np.allclose(actual, [[0.53, 0.13, -0.93]])


def test_reference_control_clips_each_wheel_in_actuator_coordinates():
    actual = reference_control(np.array([[0.0, 0.0, 1.0, 0.0]]), yaw=np.array([0.4]), limit=np.array([1.0]))

    assert np.allclose(actual, [[3.0, 1.0, -1.0]])


def test_parse_probe_output_requires_exact_numeric_shape():
    parsed = parse_probe_output("0.53 0.13 -0.93\n", expected_rows=1)

    assert np.allclose(parsed, [[0.53, 0.13, -0.93]])
    with pytest.raises(ValueError):
        parse_probe_output("0.53 0.13\n", expected_rows=1)
    with pytest.raises(ValueError):
        parse_probe_output("0.53 0.13 -0.93\n0 0 0\n", expected_rows=1)


def test_dependency_graph_parser_reads_cmake_target_labels(tmp_path):
    graph = tmp_path / "targets.dot"
    graph.write_text('node0 [ label = "control_test" ];\nnode1 [ label = "upkie_course_control" ];\nnode0 -> node1;\n', encoding="utf-8")

    assert _dependency_targets(graph) == ["control_test", "upkie_course_control"]


def test_zig_windows_cmake_args_create_archiver_wrappers(tmp_path):
    helper = getattr(engineering_lab, "_zig_windows_cmake_args", None)
    assert callable(helper), "缺少 Windows Zig 工具链参数生成器"

    zig = tmp_path / "zig.exe"
    ninja = tmp_path / "ninja.exe"
    args = helper(tmp_path / "build", zig=zig, ninja=ninja)

    assert args[:2] == ["-G", "Ninja"]
    assert f"-DCMAKE_MAKE_PROGRAM={ninja}" in args
    assert f"-DCMAKE_CXX_COMPILER={zig}" in args
    assert "-DCMAKE_CXX_COMPILER_ARG1=c++" in args
    assert (tmp_path / "build" / "zig-ar.cmd").read_text(encoding="ascii") == f'@"{zig}" ar %*\n'
    assert (tmp_path / "build" / "zig-ranlib.cmd").read_text(encoding="ascii") == f'@"{zig}" ranlib %*\n'


def test_engineering_portfolio_generators_produce_substantive_markdown():
    report_38_builder = getattr(engineering_lab, "_numerical_parity_report_markdown", None)
    report_39_builder = getattr(engineering_lab, "_build_reproducibility_report_markdown", None)
    assert callable(report_38_builder)
    assert callable(report_39_builder)

    report_38 = report_38_builder(seed=38, sample_count=1000, maximum_error=0.0)
    report_39 = report_39_builder(
        target_count=3,
        failure_excerpt="missing public header",
        graph_path="reports/engineering_39_dependencies.dot",
    )

    assert _markdown_portfolio_is_substantive(report_38)
    assert _markdown_portfolio_is_substantive(report_39)
    assert "CMake 构建" in report_39
    assert "CTest" in report_39


def test_engineering_43_portfolio_generator_produces_substantive_markdown():
    namespace = runpy.run_path("scripts/run_engineering_lab_43.py", run_name="engineering_43_test")
    report = namespace["_build_portfolio_report"](
        {
            "faults": [
                {
                    "fault_name": "imu_dropout",
                    "start_state": "ARMED",
                    "final_state": "FAULT",
                    "safe": True,
                    "detection_latency_ms": 1.0,
                    "brake_latency_ms": 2.0,
                }
            ],
            "fault_count": 1,
            "detected_count": 1,
            "all_faults_safe": True,
            "mean_detection_latency_ms": 1.0,
            "mean_brake_latency_ms": 2.0,
        },
        13,
        0,
        "results/engineering_43.json",
        "results/engineering_43_fault_injection.json",
    )

    assert _markdown_portfolio_is_substantive(report)
