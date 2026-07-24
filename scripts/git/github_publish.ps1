Write-Host "GitHub 发布检查"
git status
Write-Host "当前分支:"
git branch --show-current
Write-Host "当前 remote:"
git remote -v
Write-Host "如 remote 已配置，可执行: git push -u origin (git branch --show-current)"
Write-Host "脚本不会使用 force push，也不会打印 token。"

