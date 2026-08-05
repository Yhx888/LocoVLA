"""实验验收状态重置 API 测试（DELETE /api/experiments/{chapter_id}）。

用 monkeypatch 把 resolve_project_path 重定向到临时目录，避免触碰真实 outputs/。
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import upkie_mujoco_course.web.app as web_app
from upkie_mujoco_course.web.progress_store import ProgressStore
from upkie_mujoco_course.web.runner import TaskRunner


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    """把项目根重定向到临时目录，返回其中的 outputs/results。"""
    results = tmp_path / "outputs" / "results"
    results.mkdir(parents=True)

    def fake_resolve_project_path(*parts):
        if not parts:
            return tmp_path
        candidate = Path(parts[0]) if len(parts) == 1 else Path(*parts)
        if candidate.is_absolute():
            return candidate
        return tmp_path / candidate

    monkeypatch.setattr(web_app, "resolve_project_path", fake_resolve_project_path)
    return results


@pytest.fixture
def client(results_dir):
    runner = TaskRunner(db_path=results_dir.parent / "runs.sqlite3")
    progress = ProgressStore(results_dir.parent / "progress.json")
    app = web_app.create_app(task_runner=runner, progress_store=progress)
    with TestClient(app) as test_client:
        yield test_client


def _write_result(results_dir: Path, name: str, chapter_id: str) -> Path:
    path = results_dir / name
    path.write_text(
        json.dumps({"chapter_id": chapter_id, "passed": True, "valid": True}),
        encoding="utf-8",
    )
    return path


class TestResetExperimentEndpoint:
    def test_delete_removes_matching_files_only(self, client, results_dir):
        target = _write_result(results_dir, "test99_test.json", "test99")
        other = _write_result(results_dir, "test98_test.json", "test98")

        resp = client.delete("/api/experiments/test99")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["chapter_id"] == "test99"
        assert body["deleted"] == ["test99_test.json"]
        assert not target.exists()
        assert other.exists()

    def test_delete_unknown_chapter_returns_empty_deleted(self, client, results_dir):
        resp = client.delete("/api/experiments/no_such_chapter")

        assert resp.status_code == 200
        assert resp.json()["deleted"] == []

    def test_delete_skips_invalid_json_and_missing_chapter_field(
        self, client, results_dir
    ):
        broken = results_dir / "broken.json"
        broken.write_text("{not valid json", encoding="utf-8")
        no_field = results_dir / "nofield.json"
        no_field.write_text(json.dumps({"passed": True}), encoding="utf-8")

        resp = client.delete("/api/experiments/test99")

        assert resp.status_code == 200
        assert resp.json()["deleted"] == []
        assert broken.exists()
        assert no_field.exists()

    def test_delete_leaves_non_json_files_untouched(self, client, results_dir):
        note = results_dir / "notes.txt"
        note.write_text("keep me", encoding="utf-8")

        resp = client.delete("/api/experiments/test99")

        assert resp.status_code == 200
        assert note.exists()

    def test_delete_invalidates_results_cache(self, client, results_dir):
        _write_result(results_dir, "test99_test.json", "test99")
        client.get("/api/course")  # 填充模块级缓存
        assert web_app._results_cache is not None

        resp = client.delete("/api/experiments/test99")

        assert resp.status_code == 200
        assert web_app._results_cache is None
