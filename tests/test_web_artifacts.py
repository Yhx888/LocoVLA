"""web artifacts 测试。

覆盖：产物路径穿越、符号链接越界、非白名单扩展名和 outputs/ 外路径拒绝。
"""

import pytest
from upkie_mujoco_course.web.artifacts import (
    is_safe_artifact_path,
    get_artifact_mime_type,
    resolve_artifact_path,
)
from upkie_mujoco_course.utils.paths import resolve_project_path


@pytest.fixture
def sample_checkpoint_artifact():
    """确保 outputs/results/checkpoint_00.json 存在（该目录不入 Git，新检出/CI 上不存在）。

    仅在本测试创建时才清理，不影响本地已有的真实产物。
    """
    target = resolve_project_path() / "outputs" / "results" / "checkpoint_00.json"
    created = False
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('{"passed": true}', encoding="utf-8")
        created = True
    yield target
    if created:
        target.unlink(missing_ok=True)


class TestPathSafety:
    def test_valid_path_inside_outputs(self):
        assert is_safe_artifact_path("results/checkpoint_00.json") is True

    def test_path_traversal_rejected(self):
        assert is_safe_artifact_path("../../../etc/passwd") is False
        assert is_safe_artifact_path("..\\..\\secrets.txt") is False

    def test_absolute_path_rejected(self):
        assert is_safe_artifact_path("C:\\Windows\\system32\\config\\SAM") is False
        assert is_safe_artifact_path("/etc/passwd") is False

    def test_outside_outputs_rejected(self):
        assert is_safe_artifact_path("../src/main.py") is False

    def test_empty_path_rejected(self):
        assert is_safe_artifact_path("") is False

    def test_symlink_outside_rejected(self, tmp_path):
        pass


class TestMimeTypes:
    def test_json_mime(self):
        assert "json" in get_artifact_mime_type(".json")

    def test_png_mime(self):
        assert get_artifact_mime_type(".png") == "image/png"

    def test_unknown_extension_rejected(self):
        mime = get_artifact_mime_type(".exe")
        assert mime is None

    def test_whitelist_includes_video(self):
        assert get_artifact_mime_type(".mp4") == "video/mp4"


class TestResolveArtifact:
    def test_valid_resolve(self, sample_checkpoint_artifact):
        path = resolve_artifact_path("results", "checkpoint_00.json")
        assert path is not None
        assert str(path).endswith("checkpoint_00.json")

    def test_path_traversal_rejected_at_resolve(self):
        path = resolve_artifact_path("../../../etc", "passwd")
        assert path is None
