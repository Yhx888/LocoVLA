"""web API 集成测试（TestClient）。"""

import importlib

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from upkie_mujoco_course.web.progress_store import ProgressStore
import upkie_mujoco_course.web.runner as runner_module
from upkie_mujoco_course.web.runner import TaskRunner


@pytest.fixture
def client(tmp_path):
    runner = TaskRunner(db_path=tmp_path / "runs.sqlite3")
    progress = ProgressStore(tmp_path / "progress.json")
    runner_module._task_runner = runner
    web_app = importlib.import_module("upkie_mujoco_course.web.app")
    app = web_app.create_app(task_runner=runner, progress_store=progress)
    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in {"ready", "degraded"}
        assert "python" in data
        assert "mujoco" in data


class TestCourseEndpoint:
    def test_course_returns_58_chapters(self, client):
        resp = client.get("/api/course")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_chapters"] == 58


class TestChapterEndpoint:
    def test_chapter_00_returns_content(self, client):
        resp = client.get("/api/chapters/00")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "00"
        assert data["status"] == "ready"
        assert len(data["content"]) > 0

    def test_chapter_unknown_returns_404(self, client):
        resp = client.get("/api/chapters/XX")
        assert resp.status_code == 404

    def test_chapter_planned_has_no_presets(self, client):
        resp = client.get("/api/chapters/H02")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "planned"


class TestProgressEndpoint:
    def test_put_progress_returns_ok(self, client):
        resp = client.put("/api/progress/00", json={
            "reading_percent": 50,
            "reading_complete": False,
            "self_check_ids": [],
        })
        assert resp.status_code == 200

    def test_put_progress_422_on_invalid(self, client):
        resp = client.put("/api/progress/00", json={"reading_percent": 150})
        assert resp.status_code == 422


class TestRunEndpoint:
    def test_create_run_missing_params_422(self, client):
        resp = client.post("/api/runs", json={})
        assert resp.status_code == 422

    def test_create_run_bad_preset_400(self, client):
        resp = client.post("/api/runs", json={
            "chapter_id": "00",
            "preset_id": "nonexistent",
        })
        assert resp.status_code == 400

    def test_list_runs_returns_array(self, client):
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_second_run_conflict_exposes_active_run_id(self, client):
        body = {
            "chapter_id": "00",
            "preset_id": "script",
            "command": "python scripts/00_view_model.py --duration 3 --no-viewer",
        }
        first = client.post("/api/runs", json=body)
        assert first.status_code == 200

        conflict = client.post("/api/runs", json=body)
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["active_run_id"] == first.json()["id"]

        cancelled = client.post(f"/api/runs/{first.json()['id']}/cancel")
        assert cancelled.status_code == 200

    def test_cancel_unknown_run_returns_404(self, client):
        resp = client.post("/api/runs/missing/cancel")
        assert resp.status_code == 404

    def test_cancel_terminal_run_returns_409(self, client):
        runner = client.app.state.task_runner
        runner._store.create_run({
            "id": "finished-run",
            "chapter_id": "00",
            "preset_id": "script",
            "status": "succeeded",
            "created_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:01+00:00",
            "exit_code": 0,
            "error_category": None,
        })

        resp = client.post("/api/runs/finished-run/cancel")
        assert resp.status_code == 409

    def test_list_runs_filters_by_chapter(self, client):
        runner = client.app.state.task_runner
        runner._store.create_run({
            "id": "chapter-00",
            "chapter_id": "00",
            "preset_id": "script",
            "status": "succeeded",
            "created_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:01+00:00",
            "exit_code": 0,
            "error_category": None,
        })
        runner._store.create_run({
            "id": "chapter-01",
            "chapter_id": "01",
            "preset_id": "script",
            "status": "succeeded",
            "created_at": "2026-01-01T00:00:02+00:00",
            "finished_at": "2026-01-01T00:00:03+00:00",
            "exit_code": 0,
            "error_category": None,
        })

        resp = client.get("/api/runs?chapter_id=00")
        assert resp.status_code == 200
        assert [run["id"] for run in resp.json()] == ["chapter-00"]

    def test_run_api_does_not_expose_internal_owner_pid(self, client):
        runner = client.app.state.task_runner
        runner._store.create_run({
            "id": "internal-owner",
            "chapter_id": "00",
            "preset_id": "script",
            "status": "succeeded",
            "created_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:01+00:00",
            "exit_code": 0,
            "error_category": None,
            "owner_pid": 12345,
        })

        detail = client.get("/api/runs/internal-owner")
        history = client.get("/api/runs?chapter_id=00")

        assert detail.status_code == 200
        assert "owner_pid" not in detail.json()
        assert history.status_code == 200
        assert all("owner_pid" not in run for run in history.json())

    def test_websocket_replays_only_target_events_after_sequence_then_closes(self, client):
        runner = client.app.state.task_runner
        for run_id in ("target-run", "other-run"):
            runner._store.create_run({
                "id": run_id,
                "chapter_id": "00",
                "preset_id": "script",
                "status": "succeeded",
                "created_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T00:00:01+00:00",
                "exit_code": 0,
                "error_category": None,
            })
            runner._store.add_event(run_id, "stdout", f"{run_id}-first\n")
            runner._store.add_event(run_id, "stdout", f"{run_id}-second\n")
            runner._store.add_event(
                run_id, "status", f"{run_id}-done", status="succeeded"
            )

        with client.websocket_connect(
            "/api/runs/target-run/events?after=1"
        ) as websocket:
            second = websocket.receive_json()
            terminal = websocket.receive_json()
            assert second["run_id"] == "target-run"
            assert second["sequence"] == 2
            assert "target-run-second" in second["text"]
            assert terminal["run_id"] == "target-run"
            assert terminal["status"] == "succeeded"
            with pytest.raises(WebSocketDisconnect) as closed:
                websocket.receive_json()
            assert closed.value.code == 1000


class TestArtifactEndpoint:
    def test_artifact_outside_outputs_404(self, client):
        resp = client.get("/api/artifacts/../src/main.py")
        assert resp.status_code == 404

    def test_artifact_not_found_404(self, client):
        resp = client.get("/api/artifacts/results/nonexistent.json")
        assert resp.status_code == 404
