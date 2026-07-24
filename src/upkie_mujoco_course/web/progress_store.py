"""三层进度读写与完成判定。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from upkie_mujoco_course.utils.paths import resolve_project_path
from upkie_mujoco_course.web.schemas import ProgressRecord


class ProgressStore:
    def __init__(self, file_path: Path | str | None = None):
        if file_path is None:
            file_path = resolve_project_path("outputs", "web_progress.json")
        self.file_path = Path(file_path)
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.file_path.exists():
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        return {"chapters": {}}

    def _save(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def compute_self_check_ids(self, chapter_id: str, items: list[str]) -> list[str]:
        ids = []
        for item in items:
            hash_hex = hashlib.sha256(item.encode("utf-8")).hexdigest()[:12]
            ids.append(f"{chapter_id}-{hash_hex}")
        return ids

    def get_chapter_progress(self, chapter_id: str) -> ProgressRecord:
        ch = self._data.setdefault("chapters", {}).get(chapter_id, {})
        return ProgressRecord(
            reading_percent=ch.get("reading_percent", 0),
            reading_complete=ch.get("reading_complete", False),
            self_check_ids=list(ch.get("self_check_ids", [])),
        )

    def update_chapter_progress(
        self,
        chapter_id: str,
        reading_percent: int = 0,
        reading_complete: bool = False,
        self_check_ids: list[str] | None = None,
    ) -> ProgressRecord:
        chapters = self._data.setdefault("chapters", {})
        entry = chapters.setdefault(chapter_id, {})
        entry["reading_percent"] = max(entry.get("reading_percent", 0), reading_percent)
        entry["reading_complete"] = reading_complete
        if self_check_ids is not None:
            existing = set(entry.get("self_check_ids", []))
            entry["self_check_ids"] = sorted(existing | set(self_check_ids))
        self._save()
        return self.get_chapter_progress(chapter_id)

    def set_experiment_accepted(self, chapter_id: str, accepted: bool) -> None:
        chapters = self._data.setdefault("chapters", {})
        entry = chapters.setdefault(chapter_id, {})
        entry["experiment_accepted"] = accepted
        self._save()

    def is_chapter_completed(self, chapter_id: str) -> bool:
        ch = self._data.setdefault("chapters", {}).get(chapter_id, {})
        return bool(
            ch.get("reading_complete", False)
            and len(ch.get("self_check_ids", [])) > 0
            and ch.get("experiment_accepted", False)
        )
