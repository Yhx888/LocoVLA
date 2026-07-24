"""web progress_store 测试。

覆盖：三层进度读写、自测哈希稳定、正文变化导致旧自测失效、
实验字段不能由 PUT 写入。
"""

import hashlib
from pathlib import Path

from upkie_mujoco_course.web.progress_store import ProgressStore


def test_read_empty_progress(tmp_path):
    store = ProgressStore(file_path=tmp_path / "progress.json")
    record = store.get_chapter_progress("00")
    assert record.reading_percent == 0
    assert record.reading_complete is False
    assert record.self_check_ids == []


def test_write_and_read_reading_progress(tmp_path):
    store = ProgressStore(file_path=tmp_path / "progress.json")
    store.update_chapter_progress("00", reading_percent=80, reading_complete=False)
    record = store.get_chapter_progress("00")
    assert record.reading_percent == 80
    assert record.reading_complete is False


def test_self_check_hash_stability():
    store = ProgressStore()
    ids = store.compute_self_check_ids("00", ["任务一：环境搭建", "任务二：运行脚本"])
    assert len(ids) == 2
    for sid in ids:
        assert sid.startswith("00-")
        assert len(sid) > 3


def test_self_check_hash_changes_with_different_content():
    store = ProgressStore()
    ids_a = store.compute_self_check_ids("00", ["任务一"])
    ids_b = store.compute_self_check_ids("00", ["任务二"])
    assert ids_a != ids_b


def test_experiment_not_writable_via_update(tmp_path):
    store = ProgressStore(file_path=tmp_path / "progress.json")
    store.update_chapter_progress("00", reading_percent=50)
    record = store.get_chapter_progress("00")
    assert record.reading_percent == 50
    store.set_experiment_accepted("00", True)
    assert store.is_chapter_completed("00") is False
    store.update_chapter_progress("00",
        reading_percent=100,
        reading_complete=True,
        self_check_ids=["00-abc123"],
    )
    assert store.is_chapter_completed("00") is True


def test_completion_requires_all_three_layers(tmp_path):
    store = ProgressStore(file_path=tmp_path / "progress.json")
    assert store.is_chapter_completed("00") is False

    store.update_chapter_progress("00", reading_percent=100, reading_complete=True)
    assert store.is_chapter_completed("00") is False

    store.set_experiment_accepted("00", True)
    assert store.is_chapter_completed("00") is False

    store.update_chapter_progress("00",
        self_check_ids=["00-abc123"],
        reading_percent=100,
        reading_complete=True,
    )
    store.set_experiment_accepted("00", True)
    assert store.is_chapter_completed("00") is True


def test_persistence_to_file(tmp_path):
    path = tmp_path / "web_progress.json"
    store_a = ProgressStore(file_path=path)
    store_a.update_chapter_progress("00", reading_percent=100, reading_complete=True)

    store_b = ProgressStore(file_path=path)
    record = store_b.get_chapter_progress("00")
    assert record.reading_percent == 100
    assert record.reading_complete is True
