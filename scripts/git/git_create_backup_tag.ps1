param([string]$TagName = "backup-before-v2-manual-checkpoint")
Write-Host "准备创建备份 tag: $TagName"
git status
git tag $TagName
Write-Host "已创建 tag: $TagName"

