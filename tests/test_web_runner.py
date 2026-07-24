"""web runner 测试。"""

import asyncio
import ctypes
import sqlite3
import subprocess
import sys
from ctypes import wintypes

import pytest
import upkie_mujoco_course.web.runner as runner_module
from upkie_mujoco_course.web.runner import (
    RunNotCancellableError,
    RunNotFoundError,
    TaskRunner,
)


async def _wait_for_terminal(runner: TaskRunner, run_id: str) -> dict:
    for _ in range(200):
        run = runner.get_run(run_id)
        if run and run["status"] in {
            "succeeded",
            "failed",
            "cancelled",
            "interrupted",
        }:
            return run
        await asyncio.sleep(0.01)
    raise AssertionError(f"任务 {run_id} 未进入终态")


def _command(script) -> str:
    return f"python {script.as_posix()}"


def test_runner_initial_state():
    runner = TaskRunner(db_path=":memory:")
    assert runner.current_run is None


def test_events_after_empty():
    runner = TaskRunner(db_path=":memory:")
    events = runner.get_events_after("missing", 0)
    assert isinstance(events, list)


def test_history_initially_empty():
    runner = TaskRunner(db_path=":memory:")
    history = runner.get_history()
    assert isinstance(history, list)


def test_get_nonexistent_run():
    runner = TaskRunner(db_path=":memory:")
    assert runner.get_run("nonexistent") is None


@pytest.mark.asyncio
async def test_cancel_noop():
    runner = TaskRunner(db_path=":memory:")
    with pytest.raises(RunNotFoundError):
        await runner.cancel_run("missing")


@pytest.mark.asyncio
async def test_sequential_runs_keep_events_isolated_and_persisted(tmp_path):
    first_script = tmp_path / "first.py"
    first_script.write_text("print('first-output')\n", encoding="utf-8")
    second_script = tmp_path / "second.py"
    second_script.write_text("print('second-output')\n", encoding="utf-8")
    db_path = tmp_path / "runs.sqlite3"
    runner = TaskRunner(db_path=db_path)

    first = await runner.start_run("00", "script", [_command(first_script)])
    assert (await _wait_for_terminal(runner, first.id))["status"] == "succeeded"
    first_events = runner.get_events_after(first.id, 0)

    second = await runner.start_run("00", "custom", [_command(second_script)])
    assert (await _wait_for_terminal(runner, second.id))["status"] == "succeeded"

    assert "first-output" in "".join(event["text"] for event in first_events)
    assert "second-output" not in "".join(
        event["text"] for event in runner.get_events_after(first.id, 0)
    )
    assert "second-output" in "".join(
        event["text"] for event in runner.get_events_after(second.id, 0)
    )

    restored = TaskRunner(db_path=db_path)
    assert restored.get_run(first.id)["status"] == "succeeded"
    assert restored.get_events_after(first.id, 0) == first_events


@pytest.mark.asyncio
async def test_wrong_run_id_does_not_cancel_active_run(tmp_path):
    script = tmp_path / "slow.py"
    script.write_text("import time\ntime.sleep(1)\n", encoding="utf-8")
    runner = TaskRunner(db_path=tmp_path / "runs.sqlite3")
    active = await runner.start_run("00", "script", [_command(script)])

    with pytest.raises(RunNotFoundError):
        await runner.cancel_run("wrong-id")

    assert runner.current_run is not None
    assert runner.current_run.id == active.id
    await runner.cancel_run(active.id)
    assert (await _wait_for_terminal(runner, active.id))["status"] == "cancelled"


@pytest.mark.asyncio
async def test_process_start_error_releases_runner_for_next_run(tmp_path):
    missing = tmp_path / "missing.py"
    success = tmp_path / "success.py"
    success.write_text("print('recovered')\n", encoding="utf-8")
    runner = TaskRunner(db_path=tmp_path / "runs.sqlite3")

    failed = await runner.start_run("00", "script", [_command(missing)])
    assert (await _wait_for_terminal(runner, failed.id))["status"] == "failed"

    recovered = await runner.start_run("00", "script", [_command(success)])
    assert (await _wait_for_terminal(runner, recovered.id))["status"] == "succeeded"


