"""web API 请求与响应类型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ArtifactDto(BaseModel):
    path: str
    type: str
    size: int
    modified_at: str = ""
    url: str = ""
    evidence_valid: bool = False


class RunPreset(BaseModel):
    id: str
    label: str
    mode: Literal["demo", "full"]
    estimated_seconds: int = 60
    requires: list[str] = Field(default_factory=list)
    counts_for_acceptance: bool = False
    commands: list[str]


class ProgressRecord(BaseModel):
    reading_percent: int = Field(default=0, ge=0, le=100)
    reading_complete: bool = False
    self_check_ids: list[str] = Field(default_factory=list)


class ChapterDto(BaseModel):
    id: str
    stage: str
    stage_title: str
    title: str
    task: str = ""
    status: Literal["ready", "planned"]
    prerequisites: list[str] = Field(default_factory=list)
    content: str = ""
    reading_percent: int = 0
    reading_complete: bool = False
    self_check_ids: list[str] = Field(default_factory=list)
    self_check_items: list[dict] = Field(default_factory=list)
    experiment_accepted: bool = False
    completed: bool = False
    presets: list[RunPreset] = Field(default_factory=list)
    checkpoints: list[dict] = Field(default_factory=list)
    artifacts: list[ArtifactDto] = Field(default_factory=list)


class RunRecord(BaseModel):
    id: str
    chapter_id: str
    preset_id: str
    status: Literal[
        "queued", "running", "succeeded", "failed", "cancelled", "interrupted"
    ]
    created_at: str = ""
    finished_at: str = ""
    exit_code: int | None = None
    error_category: str | None = None


class RunEvent(BaseModel):
    run_id: str = ""
    sequence: int
    timestamp: str = ""
    kind: Literal["stdout", "stderr", "status"]
    stream: str = ""
    text: str
    status: str | None = None


class AiChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AiExplainRequest(BaseModel):
    chapter_id: str = ""
    chapter_title: str = ""
    selected_text: str = ""
    context: str = ""
    question: str = ""
    history: list[AiChatMessage] = Field(default_factory=list)


class AiGradeRequest(BaseModel):
    chapter_id: str = ""
    question_id: str = ""
    question: str
    reference_answer: str
    user_answer: str


class AiGradeResult(BaseModel):
    score: int = Field(ge=0, le=10)
    comment: str = ""
    gaps: list[str] = Field(default_factory=list)


class AiConfigRequest(BaseModel):
    """前端配置面板提交的 AI 服务配置。

    api_key 为空字符串表示保留服务器上已有的 key；base_url / model 为空时保留现值。
    """

    api_key: str = ""
    base_url: str = ""
    model: str = ""
    enabled: bool = True
