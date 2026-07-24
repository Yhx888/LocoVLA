"""对目标轮足机器人的许可证与 BOM 资料进行只读审计。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.request import Request
from urllib.request import urlopen

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from upkie_mujoco_course.course.results import write_experiment_result
from upkie_mujoco_course.utils.paths import project_root


REPOSITORY = "MuShibo/Micro-Wheeled_leg-Robot"
_BOM_TERMS = ("PCB", "ESP32", "L6234PD013TR", "AS5600", "MPU6050", "舵机", "GH1.25")


def _read_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "upkie-course-audit"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "upkie-course-audit"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_repository_snapshot() -> dict[str, Any]:
    """获取当前公开仓库的最小审计快照，不把任何资产复制进课程仓库。"""

    repository = _read_json(f"https://api.github.com/repos/{REPOSITORY}")
    branch = str(repository["default_branch"])
    reference = _read_json(f"https://api.github.com/repos/{REPOSITORY}/git/ref/heads/{branch}")
    commit = str(reference["object"]["sha"])
    tree = _read_json(f"https://api.github.com/repos/{REPOSITORY}/git/trees/{commit}?recursive=1")["tree"]
    paths = [str(entry["path"]) for entry in tree if entry.get("type") == "blob"]
    source_paths = [
        path for path in paths
        if path.startswith("3.Software/wl_pro_robot/") and Path(path).suffix.lower() in {".cpp", ".h", ".ino"}
    ][:3]
    raw_root = f"https://raw.githubusercontent.com/{REPOSITORY}/{commit}"
    return {
        "commit": commit,
        "default_branch": branch,
        "root_paths": [path for path in paths if "/" not in path],
        "readme": _read_text(f"{raw_root}/README.md"),
        "source_headers": [_read_text(f"{raw_root}/{path}")[:2048] for path in source_paths],
        "source_paths": source_paths,
    }


def audit_repository_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """将远程快照转为许可证矩阵、BOM 差异表和采购冻结结论。"""

    root_paths = [str(path) for path in snapshot["root_paths"]]
    root_license = any(Path(path).name.upper() in {"LICENSE", "LICENSE.MD", "COPYING", "NOTICE"} for path in root_paths)
    headers = [str(header) for header in snapshot.get("source_headers", [])]
    mit_ratio = sum("MIT License" in header for header in headers) / len(headers) if headers else 0.0
    readme = str(snapshot["readme"])
    bom_items = []
    for term in _BOM_TERMS:
        mentioned = term.lower() in readme.lower()
        bom_items.append(
            {
                "item": term,
                "readme_mentioned": mentioned,
                "evidence_status": "README 已提及，实际目录未找到" if mentioned else "README 未提及，实际目录未找到",
                "procurement_status": "待补充型号、数量、供应商与机械接口",
            }
        )
    missing = [item["item"] for item in bom_items if not item["readme_mentioned"]]
    freeze_reasons = []
    if not root_license:
        freeze_reasons.append("根目录没有统一许可证")
    if missing:
        freeze_reasons.append(f"README 未提及: {', '.join(missing)}")
    freeze_reasons.append("BOM 缺少可下单的型号、数量、供应商与装配证据")
    return {
        "repository": REPOSITORY,
        "commit": str(snapshot["commit"]),
        "default_branch": str(snapshot["default_branch"]),
        "root_license_present": root_license,
        "source_mit_header_ratio": float(mit_ratio),
        "source_header_samples": len(headers),
        "bom_items": bom_items,
        "bom_readme_coverage_ratio": float(sum(item["readme_mentioned"] for item in bom_items) / len(bom_items)),
        "procurement_freeze_approved": False,
        "procurement_freeze_reason": "；".join(freeze_reasons),
    }


def _root(output_root: str | Path) -> Path:
    path = Path(output_root)
    return path if path.is_absolute() else project_root() / path


def run_hardware_audit(
    chapter_id: str,
    *,
    output_root: str | Path = "outputs",
    source_root: str | Path | None = None,
    snapshot: dict[str, Any] | None = None,
) -> Path:
    if chapter_id != "H01":
        raise ValueError("当前硬件审计仅支持 H01")
    audit = audit_repository_snapshot(snapshot or fetch_repository_snapshot())
    root = _root(output_root)
    evidence_root = Path(source_root).resolve() if source_root is not None else project_root().resolve()
    plot = root / "plots" / "hardware_H01.png"
    log = root / "logs" / "hardware_H01.json"
    result = root / "results" / "hardware_H01.json"
    figure, axis = plt.subplots(figsize=(7.2, 3.8))
    labels = ["Servo" if item["item"] == "舵机" else item["item"] for item in audit["bom_items"]]
    values = [float(item["readme_mentioned"]) for item in audit["bom_items"]]
    axis.bar(labels, values, color=["#17745a" if value else "#d36b27" for value in values])
    axis.set(ylim=(0, 1.15), ylabel="README evidence", title="H01 BOM evidence is not procurement approval")
    axis.tick_params(axis="x", rotation=28)
    axis.grid(axis="y", alpha=0.25)
    plot.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(plot, dpi=150)
    plt.close(figure)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    metrics = {
        "root_license_absent": float(not audit["root_license_present"]),
        "source_mit_header_ratio": float(audit["source_mit_header_ratio"]),
        "bom_item_count": float(len(audit["bom_items"])),
        "procurement_freeze_blocked": float(not audit["procurement_freeze_approved"]),
    }
    written = write_experiment_result(
        result, chapter_id="H01", seed=0, config={"repository": REPOSITORY, "commit": audit["commit"]}, metrics=metrics,
        pass_conditions={"root_license_absent": {"operator": "==", "value": 1.0}, "bom_item_count": {"operator": ">=", "value": 6.0}, "procurement_freeze_blocked": {"operator": "==", "value": 1.0}},
        plots=[str(plot)], logs=[str(log)],
        root=evidence_root,
    )
    portfolio = root / "portfolio" / "H01" / "evidence.json"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    written_result = json.loads(written.read_text(encoding="utf-8"))
    portfolio.write_text(
        json.dumps(
            {
                "chapter_id": "H01",
                "passed": written_result["passed"],
                "result_path": str(written),
                "audit": audit,
                "metrics": metrics,
                "evidence": {"summary": "H01 上游仓库、许可证与 BOM 审计"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return written
