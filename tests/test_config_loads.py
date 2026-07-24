"""测试配置文件加载接口。

覆盖场景：
- 机器人配置（robot/upkie.json）能被加载
- 通用 JSON 配置加载工具正常工作
- 项目根路径解析正确
"""
from pathlib import Path
import re
import tomllib

from upkie_mujoco_course.model.robot_spec import load_robot_spec
from upkie_mujoco_course.utils.config import load_json_config
from upkie_mujoco_course.utils.paths import project_root


def test_robot_config_loads_and_paths_exist():
    spec = load_robot_spec()
    assert spec.name == "upkie"
    assert project_root().exists()
    assert spec.model_path.exists()
    assert spec.model_format == "urdf"
    assert spec.floating_base is True
    assert spec.root_joint_name == "root"
    assert spec.package_dir.exists()
    assert spec.frame_skip > 0
    assert "left_wheel" in spec.wheel_joints
    assert spec.wheel_directions == (1.0, -1.0)
    assert [item.kind for item in spec.torque_actuators] == ["torque", "torque"]


def test_robot_config_declares_v2_physical_contract_and_units():
    config = load_json_config("configs/robot/upkie.json")
    assert config["schema_version"] == "2.0"
    assert config["state_dimensions"] == {"nq": 13, "nv": 12, "nu": 6}
    assert config["actuator_semantics"]["wheel"]["command"] == "torque"
    assert config["actuator_semantics"]["wheel"]["unit"] == "N*m"
    assert config["sensor_contract"]["fields"]


def test_python_311_lock_contains_direct_and_transitive_dependencies():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    lock = Path("requirements.lock").read_text(encoding="utf-8")
    pinned = {
        match.group(1).lower().replace("_", "-")
        for match in re.finditer(r"^([A-Za-z0-9_.-]+)==[^\s]+$", lock, re.MULTILINE)
    }

    assert pyproject["project"]["requires-python"] == ">=3.11,<3.12"
    assert "--python-version 3.11" in lock
    assert len(pinned) >= 50
    for name in ("mujoco", "gymnasium", "numpy", "torch", "streamlit", "plotly", "pytest"):
        assert name in pinned
    for transitive in ("pandas", "requests", "protobuf", "pyarrow", "jinja2"):
        assert transitive in pinned


def test_web_runtime_dependencies_are_declared_directly():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    requirements = Path("requirements.txt").read_text(encoding="utf-8").splitlines()
    lock = Path("requirements.lock").read_text(encoding="utf-8")
    project_dependencies = pyproject["project"]["dependencies"]

    assert any(item.startswith("fastapi") for item in project_dependencies)
    assert any(item.startswith("uvicorn[standard]") for item in project_dependencies)
    assert any(item.startswith("fastapi") for item in requirements)
    assert any(item.startswith("uvicorn[standard]") for item in requirements)
    for name in ("fastapi", "uvicorn", "websockets"):
        assert re.search(rf"^{name}==[^\s]+$", lock, re.MULTILINE)


def test_pytest_asyncio_plugin_is_declared_for_configured_asyncio_mode():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    lock = Path("requirements.lock").read_text(encoding="utf-8")

    assert any(
        item.startswith("pytest-asyncio")
        for item in pyproject["project"]["optional-dependencies"]["dev"]
    )
    assert re.search(r"^pytest-asyncio==[^\s]+$", lock, re.MULTILINE)


def test_http_test_client_dependency_is_declared():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    lock = Path("requirements.lock").read_text(encoding="utf-8")

    assert any(
        item.startswith("httpx2")
        for item in pyproject["project"]["optional-dependencies"]["dev"]
    )
    assert re.search(r"^httpx2==[^\s]+$", lock, re.MULTILINE)
