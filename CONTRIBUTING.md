# Contributing to Praxis · 参与贡献

Thanks for your interest in **Praxis**! Contributions of all kinds are welcome — bug reports, fixes, new lessons, docs, and tests.

感谢你对 **Praxis** 的关注！欢迎任何形式的贡献 —— 缺陷报告、修复、新课程、文档和测试。

---

## English

### Getting started

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python scripts/01_check_model.py     # audit the robot model
pytest                               # run the test suite
```

### Ground rules

- **Keep it simple.** Prefer readable code over clever abstractions; complex logic lives in `src/`, `scripts/` are thin entry points.
- **Runnable first.** Make a tutorial or feature run correctly before optimizing the algorithm.
- **Evidence discipline.** Fixed-seed experiments must be reproducible. Never hide failures, inflate results, or bypass pass criteria. Acceptance is decided by `pytest`, not by loosening thresholds by hand.
- **Paths.** Use `pathlib.Path`; never hard-code absolute paths.
- **Model changes.** After editing the robot model, run `python scripts/11_model_contract_lab.py` and keep docs in sync.

### Pull request workflow

1. Fork the repo and create a branch (`feat/...`, `fix/...`, `docs/...`).
2. Make your change; add or update tests under `tests/`.
3. Run `pytest` locally — it must pass.
4. Open a PR describing **what** changed and **why**, and link any related issue.
5. Keep PRs focused and reasonably small.

---

## 简体中文

### 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python scripts/01_check_model.py     # 审计机器人模型
pytest                               # 运行测试套件
```

### 基本规则

- **保持简洁**：可读优先，避免过度封装；复杂逻辑放 `src/`，`scripts/` 只做入口。
- **先能跑**：先让教程/功能正确运行，再优化算法。
- **证据原则**：固定 seed 实验必须可复现；不隐藏失败、不夸大效果、不绕过通过条件。验收由 `pytest` 判定，不做人工放宽阈值。
- **路径**：统一用 `pathlib.Path`，不要写死绝对路径。
- **改模型**：修改机器人模型后必须运行 `python scripts/11_model_contract_lab.py`，并同步更新文档。

### PR 流程

1. Fork 仓库并新建分支（`feat/...`、`fix/...`、`docs/...`）。
2. 完成改动，在 `tests/` 下新增或更新测试。
3. 本地跑 `pytest`，必须通过。
4. 提交 PR，说明**改了什么**和**为什么改**，并关联相关 issue。
5. PR 保持聚焦、体量适中。

---

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

提交贡献即表示你同意你的贡献以 [MIT 许可证](LICENSE) 授权。
