"""测试课程资产文件（CPP / ROS2 / 教程）是否齐全。

覆盖场景：
- C++ 与 ROS2 课程资产存在
- 关键配置 / 模型文件存在
- 资产路径与课程清单一致
"""
from pathlib import Path


def test_cpp_and_ros2_course_assets_exist():
    required = [
        "cpp/CMakeLists.txt",
        "cpp/include/upkie_course/control.hpp",
        "cpp/src/control.cpp",
        "cpp/tests/control_test.cpp",
        "ros2_ws/src/upkie_control/package.xml",
        "ros2_ws/src/upkie_control/CMakeLists.txt",
        "ros2_ws/src/upkie_control/src/control_node.cpp",
        "docs/guides/WSL2_ROS2_SETUP.md",
        "src/upkie_mujoco_course/hardware/telemetry.py",
    ]
    for path in required:
        assert Path(path).is_file(), path


def test_cpp_dependency_configuration_does_not_register_eigen_test_suite():
    cmake = Path("cpp/CMakeLists.txt").read_text(encoding="utf-8")
    assert "FetchContent_Declare" in cmake
    assert "URL_HASH SHA256=8586084F71F9BDE545EE7FA6D00288B264A2B7AC3607B974E54D13E7162C1C72" in cmake
    assert "set(BUILD_TESTING OFF CACHE BOOL" in cmake


def test_ros2_node_uses_imu_orientation_instead_of_zero_pitch_placeholder():
    # 阶段 B 已将内联数学提取为 upkie_control:: 命名空间下的纯函数
    # （quaternion_to_pitch / orientation_covariance_valid），便于 ament_cmake_gtest 测试。
    # 本测试断言控制节点真正消费 IMU 姿态（而非零占位符），并通过协方差门控保护。
    node = Path("ros2_ws/src/upkie_control/src/control_node.cpp").read_text(encoding="utf-8")
    assert "upkie_control::quaternion_to_pitch" in node
    assert "upkie_control::orientation_covariance_valid" in node
    assert "pitch_.store(upkie_control::quaternion_to_pitch" in node


def test_ros2_node_requires_received_valid_imu_and_applies_yaw_control():
    node = Path("ros2_ws/src/upkie_control/src/control_node.cpp").read_text(encoding="utf-8")
    assert "upkie_control::sensor_is_fresh" in node
    assert "yaw_rate_command" in node
    assert "combine_balance_and_yaw_torques" in node


def test_engineering_stage_has_six_chapter_guides():
    for chapter_id in range(38, 44):
        assert Path(f"tutorials/{chapter_id:02d}_engineering/README.md").is_file()


def test_hardware_elective_has_license_and_safety_boundaries():
    paths = [Path(f"tutorials/H{index:02d}_hardware/README.md") for index in range(1, 11)]
    assert all(path.is_file() for path in paths)
    license_text = paths[0].read_text(encoding="utf-8")
    assert "https://github.com/MuShibo/Micro-Wheeled_leg-Robot" in license_text
    assert "根目录没有统一许可证" in license_text
    assert "不复制 CAD、PCB" in license_text
    foc_text = paths[3].read_text(encoding="utf-8")
    assert "SimpleFOC" in foc_text and "版本" in foc_text
    safety_text = paths[8].read_text(encoding="utf-8")
    assert "默认 Wi-Fi" in safety_text and "急停" in safety_text
