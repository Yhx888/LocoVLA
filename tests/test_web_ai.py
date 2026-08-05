"""AI 助教模块与端点测试。

覆盖：配置加载与降级、提示词构造、评分 JSON 解析、
status/explain/grade 三端点（mock LLM 调用，不发真实请求）。
"""

import importlib
import json

import pytest
from fastapi.testclient import TestClient

import upkie_mujoco_course.web.ai as ai_service
import upkie_mujoco_course.web.runner as runner_module
from upkie_mujoco_course.web.progress_store import ProgressStore
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


class TestLoadApiKey:
    def test_env_var_first(self, monkeypatch):
        monkeypatch.setenv(ai_service.API_KEY_ENV, "key-from-env")
        assert ai_service.load_api_key() == "key-from-env"

    def test_missing_key_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv(ai_service.API_KEY_ENV, raising=False)
        monkeypatch.setattr(
            ai_service, "resolve_project_path", lambda *_: tmp_path / "no-such.json"
        )
        assert ai_service.load_api_key() is None

    def test_local_json_fallback(self, monkeypatch, tmp_path):
        monkeypatch.delenv(ai_service.API_KEY_ENV, raising=False)
        local = tmp_path / "ai.local.json"
        local.write_text(json.dumps({"api_key": "key-from-file"}), encoding="utf-8")
        monkeypatch.setattr(ai_service, "resolve_project_path", lambda *_: local)
        assert ai_service.load_api_key() == "key-from-file"


class TestAiStatus:
    def test_not_configured_without_key(self, monkeypatch):
        monkeypatch.setattr(ai_service, "load_api_key", lambda: None)
        monkeypatch.setattr(
            ai_service,
            "load_ai_config",
            lambda: {"enabled": True, "base_url": "https://x/v1", "model": "m"},
        )
        status = ai_service.get_ai_status()
        assert status["configured"] is False
        assert status["has_key"] is False
        # 新契约：model / base_url 总是回回当前生效值，供前端预填
        assert status["model"] == "m"
        assert status["base_url"] == "https://x/v1"

    def test_configured_with_key(self, monkeypatch):
        monkeypatch.setattr(ai_service, "load_api_key", lambda: "k")
        monkeypatch.setattr(
            ai_service,
            "load_ai_config",
            lambda: {"enabled": True, "base_url": "https://x/v1", "model": "m"},
        )
        status = ai_service.get_ai_status()
        assert status["configured"] is True
        assert status["model"] == "m"
        assert status["has_key"] is True

    def test_require_config_raises_without_key(self, monkeypatch):
        monkeypatch.setattr(ai_service, "load_api_key", lambda: None)
        with pytest.raises(ai_service.AiNotConfiguredError):
            ai_service.require_config()


class TestSaveAiConfig:
    @pytest.fixture(autouse=True)
    def _isolate_local(self, monkeypatch, tmp_path):
        # 将 ai.local.json 重定向到临时目录，避免写到真实配置
        local = tmp_path / "ai.local.json"
        monkeypatch.setattr(ai_service, "resolve_project_path", lambda *_: local)
        monkeypatch.delenv(ai_service.API_KEY_ENV, raising=False)
        self.local = local

    def test_save_writes_local_json_and_enables(self):
        status = ai_service.save_ai_config(
            api_key="sk-test", base_url="https://api.example.com/v1", model="m"
        )
        data = json.loads(self.local.read_text(encoding="utf-8"))
        assert data == {
            "enabled": True,
            "base_url": "https://api.example.com/v1",
            "model": "m",
            "api_key": "sk-test",
        }
        assert status["configured"] is True
        assert status["has_key"] is True
        assert status["model"] == "m"

    def test_empty_api_key_keeps_existing(self):
        ai_service.save_ai_config(api_key="sk-old", base_url="https://x/v1", model="m")
        # 再次保存时不传 key，应保留旧 key
        ai_service.save_ai_config(api_key="", base_url="https://y/v1", model="m2")
        data = json.loads(self.local.read_text(encoding="utf-8"))
        assert data["api_key"] == "sk-old"
        assert data["base_url"] == "https://y/v1"
        assert data["model"] == "m2"


