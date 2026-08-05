"""环境诊断：Python 版本、核心依赖、MuJoCo 和外部工具。"""

from __future__ import annotations

import sys
import importlib.metadata

from upkie_mujoco_course.utils.paths import resolve_project_path


def get_python_info() -> dict:
    return {
        "version": sys.version,
        "executable": sys.executable,
        "compatible": sys.version_info[:2] == (3, 11),
        "recommendation": (
            None
            if sys.version_info[:2] == (3, 11)
            else "建议使用 Python 3.11，当前版本可能导致依赖兼容问题。"
        ),
    }


def get_dependency_info() -> dict:
    deps = {
        "mujoco": "mujoco",
        "numpy": "numpy",
        "scipy": "scipy",
        "gymnasium": "gymnasium",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic",
    }
    info = {}
    for key, pkg in deps.items():
        try:
            info[key] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            info[key] = None
    return info


def get_mujoco_info() -> dict:
    try:
        import mujoco
        return {
            "version": mujoco.__version__,
            "available": True,
        }
    except ImportError:
        return {"version": None, "available": False}


def get_outputs_info() -> dict:
    outputs_dir = resolve_project_path("outputs")
    return {
        "exists": outputs_dir.exists(),
        "path": str(outputs_dir),
    }


def get_diagnostics() -> dict:
    python = get_python_info()
    dependencies = get_dependency_info()
    mujoco = get_mujoco_info()
    ready = bool(
        python["compatible"]
        and mujoco["available"]
        and all(version is not None for version in dependencies.values())
    )
    return {
        "status": "ready" if ready else "degraded",
        "python": python,
        "dependencies": dependencies,
        "mujoco": mujoco,
        "outputs": get_outputs_info(),
    }
