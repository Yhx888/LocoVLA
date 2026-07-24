"""临时工具：统计有真实证据的关卡。"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
results_dir = root / "outputs" / "results"
files = sorted(results_dir.glob("*.json"))
passed = 0
total = 0
ids_with_evidence = set()
for f in files:
    d = json.loads(f.read_text(encoding="utf-8-sig"))
    if not isinstance(d, dict):
        continue
    total += 1
    cid = str(d.get("chapter_id", ""))
    if d.get("passed") and not d.get("config", {}).get("inject_fault"):
        passed += 1
        ids_with_evidence.add(cid)

# 也检查 manifest ready 数
import sys
sys.path.insert(0, str(root / 'src'))
from upkie_mujoco_course.course.manifest import load_course_manifest
manifest = load_course_manifest()
ready_count = sum(1 for ch in manifest["chapters"] if ch["status"] == "ready")
total_chapters = len(manifest["chapters"])

print(f"结果文件总数: {total}")
print(f"通过数: {passed}")
print(f"有证据关卡数: {len(ids_with_evidence)}")
print(f"有证据关卡ID: {sorted(ids_with_evidence)}")
print(f"manifest 总关卡: {total_chapters}")
print(f"manifest ready: {ready_count}")
