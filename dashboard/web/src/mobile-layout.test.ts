import { describe, expect, it } from 'vitest';
// @ts-expect-error Vitest 运行在 Node 中，但前端 tsconfig 不加载 Node 类型。
import { readFileSync } from 'node:fs';

const css = readFileSync('src/index.css', 'utf8');

describe('移动端运行面板样式契约', () => {
  it('保留抽屉和展开按钮', () => {
    const start = css.indexOf('@media (max-width: 900px)');
    const end = css.indexOf('@media (max-width: 520px)', start);
    const mobileCss = css.slice(start, end);

    expect(mobileCss).not.toContain('.chapter-runner { display: none; }');
    expect(mobileCss).toContain('position: fixed');
    expect(mobileCss).toContain('.runner-float-toggle { display: flex; }');
  });
});
