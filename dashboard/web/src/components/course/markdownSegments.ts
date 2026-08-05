// 教程 Markdown 指令切段：把整篇内容切成 markdown / animation / qa 三类段落。
// - <!-- upkie-animation:id -->            内嵌课程动画（单注释）
// - <!-- upkie-qa:id --> 答案 <!-- /upkie-qa -->  可折叠参考答案（成对注释）
// 未闭合的 upkie-qa 开始注释不匹配，会作为普通 HTML 注释留在 markdown 段中（渲染时不可见）。

export type MarkdownSegment =
  | { type: 'markdown'; content: string }
  | { type: 'animation'; id: string }
  | { type: 'qa'; id: string; answer: string };

const DIRECTIVE_PATTERN =
  /<!--\s*upkie-animation:([a-z0-9-]+)\s*-->|<!--\s*upkie-qa:([A-Za-z0-9-]+)\s*-->([\s\S]*?)<!--\s*\/upkie-qa\s*-->/g;

export function parseMarkdownSegments(content: string): MarkdownSegment[] {
  const segments: MarkdownSegment[] = [];
  let lastIndex = 0;
  DIRECTIVE_PATTERN.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = DIRECTIVE_PATTERN.exec(content)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'markdown', content: content.slice(lastIndex, match.index) });
    }
    if (match[1] !== undefined) {
      segments.push({ type: 'animation', id: match[1] });
    } else {
      segments.push({ type: 'qa', id: match[2], answer: match[3].trim() });
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < content.length) {
    segments.push({ type: 'markdown', content: content.slice(lastIndex) });
  }
  return segments;
}

// 从 qa 块前的 markdown 段提取题目文本：取最后一行非空内容，
// 去掉有序/无序列表前缀与粗体标记，供 AI 评分请求携带。
export function extractQuestionBefore(markdown: string): string {
  const lines = markdown.split('\n').map((line) => line.trim()).filter(Boolean);
  const last = lines[lines.length - 1];
  if (!last) return '';
  const listItem = last.match(/^(?:\d+[.)]|[-*])\s+(.*)$/);
  const text = listItem ? listItem[1] : last;
  return text.replace(/\*\*/g, '').trim();
}