@pytest.mark.asyncio
async def test_sqlite_enforces_one_active_run_across_runner_instances(tmp_path):
    script = tmp_path / "slow.py"
    script.write_text("import time\ntime.sleep(2)\n", encoding="utf-8")
    db_path = tmp_path / "runs.sqlite3"
    first_runner = TaskRunner(db_path=db_path)
    first = await first_runner.start_run("00", "script", [_command(script)])

    try:
        second_runner = TaskRunner(db_path=db_path)
        assert second_runner.get_run(first.id)["status"] in {"queued", "running"}
        with pytest.raises(RuntimeError, match=first.id):
            await second_runner.start_run("01", "script", [_command(script)])
    finally:
        task = first_runner._execute_task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


def test_restart_marks_only_dead_owner_run_interrupted(tmp_path):
    db_path = tmp_path / "runs.sqlite3"
    original = TaskRunner(db_path=db_path)
    original._store.create_run({
        "id": "dead-owner",
        "chapter_id": "00",
        "preset_id": "script",
        "status": "running",
        "created_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "",
        "exit_code": None,
        "error_category": None,
        "owner_pid": 2_147_483_647,
    })
    original._store.add_event(
        "dead-owner", "status", "任务开始", status="running"
    )

    restored = TaskRunner(db_path=db_path)
    run = restored.get_run("dead-owner")
    assert run["status"] == "interrupted"
    assert run["error_category"] == "server_restarted"
    assert restored.get_events_after("dead-owner", 0)[-1]["status"] == "interrupted"


def test_new_runner_preserves_run_owned_by_live_process(tmp_path):
    owner = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        db_path = tmp_path / "runs.sqlite3"
        original = TaskRunner(db_path=db_path)
        original._store.create_run({
            "id": "live-owner",
            "chapter_id": "00",
            "preset_id": "script",
            "status": "running",
            "created_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "",
            "exit_code": None,
            "error_category": None,
            "owner_pid": owner.pid,
        })
        original._store.add_event(
            "live-owner", "status", "任务开始", status="running"
        )

        restored = TaskRunner(db_path=db_path)
        assert restored.get_run("live-owner")["status"] == "running"
    finally:
        owner.terminate()
        owner.wait(timeout=5)


