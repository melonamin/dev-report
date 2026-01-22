"""Repository discovery and configuration loading."""

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
import subprocess
import tomllib


CONFIG_PATH = Path.home() / ".config" / "dev-report" / "config.toml"


@dataclass
class Config:
    """Configuration for dev-report."""

    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    author_emails: list[str] = field(default_factory=list)


def load_config() -> Config:
    """Load configuration from ~/.config/dev-report/config.toml."""
    if not CONFIG_PATH.exists():
        return Config()

    try:
        with open(CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
        return Config(
            include=data.get("include", []),
            exclude=data.get("exclude", []),
            author_emails=data.get("author_emails", []),
        )
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"Error parsing config file {CONFIG_PATH}: {e}")


def get_git_user_email() -> str | None:
    """Get the user's email from git config."""
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except subprocess.CalledProcessError:
        return None


def get_author_emails(config: Config) -> list[str]:
    """Get list of author emails to filter by."""
    if config.author_emails:
        return config.author_emails

    email = get_git_user_email()
    if email:
        return [email]

    return []


def expand_path(path: str) -> Path:
    """Expand ~ and resolve path."""
    return Path(path).expanduser().resolve()


def matches_pattern(path: Path, pattern: str) -> bool:
    """Check if path matches a glob-like pattern."""
    pattern_expanded = str(expand_path(pattern))
    path_str = str(path)

    # Handle ** patterns
    if "**" in pattern_expanded:
        pattern_expanded = pattern_expanded.replace("**", "*")

    return fnmatch(path_str, pattern_expanded)


def find_repos(root: Path, config: Config) -> list[Path]:
    """Find all git repositories under root, applying config filters."""
    root = root.resolve()
    repos: list[Path] = []

    for git_dir in root.rglob(".git"):
        if not git_dir.is_dir():
            continue

        repo_path = git_dir.parent

        # Apply include filter (if specified, repo must match at least one)
        if config.include:
            if not any(matches_pattern(repo_path, p) for p in config.include):
                continue

        # Apply exclude filter
        if config.exclude:
            if any(matches_pattern(repo_path, p) for p in config.exclude):
                continue

        repos.append(repo_path)

    return sorted(repos)