class TestConfigEndpoint:
    def test_config_saves_and_returns_status(self, client, monkeypatch):
        captured = {}

        def fake_save(*, api_key, base_url, model, enabled):
            captured.update(
                api_key=api_key, base_url=base_url, model=model, enabled=enabled
            )
            return {"configured": True, "model": model, "base_url": base_url, "has_key": True}

        monkeypatch.setattr(ai_service, "save_ai_config", fake_save)
        resp = client.post(
            "/api/ai/config",
            json={"api_key": "sk-x", "base_url": "https://api.example.com/v1", "model": "m"},
        )
        assert resp.status_code == 200
        assert resp.json()["configured"] is True
        assert captured == {
            "api_key": "sk-x",
            "base_url": "https://api.example.com/v1",
            "model": "m",
            "enabled": True,
        }


class TestBuildExplainMessages:
    def test_selected_text_builds_user_message(self):
        messages = ai_service.build_explain_messages(
            chapter_title="14 直立控制",
            selected_text="重力项会放大偏角",
            context="……上下文……",
            question="",
            history=[],
        )
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert "重力项会放大偏角" in messages[-1]["content"]
        assert "14 直立控制" in messages[-1]["content"]

    def test_empty_inputs_raise_value_error(self):
        with pytest.raises(ValueError):
            ai_service.build_explain_messages("", "", "", "", [])

    def test_history_is_truncated(self):
        history = [{"role": "user", "content": f"问题{i}"} for i in range(30)]
        messages = ai_service.build_explain_messages("", "", "", "追问", history)
        # system + 截断后的 history + 本次提问
        assert len(messages) == 1 + ai_service.MAX_HISTORY_MESSAGES + 1

    def test_invalid_history_roles_skipped(self):
        history = [{"role": "system", "content": "越权"}, {"role": "user", "content": ""}]
        messages = ai_service.build_explain_messages("", "", "", "追问", history)
        assert len(messages) == 2


class TestParseGradeResponse:
    def test_valid_json(self):
        result = ai_service.parse_grade_response(
            '{"score": 8, "comment": "不错", "gaps": ["缺少举例"]}'
        )
        assert result == {"score": 8, "comment": "不错", "gaps": ["缺少举例"]}

    def test_json_with_code_fence(self):
        result = ai_service.parse_grade_response(
            '```json\n{"score": 5, "comment": "一般", "gaps": []}\n```'
        )
        assert result["score"] == 5

    def test_score_clamped_to_range(self):
        assert ai_service.parse_grade_response('{"score": 99}')["score"] == 10
        assert ai_service.parse_grade_response('{"score": -3}')["score"] == 0

    def test_gaps_limited_to_four(self):
        payload = json.dumps({"score": 6, "gaps": [f"g{i}" for i in range(9)]})
        assert len(ai_service.parse_grade_response(payload)["gaps"]) == 4

    def test_invalid_json_raises(self):
        with pytest.raises(ai_service.AiServiceError):
            ai_service.parse_grade_response("抱歉我无法评分")

    def test_missing_score_raises(self):
        with pytest.raises(ai_service.AiServiceError):
            ai_service.parse_grade_response('{"comment": "没有分数"}')


