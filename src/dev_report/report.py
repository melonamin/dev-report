"""Rich terminal report rendering."""

from dataclasses import dataclass
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .git_stats import RepoStats
from .github_prs import RepoPRs


@dataclass
class PeriodStats:
    """Aggregated statistics for a time period."""

    name: str
    repo_stats: list[RepoStats]
    repo_prs: list[RepoPRs]

    @property
    def total_commits(self) -> int:
        return sum(r.total_commits for r in self.repo_stats)

    @property
    def repos_with_commits(self) -> int:
        return sum(1 for r in self.repo_stats if r.total_commits > 0)

    @property
    def lines_added(self) -> int:
        return sum(r.lines_added for r in self.repo_stats)

    @property
    def lines_removed(self) -> int:
        return sum(r.lines_removed for r in self.repo_stats)

    @property
    def files_changed(self) -> int:
        return sum(r.files_changed for r in self.repo_stats)

    @property
    def prs_opened(self) -> int:
        return sum(len(r.prs_opened) for r in self.repo_prs)

    @property
    def prs_merged(self) -> int:
        return sum(len(r.prs_merged) for r in self.repo_prs)


def format_lines(added: int, removed: int) -> Text:
    """Format lines added/removed with colors."""
    text = Text()
    text.append(f"+{added}", style="green")
    text.append(" / ")
    text.append(f"-{removed}", style="red")
    return text


def render_period(console: Console, period: PeriodStats) -> None:
    """Render a single time period's statistics."""
    # Header
    console.print()
    console.rule(f"[bold cyan]{period.name}[/bold cyan]", style="cyan")
    console.print()

    if period.total_commits == 0 and period.prs_opened == 0 and period.prs_merged == 0:
        console.print("[dim]No activity[/dim]")
        return

    # Summary line
    summary = Text()
    summary.append("Commits: ", style="bold")
    summary.append(f"{period.total_commits}")
    if period.repos_with_commits > 0:
        summary.append(f" across {period.repos_with_commits} repo(s)")

    summary.append("  |  PRs Opened: ", style="bold")
    summary.append(f"{period.prs_opened}")
    summary.append("  |  PRs Merged: ", style="bold")
    summary.append(f"{period.prs_merged}")

    console.print(summary)

    # Lines summary
    if period.lines_added > 0 or period.lines_removed > 0:
        lines_summary = Text()
        lines_summary.append("Lines: ", style="bold")
        lines_summary.append_text(format_lines(period.lines_added, period.lines_removed))
        lines_summary.append("  |  Files: ", style="bold")
        lines_summary.append(f"{period.files_changed}")
        console.print(lines_summary)

    # Per-repo breakdown (only repos with activity)
    active_repos = [r for r in period.repo_stats if r.total_commits > 0]
    if active_repos:
        console.print()

        table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        table.add_column("Repo", style="cyan", no_wrap=True)
        table.add_column("Commits", justify="right")
        table.add_column("Lines", justify="right")

        for repo in sorted(active_repos, key=lambda r: r.total_commits, reverse=True):
            table.add_row(
                repo.name,
                f"{repo.total_commits} commit(s)",
                format_lines(repo.lines_added, repo.lines_removed),
            )

        console.print(table)


def render_report(
    console: Console,
    periods: list[PeriodStats],
    warnings: list[str],
) -> None:
    """Render the full report."""
    # Header
    now = datetime.now(timezone.utc)
    header = Text()
    header.append("Dev Report", style="bold magenta")
    header.append(" - Generated ")
    header.append(now.strftime("%Y-%m-%d %H:%M UTC"), style="dim")

    console.print()
    console.print(Panel(header, border_style="magenta"))

    # Warnings
    for warning in warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    # Each period
    for period in periods:
        render_period(console, period)

    console.print()
