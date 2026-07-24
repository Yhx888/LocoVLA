"""web presets 测试。"""

import pytest
from upkie_mujoco_course.web.presets import (
    get_chapter_presets,
    validate_preset_args,
    validate_command,
)


class TestValidateCommand:
    def test_valid_python_script(self):
        assert validate_command("python scripts/course_checkpoint.py --chapter 00") is True

    def test_script_not_in_scripts_dir(self):
        assert validate_command("python src/main.py") is False

    def test_non_python_command(self):
        assert validate_command("bash run.sh") is False

    def test_shell_metacharacters_rejected(self):
        assert validate_command("python scripts/check.py ; rm -rf /") is False
        assert validate_command("python scripts/check.py && echo x") is False
        assert validate_command("python scripts/check.py | cat") is False

    def test_empty_command(self):
        assert validate_command("") is False


class TestGetChapterPresets:
    def test_ready_chapter_has_two_presets(self):
        presets = get_chapter_presets("00")
        assert len(presets) == 2
        ids = {p.id for p in presets}
        assert ids == {"demo", "full"}

    def test_demo_does_not_count_for_acceptance(self):
        presets = get_chapter_presets("00")
        demo = next(p for p in presets if p.id == "demo")
        assert demo.counts_for_acceptance is False
        assert demo.mode == "demo"

    def test_full_counts_for_acceptance(self):
        presets = get_chapter_presets("00")
        full = next(p for p in presets if p.id == "full")
        assert full.counts_for_acceptance is True
        assert full.mode == "full"

    def test_planned_chapter_has_no_presets(self):
        presets = get_chapter_presets("H02")
        assert len(presets) == 0

    def test_unknown_chapter_raises(self):
        with pytest.raises(ValueError):
            get_chapter_presets("XX")

    def test_demo_commands_safe(self):
        presets = get_chapter_presets("00")
        demo = next(p for p in presets if p.id == "demo")
        for cmd in demo.commands:
            assert validate_command(cmd), f"不安全命令: {cmd}"


class TestValidatePresetArgs:
    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError):
            validate_preset_args("00", "nonexistent")

    def test_planned_chapter_raises(self):
        with pytest.raises(ValueError):
            validate_preset_args("H02", "demo")

    def test_known_preset_returns_commands(self):
        cmds = validate_preset_args("00", "demo")
        assert len(cmds) > 0
