"""结构化预设加载、manifest 命令校验和 argv 生成。"""

from __future__ import annotations

from upkie_mujoco_course.course.manifest import load_course_manifest
from upkie_mujoco_course.utils.config import load_json_config
from upkie_mujoco_course.web.schemas import RunPreset


def load_presets_config() -> dict:
    """加载 web_run_presets.json 配置。"""
    return load_json_config("configs/course/web_run_presets.json")


def get_chapter_presets(chapter_id: str) -> list[RunPreset]:
    """返回指定章节的所有运行预设。"""
    manifest = load_course_manifest()
    by_id = {ch["id"]: ch for ch in manifest["chapters"]}

    if chapter_id not in by_id:
        raise ValueError(f"未知章节: {chapter_id}")

    chapter = by_id[chapter_id]
    presets_config = load_presets_config()
    defaults = presets_config.get("defaults", {})
    chapter_overrides = presets_config.get("chapters", {}).get(chapter_id, {})

    presets: list[RunPreset] = []

    if chapter["status"] != "ready":
        return presets

    # demo 预设
    demo_override = chapter_overrides.get("demo", {})
    demo_command = demo_override.get(
        "command_pattern",
        defaults["demo"]["command_pattern"],
    ).format(chapter_id=chapter_id)
    demo_seconds = demo_override.get(
        "estimated_seconds",
        defaults["demo"]["estimated_seconds"],
    )
    presets.append(RunPreset(
        id="demo",
        label="快速演示",
        mode="demo",
        estimated_seconds=demo_seconds,
        counts_for_acceptance=False,
        commands=[demo_command],
    ))

    # full 预设
    full_override = chapter_overrides.get("full", {})
    full_seconds = full_override.get(
        "estimated_seconds",
        defaults["full"]["estimated_seconds"],
    )
    full_commands = chapter.get("commands", [])
    if not full_commands:
        full_commands = [f"python scripts/course_checkpoint.py --chapter {chapter_id}"]

    presets.append(RunPreset(
        id="full",
        label="正式运行",
        mode="full",
        estimated_seconds=full_seconds,
        counts_for_acceptance=True,
        commands=full_commands,
    ))

    return presets


def validate_command(command: str) -> bool:
    """校验命令是否安全：必须在 scripts/ 目录内。"""
    import re

    parts = command.strip().split()
    if not parts:
        return False

    script = parts[0]
    if script not in ("python", "python3", "py"):
        return False

    if len(parts) < 2:
        return False

    arg = parts[1]
    if not arg.startswith("scripts/"):
        return False

    if not arg.endswith(".py"):
        return False

    forbidden = {"&&", ";", "|", "$(", "`", "<", ">", "&", "\n", "\r"}
    for ch in forbidden:
        if ch in command:
            return False

    return True


def validate_preset_args(chapter_id: str, preset_id: str) -> list[str]:
    """返回受控的预设命令列表，未注册时抛出异常。"""
    presets = get_chapter_presets(chapter_id)
    for preset in presets:
        if preset.id == preset_id:
            for cmd in preset.commands:
                if not validate_command(cmd):
                    raise ValueError(f"命令未通过安全校验: {cmd}")
            return list(preset.commands)
    raise ValueError(f"章节 {chapter_id} 无预设 {preset_id}")
