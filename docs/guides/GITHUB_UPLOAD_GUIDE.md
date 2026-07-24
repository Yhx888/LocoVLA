# GitHub 上传指南

## 已有 remote

```powershell
git remote -v
git push -u origin tutorial-restructure/upkie-mujoco-course
```

## 没有 remote 但有 GitHub CLI

```powershell
gh repo create <repo-name> --private --source . --remote origin --push
```

建议：新仓库默认使用 private，除非明确需要公开。
