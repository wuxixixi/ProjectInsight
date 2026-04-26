@echo off
setlocal
REM GitHub Auto Fix scheduled task entrypoint

cd /d H:\ProjectInsight

if "%GITHUB_TOKEN%"=="" (
  echo [%date% %time%] GITHUB_TOKEN is not set.>> logs\auto_fix.log
  exit /b 2
)

set HTTP_PROXY=
set HTTPS_PROXY=
set ALL_PROXY=
set http_proxy=
set https_proxy=
set all_proxy=
set GIT_HTTP_PROXY=
set GIT_HTTPS_PROXY=

set GITHUB_OWNER=wuxixixi
set GITHUB_REPO=ProjectInsight
set AUTO_FIX_MAX_ISSUES=5
set AUTO_FIX_TOP_POOL=15
set AUTO_MERGE=0
set DRY_RUN=0
set DEPLOY_ON_SUCCESS=1

python auto_fix_issues.py >> logs\auto_fix_runner.log 2>&1
endlocal
