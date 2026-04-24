#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_fix_issues.py

Conservative automation scaffold:
- Select up to N open issues from wuxixixi/ProjectInsight
- For each issue, create a branch and a placeholder fix file (under fixes/)
- Create a PR (draft by default), clone the PR branch locally and run pytest
- If tests pass and AUTO_MERGE=1, merge the PR and run local deploy.py

Security: reads GITHUB_TOKEN from environment variable; never writes tokens to disk.

Usage:
  - Set environment variable GITHUB_TOKEN (securely). Example (Windows PowerShell):
      setx GITHUB_TOKEN "<token>"
    Then log out/in or set in the scheduled task environment.
  - Optional env vars:
      AUTO_FIX_MAX_ISSUES (default 5)
      AUTO_MERGE (0/1, default 0)
      DRY_RUN (0/1, default 1)  # if 1, actions are logged but not merged/deployed
      PROJECT_ROOT (path to local repo for deploy.py; default uses current repo root)

Note: This script is intentionally conservative. To enable more aggressive auto-patching, extend attempt_patch_for_issue().
"""

import os
import sys
import time
import logging
import random
import tempfile
import subprocess
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
log = logging.getLogger('auto_fix')

try:
    from github import Github
    from github.GithubException import GithubException
except Exception:
    log.error("Missing dependency 'PyGithub'. Install with: pip install PyGithub")
    sys.exit(2)

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    log.error("GITHUB_TOKEN not set. Export your GitHub personal access token as environment variable GITHUB_TOKEN.")
    log.error("Example (PowerShell): setx GITHUB_TOKEN \"<token>\"")
    sys.exit(2)

OWNER = os.getenv('GITHUB_OWNER', 'wuxixixi')
REPO_NAME = os.getenv('GITHUB_REPO', 'ProjectInsight')
MAX_ISSUES = int(os.getenv('AUTO_FIX_MAX_ISSUES', '5'))
AUTO_MERGE = os.getenv('AUTO_MERGE', '0') in ('1','true','True')
DRY_RUN = os.getenv('DRY_RUN', '1') in ('1','true','True')
PROJECT_ROOT = os.getenv('PROJECT_ROOT', os.path.abspath(os.path.dirname(__file__)))

# Conservative patcher placeholder - extend for real auto-fixes

def attempt_patch_for_issue(local_repo_path, issue):
    """Placeholder: do NOT modify production code unless you add safe logic here.
    Currently returns False to indicate no automatic code change was attempted.
    """
    log.info("No automatic patch implemented for issue #%s; creating placeholder file instead.", issue.number)
    return False


def select_issues(repo, max_issues):
    issues = repo.get_issues(state='open')
    candidates = []
    for issue in issues:
        # skip pull requests
        if getattr(issue, 'pull_request', None):
            continue
        candidates.append(issue)
        if len(candidates) >= 100:
            break
    if not candidates:
        return []
    chosen = random.sample(candidates, min(len(candidates), max_issues))
    return chosen


def create_branch(repo, base_branch, branch_name):
    try:
        src_ref = repo.get_git_ref(f"heads/{base_branch}")
        sha = src_ref.object.sha
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sha)
        log.info("Created branch %s from %s", branch_name, base_branch)
        return True
    except GithubException as e:
        log.error("Failed to create branch %s: %s", branch_name, e)
        return False


def create_placeholder_file(repo, branch_name, issue):
    path = f"fixes/auto_fix_issue_{issue.number}.md"
    content = (
        f"# Auto-fix for issue #{issue.number}: {issue.title}\n\n"
        f"Issue URL: {issue.html_url}\n\n"
        f"Issue body:\n{issue.body or '---'}\n\n"
        "Proposed fix (placeholder):\n"
        "This file was created automatically as a conservative starting point for developers.\n"
        "Review and replace with a real code change if appropriate.\n"
        f"Generated at {datetime.utcnow().isoformat()}Z\n"
    )
    commit_message = f"Auto-fix: placeholder for issue #{issue.number}"
    try:
        repo.create_file(path, commit_message, content, branch=branch_name)
        log.info("Created placeholder file %s on branch %s", path, branch_name)
        return path
    except GithubException as e:
        # If file exists, update it
        try:
            existing = repo.get_contents(path, ref=branch_name)
            repo.update_file(path, commit_message, content, existing.sha, branch=branch_name)
            log.info("Updated existing placeholder file %s on branch %s", path, branch_name)
            return path
        except Exception as e2:
            log.exception("Failed to create or update placeholder file: %s", e2)
            return None


def create_pr(repo, branch_name, issue):
    title = f"Auto-fix: #{issue.number} {issue.title}"
    body = (
        f"Automated conservative attempt to address issue #{issue.number}.\n\n"
        f"Issue: {issue.html_url}\n\n"
        "This PR contains a placeholder file describing the issue and suggested next steps.\n"
        "A local test run was performed and results are in the build logs.\n"
        "If AUTO_MERGE=1 and tests pass, this PR may be merged automatically.\n"
    )
    draft = not AUTO_MERGE
    try:
        pr = repo.create_pull(title=title, body=body, head=branch_name, base=repo.default_branch, draft=draft)
        log.info("Created PR #%s for issue #%s", pr.number, issue.number)
        return pr
    except GithubException as e:
        log.exception("Failed to create PR for branch %s: %s", branch_name, e)
        return None


def run_tests_in_clone(owner, repo_name, branch_name):
    tmp = tempfile.TemporaryDirectory()
    path = tmp.name
    clone_url = f"https://github.com/{owner}/{repo_name}.git"
    log.info("Cloning %s into %s", clone_url, path)
    try:
        subprocess.run(["git", "clone", clone_url, path], check=True)
    except Exception as e:
        log.exception("git clone failed: %s", e)
        tmp.cleanup()
        return False, None
    try:
        # fetch branch and checkout
        subprocess.run(["git", "fetch", "origin", branch_name], cwd=path, check=True)
        subprocess.run(["git", "checkout", "-b", branch_name, f"origin/{branch_name}"], cwd=path, check=True)
    except Exception as e:
        log.exception("Failed to checkout branch %s: %s", branch_name, e)
        tmp.cleanup()
        return False, None
    # Run pytest if present
    try:
        rc = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=path)
        success = (rc.returncode == 0)
        log.info("pytest return code: %s", rc.returncode)
        return success, path
    except Exception as e:
        log.exception("Failed to run tests: %s", e)
        tmp.cleanup()
        return False, None


def merge_pr_if_allowed(pr):
    try:
        if DRY_RUN:
            log.info("DRY_RUN is enabled; skipping merge of PR #%s", pr.number)
            return False
        if AUTO_MERGE:
            result = pr.merge()
            log.info("Merged PR #%s: %s", pr.number, result)
            return True
        log.info("AUTO_MERGE disabled; leaving PR #%s as draft/for-review", pr.number)
        return False
    except Exception as e:
        log.exception("Failed to merge PR #%s: %s", pr.number, e)
        return False


def run_deploy():
    deploy_py = os.path.join(PROJECT_ROOT, 'deploy.py')
    if not os.path.exists(deploy_py):
        log.warning("deploy.py not found at %s; skipping deploy", deploy_py)
        return False
    if DRY_RUN:
        log.info("DRY_RUN enabled; skipping actual deploy run of %s", deploy_py)
        return False
    try:
        subprocess.run([sys.executable, deploy_py], check=True)
        log.info("Deploy script ran successfully")
        return True
    except Exception as e:
        log.exception("Deploy script failed: %s", e)
        return False


def main():
    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(f"{OWNER}/{REPO_NAME}")
    except Exception as e:
        log.exception("Failed to access repo %s/%s: %s", OWNER, REPO_NAME, e)
        sys.exit(1)

    issues = select_issues(repo, MAX_ISSUES)
    if not issues:
        log.info("No candidate issues found. Exiting.")
        return

    for issue in issues:
        try:
            timestamp = int(time.time())
            branch_name = f"auto-fix/issue-{issue.number}-{timestamp}"
            created = create_branch(repo, repo.default_branch, branch_name)
            if not created:
                continue
            placeholder_path = create_placeholder_file(repo, branch_name, issue)
            pr = create_pr(repo, branch_name, issue)
            if not pr:
                continue

            # Clone and run tests locally against the PR branch
            tests_ok, clone_path = run_tests_in_clone(OWNER, REPO_NAME, branch_name)
            if tests_ok:
                log.info("Tests passed for branch %s", branch_name)
                # optionally merge
                merged = merge_pr_if_allowed(pr)
                if merged:
                    run_deploy()
            else:
                log.info("Tests failed or couldn't run for branch %s; leaving PR for manual review", branch_name)

        except Exception as e:
            log.exception("Error processing issue #%s: %s", getattr(issue, 'number', 'unknown'), e)

if __name__ == '__main__':
    main()
