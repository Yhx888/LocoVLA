"""AI 助教：OpenAI 兼容 Chat Completions 客户端、提示词模板与评分解析。

配置来源（优先级从低到高）：
- configs/course/ai.json（入 Git）：随项目发布的默认 base_url、model 等；
- configs/course/ai.local.json（不入 Git）：前端配置面板写入的覆盖项，
  可覆盖 enabled、base_url、model 并保存 api_key；
- 环境变量 UPKIE_AI_API_KEY：仅覆盖 api_key，优先级最高。
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import AsyncIterator

import httpx2

from upkie_mujoco_course.utils.config import load_json_config
from upkie_mujoco_course.utils.paths import resolve_project_path

AI_CONFIG_PATH = "configs/course/ai.json"
AI_LOCAL_KEY_PATH = "configs/course/ai.local.json"
API_KEY_ENV = "UPKIE_AI_API_KEY"

# 前端配置面板写入 ai.local.json 后可覆盖的非敏感字段
OVERRIDABLE_FIELDS = ("enabled", "base_url", "model")

# 输入长度上限：防止把整章教程塞进请求
MAX_TEXT_CHARS = 4000
MAX_HISTORY_MESSAGES = 12

EXPLAIN_SYSTEM_PROMPT = (
    "你是 Upkie 双腿轮足机器人 MuJoCo 运动控制课程的中文助教。"
    "学习者只学过高中数学，正在零基础学习运动控制与 VLA。"
    "请遵守：\n"
    "1. 永远用中文回答，术语首次出现时给大白话解释；\n"
    "2. 涉及公式时先讲直觉，再拆解每个符号的含义；\n"
    "3. 结合 Upkie 机器人（双腿+轮子的倒立摆结构）举例；\n"
    "4. 回答控制在 500 字以内，先给一句话结论，再展开；\n"
    "5. 不确定时明确说不确定，不要编造课程细节。"
)

GRADE_SYSTEM_PROMPT = (
    "你是 Upkie 运动控制课程的中文批改助教。请对比学习者答案与参考答案，"
    "只输出一个 JSON 对象，不要输出任何其他文字或代码块围栏，格式为：\n"
    '{"score": 0到10的整数, "comment": "一段中文点评（100字以内）", '
    '"gaps": ["与参考答案相比缺失或错误的要点，每条30字以内"]}\n'
    "评分标准：核心概念正确性占 6 分，表达完整性占 2 分，举例或量化占 2 分。"
    "学习者答案为空或完全无关时给 0 分。gaps 最多 4 条，答案完整时可为空数组。"
)


class AiNotConfiguredError(RuntimeError):
    """AI 服务未配置（缺少 API key、base_url 或被禁用）。"""


class AiServiceError(RuntimeError):
    """AI 服务调用失败，message 为可读中文信息。"""


# ── 配置 ──

def _load_local_overrides() -> dict:
    """读取 ai.local.json（前端面板写入的本地覆盖），不存在或不合法时返回空字典。"""
    path = resolve_project_path(AI_LOCAL_KEY_PATH)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_ai_config() -> dict:
    config = {
        "enabled": False,
        "base_url": "",
        "model": "",
        "temperature": 0.3,
        "max_tokens": 2048,
        "timeout_seconds": 90,
    }
    path = resolve_project_path(AI_CONFIG_PATH)
    if path.exists():
        config.update(load_json_config(AI_CONFIG_PATH))
    # ai.local.json 中的非敏感字段覆盖项目默认（前端面板可修改）
    local = _load_local_overrides()
    for field in OVERRIDABLE_FIELDS:
        value = local.get(field)
        if value not in (None, ""):
            config[field] = value
    return config


def load_api_key() -> str | None:
    key = os.environ.get(API_KEY_ENV, "").strip()
    if key:
        return key
    key = str(_load_local_overrides().get("api_key", "")).strip()
    return key or None


def get_ai_status() -> dict:
    """返回 AI 服务可用状态，前端据此启停 AI 入口并预填配置表单。

    为了支持前端预填，base_url / model 总是回回当前生效值（非敏感）；
    api_key 不回回，仅用 has_key 表示是否已设置。
    """
    config = load_ai_config()
    has_key = bool(load_api_key())
    configured = bool(
        config.get("enabled")
        and config.get("base_url")
        and config.get("model")
        and has_key
    )
    return {
        "configured": configured,
        "model": config.get("model", ""),
        "base_url": config.get("base_url", ""),
        "has_key": has_key,
    }


def save_ai_config(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    enabled: bool = True,
) -> dict:
    """将前端配置面板的输入写入 ai.local.json（合并现有内容），返回最新状态。

    - base_url / model：提供非空值时覆盖；
    - api_key：仅当提供非空值时更新（空字符串表示保留现有 key）；
    - enabled：默认 True，保存即启用。
    """
    data = _load_local_overrides()
    data["enabled"] = bool(enabled)
    if base_url is not None and base_url.strip():
        data["base_url"] = base_url.strip()
    if model is not None and model.strip():
        data["model"] = model.strip()
    if api_key is not None and api_key.strip():
        data["api_key"] = api_key.strip()
    path = resolve_project_path(AI_LOCAL_KEY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return get_ai_status()


def require_config() -> tuple[dict, str]:
    """返回 (config, api_key)，未配置时抛 AiNotConfiguredError。"""
    config = load_ai_config()
    key = load_api_key()
    if not config.get("enabled"):
        raise AiNotConfiguredError("AI 助教未启用：configs/course/ai.json 中 enabled 为 false")
    if not config.get("base_url") or not config.get("model"):
        raise AiNotConfiguredError("AI 助教未配置：configs/course/ai.json 缺少 base_url 或 model")
    if not key:
        raise AiNotConfiguredError(
            "AI 助教缺少 API key：请设置环境变量 UPKIE_AI_API_KEY，"
            "或在 configs/course/ai.local.json 写入 {\"api_key\": \"...\"}"
        )
    return config, key


# ── 提示词构造 ──

def _clip(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    text = text.strip()
    return text[:limit]


def build_explain_messages(
    chapter_title: str,
    selected_text: str,
    context: str,
    question: str,
    history: list[dict],
) -> list[dict]:
    """构造圈选解释/追问的 messages 列表。"""
    messages: list[dict] = [{"role": "system", "content": EXPLAIN_SYSTEM_PROMPT}]
    for item in history[-MAX_HISTORY_MESSAGES:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": _clip(content)})
    parts: list[str] = []
    if chapter_title:
        parts.append(f"当前章节：{_clip(chapter_title, 100)}")
    if selected_text:
        parts.append(f"我在教程里圈选了这段话，请解释它：\n「{_clip(selected_text)}」")
        if context:
            parts.append(f"圈选处的上下文（供参考，不必逐句解释）：\n{_clip(context)}")
    if question:
        parts.append(_clip(question))
    if not parts:
        raise ValueError("selected_text 和 question 至少提供一个")
    messages.append({"role": "user", "content": "\n\n".join(parts)})
    return messages


def build_grade_messages(
    question: str,
    reference_answer: str,
    user_answer: str,
) -> list[dict]:
    """构造答题评分的 messages 列表。"""
    user_content = (
        f"题目：{_clip(question)}\n\n"
        f"参考答案：\n{_clip(reference_answer)}\n\n"
        f"学习者答案：\n{_clip(user_answer)}"
    )
    return [
        {"role": "system", "content": GRADE_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def parse_grade_response(text: str) -> dict:
    """解析评分回复为 {score, comment, gaps}，失败时抛 AiServiceError。"""
    cleaned = text.strip()
    # 容忍模型仍然输出 ```json 围栏
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AiServiceError(f"AI 评分结果不是合法 JSON：{cleaned[:200]}") from exc
    if not isinstance(data, dict):
        raise AiServiceError("AI 评分结果不是 JSON 对象")
    try:
        score = int(data["score"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AiServiceError("AI 评分结果缺少有效的 score 字段") from exc
    score = max(0, min(10, score))
    comment = str(data.get("comment", "")).strip()
    gaps_raw = data.get("gaps", [])
    gaps = [str(item).strip() for item in gaps_raw if str(item).strip()] if isinstance(gaps_raw, list) else []
    return {"score": score, "comment": comment, "gaps": gaps[:4]}


# ── HTTP 调用 ──

def _chat_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/chat/completions"


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _body(config: dict, messages: list[dict], stream: bool) -> dict:
    return {
        "model": config["model"],
        "messages": messages,
        "temperature": config.get("temperature", 0.3),
        "max_tokens": config.get("max_tokens", 2048),
        "stream": stream,
    }


def _classify_status_error(status_code: int, detail: str) -> AiServiceError:
    if status_code in (401, 403):
        return AiServiceError("AI 服务鉴权失败：请检查 API key 是否正确、是否过期")
    if status_code == 429:
        return AiServiceError("AI 服务限流：请求过于频繁，请稍后重试")
    return AiServiceError(f"AI 服务返回错误（HTTP {status_code}）：{detail[:200]}")


async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
    """流式调用 chat/completions，逐段产出增量文本。"""
    config, api_key = require_config()
    timeout = config.get("timeout_seconds", 90)
    try:
        async with httpx2.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                _chat_url(config["base_url"]),
                headers=_headers(api_key),
                json=_body(config, messages, stream=True),
            ) as response:
                if response.status_code != 200:
                    detail = (await response.aread()).decode("utf-8", errors="replace")
                    raise _classify_status_error(response.status_code, detail)
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        return
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = (choices[0].get("delta") or {}).get("content")
                    if delta:
                        yield delta
    except httpx2.TimeoutException as exc:
        raise AiServiceError("AI 服务响应超时：请检查网络或调大 timeout_seconds") from exc
    except httpx2.HTTPError as exc:
        raise AiServiceError(f"无法连接 AI 服务：{exc}") from exc


async def complete_chat(messages: list[dict]) -> str:
    """非流式调用 chat/completions，返回完整回复文本。"""
    config, api_key = require_config()
    timeout = config.get("timeout_seconds", 90)
    try:
        async with httpx2.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                _chat_url(config["base_url"]),
                headers=_headers(api_key),
                json=_body(config, messages, stream=False),
            )
    except httpx2.TimeoutException as exc:
        raise AiServiceError("AI 服务响应超时：请检查网络或调大 timeout_seconds") from exc
    except httpx2.HTTPError as exc:
        raise AiServiceError(f"无法连接 AI 服务：{exc}") from exc
    if response.status_code != 200:
        raise _classify_status_error(response.status_code, response.text)
    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AiServiceError("AI 服务返回格式异常：缺少 choices[0].message.content") from exc
    return str(content)


async def grade_answer(
    question: str,
    reference_answer: str,
    user_answer: str,
) -> dict:
    """调用 LLM 评分并解析为结构化结果。"""
    messages = build_grade_messages(question, reference_answer, user_answer)
    reply = await complete_chat(messages)
    return parse_grade_response(reply)
