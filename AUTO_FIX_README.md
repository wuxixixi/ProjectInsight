# ProjectInsight Auto Fix

`auto_fix_issues.py` is a local maintenance script for selecting open GitHub issues,
attempting real fixes in a temporary clone, validating them, and optionally creating PRs.
`register_schtask.ps1` registers a Windows scheduled task to run it hourly.

## Current Behavior

The script currently does the following:

- Fetches open issues from `wuxixixi/ProjectInsight`
- Scores and randomly selects issues from the top candidate pool
- Clones the repository into a temporary working directory
- Creates a dedicated branch per issue
- Calls `codex exec --full-auto` with the issue payload
- Runs validation:
  - `pytest -q`
  - `npm run build` in `frontend/` if that directory exists
- Pushes the branch and creates a PR when validation passes
- Optionally attempts merge and local deployment
- Writes summary and per-run reports under `logs/` and `reports/auto_fix/`

This is not a placeholder PR generator anymore.

## Required Setup

1. Set `GITHUB_TOKEN` in the local environment.

PowerShell for the current user:

```powershell
setx GITHUB_TOKEN "<your_token>"
```

2. Install required Python dependencies.

```powershell
pip install -r requirements.txt
```

3. Ensure these tools are available in `PATH` when you use the full workflow:

- `git`
- `python`
- `codex`
- `gh`
- `npm`

## Main Environment Variables

- `GITHUB_OWNER`: defaults to `wuxixixi`
- `GITHUB_REPO`: defaults to `ProjectInsight`
- `AUTO_FIX_MAX_ISSUES`: max selected issues per run, default `5`
- `AUTO_FIX_TOP_POOL`: candidate pool size before random selection, default `15`
- `AUTO_MERGE`: `1` to allow merge attempts after PR creation
- `DRY_RUN`: `1` to skip push and PR creation
- `DEPLOY_ON_SUCCESS`: `1` to run local deployment when validation passes
- `PYTHON_BIN`: Python executable path override
- `CODEX_BIN`: Codex executable path override
- `DEFAULT_BRANCH`: override default branch detection

## Manual Run

```powershell
python auto_fix_issues.py
```

Outputs:

- `logs/auto_fix.log`
- `logs/auto_fix_summary.json`
- `reports/auto_fix/auto_fix_run_*.json`
- `reports/auto_fix/auto_fix_run_*.md`

## Scheduled Task

Register the Windows task:

```powershell
.\register_schtask.ps1
```

The current task registration uses:

- hourly repetition
- restart on failure
- ignore overlapping runs
- two-hour execution limit

## Notes

- The script clears proxy-related environment variables before network operations.
- Validation failure stops PR creation for that issue.
- Generated logs and reports are local artifacts and should not be committed.
