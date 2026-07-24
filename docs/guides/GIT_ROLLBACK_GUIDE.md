# Git 回滚指南

## 查看当前状态

```powershell
git status
git log --oneline --decorate -n 20
```

## 回到重构前状态

```powershell
git checkout backup-before-v2-rebuild-20260530
```

## 从 tag 新建分支

```powershell
git checkout -b restore-before-v2 backup-before-v2-rebuild-20260530
```

## 回滚最近一次 commit，但保留文件改动

```powershell
git reset --soft HEAD~1
```

## 放弃某个文件的改动

```powershell
git restore path/to/file.py
```

注意：此操作不可逆，请谨慎使用。
