#!/usr/bin/env python3
"""
转换 tutorials/v2/*/README.md 中 ```text 公式块为 KaTeX $$...$$ 格式。

启发式判断：
- 含希腊字母名、^ 上标、[[ 矩阵、函数符号 → 数学公式，转 KaTeX
- 输出数据、中文说明、变量名解释 → 移除 ```text 包裹，保留纯文本
"""

import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TUTORIAL_DIR = PROJECT_ROOT / "tutorials" / "v2"

GREEK_MAP = {
    "alpha": "\\alpha", "beta": "\\beta", "gamma": "\\gamma",
    "delta": "\\delta", "epsilon": "\\epsilon", "zeta": "\\zeta",
    "eta": "\\eta", "theta": "\\theta", "iota": "\\iota",
    "kappa": "\\kappa", "lambda": "\\lambda", "mu": "\\mu",
    "nu": "\\nu", "xi": "\\xi", "omicron": "\\omicron",
    "pi": "\\pi", "rho": "\\rho", "sigma": "\\sigma",
    "tau": "\\tau", "upsilon": "\\upsilon", "phi": "\\phi",
    "chi": "\\chi", "psi": "\\psi", "omega": "\\omega",
    "Delta": "\\Delta", "Sigma": "\\Sigma", "Theta": "\\Theta",
    "Omega": "\\Omega", "Phi": "\\Phi", "Gamma": "\\Gamma",
    "Lambda": "\\Lambda", "Pi": "\\Pi",
}

MATH_FUNCS = {"sin", "cos", "tan", "cot", "sec", "csc",
              "sinh", "cosh", "tanh", "log", "ln", "exp",
              "det", "tr", "diag", "sqrt"}


def has_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def is_output_line(line):
    s = line.strip()
    if not s:
        return False
    if re.match(r'^[a-z_][a-z0-9_]*:\s*', s):
        return True
    if re.match(r'^[-+]?\d+\.?\d*(?:e[+-]?\d+)?(?:\s*[a-zA-Z/°^]+)?$', s):
        return True
    if re.match(r'^[a-zA-Z_]\w*\s*=\s*[-+]?\d+\.?\d*(?:e[+-]?\d+)?(?:\s*[a-zA-Z/°^]+)?$', s):
        return True
    if re.match(r'^\[[-+]?\d+\.?\d*(?:e[+-]?\d+)?(?:\s*,\s*[-+]?\d+\.?\d*(?:e[+-]?\d+)?)*\]\s*[a-zA-Z/°]*$', s):
        return True
    return False


def is_strong_math(text):
    if re.search(r'\^[T0-9{\[(]', text):
        return True
    if '[[' in text:
        return True
    if re.search(r'\b(sqrt|sum|int|prod|partial|exp|log|ln)\b', text):
        return True
    for name in GREEK_MAP:
        if re.search(r'\b' + name + r'\b', text):
            return True
    return False


def classify_section(lines):
    text = '\n'.join(lines).strip()
    if not text:
        return 'empty'

    if has_chinese(text):
        return 'text'

    if is_strong_math(text):
        return 'math'

    non_empty = [l for l in lines if l.strip()]
    if non_empty and all(is_output_line(l) for l in non_empty):
        return 'output'

    score = 1 if '=' in text else 0
    if re.search(r'\w\s*\*\s*\w', text):
        score += 2
    if '≈' in text:
        score += 2
    if re.search(r'\[', text):
        score += 1
    if re.search(r'\b[a-z]\(', text):
        score += 1
    if re.search(r'_', text):
        score += 1
    if re.search(r'[a-zA-Z0-9]\s*/\s*[a-zA-Z0-9]', text):
        score += 1
    if re.search(r'\.\.\.', text):
        score += 1
    if "'" in text:
        score += 1

    return 'math' if score >= 3 else 'text'


def convert_subscripts(text):
    def multi_sub(m):
        full = m.group(0)
        parts = full.split('_')
        base = parts[0]
        subs = parts[1:]
        tex = []
        for s in subs:
            if len(s) <= 2 and s.isalnum():
                tex.append(s)
            else:
                tex.append('\\text{' + s + '}')
        return base + '_{' + ','.join(tex) + '}'

    text = re.sub(r'\b[a-zA-Z]\w*(?:_[a-zA-Z0-9]+)+', multi_sub, text)
    text = re.sub(r'_\(([^)]+)\)', r'_{\1}', text)
    return text


