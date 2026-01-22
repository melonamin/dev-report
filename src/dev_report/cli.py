"""CLI entrypoint for dev-report."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .discovery import find_repos, get_author_emails, load_config
from .git_stats import RepoStats, analyze_repo
from .github_prs import RepoPRs, fetch_prs, is_gh_available
from .report import PeriodStats, render_report


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate daily/weekly/monthly dev activity reports",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan for git repos (default: current directory)",
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="Only show last 24 hours",
    )
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="Only show last 7 days",
    )
    parser.add_argument(
        "--monthly",
        action="store_true",
        help="Only show last 30 days",
    )

    return parser.parse_args()


def get_periods(args: argparse.Namespace) -> list[tuple[str, datetime]]:
    """Get time periods to report on based on arguments."""
    now = datetime.now(timezone.utc)

    all_periods = [
        ("Last 24 Hours", now - timedelta(hours=24)),
        ("Last 7 Days", now - timedelta(days=7)),
        ("Last 30 Days", now - timedelta(days=30)),
    ]

    # If specific period requested, filter
    if args.daily:
        return [all_periods[0]]
    if args.weekly:
        return [all_periods[1]]
    if args.monthly:
        return [all_periods[2]]

    return all_periods


def analyze_repos_parallel(
    repos: list[Path],
    author_emails: list[str],
    since: datetime,
    console: Console,
) -> list[RepoStats]:
    """Analyze multiple repos in parallel."""
    results: list[RepoStats] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Analyzing repos...", total=len(repos))

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(analyze_repo, repo, author_emails, since): repo
                for repo in repos
            }

            for future in as_completed(futures):
                results.append(future.result())
                progress.advance(task)

    return results


def fetch_prs_parallel(
    repos: list[Path],
    since: datetime,
    console: Console,
) -> list[RepoPRs]:
    """Fetch PRs for multiple repos in parallel."""
    if not is_gh_available():
        return [RepoPRs(repo_path=r, repo_name=r.name, owner="", prs_opened=[], prs_merged=[]) for r in repos]

    results: list[RepoPRs] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Fetching PRs...", total=len(repos))

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(fetch_prs, repo, since): repo
                for repo in repos
            }

            for future in as_completed(futures):
                results.append(future.result())
                progress.advance(task)

    return results


def main() -> None:
    """Main entry point."""
    args = parse_args()
    console = Console()

    # Load config and discover repos
    config = load_config()
    root_path = Path(args.path).resolve()

    if not root_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {root_path}")
        sys.exit(1)

    console.print(f"[dim]Scanning {root_path}...[/dim]")
    repos = find_repos(root_path, config)

    if not repos:
        console.print("[yellow]No git repositories found.[/yellow]")
        sys.exit(0)

    console.print(f"[dim]Found {len(repos)} repositories[/dim]")

    # Get author emails
    author_emails = get_author_emails(config)
    if not author_emails:
        console.print("[red]Error:[/red] Could not determine git user email. Set it with: git config --global user.email")
        sys.exit(1)

    # Get periods to analyze
    periods = get_periods(args)
    warnings: list[str] = []

    # Find the earliest date we need
    earliest_since = min(since for _, since in periods)

    # Analyze all repos once with the earliest date
    all_repo_stats = analyze_repos_parallel(repos, author_emails, earliest_since, console)
    all_repo_prs = fetch_prs_parallel(repos, earliest_since, console)

    # Collect warnings
    for pr_result in all_repo_prs:
        if pr_result.error:
            warnings.append(pr_result.error)
            break  # Only show first warning

    # Build period stats by filtering results
    period_stats: list[PeriodStats] = []

    for period_name, since in periods:
        # Filter commits to this period
        filtered_repo_stats = []
        for repo_stat in all_repo_stats:
            filtered_commits = [c for c in repo_stat.commits if c.authored_date >= since]
            filtered = RepoStats(
                path=repo_stat.path,
                name=repo_stat.name,
                commits=filtered_commits,
                error=repo_stat.error,
            )
            filtered_repo_stats.append(filtered)

        # Filter PRs to this period
        filtered_repo_prs = []
        for repo_pr in all_repo_prs:
            filtered = RepoPRs(
                repo_path=repo_pr.repo_path,
                repo_name=repo_pr.repo_name,
                owner=repo_pr.owner,
                prs_opened=[p for p in repo_pr.prs_opened if p.created_at >= since],
                prs_merged=[p for p in repo_pr.prs_merged if p.merged_at and p.merged_at >= since],
                error=repo_pr.error,
            )
            filtered_repo_prs.append(filtered)

        period_stats.append(PeriodStats(
            name=period_name,
            repo_stats=filtered_repo_stats,
            repo_prs=filtered_repo_prs,
        ))

    # Render the report
    render_report(console, period_stats, warnings)


if __name__ == "__main__":
    main()
