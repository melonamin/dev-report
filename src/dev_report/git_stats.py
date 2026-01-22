"""Git repository statistics using gitpython."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from git import Repo
from git.exc import InvalidGitRepositoryError


@dataclass
class CommitInfo:
    """Information about a single commit."""

    sha: str
    message: str
    author_email: str
    authored_date: datetime
    lines_added: int
    lines_removed: int
    files_changed: int


@dataclass
class RepoStats:
    """Statistics for a single repository."""

    path: Path
    name: str
    commits: list[CommitInfo] = field(default_factory=list)
    error: str | None = None

    @property
    def total_commits(self) -> int:
        return len(self.commits)

    @property
    def lines_added(self) -> int:
        return sum(c.lines_added for c in self.commits)

    @property
    def lines_removed(self) -> int:
        return sum(c.lines_removed for c in self.commits)

    @property
    def files_changed(self) -> int:
        # This is an approximation - same file in multiple commits counts multiple times
        return sum(c.files_changed for c in self.commits)


def get_commit_stats(commit) -> tuple[int, int, int]:
    """Get lines added, removed, and files changed for a commit."""
    try:
        stats = commit.stats.total
        return stats.get("insertions", 0), stats.get("deletions", 0), stats.get("files", 0)
    except Exception:
        return 0, 0, 0


def analyze_repo(
    repo_path: Path,
    author_emails: list[str],
    since: datetime,
) -> RepoStats:
    """Analyze a git repository for commits by specified authors since a date."""
    stats = RepoStats(path=repo_path, name=repo_path.name)

    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        stats.error = "Not a valid git repository"
        return stats

    if repo.bare:
        stats.error = "Bare repository"
        return stats

    # Normalize author emails for comparison
    author_emails_lower = [e.lower() for e in author_emails]

    try:
        # Get commits since the date
        for commit in repo.iter_commits(since=since.isoformat()):
            commit_email = commit.author.email.lower() if commit.author.email else ""

            # Filter by author
            if author_emails_lower and commit_email not in author_emails_lower:
                continue

            # Get commit timestamp
            authored_date = datetime.fromtimestamp(
                commit.authored_date,
                tz=timezone.utc,
            )

            # Skip if before our since date (iter_commits since can be approximate)
            if authored_date < since:
                continue

            lines_added, lines_removed, files_changed = get_commit_stats(commit)

            stats.commits.append(
                CommitInfo(
                    sha=commit.hexsha[:8],
                    message=commit.message.split("\n")[0][:80],
                    author_email=commit.author.email or "",
                    authored_date=authored_date,
                    lines_added=lines_added,
                    lines_removed=lines_removed,
                    files_changed=files_changed,
                )
            )
    except Exception as e:
        stats.error = str(e)

    return stats
