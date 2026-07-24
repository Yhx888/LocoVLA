"""持久化单任务运行器、日志事件、取消与恢复。"""

from __future__ import annotations

import asyncio
import ctypes
import os
import shlex
import signal
import sqlite3
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

from upkie_mujoco_course.utils.paths import resolve_project_path
from upkie_mujoco_course.web.schemas import RunRecord


TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "interrupted"}


class RunNotFoundError(LookupError):
    """任务 ID 不存在。"""


class RunNotCancellableError(RuntimeError):
    """任务存在，但当前不能取消。"""


class ActiveRunConflictError(RuntimeError):
    """SQLite 中已经存在活动任务。"""

    def __init__(self, run_id: str | None):
        self.run_id = run_id
        suffix = f": {run_id}" if run_id else ""
        super().__init__(f"已有任务在运行中{suffix}")


def _process_is_alive(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)
        ]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        process_query_limited_information = 0x1000
        still_active = 259
        handle = kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(
                handle, ctypes.byref(exit_code)
            ):
                return False
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _terminate_windows_process_tree(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


class RunStore:
    """用 SQLite 保存任务和按任务递增的事件序列。"""

    def __init__(self, db_path: str | Path):
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()
        self._mark_interrupted_runs()
        self._create_active_index()

    def _create_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    chapter_id TEXT NOT NULL,
                    preset_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL DEFAULT '',
                    exit_code INTEGER,
                    error_category TEXT
                );
                CREATE TABLE IF NOT EXISTS run_events (
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    stream TEXT NOT NULL,
                    text TEXT NOT NULL,
                    status TEXT,
                    PRIMARY KEY (run_id, sequence),
                    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_runs_created_at
                    ON runs(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_runs_chapter_created
                    ON runs(chapter_id, created_at DESC);
                """
            )
            columns = {
                str(row["name"])
                for row in self._conn.execute("PRAGMA table_info(runs)").fetchall()
            }
            if "owner_pid" not in columns:
                self._conn.execute("ALTER TABLE runs ADD COLUMN owner_pid INTEGER")

    def _create_active_index(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_runs_single_active
                ON runs ((1))
                WHERE status IN ('queued', 'running')
                """
            )

    def _mark_interrupted_runs(self) -> None:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, owner_pid FROM runs
                WHERE status IN ('queued', 'running')
                """
            ).fetchall()
        for row in rows:
            if _process_is_alive(row["owner_pid"]):
                continue
            self.finalize_run(
                str(row["id"]),
                "interrupted",
                error_category="server_restarted",
                message="服务重启，任务已中断",
            )

    def create_run(self, run: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO runs (
                    id, chapter_id, preset_id, status, created_at,
                    finished_at, exit_code, error_category, owner_pid
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run["id"],
                    run["chapter_id"],
                    run["preset_id"],
                    run["status"],
                    run["created_at"],
                    run["finished_at"],
                    run["exit_code"],
                    run["error_category"],
                    run.get("owner_pid"),
                ),
            )

    def create_active_run(self, run: dict) -> None:
        try:
            with self._lock, self._conn:
                self._conn.execute(
                    """
                    INSERT INTO runs (
                        id, chapter_id, preset_id, status, created_at,
                        finished_at, exit_code, error_category, owner_pid
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run["id"],
                        run["chapter_id"],
                        run["preset_id"],
                        run["status"],
                        run["created_at"],
                        run["finished_at"],
                        run["exit_code"],
                        run["error_category"],
                        run["owner_pid"],
                    ),
                )
                self._add_event_locked(
                    run["id"], "status", "任务已提交", status="queued"
                )
        except sqlite3.IntegrityError as exc:
            active_run_id = self.get_active_run_id()
            if active_run_id is None:
                raise
            raise ActiveRunConflictError(active_run_id) from exc

    def update_run(self, run_id: str, **fields) -> None:
        if not fields:
            return
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = [*fields.values(), run_id]
        with self._lock, self._conn:
            self._conn.execute(
                f"UPDATE runs SET {assignments} WHERE id = ?", values
            )

    def get_run(self, run_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_active_run_id(self) -> str | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id FROM runs
                WHERE status IN ('queued', 'running')
                ORDER BY created_at DESC LIMIT 1
                """
            ).fetchone()
        return str(row["id"]) if row else None

    def list_runs(self, chapter_id: str | None = None) -> list[dict]:
        with self._lock:
            if chapter_id is None:
                rows = self._conn.execute(
                    "SELECT * FROM runs ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """
                    SELECT * FROM runs
                    WHERE chapter_id = ? ORDER BY created_at DESC
                    """,
                    (chapter_id,),
                ).fetchall()
        return [dict(row) for row in rows]

    def add_event(
        self,
        run_id: str,
        kind: str,
        text: str,
        *,
        stream: str = "",
        status: str | None = None,
        timestamp: str | None = None,
    ) -> dict:
        with self._lock, self._conn:
            return self._add_event_locked(
                run_id,
                kind,
                text,
                stream=stream,
                status=status,
                timestamp=timestamp,
            )

    def _add_event_locked(
        self,
        run_id: str,
        kind: str,
        text: str,
        *,
        stream: str = "",
        status: str | None = None,
        timestamp: str | None = None,
    ) -> dict:
        event_time = timestamp or datetime.now(timezone.utc).isoformat()
        row = self._conn.execute(
            """
            SELECT COALESCE(MAX(sequence), 0) AS sequence
            FROM run_events WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        sequence = int(row["sequence"]) + 1
        self._conn.execute(
            """
            INSERT INTO run_events (
                run_id, sequence, timestamp, kind, stream, text, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, sequence, event_time, kind, stream, text, status),
        )
        return {
            "run_id": run_id,
            "sequence": sequence,
            "timestamp": event_time,
            "kind": kind,
            "stream": stream,
            "text": text,
            "status": status,
        }

    def mark_running(self, run_id: str) -> None:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """
                UPDATE runs SET status = 'running'
                WHERE id = ? AND status = 'queued'
                """,
                (run_id,),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"任务不能进入运行态: {run_id}")
            self._add_event_locked(
                run_id, "status", "任务开始", status="running"
            )

    def finalize_run(
        self,
        run_id: str,
        status: str,
        *,
        exit_code: int | None = None,
        error_category: str | None = None,
        message: str,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """
                UPDATE runs
                SET status = ?, finished_at = ?, exit_code = ?, error_category = ?
                WHERE id = ? AND status IN ('queued', 'running')
                """,
                (status, now, exit_code, error_category, run_id),
            )
            if cursor.rowcount != 1:
                return False
            self._add_event_locked(
                run_id, "status", message, status=status, timestamp=now
            )
            return True

    def get_events_after(self, run_id: str, sequence: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT run_id, sequence, timestamp, kind, stream, text, status
                FROM run_events
                WHERE run_id = ? AND sequence > ?
                ORDER BY sequence
                """,
                (run_id, sequence),
            ).fetchall()
        return [dict(row) for row in rows]


class TaskRunner:
    def __init__(self, db_path: str | Path | None = None):
        resolved_db = db_path or resolve_project_path("outputs", "web_runs.sqlite3")
        if resolved_db != ":memory:":
            Path(resolved_db).parent.mkdir(parents=True, exist_ok=True)
        self._store = RunStore(resolved_db)
        self._active_run_id: str | None = None
        self._proc: asyncio.subprocess.Process | None = None
        self._execute_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._on_complete: Callable[[], None] | None = None

    def set_on_complete(self, callback: Callable[[], None]) -> None:
        self._on_complete = callback

    @property
    def active_run_id(self) -> str | None:
        return self._store.get_active_run_id()

    @property
    def current_run(self) -> RunRecord | None:
        run_id = self.active_run_id
        if run_id is None:
            return None
        run = self._store.get_run(run_id)
        return RunRecord(**run) if run else None

    def get_events_after(self, run_id: str, sequence: int) -> list[dict]:
        return self._store.get_events_after(run_id, sequence)

    def get_run(self, run_id: str) -> dict | None:
        run = self._store.get_run(run_id)
        if run is None:
            return None
        public = dict(run)
        public.pop("owner_pid", None)
        return public

    def get_history(self, chapter_id: str | None = None) -> list[dict]:
        runs = self._store.list_runs(chapter_id)
        for run in runs:
            run.pop("owner_pid", None)
        return runs

    async def start_run(
        self, chapter_id: str, preset_id: str, commands: list[str]
    ) -> RunRecord:
        async with self._lock:
            if self._active_run_id is not None:
                raise RuntimeError("已有任务在运行中")

            run_id = uuid.uuid4().hex[:12]
            now = datetime.now(timezone.utc).isoformat()
            run = {
                "id": run_id,
                "chapter_id": chapter_id,
                "preset_id": preset_id,
                "status": "queued",
                "created_at": now,
                "finished_at": "",
                "exit_code": None,
                "error_category": None,
                "owner_pid": os.getpid(),
            }
            self._store.create_active_run(run)
            self._active_run_id = run_id
            try:
                self._execute_task = asyncio.create_task(
                    self._execute_commands(run_id, commands)
                )
            except Exception:
                try:
                    self._finalize(
                        run_id,
                        "failed",
                        error_category="process_error",
                        message="任务启动异常",
                    )
                finally:
                    self._release_local_run(run_id)
                raise
            return RunRecord(**run)

    async def _execute_commands(self, run_id: str, commands: list[str]) -> None:
        try:
            self._store.mark_running(run_id)
            for command in commands:
                self._store.add_event(
                    run_id, "stdout", f"$ {command}\n", stream="cmd"
                )
                argv = shlex.split(command, posix=True)
                if len(argv) < 2:
                    raise ValueError(f"无效命令: {command}")
                self._proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    *argv[1:],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=(
                        subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
                    ),
                    start_new_session=os.name != "nt",
                )
                await self._stream_output(run_id)
                exit_code = await self._proc.wait()
                self._proc = None
                if exit_code != 0:
                    self._finalize(
                        run_id,
                        "failed",
                        exit_code=exit_code,
                        error_category="command_failed",
                        message=f"命令失败，退出码 {exit_code}",
                    )
                    return

            self._finalize(run_id, "succeeded", exit_code=0, message="任务完成")
        except asyncio.CancelledError:
            await self._terminate_proc()
            self._finalize(
                run_id,
                "cancelled",
                error_category="user_cancelled",
                message="任务已取消",
            )
        except Exception as exc:
            await self._terminate_proc()
            try:
                self._store.add_event(
                    run_id, "stderr", f"任务异常: {exc}\n", stream="stderr"
                )
            except Exception:
                pass
            try:
                self._finalize(
                    run_id,
                    "failed",
                    error_category="process_error",
                    message="任务异常结束",
                )
            except Exception:
                pass
        finally:
            self._proc = None
            self._release_local_run(run_id)

    def _finalize(
        self,
        run_id: str,
        status: str,
        *,
        exit_code: int | None = None,
        error_category: str | None = None,
        message: str,
    ) -> None:
        for attempt in range(2):
            try:
                finalized = self._store.finalize_run(
                    run_id,
                    status,
                    exit_code=exit_code,
                    error_category=error_category,
                    message=message,
                )
                break
            except sqlite3.Error:
                if attempt == 1:
                    raise
        if finalized:
            self._notify_complete()

    def _release_local_run(self, run_id: str) -> None:
        if self._active_run_id == run_id:
            self._active_run_id = None
            self._execute_task = None

    async def cancel_run(self, run_id: str) -> None:
        async with self._lock:
            run = self._store.get_run(run_id)
            if run is None:
                raise RunNotFoundError(f"任务不存在: {run_id}")
            if self._active_run_id != run_id or run["status"] in TERMINAL_STATUSES:
                raise RunNotCancellableError(f"任务不可取消: {run_id}")
            task = self._execute_task
            if task is not None:
                task.cancel()

        if task is not None:
            try:
                await task
            except asyncio.CancelledError:
                pass
        try:
            self._finalize(
                run_id,
                "cancelled",
                error_category="user_cancelled",
                message="任务已取消",
            )
        finally:
            self._release_local_run(run_id)

    async def _terminate_proc(self) -> None:
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return
        try:
            if os.name == "nt":
                try:
                    await asyncio.to_thread(
                        _terminate_windows_process_tree, proc.pid
                    )
                except OSError:
                    proc.terminate()
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                if os.name == "nt":
                    proc.kill()
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                await proc.wait()
        except ProcessLookupError:
            pass

    async def _stream_output(self, run_id: str) -> None:
        if self._proc is None:
            return

        def safe_decode(raw: bytes) -> str:
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("gbk", errors="replace")

        async def read_stream(stream, kind: str) -> None:
            while True:
                line = await stream.readline()
                if not line:
                    break
                self._store.add_event(
                    run_id, kind, safe_decode(line), stream=kind
                )

        await asyncio.gather(
            read_stream(self._proc.stdout, "stdout"),
            read_stream(self._proc.stderr, "stderr"),
        )

    async def shutdown(self) -> None:
        if self._active_run_id is not None:
            await self.cancel_run(self._active_run_id)

    def _notify_complete(self) -> None:
        if self._on_complete is None:
            return
        try:
            self._on_complete()
        except Exception:
            pass


_task_runner: TaskRunner | None = None


def get_task_runner() -> TaskRunner:
    global _task_runner
    if _task_runner is None:
        _task_runner = TaskRunner()
    return _task_runner
