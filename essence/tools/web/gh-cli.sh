#!/data/data/com.termux/files/usr/bin/bash
# GitHub CLI Wrapper Tool - Enhanced

set -e

CMD="${1:-help}"
shift || true

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if gh is installed
check_gh() {
    if ! command -v gh &> /dev/null; then
        echo -e "${RED}❌ GitHub CLI (gh) not installed${NC}"
        echo ""
        echo "Install with:"
        echo "  pkg install gh"
        exit 1
    fi
}

# Check authentication
check_auth() {
    if ! gh auth status &> /dev/null; then
        echo -e "${YELLOW}⚠️  Not authenticated with GitHub${NC}"
        echo "Run: gh auth login"
        exit 1
    fi
}

# Show help
show_help() {
    cat << 'EOF'
🐙 GitHub CLI Wrapper

Usage: dzii web github <command> [args]

Commands:
  auth              Check authentication status
  login             Authenticate with GitHub
  pr                Pull request commands
  issue             Issue commands  
  run               Workflow run commands
  repo              Repository commands
  api               Direct API access

PR Commands:
  gh pr list [--repo owner/repo]
  gh pr view <number> [--repo owner/repo]
  gh pr checks <number> [--repo owner/repo]
  gh pr checkout <number>

Issue Commands:
  gh issue list [--repo owner/repo]
  gh issue view <number> [--repo owner/repo]
  gh issue create [--repo owner/repo]

Run Commands:
  gh run list [--repo owner/repo]
  gh run view <run-id> [--repo owner/repo]
  gh run view <run-id> --log-failed

Examples:
  dzii web github pr list --repo openclaw/openclaw
  dzii web github run list --repo openclaw/openclaw --limit 5

EOF
}

# Main
case "$CMD" in
    help|-h|--help)
        show_help
        ;;
    auth|status)
        check_gh
        gh auth status
        ;;
    login)
        check_gh
        gh auth login
        ;;
    pr|issue|run|repo|workflow|release|gist)
        check_gh
        check_auth
        gh "$CMD" "$@"
        ;;
    api)
        check_gh
        check_auth
        gh api "$@"
        ;;
    browse)
        check_gh
        check_auth
        gh browse "$@"
        ;;
    clone)
        check_gh
        check_auth
        gh repo clone "$@"
        ;;
    *)
        check_gh
        check_auth
        gh "$CMD" "$@"
        ;;
esac
