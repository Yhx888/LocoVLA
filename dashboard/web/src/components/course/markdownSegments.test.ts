import { describe, expect, it } from 'vitest';
import { extractQuestionBefore, parseMarkdownSegments } from './markdownSegments';

describe('parseMarkdownSegments 切段', () => {
  it('纯文本只产出一个 markdown 段', () => {
    expect(parseMarkdownSegments('# 标题\n\n正文')).toEqual([
      { type: 'markdown', content: '# 标题\n\n正文' },
    ]);
  });

  it('识别动画指令并保留前后 markdown', () => {
    const segments = parseMarkdownSegments('前文\n\n<!-- upkie-animation:pendulum-family -->\n\n后文');
    expect(segments).toEqual([
      { type: 'markdown', content: '前文\n\n' },
      { type: 'animation', id: 'pendulum-family' },
      { type: 'markdown', content: '\n\n后文' },
    ]);
  });

  it('识别 qa 成对注释并去除答案首尾空白', () => {
    const segments = parseMarkdownSegments(
      '1. 问题？\n\n<!-- upkie-qa:14-q1 -->\n答案含 $E = mc^2$ 公式\n<!-- /upkie-qa -->\n\n2. 下一题',
    );
    expect(segments).toEqual([
      { type: 'markdown', content: '1. 问题？\n\n' },
      { type: 'qa', id: '14-q1', answer: '答案含 $E = mc^2$ 公式' },
      { type: 'markdown', content: '\n\n2. 下一题' },
    ]);
  });

  it('动画与 qa 混排时按出现顺序切段', () => {
    const segments = parseMarkdownSegments(
      'A<!-- upkie-animation:demo -->B<!-- upkie-qa:00-q1 -->答<!-- /upkie-qa -->C',
    );
    expect(segments.map((s) => s.type)).toEqual([
      'markdown', 'animation', 'markdown', 'qa', 'markdown',
    ]);
  });

  it('未闭合的 qa 开始注释留在 markdown 段中', () => {
    const segments = parseMarkdownSegments('前<!-- upkie-qa:00-q1 -->没有结束注释');
    expect(segments).toEqual([
      { type: 'markdown', content: '前<!-- upkie-qa:00-q1 -->没有结束注释' },
    ]);
  });

  it('多个 qa 块各自独立匹配（非贪婪）', () => {
    const segments = parseMarkdownSegments(
      '<!-- upkie-qa:00-q1 -->答一<!-- /upkie-qa -->\n<!-- upkie-qa:00-q2 -->答二<!-- /upkie-qa -->',
    );
    const qa = segments.filter((s) => s.type === 'qa');
    expect(qa).toEqual([
      { type: 'qa', id: '00-q1', answer: '答一' },
      { type: 'qa', id: '00-q2', answer: '答二' },
    ]);
  });

  it('支持 H 章节 ID', () => {
    const segments = parseMarkdownSegments('<!-- upkie-qa:H01-q1 -->答<!-- /upkie-qa -->');
    expect(segments[0]).toEqual({ type: 'qa', id: 'H01-q1', answer: '答' });
  });
});

describe('extractQuestionBefore 题目提取', () => {
  it('从有序列表项提取题目文本', () => {
    expect(extractQuestionBefore('前文\n\n3. 为什么重力项会放大偏角？\n\n')).toBe(
      '为什么重力项会放大偏角？',
    );
  });

  it('去掉无序列表前缀与粗体标记', () => {
    expect(extractQuestionBefore('- **问题：什么是 LQR？**')).toBe('问题：什么是 LQR？');
  });

  it('空内容返回空串', () => {
    expect(extractQuestionBefore('\n\n  \n')).toBe('');
  });
});
