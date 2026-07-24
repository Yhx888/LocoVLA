"""FastAPI 工厂、路由挂载、生产静态托管。"""

from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from upkie_mujoco_course.utils.paths import resolve_project_path
from upkie_mujoco_course.web.content import build_chapter_dto, build_course_summary
from upkie_mujoco_course.web.progress_store import ProgressStore
from upkie_mujoco_course.web.presets import get_chapter_presets, validate_command, validate_preset_args
from upkie_mujoco_course.web.runner import (
    TERMINAL_STATUSES,
    RunNotCancellableError,
    RunNotFoundError,
    TaskRunner,
    get_task_runner,
)
from upkie_mujoco_course.web.diagnostics import get_diagnostics
from upkie_mujoco_course.web.artifacts import resolve_artifact_path, get_artifact_mime_type
from upkie_mujoco_course.web.schemas import ProgressRecord

# ── 模块级结果缓存 ──
_results_cache: list[dict] | None = None
_cache_ts: float = 0.0
_CACHE_TTL: float = 300.0


def _get_cached_results() -> list[dict]:
    global _results_cache, _cache_ts
    now = time.time()
    if _results_cache is not None and now - _cache_ts < _CACHE_TTL:
        return _results_cache
    from upkie_mujoco_course.course.dashboard_data import load_experiment_results
    try:
        _results_cache = load_experiment_results(resolve_project_path("outputs"))
    except Exception:
        _results_cache = []
    _cache_ts = now
    return _results_cache


def _invalidate_results_cache() -> None:
    global _results_cache, _cache_ts
    _results_cache = None
    _cache_ts = 0.0


def create_app(
    *,
    task_runner: TaskRunner | None = None,
    progress_store: ProgressStore | None = None,
) -> FastAPI:
    runner = task_runner or get_task_runner()
    store = progress_store or ProgressStore()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runner.set_on_complete(_invalidate_results_cache)
        yield
        await runner.shutdown()

    app = FastAPI(title="Upkie 运动控制课程", version="0.3.0", lifespan=lifespan)

    app.state.task_runner = runner
    app.state.progress_store = store

    # ── 健康检查 ──
    @app.get("/api/health")
    async def health():
        return get_diagnostics()

    # ── 课程摘要 ──
    @app.get("/api/course")
    async def course_summary():
        progress = store._data
        results = _get_cached_results()
        return build_course_summary(progress, results)

    # ── 章节详情 ──
    @app.get("/api/chapters/{chapter_id}")
    async def chapter_detail(chapter_id: str):
        progress = store._data
        results = _get_cached_results()
        try:
            dto = build_chapter_dto(chapter_id, progress, results)
            dto.presets = get_chapter_presets(chapter_id)
            return dto.model_dump()
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ── 进度更新 ──
    @app.put("/api/progress/{chapter_id}")
    async def update_progress(chapter_id: str, record: ProgressRecord):
        store.update_chapter_progress(
            chapter_id,
            reading_percent=record.reading_percent,
            reading_complete=record.reading_complete,
            self_check_ids=record.self_check_ids,
        )
        return {"status": "ok"}

    # ── 运行任务 ──
    @app.post("/api/runs")
    async def create_run(body: dict):
        chapter_id = body.get("chapter_id")
        preset_id = body.get("preset_id")
        command = body.get("command")
        if not chapter_id:
            raise HTTPException(status_code=422, detail="缺少 chapter_id")
        if not preset_id and not command:
            raise HTTPException(status_code=422, detail="缺少 preset_id 或 command")

        try:
            if command:
                if not validate_command(command):
                    raise ValueError(f"命令未通过安全校验: {command}")
                commands = [command]
                preset_id = preset_id or "custom"
            else:
                commands = validate_preset_args(chapter_id, preset_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        try:
            record = await runner.start_run(chapter_id, preset_id, commands)
            return record.model_dump()
        except RuntimeError as e:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": str(e),
                    "active_run_id": runner.active_run_id,
                },
            )

    @app.get("/api/runs")
    async def list_runs(chapter_id: str | None = None):
        return runner.get_history(chapter_id)

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str):
        run = runner.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        events = runner.get_events_after(run_id, 0)
        run["last_event_sequence"] = events[-1]["sequence"] if events else 0
        return run

    @app.post("/api/runs/{run_id}/cancel")
    async def cancel_run(run_id: str):
        try:
            await runner.cancel_run(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except RunNotCancellableError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return {"status": "cancelled"}

    # ── WebSocket 事件流 ──
    @app.websocket("/api/runs/{run_id}/events")
    async def run_events(websocket: WebSocket, run_id: str, after: int = 0):
        await websocket.accept()
        if runner.get_run(run_id) is None:
            await websocket.close(code=4404, reason="任务不存在")
            return
        try:
            import asyncio
            while True:
                events = runner.get_events_after(run_id, after)
                if events:
                    for e in events:
                        await websocket.send_text(json.dumps(e, ensure_ascii=False))
                        after = e["sequence"]
                run = runner.get_run(run_id)
                if run is None or run["status"] in TERMINAL_STATUSES:
                    await websocket.close(code=1000)
                    return
                await asyncio.sleep(0.5)
        except WebSocketDisconnect:
            pass

    # ── 产物访问 ──
    @app.get("/api/artifacts/{rest_of_path:path}")
    async def serve_artifact(rest_of_path: str):
        file_path = resolve_artifact_path(rest_of_path)
        if file_path is None:
            raise HTTPException(status_code=404, detail="产物不存在或路径不安全")

        mime = get_artifact_mime_type(file_path.suffix)
        if mime is None:
            raise HTTPException(status_code=403, detail="不支持的文件类型")

        return FileResponse(str(file_path), media_type=mime)

    # ── 生产静态文件托管（所有 API 路由之后）──
    dist_dir = resolve_project_path("dashboard", "web", "dist")
    if dist_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

        @app.get("/")
        async def root():
            return FileResponse(str(dist_dir / "index.html"), media_type="text/html")

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            if full_path.startswith("api/") or full_path.startswith("ws/"):
                raise HTTPException(status_code=404)
            index_file = dist_dir / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file), media_type="text/html")
            raise HTTPException(status_code=404)

    return app


app = create_app()
