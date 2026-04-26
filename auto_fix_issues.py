#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hourly GitHub issue auto-fix runner for ProjectInsight.
"""

from __future__ import annotations

import json
import logging
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from github import Github
from github.GithubException import GithubException


LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "auto_fix.log"
WORK_ROOT = Path(__file__).resolve().parent / ".auto_fix_work"
WORK_ROOT.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path(__file__).resolve().parent / "reports" / "auto_fix"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def build_log_handlers() -> list[logging.Handler]:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(logging.FileHandler(LOG_PATH, encoding="utf-8"))
    except PermissionError:
        fallback = LOG_DIR / f"auto_fix_{time.strftime('%Y%m%d_%H%M%S')}.log"
        handlers.append(logging.FileHandler(fallback, encoding="utf-8"))
    return handlers


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=build_log_handlers(),
)
log = logging.getLogger("auto_fix")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "wuxixixi").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "ProjectInsight").strip()
AUTO_FIX_MAX_ISSUES = int(os.getenv("AUTO_FIX_MAX_ISSUES", "5"))
AUTO_FIX_TOP_POOL = int(os.getenv("AUTO_FIX_TOP_POOL", "15"))
AUTO_MERGE = os.getenv("AUTO_MERGE", "0").lower() in {"1", "true", "yes"}
DRY_RUN = os.getenv("DRY_RUN", "0").lower() in {"1", "true", "yes"}
DEPLOY_ON_SUCCESS = os.getenv("DEPLOY_ON_SUCCESS", "1").lower() in {"1", "true", "yes"}
PYTHON_BIN = os.getenv("PYTHON_BIN", sys.executable)
CODEX_BIN = os.getenv("CODEX_BIN", "codex")
DEFAULT_BRANCH = os.getenv("DEFAULT_BRANCH", "").strip()
PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY",
)


@dataclass
class IssueCandidate:
    number: int
    title: str
    body: str
    html_url: str
    labels: list[str]
    score: float


def now_stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def write_run_report(summaries: list[dict[str, object]], selected: list[IssueCandidate]) -> tuple[Path, Path]:
    stamp = now_stamp()
    json_path = REPORT_DIR / f"auto_fix_run_{stamp}.json"
    md_path = REPORT_DIR / f"auto_fix_run_{stamp}.md"

    selected_map = {issue.number: issue for issue in selected}
    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "owner": GITHUB_OWNER,
        "repo": GITHUB_REPO,
        "max_issues": AUTO_FIX_MAX_ISSUES,
        "selected_issues": [
            {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "labels": issue.labels,
                "score": issue.score,
            }
            for issue in selected
        ],
        "results": summaries,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    total = len(summaries)
    fixed = sum(1 for item in summaries if item.get("fixed"))
    validated = sum(1 for item in summaries if item.get("validated"))
    deployed = sum(1 for item in summaries if item.get("deployed"))

    lines = [
        "# Auto Fix Run Report",
        "",
        f"- Time: {payload['generated_at']}",
        f"- Repo: {GITHUB_OWNER}/{GITHUB_REPO}",
        f"- Selected: {total}",
        f"- Fixed: {fixed}",
        f"- Validated: {validated}",
        f"- Deployed: {deployed}",
        "",
        "## Issue Results",
        "",
    ]

    for item in summaries:
        issue_number = int(item["issue"])
        issue = selected_map.get(issue_number)
        title = issue.title if issue else ""
        lines.append(f"### #{issue_number} {title}".rstrip())
        if issue:
            lines.append(f"- URL: {issue.html_url}")
            lines.append(f"- Score: {issue.score:.1f}")
        lines.append(f"- Branch: {item.get('branch', '')}")
        lines.append(f"- Fixed: {item.get('fixed')}")
        lines.append(f"- Validated: {item.get('validated')}")
        lines.append(f"- Deployed: {item.get('deployed')}")
        pr_url = item.get("pr_url")
        lines.append(f"- PR: {pr_url if pr_url else 'N/A'}")
        errors = item.get("errors") or []
        if errors:
            lines.append(f"- Errors: {'; '.join(str(err) for err in errors)}")
        else:
            lines.append("- Errors: None")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    for key in PROXY_ENV_KEYS:
        env.pop(key, None)
    log.info("Run: %s", " ".join(args))
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        check=check,
        encoding="utf-8",
        errors="replace",
    )
    if result.stdout:
        log.info("stdout:\n%s", result.stdout[-4000:])
    if result.stderr:
        log.warning("stderr:\n%s", result.stderr[-4000:])
    return result


def git(args: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", "-c", f"safe.directory={cwd.as_posix()}", *args], cwd=cwd, check=check)


def score_issue(issue) -> float:
    labels = [label.name.lower() for label in issue.labels]
    score = 0.0
    score += min(issue.comments, 20) * 1.5
    score += sum(4 for label in labels if any(key in label for key in ("bug", "critical", "security", "high")))
    score += sum(2 for label in labels if any(key in label for key in ("backend", "frontend", "api", "regression")))
    score += min((time.time() - issue.created_at.timestamp()) / 86400.0, 10.0)
    if issue.assignees:
        score += 1
    return score


def collect_candidates(repo) -> list[IssueCandidate]:
    items: list[IssueCandidate] = []
    for issue in repo.get_issues(state="open", sort="updated", direction="desc"):
        if getattr(issue, "pull_request", None):
            continue
        items.append(
            IssueCandidate(
                number=issue.number,
                title=issue.title,
                body=issue.body or "",
                html_url=issue.html_url,
                labels=[label.name for label in issue.labels],
                score=score_issue(issue),
            )
        )
        if len(items) >= 50:
            break
    return items


def choose_issues(candidates: list[IssueCandidate]) -> list[IssueCandidate]:
    if not candidates:
        return []
    ranked = sorted(candidates, key=lambda item: item.score, reverse=True)
    pool = ranked[: max(1, min(len(ranked), AUTO_FIX_TOP_POOL))]
    return random.sample(pool, min(AUTO_FIX_MAX_ISSUES, len(pool)))


def clone_repo(temp_root: Path) -> Path:
    repo_dir = temp_root / GITHUB_REPO
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git"
    run(["git", "clone", clone_url, str(repo_dir)])
    return repo_dir


def detect_default_branch(repo_dir: Path) -> str:
    if DEFAULT_BRANCH:
        return DEFAULT_BRANCH
    result = git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo_dir)
    return result.stdout.strip().split("/")[-1]


def prepare_branch(repo_dir: Path, issue_number: int) -> str:
    default_branch = detect_default_branch(repo_dir)
    branch = f"auto-fix/issue-{issue_number}-{int(time.time())}"
    git(["config", "user.name", "ProjectInsight Auto Fix Bot"], cwd=repo_dir)
    git(["config", "user.email", "autofix@projectinsight.local"], cwd=repo_dir)
    git(["checkout", default_branch], cwd=repo_dir)
    git(["pull", "--ff-only", "origin", default_branch], cwd=repo_dir)
    git(["checkout", "-b", branch], cwd=repo_dir)
    return branch


def build_prompt(issue: IssueCandidate) -> str:
    payload = {
        "number": issue.number,
        "title": issue.title,
        "url": issue.html_url,
        "labels": issue.labels,
        "body": issue.body[:12000],
    }
    return (
        "Fix this GitHub issue in the current repository.\n"
        "Constraints:\n"
        "- Make a real code fix, not a placeholder.\n"
        "- Keep the change minimal and safe.\n"
        "- After editing, run targeted validation, then run pytest -q.\n"
        "- If frontend files changed or are affected, run npm run build in frontend.\n"
        "- Stop if no safe fix is possible.\n\n"
        f"Issue:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
    )


def run_codex_fix(repo_dir: Path, issue: IssueCandidate) -> bool:
    result = run(
        [
            CODEX_BIN,
            "exec",
            "--skip-git-repo-check",
            "--full-auto",
            "--output-last-message",
            str(repo_dir / "codex_last_message.txt"),
            build_prompt(issue),
        ],
        cwd=repo_dir,
        check=False,
    )
    return result.returncode == 0


def has_changes(repo_dir: Path) -> bool:
    status = git(["status", "--short"], cwd=repo_dir).stdout.strip()
    return bool(status)


def validate(repo_dir: Path) -> tuple[bool, list[str]]:
    failures: list[str] = []
    tests = run([PYTHON_BIN, "-m", "pytest", "-q"], cwd=repo_dir, check=False)
    if tests.returncode != 0:
        failures.append("pytest -q failed")

    frontend_dir = repo_dir / "frontend"
    if frontend_dir.exists() and (frontend_dir / "package.json").exists():
        build = run(["npm", "run", "build"], cwd=frontend_dir, check=False)
        if build.returncode != 0:
            failures.append("npm run build failed")

    return len(failures) == 0, failures


def commit_and_push(repo_dir: Path, issue: IssueCandidate, branch: str) -> bool:
    if DRY_RUN:
        return True
    git(["add", "-A"], cwd=repo_dir)
    commit = git(["commit", "-m", f"fix: resolve issue #{issue.number}"], cwd=repo_dir, check=False)
    combined = f"{commit.stdout}\n{commit.stderr}".lower()
    if commit.returncode != 0 and "nothing to commit" in combined:
        return False
    if commit.returncode != 0:
        raise RuntimeError(commit.stderr or commit.stdout)
    git(["push", "-u", "origin", branch], cwd=repo_dir)
    return True


def create_pr(repo_dir: Path, base_branch: str, issue: IssueCandidate, branch: str, failures: Iterable[str]) -> str | None:
    if DRY_RUN:
        return None
    body = [
        f"Fixes #{issue.number}",
        "",
        f"Issue: {issue.html_url}",
        "",
        "Validation:",
    ]
    if failures:
        body.extend(f"- {item}" for item in failures)
    else:
        body.extend(["- pytest -q", "- npm run build"])

    result = run(
        [
            "gh",
            "pr",
            "create",
            "--title",
            f"fix: issue #{issue.number} {issue.title}",
            "--body",
            "\n".join(body),
            "--base",
            base_branch,
            "--head",
            branch,
        ],
        cwd=repo_dir,
        check=False,
        extra_env={"GITHUB_TOKEN": GITHUB_TOKEN},
    )
    if result.returncode != 0:
        return None
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else None


def maybe_merge(repo_dir: Path, branch: str) -> None:
    if DRY_RUN or not AUTO_MERGE:
        return
    run(
        ["gh", "pr", "merge", branch, "--merge", "--auto"],
        cwd=repo_dir,
        check=False,
        extra_env={"GITHUB_TOKEN": GITHUB_TOKEN},
    )


def deploy_local(repo_dir: Path) -> bool:
    if not DEPLOY_ON_SUCCESS:
        return False
    deploy_script = repo_dir / "deploy.py"
    if not deploy_script.exists():
        return False
    result = run([PYTHON_BIN, str(deploy_script)], cwd=repo_dir, check=False)
    return result.returncode == 0


def process_issue(issue: IssueCandidate) -> dict[str, object]:
    temp_dir = WORK_ROOT / f"issue-{issue.number}-{int(time.time())}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        repo_dir = clone_repo(temp_dir)
        base_branch = detect_default_branch(repo_dir)
        branch = prepare_branch(repo_dir, issue.number)

        summary: dict[str, object] = {
            "issue": issue.number,
            "branch": branch,
            "fixed": False,
            "validated": False,
            "pr_url": None,
            "deployed": False,
            "errors": [],
        }

        if not run_codex_fix(repo_dir, issue):
            summary["errors"] = ["codex fix attempt failed"]
            return summary

        if not has_changes(repo_dir):
            summary["errors"] = ["no code changes produced"]
            return summary

        valid, failures = validate(repo_dir)
        summary["fixed"] = True
        summary["validated"] = valid
        summary["errors"] = failures
        if not valid:
            return summary

        if not commit_and_push(repo_dir, issue, branch):
            summary["errors"] = ["nothing to commit after validation"]
            return summary

        summary["pr_url"] = create_pr(repo_dir, base_branch, issue, branch, failures)
        maybe_merge(repo_dir, branch)
        summary["deployed"] = deploy_local(repo_dir)
        return summary
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> int:
    for key in PROXY_ENV_KEYS:
        os.environ.pop(key, None)

    if not GITHUB_TOKEN:
        log.error("GITHUB_TOKEN is not set.")
        return 2

    try:
        gh = Github(GITHUB_TOKEN)
        repo = gh.get_repo(f"{GITHUB_OWNER}/{GITHUB_REPO}")
    except GithubException as exc:
        log.error("Failed to access %s/%s: %s", GITHUB_OWNER, GITHUB_REPO, exc)
        return 1

    candidates = collect_candidates(repo)
    selected = choose_issues(candidates)
    if not selected:
        log.info("No issues selected.")
        return 0

    log.info("Selected issues: %s", ", ".join(f"#{item.number}" for item in selected))
    summaries: list[dict[str, object]] = []
    for issue in selected:
        try:
            summaries.append(process_issue(issue))
        except Exception as exc:
            log.exception("Issue #%s failed: %s", issue.number, exc)
            summaries.append(
                {
                    "issue": issue.number,
                    "fixed": False,
                    "validated": False,
                    "pr_url": None,
                    "deployed": False,
                    "errors": [str(exc)],
                }
            )

    summary_path = LOG_DIR / "auto_fix_summary.json"
    summary_path.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    report_json, report_md = write_run_report(summaries, selected)
    validated_count = sum(1 for item in summaries if item.get("validated"))
    log.info(
        "Validated %s/%s issue attempts. Summary saved to %s. Reports: %s, %s",
        validated_count,
        len(summaries),
        summary_path,
        report_json,
        report_md,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