def convert_matrix(text):
    text = re.sub(
        r'\[\[([\s\S]*?)\]\]',
        lambda m: m.group(0).replace('\n', ' '),
        text,
    )

    def bmatrix_repl(m):
        inner = m.group(1)
        rows = re.split(r'\],\s*\[', inner)
        tex_rows = []
        for row in rows:
            cells = [c.strip() for c in row.split(',')]
            tex_rows.append(' & '.join(cells))
        return ('\\begin{bmatrix}\n'
                + ' \\\\\n'.join(tex_rows)
                + '\n\\end{bmatrix}')

    text = re.sub(r'\[\[([^\]]+)\]\]', bmatrix_repl, text)
    return text


def convert_frac(text):
    def frac_repl(m):
        return '\\frac{' + m.group(1) + '}{' + m.group(2) + '}'

    text = re.sub(r'\b([a-zA-Z0-9])\s*/\s*([a-zA-Z0-9])\b', frac_repl, text)
    return text


def convert_math_text(text):
    text = convert_matrix(text)
    text = convert_subscripts(text)

    for name, cmd in sorted(GREEK_MAP.items(), key=lambda x: -len(x[0])):
        rep = cmd
        text = re.sub(r'\b' + name + r'\b', lambda m, r=rep: r, text)

    for func in MATH_FUNCS:
        rep = '\\' + func
        text = re.sub(r'\b' + func + r'\b', lambda m, r=rep: r, text)

    text = re.sub(r'(\w)\s*\*\s*(\w)', lambda m: m.group(1) + r' \cdot ' + m.group(2), text)
    text = re.sub(r'(\))\s*\*\s*(\w)', lambda m: m.group(1) + r' \cdot ' + m.group(2), text)
    text = re.sub(r'(\w)\s*\*\s*(\()', lambda m: m.group(1) + r' \cdot ' + m.group(2), text)

    text = text.replace('≈', '\\approx ')
    text = text.replace('±', '\\pm ')
    text = text.replace('→', '\\to ')
    text = text.replace('...', '\\dots')
    text = text.replace('||', '\\lVert ')
    text = text.replace('>=', '\\ge ')
    text = text.replace('<=', '\\le ')
    text = text.replace('!=', '\\ne ')

    text = re.sub(r'\bkp\b', lambda m: 'k_{p}', text)
    text = re.sub(r'\bkd\b', lambda m: 'k_{d}', text)

    text = convert_frac(text)

    return text


def format_non_math_section(lines):
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(.+)', stripped)
        if m and has_chinese(m.group(2)):
            result.append(f'- `${m.group(1)}` — {m.group(2).strip()}')
        else:
            result.append(stripped)
    return result


def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if '$$' in content:
        return 0, 0

    orig_lines = content.split('\n')
    new_lines = []
    i = 0
    math_count = 0
    text_count = 0

    while i < len(orig_lines):
        if orig_lines[i].strip() == '```text':
            block_lines = []
            i += 1
            while i < len(orig_lines) and orig_lines[i].strip() != '```':
                block_lines.append(orig_lines[i])
                i += 1
            # i 指向 ```
            i += 1

            if not block_lines:
                continue

            sections = []
            cur = []
            for line in block_lines:
                if not line.strip():
                    if cur:
                        sections.append(cur)
                        cur = []
                else:
                    cur.append(line)
            if cur:
                sections.append(cur)

            parts = []
            for sec_lines in sections:
                cls = classify_section(sec_lines)
                sec_text = '\n'.join(sec_lines)

                if cls == 'math':
                    converted = convert_math_text(sec_text)
                    parts.append('$$\n' + converted + '\n$$')
                    math_count += 1
                elif cls == 'output':
                    parts.extend(sec_lines)
                    text_count += 1
                else:
                    formatted = format_non_math_section(sec_lines)
                    parts.extend(formatted)
                    text_count += 1

            new_lines.extend(parts)
        else:
            new_lines.append(orig_lines[i])
            i += 1

    new_content = '\n'.join(new_lines)

    if new_content != content:
        shutil.copy2(filepath, filepath.with_suffix(filepath.suffix + '.bak'))

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return math_count, text_count


def main():
    files = sorted(TUTORIAL_DIR.glob('*/README.md'))
    total_files = 0
    total_math = 0
    total_text = 0
    skipped = 0

    for fp in files:
        rel = fp.relative_to(PROJECT_ROOT)
        print(f"[{rel}]")
        m, t = process_file(fp)
        if m == 0 and t == 0:
            skipped += 1
        else:
            total_files += 1
            total_math += m
            total_text += t
        print(f"   -> blocks: {m} math, {t} text")

    print(f"Scanned {len(files)} files, converted {total_files} ({skipped} skipped)")
    print(f"Math blocks: {total_math}, Text blocks: {total_text}")


if __name__ == '__main__':
    main()
