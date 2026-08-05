"""教程 qa 注释块格式校验（内容质量门禁）。

规则：
- `<!-- upkie-qa:ID -->` 与 `<!-- /upkie-qa -->` 必须成对闭合、不嵌套；
- ID 形如 `{章节id}-q{序号}`，前缀必须与所在章节目录一致；
- ID 全课程唯一；
- 答案正文非空。
随各批次答案撰写推进，本测试应始终保持全绿。
"""

import re

from upkie_mujoco_course.utils.paths import resolve_project_path

QA_OPEN = re.compile(r"<!--\s*upkie-qa:([^\s>]+)\s*-->")
QA_CLOSE = re.compile(r"<!--\s*/upkie-qa\s*-->")
QA_ID = re.compile(r"^([0-9]{2}|H[0-9]{2})-q[1-9][0-9]*$")
QA_BLOCK = re.compile(
    r"<!--\s*upkie-qa:([^\s>]+)\s*-->([\s\S]*?)<!--\s*/upkie-qa\s*-->"
)


def iter_tutorials():
    root = resolve_project_path("tutorials/v2")
    for readme in sorted(root.glob("*/README.md")):
        yield readme.parent.name, readme.read_text(encoding="utf-8")


def test_qa_comments_are_paired():
    for chapter, content in iter_tutorials():
        opens = len(QA_OPEN.findall(content))
        closes = len(QA_CLOSE.findall(content))
        assert opens == closes, (
            f"章节 {chapter}：upkie-qa 开始注释 {opens} 个、结束注释 {closes} 个，不成对"
        )
        # 成对匹配后不应残留孤立标记（防止嵌套或顺序错乱）
        leftover = QA_BLOCK.sub("", content)
        assert not QA_OPEN.search(leftover) and not QA_CLOSE.search(leftover), (
            f"章节 {chapter}：存在无法配对的 upkie-qa 注释（顺序或嵌套错误）"
        )


def test_qa_ids_match_chapter_and_are_unique():
    seen: dict[str, str] = {}
    for chapter, content in iter_tutorials():
        for match in QA_BLOCK.finditer(content):
            qa_id = match.group(1)
            assert QA_ID.match(qa_id), (
                f"章节 {chapter}：qa ID `{qa_id}` 不符合 `{{章节id}}-q{{序号}}` 约定"
            )
            prefix = qa_id.split("-q")[0]
            assert prefix == chapter, (
                f"章节 {chapter}：qa ID `{qa_id}` 前缀与章节目录不一致"
            )
            assert qa_id not in seen, (
                f"qa ID `{qa_id}` 重复出现（{seen[qa_id]} 与 {chapter}）"
            )
            seen[qa_id] = chapter


def test_qa_answers_not_empty():
    for chapter, content in iter_tutorials():
        for match in QA_BLOCK.finditer(content):
            answer = match.group(2).strip()
            assert answer, f"章节 {chapter}：qa `{match.group(1)}` 的答案正文为空"


def test_batch1_chapters_have_answers():
    """第 1 批（00~05）每章的复盘与面试小节应已配备 qa 答案块。"""
    root = resolve_project_path("tutorials/v2")
    for chapter in ["00", "01", "02", "03", "04", "05"]:
        content = (root / chapter / "README.md").read_text(encoding="utf-8")
        count = len(QA_BLOCK.findall(content))
        assert count >= 4, f"章节 {chapter}：qa 答案块只有 {count} 个，第 1 批要求已覆盖"
