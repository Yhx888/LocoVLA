"""web 课程网站启动入口。"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import webbrowser
from pathlib import Path


def _frontend_fingerprint(web_dir: Path) -> str:
    digest = hashlib.sha256()
    roots = [web_dir / "src", web_dir / "public"]
    files = [
        web_dir / "index.html",
        web_dir / "package.json",
        web_dir / "package-lock.json",
        web_dir / "tsconfig.json",
        web_dir / "vite.config.ts",
    ]
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    for path in sorted(files):
        if not path.exists():
            continue
        digest.update(path.relative_to(web_dir).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _ensure_frontend_build(web_dir: Path) -> None:
    dist_dir = web_dir / "dist"
    # marker 必须放在 dist 目录之外：vite 构建时 emptyOutDir 默认为 True，
    # 会清空整个 dist，若 marker 在 dist 内则每次启动都会丢失指纹导致重复构建。
    marker = web_dir / ".source-fingerprint"
    fingerprint = _frontend_fingerprint(web_dir)
    built_fingerprint = marker.read_text(encoding="ascii").strip() if marker.exists() else ""
    if (dist_dir / "index.html").exists() and built_fingerprint == fingerprint:
        return

    print("\n[!] 前端源码已变化，正在构建...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(web_dir),
        shell=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print("[错误] 前端构建失败，请检查 npm/node 是否安装")
        print(result.stderr.decode("utf-8", errors="replace")[-1000:])
        sys.exit(1)
    marker.write_text(fingerprint, encoding="ascii")
    print("[OK] 前端构建完成")


def main():
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    print("Upkie 运动控制课程 · 本地网站")
    print(f"Python: {sys.version}")

    web_dir = Path(__file__).resolve().parents[1] / "dashboard" / "web"
    _ensure_frontend_build(web_dir)

    host = "127.0.0.1"
    port = 8765

    url = f"http://{host}:{port}"
    print(f"启动服务器: {url}")

    webbrowser.open(url)

    import uvicorn
    uvicorn.run(
        "upkie_mujoco_course.web.app:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
