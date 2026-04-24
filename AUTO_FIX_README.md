ProjectInsight 自动修复任务说明

概览

本项目包含一个保守的自动修复脚本 ops/auto_fix_issues.py 和一个帮助注册 Windows 计划任务的脚本 ops/register_schtask.ps1。脚本会：
- 每小时选取最多 5 个 open issues（随机）
- 为每个 issue 在远端分支创建一个占位修复文件（fixes/auto_fix_issue_<num>.md）并提交
- 创建 PR（默认为 draft）
- 在临时目录克隆仓库、检出 PR 分支并运行 pytest；若测试通过且 AUTO_MERGE=1 则尝试合并并运行本地 deploy.py

安全与安装

1) 不要把 Token 写入仓库。将你的 GitHub Personal Access Token 设为本机环境变量：
   在 PowerShell（以管理员身份）运行：
     setx GITHUB_TOKEN "<your_token>" /M
   或为当前用户运行（不带 /M）。

2) 安装必要依赖：
   pip install PyGithub

3) 可选环境变量：
   - GITHUB_OWNER（默认 wuxixixi）
   - GITHUB_REPO（默认 ProjectInsight）
   - AUTO_FIX_MAX_ISSUES（默认 5）
   - AUTO_MERGE（0/1，默认 0）
   - DRY_RUN（0/1，默认 1；1 表示只是演练，不会自动合并或部署）
   - PROJECT_ROOT（部署脚本 deploy.py 所在目录，默认为仓库根）

4) 注册计划任务（在本机运行）：
   - 编辑 ops/register_schtask.ps1，确保任务入口路径与当前环境一致
   - 以管理员身份打开 PowerShell，运行：
       .\ops\register_schtask.ps1

5) 首次运行（建议手动）：
   - 手动执行： python ops/auto_fix_issues.py
   - 检查输出日志、PR 链接与测试结果

注意

- 默认为保守模式：脚本不会自动修改源码，只会生成占位文件并创建 PR。若需要自动补丁逻辑，需要扩展 attempt_patch_for_issue()。
- 如果你希望在云端使用 GitHub Actions 而不是本地计划任务，请说明（注意：云端无法直接部署到本地，需使用自托管 runner）。
