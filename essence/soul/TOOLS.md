# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## API Keys

### Brave Search
- **Key:** `BSA05ihIMkD4Na1zjew3q7MqLswohKs`
- **Usage:** web_search tool with brave provider
- **Limits:** 2000 queries/month (free tier)

## Android Device
- **Model:** Samsung Galaxy S20 FE (Lineage OS 16)
- **Root:** Magisk
- **User:** u0_a157
- **Tools Location:** /data/data/com.termux/files/home/tools/

## Automation Scripts
- phone_agent.sh — AI vision-based control
- phone_control.sh — CLI device control
- phoneclaw/ — Android app project

## Directory Structure
```
tools/
├── system/         # Device control tools
├── ai/            # AI/ML integrations
├── web/           # Web scraping & APIs
├── media/         # Screenshot, audio, video
├── comms/         # Messaging, notifications
└── schemas/       # JSON schemas for validation
```

## 🐙 GitHub CLI (gh)

**Version:** 2.87.3

### Authentication
```bash
gh auth login          # Interactive login
gh auth status         # Check auth status
gh auth logout         # Logout
```

### Pull Requests
```bash
gh pr list                           # List PRs
gh pr view <number>                  # View PR details
gh pr checks <number>                # Check CI status
gh pr checkout <number>              # Checkout PR locally
gh pr create                         # Create new PR
gh pr merge <number>                 # Merge PR
gh pr comment <number> -b "text"     # Comment on PR
```

### Issues
```bash
gh issue list                        # List issues
gh issue view <number>               # View issue
gh issue create                      # Create issue
gh issue close <number>              # Close issue
gh issue comment <number> -b "text"  # Comment
```

### GitHub Actions
```bash
gh run list                          # List workflow runs
gh run view <run-id>                 # View run details
gh run view <run-id> --log-failed    # View failed logs
gh run watch <run-id>                # Watch run progress
gh workflow list                     # List workflows
```

### Repositories
```bash
gh repo view                         # View current repo
gh repo clone <owner/repo>           # Clone repo
gh repo fork                         # Fork current repo
gh repo create <name>                # Create new repo
```

### API Access
```bash
gh api repos/owner/repo/pulls        # API call
gh api repos/owner/repo/issues --jq '.[].title'  # With jq filter
```

### Useful Flags
- `-R, --repo owner/repo` — Specify repo (when not in git dir)
- `--json` — Output as JSON
- `--jq '<filter>'` — Filter JSON output with jq

---
Add whatever helps you do your job. This is your cheat sheet.
