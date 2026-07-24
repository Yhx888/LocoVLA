"""web schemas 类型契约测试。

覆盖 ChapterDto、ProgressRecord、RunPreset、RunRecord、RunEvent、ArtifactDto
六个 DTO 的必需字段、枚举值和实验完成字段只读语义。
"""

import pytest
from pydantic import ValidationError


class TestChapterDto:
    def test_required_fields(self):
        from upkie_mujoco_course.web.schemas import ChapterDto

        dto = ChapterDto(
            id="00",
            stage="0",
            stage_title="数学与工具",
            title="课程导航",
            task="了解课程结构",
            status="ready",
            prerequisites=[],
            content="# 课程导航\n\n欢迎学习。",
        )
        assert dto.id == "00"
        assert dto.stage == "0"
        assert dto.title == "课程导航"
        assert dto.status == "ready"

    def test_missing_required_raises(self):
        from upkie_mujoco_course.web.schemas import ChapterDto

        with pytest.raises(ValidationError):
            ChapterDto(title="无id的章节")

    def test_status_enum_valid_values(self):
        from upkie_mujoco_course.web.schemas import ChapterDto

        for status in ("ready", "planned"):
            dto = ChapterDto(
                id="00",
                stage="0",
                stage_title="数学",
                title="测试",
                task="测试",
                status=status,
                prerequisites=[],
                content="",
            )
            assert dto.status == status

    def test_reading_percent_default_zero(self):
        from upkie_mujoco_course.web.schemas import ChapterDto

        dto = ChapterDto(
            id="00",
            stage="0",
            stage_title="数学",
            title="测试",
            task="测试",
            status="ready",
            prerequisites=[],
            content="",
        )
        assert dto.reading_percent == 0
        assert dto.reading_complete is False

    def test_experiment_accepted_readonly(self):
        from upkie_mujoco_course.web.schemas import ChapterDto

        dto = ChapterDto(
            id="00",
            stage="0",
            stage_title="数学",
            title="测试",
            task="测试",
            status="ready",
            prerequisites=[],
            content="",
            experiment_accepted=True,
        )
        assert dto.experiment_accepted is True

    def test_completed_field(self):
        from upkie_mujoco_course.web.schemas import ChapterDto

        dto = ChapterDto(
            id="00",
            stage="0",
            stage_title="数学",
            title="测试",
            task="测试",
            status="ready",
            prerequisites=[],
            content="",
            completed=False,
        )
        assert dto.completed is False


class TestProgressRecord:
    def test_required_and_defaults(self):
        from upkie_mujoco_course.web.schemas import ProgressRecord

        record = ProgressRecord()
        assert record.reading_percent == 0
        assert record.reading_complete is False
        assert record.self_check_ids == []

    def test_update_reading_percent(self):
        from upkie_mujoco_course.web.schemas import ProgressRecord

        record = ProgressRecord(reading_percent=75, reading_complete=False)
        assert record.reading_percent == 75
        assert record.reading_complete is False

    def test_experiment_accepted_not_in_writable(self):
        from upkie_mujoco_course.web.schemas import ProgressRecord

        record = ProgressRecord(reading_percent=100, reading_complete=True)
        assert "experiment_accepted" not in type(record).model_fields


class TestRunPreset:
    def test_valid_preset(self):
        from upkie_mujoco_course.web.schemas import RunPreset

        preset = RunPreset(
            id="demo",
            label="快速演示",
            mode="demo",
            estimated_seconds=10,
            commands=["python scripts/course_checkpoint.py --chapter 00 --smoke"],
        )
        assert preset.id == "demo"
        assert preset.mode == "demo"
        assert preset.counts_for_acceptance is False

    def test_full_preset_counts_for_acceptance(self):
        from upkie_mujoco_course.web.schemas import RunPreset

        preset = RunPreset(
            id="full",
            label="正式运行",
            mode="full",
            estimated_seconds=300,
            commands=["python scripts/course_checkpoint.py --chapter 00"],
            counts_for_acceptance=True,
        )
        assert preset.counts_for_acceptance is True

    def test_mode_enum(self):
        from upkie_mujoco_course.web.schemas import RunPreset

        for mode in ("demo", "full"):
            preset = RunPreset(
                id=mode,
                label="测试",
                mode=mode,
                estimated_seconds=5,
                commands=["echo test"],
            )
            assert preset.mode == mode

    def test_commands_required(self):
        from upkie_mujoco_course.web.schemas import RunPreset

        with pytest.raises(ValidationError):
            RunPreset(id="demo", label="测试", mode="demo", estimated_seconds=5)


class TestRunRecord:
    def test_required_fields(self):
        from upkie_mujoco_course.web.schemas import RunRecord

        record = RunRecord(
            id="abc123",
            chapter_id="00",
            preset_id="demo",
            status="queued",
        )
        assert record.id == "abc123"
        assert record.status == "queued"

    def test_status_enum_valid(self):
        from upkie_mujoco_course.web.schemas import RunRecord

        for status in ("queued", "running", "succeeded", "failed", "cancelled"):
            record = RunRecord(
                id="x",
                chapter_id="00",
                preset_id="demo",
                status=status,
            )
            assert record.status == status

    def test_status_enum_invalid_raises(self):
        from upkie_mujoco_course.web.schemas import RunRecord

        with pytest.raises(ValidationError):
            RunRecord(id="x", chapter_id="00", preset_id="demo", status="invalid")


class TestRunEvent:
    def test_required_fields(self):
        from upkie_mujoco_course.web.schemas import RunEvent

        event = RunEvent(sequence=0, kind="stdout", text="hello")
        assert event.sequence == 0
        assert event.kind == "stdout"
        assert event.text == "hello"

    def test_kind_enum_valid(self):
        from upkie_mujoco_course.web.schemas import RunEvent

        for kind in ("stdout", "stderr", "status"):
            event = RunEvent(sequence=0, kind=kind, text="")
            assert event.kind == kind

    def test_kind_enum_invalid_raises(self):
        from upkie_mujoco_course.web.schemas import RunEvent

        with pytest.raises(ValidationError):
            RunEvent(sequence=0, kind="invalid", text="")


class TestArtifactDto:
    def test_required_fields(self):
        from upkie_mujoco_course.web.schemas import ArtifactDto

        artifact = ArtifactDto(
            path="results/checkpoint_00.json",
            type="application/json",
            size=1024,
        )
        assert artifact.path == "results/checkpoint_00.json"
        assert artifact.type == "application/json"
        assert artifact.size == 1024

    def test_evidence_validity_field(self):
        from upkie_mujoco_course.web.schemas import ArtifactDto

        artifact = ArtifactDto(
            path="results/checkpoint_00.json",
            type="application/json",
            size=1024,
            evidence_valid=True,
        )
        assert artifact.evidence_valid is True
