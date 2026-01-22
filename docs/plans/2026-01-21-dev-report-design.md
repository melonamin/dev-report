# Dev Report CLI - Design Document

## Overview

A Python CLI tool runnable via `uvx` that generates daily, weekly, and monthly reports on development activity across multiple git repositories.

## Requirements

- **Time windows**: Rolling periods - last 24 hours, 7 days, 30 days
- **Metrics tracked**:
  - Commits: count and summary of messages
  - PRs: opened and merged (separately)
  - Changes: lines added/removed, files changed
- **Output**: Rich terminal formatting (colors, tables)
- **Repo discovery**: Auto-discover git repos, with optional config file filtering
- **Author filtering**: Only show user's own commits (via `git config user.email`)
- **PR fetching**: Via GitHub CLI (`gh`)

## Invocation

```bash
uvx dev-report          # Scans current directory
uvx dev-report ~/code   # Scans specific directory
uvx dev-report --daily  # Only show last 24h
uvx dev-report --weekly # Only show last 7 days
```

## Output Example

```
Dev Report - Generated 2026-01-21 19:30

=== Last 24 Hours ===
Commits: 5 across 2 repos
PRs Opened: 1 | PRs Merged: 0
Lines: +342 / -128 | Files: 12

  hydra          3 commits   +200/-50
  kp-web         2 commits   +142/-78

=== Last 7 Days ===
...
```

## Technical Architecture

### Dependencies

- `rich` - Terminal formatting
- `gitpython` - Git repo inspection (commits, diffs)
- `tomli` - Config file parsing (built-in Python 3.11+)

No direct GitHub API library - shells out to `gh` CLI for PRs.

### File Structure

```
dev-report/
├── pyproject.toml
└── src/
    └── dev_report/
        ├── __init__.py
        ├── cli.py          # Argument parsing, main entrypoint
        ├── discovery.py    # Find repos, load config
        ├── git_stats.py    # Commit/diff analysis via gitpython
        ├── github_prs.py   # PR fetching via gh CLI
        └── report.py       # Rich output formatting
```

### Config File

Location: `~/.config/dev-report/config.toml`

```toml
# Optional: only report on these repos (paths or globs)
include = [
    "~/Developer/github.com/melonamin/*"
]

# Optional: skip these
exclude = [
    "*/node_modules/*",
    "*/tries/*"
]

# Optional: multiple author emails
author_emails = [
    "sasha@example.com",
    "sasha@work.com"
]
```

## Data Flow

1. **CLI** parses args (path, --daily/--weekly/--monthly flags)
2. **Discovery**:
   - Find all `.git` directories recursively
   - Load config file if exists
   - Apply include/exclude filters
   - Get user email from `git config user.email`
3. **Per-repo analysis** (parallelized):
   - Filter commits by author + date range
   - Calculate diff stats (lines, files)
   - If remote is GitHub, query `gh pr list`
4. **Aggregation**:
   - Group by time window (24h, 7d, 30d)
   - Sum totals, keep per-repo breakdowns
5. **Report**: Render rich tables to terminal

## Error Handling

### Graceful Degradation

- Repo has no commits in period: show `0 commits`, don't skip
- `gh` not installed: warn once, skip PR stats, show git stats only
- `gh` not authenticated: same as above
- Repo has no GitHub remote: skip PR fetching silently
- Config file missing: use defaults (auto-discover, no filters)
- Config file malformed: error with clear message

### Author Matching

- Primary: match `git config user.email`
- Fallback: `author_emails` list in config for multiple identities

## Packaging

```toml
[project]
name = "dev-report"
version = "0.1.0"
description = "Daily/weekly/monthly dev activity reports"
requires-python = ">=3.11"
dependencies = [
    "rich>=13.0",
    "gitpython>=3.1",
]

[project.scripts]
dev-report = "dev_report.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Usage After Creation

```bash
# Run directly from local directory
uvx --from ./dev-report dev-report

# Or install globally
uv tool install ./dev-report
dev-report ~/Developer
```
