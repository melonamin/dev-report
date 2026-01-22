"""GitHub PR fetching via gh CLI."""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

from git import Repo
from git.exc import InvalidGitRepositoryError


@dataclass
class PRInfo:
    """Information about a pull request."""

    number: int
    title: str
    state: str
    created_at: datetime
    merged_at: datetime | None
    url: str


@dataclass
class RepoPRs:
    """PRs for a repository."""

    repo_path: Path
    repo_name: str
    owner: str
    prs_opened: list[PRInfo]
    prs_merged: list[PRInfo]
    error: str | None = None


_gh_available: bool | None = None
_gh_warning_shown: bool = False


def is_gh_available() -> bool:
    """Check if gh CLI is installed and authenticated."""
    global _gh_available

    if _gh_available is not None:
        return _gh_available

    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
        )
        _gh_available = result.returncode == 0
    except FileNotFoundError:
        _gh_available = False

    return _gh_available


def show_gh_warning() -> str | None:
    """Show warning about gh not being available (once)."""
    global _gh_warning_shown

    if _gh_warning_shown:
        return None

    _gh_warning_shown = True
    return "gh CLI not available or not authenticated - PR stats will be skipped"


def get_github_remote(repo_path: Path) -> tuple[str, str] | None:
    """Get GitHub owner/repo from a repository's remote."""
    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        return None

    for remote in repo.remotes:
        url = remote.url

        # Handle SSH URLs: git@github.com:owner/repo.git
        ssh_match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
        if ssh_match:
            return ssh_match.group(1), ssh_match.group(2)

        # Handle HTTPS URLs: https://github.com/owner/repo.git
        https_match = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
        if https_match:
            return https_match.group(1), https_match.group(2)

    return None


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string from GitHub API."""
    # Handle both 'Z' suffix and timezone offset
    dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str)


def fetch_prs(
    repo_path: Path,
    since: datetime,
) -> RepoPRs:
    """Fetch PRs for a repository using gh CLI."""
    result = RepoPRs(
        repo_path=repo_path,
        repo_name=repo_path.name,
        owner="",
        prs_opened=[],
        prs_merged=[],
    )

    if not is_gh_available():
        result.error = show_gh_warning()
        return result

    github_info = get_github_remote(repo_path)
    if not github_info:
        # Not a GitHub repo, skip silently
        return result

    owner, repo_name = github_info
    result.owner = owner
    result.repo_name = repo_name

    try:
        # Fetch PRs authored by the authenticated user (@me)
        cmd = [
            "gh", "pr", "list",
            "--repo", f"{owner}/{repo_name}",
            "--author", "@me",
            "--state", "all",
            "--json", "number,title,state,createdAt,mergedAt,url",
            "--limit", "100",
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            result.error = f"gh error: {proc.stderr.strip()}"
            return result

        prs_data = json.loads(proc.stdout) if proc.stdout.strip() else []

        for pr in prs_data:
            created_at = parse_datetime(pr["createdAt"])
            merged_at = parse_datetime(pr["mergedAt"]) if pr.get("mergedAt") else None

            pr_info = PRInfo(
                number=pr["number"],
                title=pr["title"][:80],
                state=pr["state"],
                created_at=created_at,
                merged_at=merged_at,
                url=pr["url"],
            )

            # Check if PR was opened in our time range
            if created_at >= since:
                result.prs_opened.append(pr_info)

            # Check if PR was merged in our time range
            if merged_at and merged_at >= since:
                result.prs_merged.append(pr_info)

    except json.JSONDecodeError as e:
        result.error = f"Failed to parse gh output: {e}"
    except Exception as e:
        result.error = str(e)

    return result
