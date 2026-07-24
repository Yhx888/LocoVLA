param([string]$Message = "checkpoint: 手动保存 v2 课程进度")
Write-Host "即将创建 checkpoint commit: $Message"
git status
git add -A
git commit -m $Message

