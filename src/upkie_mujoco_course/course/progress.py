"""可恢复的课程检查点记录。"""

from __future__ import annotations

import json
from pathlib import Path


class CourseProgress:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"chapters": {}}

    def chapter_status(self, chapter_id: str) -> dict:
        return self.data["chapters"].get(
            chapter_id,
            {"completed_checkpoints": [], "evidence": []},
        )

    def complete_checkpoint(self, chapter_id: str, checkpoint: str, evidence: str) -> None:
        status = self.data["chapters"].setdefault(
            chapter_id,
            {"completed_checkpoints": [], "evidence": []},
        )
        if checkpoint not in status["completed_checkpoints"]:
            status["completed_checkpoints"].append(checkpoint)
            status["evidence"].append(evidence)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

