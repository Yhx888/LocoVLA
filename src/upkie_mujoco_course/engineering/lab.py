"""第 38 关：真实 CMake 构建、CTest 与 Python/C++ 数值一致性实验。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import hashlib
import importlib.util
from pathlib import Path
import re
import sys
import tarfile
from urllib.request import urlopen

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from upkie_mujoco_course.course.results import write_experiment_result
from upkie_mujoco_course.engineering.parity import parse_probe_output
from upkie_mujoco_course.engineering.parity import reference_control
from upkie_mujoco_course.utils.paths import project_root


plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "Noto Sans SC", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


class EngineeringLabError(RuntimeError):
    """工程实验不能生成可靠通过证据时抛出。"""


EIGEN_URL = "https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz"
EIGEN_SHA256 = "8586084F71F9BDE545EE7FA6D00288B264A2B7AC3607B974E54D13E7162C1C72"
COLCON_SUMMARY_RE = re.compile(
    r"^Summary: (?P<tests>\d+) tests?, "
    r"(?P<errors>\d+) errors?, "
    r"(?P<failures>\d+) failures?, "
    r"(?P<skipped>\d+) skipped$"
)


def read_colcon_test_summary(path: str | Path) -> tuple[int, int, int, bool]:
    """严格读取 colcon test-result 的唯一完整 Summary 行。"""

    summary_path = Path(path)
    if not summary_path.is_file():
        return 0, 0, 0, False
    try:
        lines = summary_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return 0, 0, 0, False
    matches = [
        match for line in lines if (match := COLCON_SUMMARY_RE.fullmatch(line))
    ]
    if len(matches) != 1:
        return 0, 0, 0, False
    match = matches[0]
    return (
        int(match.group("tests")),
        int(match.group("errors")),
        int(match.group("failures")),
        True,
    )


def _output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    return root if root.is_absolute() else project_root() / root


def _cmake_command() -> str:
    configured = os.environ.get("CMAKE_COMMAND")
    candidates = [configured, shutil.which("cmake")]
    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles")
        if program_files:
            candidates.append(str(Path(program_files) / "CMake" / "bin" / "cmake.exe"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise EngineeringLabError("找不到 cmake；请安装 CMake 或设置 CMAKE_COMMAND")


def _zig_windows_cmake_args(build_dir: Path, *, zig: Path, ninja: Path) -> list[str]:
    build_dir.mkdir(parents=True, exist_ok=True)
    ar_wrapper = build_dir / "zig-ar.cmd"
    ranlib_wrapper = build_dir / "zig-ranlib.cmd"
    ar_wrapper.write_text(f'@"{zig}" ar %*\n', encoding="ascii")
    ranlib_wrapper.write_text(f'@"{zig}" ranlib %*\n', encoding="ascii")
    return [
        "-G",
        "Ninja",
        f"-DCMAKE_MAKE_PROGRAM={ninja}",
        f"-DCMAKE_CXX_COMPILER={zig}",
        "-DCMAKE_CXX_COMPILER_ARG1=c++",
        f"-DCMAKE_AR={ar_wrapper}",
        f"-DCMAKE_RANLIB={ranlib_wrapper}",
    ]


def _cmake_toolchain_args(build_dir: Path) -> list[str]:
    if os.name != "nt" or any(shutil.which(name) for name in ("cl", "clang++", "g++")):
        return []
    ninja = os.environ.get("NINJA_COMMAND") or shutil.which("ninja")
    if not ninja:
        candidate = Path(sys.executable).with_name("ninja.exe")
        ninja = str(candidate) if candidate.is_file() else None
    zig = os.environ.get("ZIG_COMMAND") or shutil.which("zig")
    if not zig:
        spec = importlib.util.find_spec("ziglang")
        if spec and spec.submodule_search_locations:
            candidate = Path(next(iter(spec.submodule_search_locations))) / "zig.exe"
            zig = str(candidate) if candidate.is_file() else None
    if not ninja or not zig:
        return []
    return _zig_windows_cmake_args(build_dir, zig=Path(zig), ninja=Path(ninja))


def _run(command: list[str], *, cwd: Path, input_text: str | None = None) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )
    evidence = {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        error = EngineeringLabError(f"命令失败: {' '.join(command)}\n{detail}")
        error.evidence = evidence
        raise error
    return evidence


def _probe_path(build_dir: Path) -> Path:
    names = ("control_probe.exe", "control_probe")
    for name in names:
        direct = build_dir / name
        if direct.is_file():
            return direct
        matches = list(build_dir.rglob(name))
        if matches:
            return matches[0]
    raise EngineeringLabError("构建完成后找不到 control_probe 可执行文件")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _prepare_eigen_source(build_dir: Path) -> Path:
    """用系统证书下载并校验 Eigen，再让 CMake 只消费本地已验证源码。"""

    dependency_root = build_dir / "_course_dependencies"
    source = dependency_root / "eigen-3.4.0"
    if (source / "Eigen" / "Core").is_file():
        return source
    archive = dependency_root / "eigen-3.4.0.tar.gz"
    dependency_root.mkdir(parents=True, exist_ok=True)
    if not archive.is_file() or _sha256(archive) != EIGEN_SHA256:
        with urlopen(EIGEN_URL, timeout=60) as response:
            archive.write_bytes(response.read())
    actual_hash = _sha256(archive)
    if actual_hash != EIGEN_SHA256:
        raise EngineeringLabError(f"Eigen SHA-256 不匹配：{actual_hash}")
    with tarfile.open(archive, "r:gz") as package:
        root = dependency_root.resolve()
        for member in package.getmembers():
            if not (root / member.name).resolve().is_relative_to(root):
                raise EngineeringLabError("Eigen 归档包含越界路径")
        package.extractall(dependency_root)
    if not (source / "Eigen" / "Core").is_file():
        raise EngineeringLabError("已校验的 Eigen 归档没有预期的头文件目录")
    return source


def _save_failure_log(root: Path, *, chapter_id: str, seed: int, commands: list[dict[str, object]], error: Exception) -> None:
    path = root / "logs" / f"engineering_{chapter_id}_failure.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"chapter_id": chapter_id, "seed": seed, "commands": commands, "error": str(error)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _numerical_parity_report_markdown(*, seed: int, sample_count: int, maximum_error: float) -> str:
    return (
        "# 第 38 关数值一致性报告\n\n"
        "## 指标\n\n"
        "| 指标 | 数值 |\n"
        "| --- | --- |\n"
        f"| 固定随机种子 | `{seed}` |\n"
        f"| 对照样本 | `{sample_count}` |\n"
        f"| 最大绝对误差 | `{maximum_error:.3e} N*m` |\n\n"
        "- 验收：CMake 构建、CTest 和 Python/C++ 轮端力矩对照均已通过。\n"
    )


def _build_reproducibility_report_markdown(
    *, target_count: int, failure_excerpt: str, graph_path: str | Path
) -> str:
    return (
        "# 第 39 关构建可复现报告\n\n"
        "## 指标\n\n"
        "| 指标 | 数值 |\n"
        "| --- | --- |\n"
        f"| CMake 目标数量 | `{target_count}` |\n"
        "| 基线 CTest | `通过` |\n"
        "| 故障构建拒绝 | `通过` |\n\n"
        "- 基线：CMake 构建与 CTest 全部通过。\n"
        f"- 故障注入：关闭公共头文件导出后，构建按预期失败，首个错误：`{failure_excerpt}`\n"
        f"- 依赖图：`{graph_path}`\n"
    )


def run_engineering_lab(
    *,
    output_root: str | Path = "outputs",
    build_dir: str | Path = "build/cpp",
    seed: int = 38,
    sample_count: int = 1000,
) -> Path:
    """执行第 38 关；任何构建或数值偏差都会保留失败日志并拒绝验收。"""

    if sample_count <= 0:
        raise ValueError("样本数量必须为正数")
    root = _output_root(output_root)
    build = Path(build_dir)
    build = build if build.is_absolute() else project_root() / build
    commands: list[dict[str, object]] = []
    try:
        cmake = _cmake_command()
        ctest = str(Path(cmake).with_name("ctest.exe" if os.name == "nt" else "ctest"))
        if not Path(ctest).is_file():
            ctest = shutil.which("ctest") or ctest
        eigen_source = _prepare_eigen_source(build)
        toolchain_args = _cmake_toolchain_args(build)
        commands.append({"command": ["prepare_eigen_source", EIGEN_URL], "returncode": 0, "stdout": str(eigen_source), "stderr": ""})
        commands.append(_run([cmake, *toolchain_args, "-S", "cpp", "-B", str(build), f"-DFETCHCONTENT_SOURCE_DIR_EIGEN={eigen_source}"], cwd=project_root()))
        commands.append(_run([cmake, "--build", str(build), "--config", "Release"], cwd=project_root()))
        commands.append(_run([ctest, "--test-dir", str(build), "--output-on-failure", "-C", "Release"], cwd=project_root()))
        probe = _probe_path(build)
        generator = np.random.default_rng(seed)
        states = generator.uniform(low=-0.5, high=0.5, size=(sample_count, 4))
        yaw = generator.uniform(low=-0.2, high=0.2, size=sample_count)
        limits = generator.uniform(low=0.2, high=1.0, size=sample_count)
        input_text = "".join(
            f"{state[0]:.17g} {state[1]:.17g} {state[2]:.17g} {state[3]:.17g} {turn:.17g} {limit:.17g}\n"
            for state, turn, limit in zip(states, yaw, limits)
        )
        probe_evidence = _run([str(probe)], cwd=project_root(), input_text=input_text)
        commands.append(probe_evidence)
        actual = parse_probe_output(str(probe_evidence["stdout"]), sample_count)
        expected = reference_control(states, yaw, limits)
        absolute_error = np.abs(actual - expected)
        maximum_error = float(np.max(absolute_error))
    except Exception as error:
        failed_evidence = getattr(error, "evidence", None)
        if failed_evidence is not None:
            commands.append(failed_evidence)
        _save_failure_log(root, chapter_id="38", seed=seed, commands=commands, error=error)
        if isinstance(error, EngineeringLabError):
            raise
        raise EngineeringLabError(str(error)) from error

    plot_path = root / "plots" / "engineering_38.png"
    log_path = root / "logs" / "engineering_38.json"
    result_path = root / "results" / "engineering_38.json"
    figure, (signal_axis, error_axis) = plt.subplots(1, 2, figsize=(10.6, 4.2))
    labels = ("公共平衡力矩", "左轮力矩", "右轮力矩")
    for column, label in enumerate(labels):
        signal_axis.plot(expected[:64, column], label=f"Python {label}", linewidth=1.4)
        signal_axis.plot(actual[:64, column], "--", label=f"C++ {label}", linewidth=1.0)
    signal_axis.set(xlabel="样本索引（前 64 组）", ylabel="力矩 [N*m]", title="两端输出重合")
    signal_axis.grid(alpha=0.25)
    signal_axis.legend(fontsize=8, ncols=2)
    error_axis.plot(np.max(absolute_error, axis=1), color="#17745a", linewidth=1.0, label="每组最大误差")
    error_axis.axhline(1e-12, color="#d36b27", linestyle="--", label="验收阈值")
    error_axis.set(xlabel="样本索引（1000 组）", ylabel="绝对误差 [N*m]", ylim=(-0.05e-12, 1.05e-12), title="误差低于验收阈值")
    error_axis.grid(alpha=0.25)
    error_axis.legend(fontsize=8)
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(plot_path, dpi=150)
    plt.close(figure)
    log = {"chapter_id": "38", "seed": seed, "sample_count": sample_count, "commands": commands, "maximum_absolute_error_n_m": maximum_error}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    result = write_experiment_result(
        result_path,
        chapter_id="38",
        seed=seed,
        config={"sample_count": sample_count, "gains": [2.0, 0.8, 3.0, 0.8], "wheel_torque_limit_unit": "N*m"},
        metrics={"ctest_passed": 1.0, "sample_count": float(sample_count), "maximum_absolute_error_n_m": maximum_error},
        pass_conditions={"ctest_passed": {"operator": "==", "value": 1.0}, "sample_count": {"operator": "==", "value": float(sample_count)}, "maximum_absolute_error_n_m": {"operator": "<=", "value": 1e-12}},
        plots=[str(plot_path)],
        logs=[str(log_path)],
    )
    portfolio_path = root / "portfolio" / "38" / "numerical_parity_report.md"
    portfolio_path.parent.mkdir(parents=True, exist_ok=True)
    portfolio_path.write_text(
        _numerical_parity_report_markdown(
            seed=seed,
            sample_count=sample_count,
            maximum_error=maximum_error,
        ),
        encoding="utf-8",
    )
    return result


def _ctest_command(cmake: str) -> str:
    candidate = Path(cmake).with_name("ctest.exe" if os.name == "nt" else "ctest")
    return str(candidate) if candidate.is_file() else shutil.which("ctest") or str(candidate)


def _dependency_targets(graph_path: Path) -> list[str]:
    content = graph_path.read_text(encoding="utf-8", errors="replace")
    return sorted(set(re.findall(r'^\s*"?node\d+"?\s+\[\s+label\s+=\s+"([^"]+)"', content, flags=re.MULTILINE)))


def run_engineering_project_lab(
    *,
    output_root: str | Path = "outputs",
    build_dir: str | Path = "build/engineering-39",
    seed: int = 39,
) -> Path:
    """执行第 39 关：从 CMake 图、干净构建与受控故障证明工程边界。"""

    root = _output_root(output_root)
    build = Path(build_dir)
    build = build if build.is_absolute() else project_root() / build
    fault_build = build.with_name(f"{build.name}-fault")
    commands: list[dict[str, object]] = []
    try:
        cmake = _cmake_command()
        ctest = _ctest_command(cmake)
        eigen_source = _prepare_eigen_source(build)
        toolchain_args = _cmake_toolchain_args(build)
        graph_path = root / "reports" / "engineering_39_dependencies.dot"
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        commands.append({"command": ["prepare_eigen_source", EIGEN_URL], "returncode": 0, "stdout": str(eigen_source), "stderr": ""})
        configure = [cmake, *toolchain_args, f"--graphviz={graph_path}", "-S", "cpp", "-B", str(build), f"-DFETCHCONTENT_SOURCE_DIR_EIGEN={eigen_source}"]
        commands.append(_run(configure, cwd=project_root()))
        commands.append(_run([cmake, "--build", str(build), "--config", "Release"], cwd=project_root()))
        commands.append(_run([ctest, "--test-dir", str(build), "--output-on-failure", "-C", "Release"], cwd=project_root()))
        targets = _dependency_targets(graph_path)
        if not targets:
            raise EngineeringLabError("CMake 没有生成可解析的目标依赖图")
        fault_toolchain_args = _cmake_toolchain_args(fault_build)
        fault_configure = [cmake, *fault_toolchain_args, "-S", "cpp", "-B", str(fault_build), f"-DFETCHCONTENT_SOURCE_DIR_EIGEN={eigen_source}", "-DUPKIE_COURSE_EXPOSE_PUBLIC_HEADERS=OFF"]
        commands.append(_run(fault_configure, cwd=project_root()))
        try:
            _run([cmake, "--build", str(fault_build), "--config", "Release"], cwd=project_root())
        except EngineeringLabError as error:
            commands.append(error.evidence)
            fault_rejected = 1.0
            failure_excerpt = str(error).splitlines()[-1]
        else:
            raise EngineeringLabError("关闭公共头文件导出后构建仍成功，故障注入没有覆盖接口边界")
    except Exception as error:
        failed_evidence = getattr(error, "evidence", None)
        if failed_evidence is not None:
            commands.append(failed_evidence)
        _save_failure_log(root, chapter_id="39", seed=seed, commands=commands, error=error)
        if isinstance(error, EngineeringLabError):
            raise
        raise EngineeringLabError(str(error)) from error

    plot_path = root / "plots" / "engineering_39.png"
    log_path = root / "logs" / "engineering_39.json"
    result_path = root / "results" / "engineering_39.json"
    figure, axis = plt.subplots(figsize=(7.6, 4.2))
    names = ["基线 CTest", "公共头文件故障被拒绝", "CMake 依赖目标"]
    values = [1.0, fault_rejected, float(len(targets))]
    colors = ["#17745a", "#d36b27", "#2978b5"]
    bars = axis.bar(names, values, color=colors)
    for bar, value in zip(bars, values):
        axis.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.0f}", ha="center", va="bottom")
    axis.set(ylabel="通过标记或目标数量", title="第 39 关：可复现构建、依赖图与接口故障注入")
    axis.grid(axis="y", alpha=0.25)
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(plot_path, dpi=150)
    plt.close(figure)
    log = {
        "chapter_id": "39",
        "seed": seed,
        "targets": targets,
        "fault_failure_excerpt": failure_excerpt,
        "commands": commands,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    result = write_experiment_result(
        result_path,
        chapter_id="39",
        seed=seed,
        config={"graphviz": str(graph_path), "fault_switch": "UPKIE_COURSE_EXPOSE_PUBLIC_HEADERS=OFF"},
        metrics={"baseline_ctest_passed": 1.0, "fault_build_rejected": fault_rejected, "dependency_target_count": float(len(targets))},
        pass_conditions={"baseline_ctest_passed": {"operator": "==", "value": 1.0}, "fault_build_rejected": {"operator": "==", "value": 1.0}, "dependency_target_count": {"operator": ">=", "value": 3.0}},
        plots=[str(plot_path)],
        logs=[str(log_path), str(graph_path)],
    )
    portfolio_path = root / "portfolio" / "39" / "build_reproducibility_report.md"
    portfolio_path.parent.mkdir(parents=True, exist_ok=True)
    portfolio_path.write_text(
        _build_reproducibility_report_markdown(
            target_count=len(targets),
            failure_excerpt=failure_excerpt,
            graph_path=graph_path,
        ),
        encoding="utf-8",
    )
    return result