def test_windows_process_probe_declares_pointer_sized_handle(monkeypatch):
    class FakeFunction:
        def __init__(self, result, callback=None):
            self.result = result
            self.callback = callback
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            if self.callback:
                self.callback(*args)
            return self.result

    def set_active_exit_code(_handle, exit_code):
        exit_code._obj.value = 259

    class FakeKernel32:
        OpenProcess = FakeFunction(0x1_0000_0001)
        GetExitCodeProcess = FakeFunction(1, set_active_exit_code)
        CloseHandle = FakeFunction(1)

    fake_kernel32 = FakeKernel32()
    monkeypatch.setattr(runner_module.os, "name", "nt")
    monkeypatch.setattr(
        runner_module.ctypes,
        "windll",
        type("FakeWindll", (), {"kernel32": fake_kernel32})(),
        raising=False,
    )

    assert runner_module._process_is_alive(12345) is True
    assert fake_kernel32.OpenProcess.argtypes == [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    assert fake_kernel32.OpenProcess.restype is wintypes.HANDLE
    assert fake_kernel32.GetExitCodeProcess.argtypes == [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    assert fake_kernel32.CloseHandle.argtypes == [wintypes.HANDLE]


@pytest.mark.asyncio
async def test_real_process_creation_error_finishes_and_releases_runner(tmp_path, monkeypatch):
    runner = TaskRunner(db_path=tmp_path / "runs.sqlite3")

    async def fail_to_create_process(*_args, **_kwargs):
        raise OSError("injected create_subprocess_exec failure")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fail_to_create_process)
    failed = await runner.start_run("00", "script", ["python scripts/missing.py"])
    result = await _wait_for_terminal(runner, failed.id)

    assert result["status"] == "failed"
    assert result["error_category"] == "process_error"
    assert runner.active_run_id is None


@pytest.mark.asyncio
async def test_running_transition_error_releases_local_active(tmp_path, monkeypatch):
    runner = TaskRunner(db_path=tmp_path / "runs.sqlite3")

    def fail_running_transition(*_args, **_kwargs):
        raise sqlite3.OperationalError("injected running transition failure")

    monkeypatch.setattr(runner._store, "mark_running", fail_running_transition)
    failed = await runner.start_run("00", "script", ["python scripts/missing.py"])
    result = await _wait_for_terminal(runner, failed.id)

    assert result["status"] == "failed"
    assert runner._active_run_id is None


@pytest.mark.asyncio
async def test_terminal_run_and_event_remain_atomic_after_transient_insert_error(tmp_path):
    runner = TaskRunner(db_path=tmp_path / "runs.sqlite3")
    attempts = 0

    def fail_once():
        nonlocal attempts
        attempts += 1
        return int(attempts == 1)

    runner._store._conn.create_function("fail_once", 0, fail_once)
    runner._store._conn.execute(
        """
        CREATE TRIGGER fail_first_terminal_event
        BEFORE INSERT ON run_events
        WHEN NEW.status IN ('succeeded', 'failed', 'cancelled', 'interrupted')
             AND fail_once() = 1
        BEGIN
            SELECT RAISE(ABORT, 'injected terminal event failure');
        END
        """
    )
    run = await runner.start_run("00", "empty", [])
    result = await _wait_for_terminal(runner, run.id)
    events = runner.get_events_after(run.id, 0)

    assert result["status"] == "succeeded"
    assert events[-1]["status"] == result["status"]
    assert runner.active_run_id is None


@pytest.mark.asyncio
async def test_cancelled_run_retries_transient_terminal_event_error(tmp_path):
    script = tmp_path / "slow.py"
    script.write_text("import time\ntime.sleep(2)\n", encoding="utf-8")
    runner = TaskRunner(db_path=tmp_path / "runs.sqlite3")
    attempts = 0

    def fail_once():
        nonlocal attempts
        attempts += 1
        return int(attempts == 1)

    runner._store._conn.create_function("fail_once", 0, fail_once)
    runner._store._conn.execute(
        """
        CREATE TRIGGER fail_first_terminal_event
        BEFORE INSERT ON run_events
        WHEN NEW.status IN ('succeeded', 'failed', 'cancelled', 'interrupted')
             AND fail_once() = 1
        BEGIN
            SELECT RAISE(ABORT, 'injected terminal event failure');
        END
        """
    )
    run = await runner.start_run("00", "script", [_command(script)])
    await runner.cancel_run(run.id)
    result = await _wait_for_terminal(runner, run.id)
    events = runner.get_events_after(run.id, 0)

    assert result["status"] == "cancelled"
    assert events[-1]["status"] == "cancelled"
    assert runner.active_run_id is None


@pytest.mark.asyncio
async def test_terminal_run_cannot_be_cancelled(tmp_path):
    runner = TaskRunner(db_path=tmp_path / "runs.sqlite3")
    run = await runner.start_run("00", "empty", [])
    await _wait_for_terminal(runner, run.id)

    with pytest.raises(RunNotCancellableError):
        await runner.cancel_run(run.id)


def test_windows_tree_termination_uses_taskkill(monkeypatch):
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)
    runner_module._terminate_windows_process_tree(4321)

    assert observed["command"] == ["taskkill", "/PID", "4321", "/T", "/F"]
    assert observed["kwargs"]["check"] is False
