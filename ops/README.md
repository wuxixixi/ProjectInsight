Operations and automation scripts live here.

Key entrypoints:
- `run_auto_fix.bat`: scheduled-task entrypoint for the GitHub issue auto-fix workflow
- `register_schtask.ps1`: registers the Windows scheduled task
- `auto_fix_issues.py`: auto-fix runner

These scripts assume the repository root is the parent directory of `ops/`.
