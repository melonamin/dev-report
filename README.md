# dev-report

A CLI tool that generates daily, weekly, and monthly reports on your development activity across multiple git repositories.

## Installation

```bash
# Install globally with uv
uv tool install git+https://github.com/melonamin/dev-report

# Or run directly without installing
uvx git+https://github.com/melonamin/dev-report ~/Developer
```

## Usage

```bash
# Scan current directory
dev-report

# Scan specific directory
dev-report ~/Developer

# Show specific time period only
dev-report --daily    # Last 24 hours
dev-report --weekly   # Last 7 days
dev-report --monthly  # Last 30 days
```

### Example Output

```
╭──────────────────────────────────────────────────────────────────────────────╮
│ Dev Report - Generated 2026-01-22 00:56 UTC                                  │
╰──────────────────────────────────────────────────────────────────────────────╯

──────────────────────────────── Last 24 Hours ─────────────────────────────────

Commits: 20 across 2 repo(s)  |  PRs Opened: 2  |  PRs Merged: 0
Lines: +6856 / -790  |  Files: 176

my-project   19 commit(s)  +6700 / -790
other-repo    1 commit(s)   +156 / -0
```

## Features

- Auto-discovers git repositories recursively
- Tracks commits, lines changed, and files modified
- Fetches GitHub PR statistics via `gh` CLI
- Filters activity by your git author email
- Rich terminal output with colors and tables
- Configurable include/exclude patterns

## Configuration

Create `~/.config/dev-report/config.toml` to customize behavior:

```toml
# Only include repos matching these patterns
include = [
    "~/Developer/github.com/myusername/*"
]

# Exclude repos matching these patterns
exclude = [
    "*/node_modules/*",
    "*/vendor/*"
]

# Use multiple author emails (if you use different emails across repos)
author_emails = [
    "me@personal.com",
    "me@work.com"
]
```

## Requirements

- Python 3.11+
- [gh CLI](https://cli.github.com/) (optional, for PR statistics)

## How It Works

1. Recursively finds all `.git` directories under the specified path
2. Filters repositories based on config include/exclude patterns
3. Analyzes commits by your author email within the time window
4. Fetches PR data from GitHub using `gh pr list --author @me`
5. Aggregates statistics and renders a formatted report

## License

MIT