class TestStatusEndpoint:
    def test_status_returns_configured_flag(self, client, monkeypatch):
        monkeypatch.setattr(ai_service, "load_api_key", lambda: None)
        resp = client.get("/api/ai/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is False
        assert "model" in data


class TestExplainEndpoint:
    def test_not_configured_returns_503(self, client, monkeypatch):
        def raise_not_configured():
            raise ai_service.AiNotConfiguredError("缺 key")

        monkeypatch.setattr(ai_service, "require_config", raise_not_configured)
        resp = client.post("/api/ai/explain", json={"selected_text": "什么是 LQR"})
        assert resp.status_code == 503

    def test_empty_request_returns_422(self, client, monkeypatch):
        monkeypatch.setattr(ai_service, "require_config", lambda: ({}, "k"))
        resp = client.post("/api/ai/explain", json={})
        assert resp.status_code == 422

    def test_stream_returns_deltas_and_done(self, client, monkeypatch):
        monkeypatch.setattr(ai_service, "require_config", lambda: ({}, "k"))

        async def fake_stream(messages):
            yield "第一段"
            yield "第二段"

        monkeypatch.setattr(ai_service, "stream_chat", fake_stream)
        resp = client.post("/api/ai/explain", json={"question": "什么是 LQR"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        body = resp.text
        assert 'data: {"delta": "第一段"}' in body
        assert 'data: {"delta": "第二段"}' in body
        assert "data: [DONE]" in body

    def test_stream_error_emits_error_event(self, client, monkeypatch):
        monkeypatch.setattr(ai_service, "require_config", lambda: ({}, "k"))

        async def failing_stream(messages):
            raise ai_service.AiServiceError("上游超时")
            yield  # pragma: no cover

        monkeypatch.setattr(ai_service, "stream_chat", failing_stream)
        resp = client.post("/api/ai/explain", json={"question": "什么是 LQR"})
        assert resp.status_code == 200
        assert '"error"' in resp.text
        assert "上游超时" in resp.text


class TestGradeEndpoint:
    GRADE_BODY = {
        "chapter_id": "00",
        "question_id": "00-q1",
        "question": "本关最关键的假设是什么？",
        "reference_answer": "环境已正确配置。",
        "user_answer": "环境配置好了。",
    }

    def test_empty_answer_returns_422(self, client):
        body = dict(self.GRADE_BODY, user_answer="   ")
        resp = client.post("/api/ai/grade", json=body)
        assert resp.status_code == 422

    def test_grade_returns_structured_result(self, client, monkeypatch):
        async def fake_grade(question, reference_answer, user_answer):
            return {"score": 7, "comment": "接近参考答案", "gaps": ["缺少失效信号"]}

        monkeypatch.setattr(ai_service, "grade_answer", fake_grade)
        resp = client.post("/api/ai/grade", json=self.GRADE_BODY)
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 7
        assert data["gaps"] == ["缺少失效信号"]

    def test_not_configured_returns_503(self, client, monkeypatch):
        async def fake_grade(**kwargs):
            raise ai_service.AiNotConfiguredError("缺 key")

        monkeypatch.setattr(ai_service, "grade_answer", fake_grade)
        resp = client.post("/api/ai/grade", json=self.GRADE_BODY)
        assert resp.status_code == 503

    def test_service_error_returns_502(self, client, monkeypatch):
        async def fake_grade(**kwargs):
            raise ai_service.AiServiceError("评分 JSON 解析失败")

        monkeypatch.setattr(ai_service, "grade_answer", fake_grade)
        resp = client.post("/api/ai/grade", json=self.GRADE_BODY)
        assert resp.status_code == 502


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class _FakeAsyncClient:
    """替身 httpx2.AsyncClient：记录请求并返回预设响应。"""

    response: _FakeResponse = _FakeResponse(200)

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None):
        return type(self).response


class TestCompleteChat:
    @pytest.fixture(autouse=True)
    def configured(self, monkeypatch):
        monkeypatch.setattr(
            ai_service,
            "require_config",
            lambda: ({"base_url": "https://x/v1", "model": "m"}, "k"),
        )
        monkeypatch.setattr(ai_service.httpx2, "AsyncClient", _FakeAsyncClient)

    async def test_returns_message_content(self):
        _FakeAsyncClient.response = _FakeResponse(
            200, payload={"choices": [{"message": {"content": "你好"}}]}
        )
        assert await ai_service.complete_chat([{"role": "user", "content": "hi"}]) == "你好"

    async def test_auth_failure_maps_to_readable_error(self):
        _FakeAsyncClient.response = _FakeResponse(401, text="Unauthorized")
        with pytest.raises(ai_service.AiServiceError, match="鉴权失败"):
            await ai_service.complete_chat([{"role": "user", "content": "hi"}])

    async def test_malformed_payload_raises(self):
        _FakeAsyncClient.response = _FakeResponse(200, payload={"unexpected": True})
        with pytest.raises(ai_service.AiServiceError, match="格式异常"):
            await ai_service.complete_chat([{"role": "user", "content": "hi"}])
