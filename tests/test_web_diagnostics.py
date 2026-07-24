"""web diagnostics 测试。"""

from upkie_mujoco_course.web.diagnostics import (
    get_python_info,
    get_dependency_info,
    get_mujoco_info,
    get_diagnostics,
)


def test_python_info_has_keys():
    info = get_python_info()
    assert "version" in info
    assert "executable" in info
    assert "compatible" in info
    assert isinstance(info["compatible"], bool)


def test_dependency_info_keys():
    info = get_dependency_info()
    for key in ["mujoco", "numpy", "fastapi", "uvicorn"]:
        assert key in info


def test_mujoco_info():
    info = get_mujoco_info()
    assert "available" in info
    assert isinstance(info["available"], bool)


def test_full_diagnostics():
    diag = get_diagnostics()
    assert "python" in diag
    assert "dependencies" in diag
    assert "mujoco" in diag
    assert "outputs" in diag
