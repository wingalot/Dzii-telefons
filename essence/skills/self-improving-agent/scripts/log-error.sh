#!/data/data/com.termux/files/usr/bin/bash
# Error Logger - Logs errors to .learnings/ERRORS.md

ERRORS_FILE="${ERRORS_FILE:-/data/data/com.termux/files/home/.openclaw/workspace-thinker/.learnings/ERRORS.md}"

# Parse arguments
COMMAND=""
ERROR_OUTPUT=""
CONTEXT=""
PRIORITY="high"
REPRODUCIBLE="unknown"
SUGGESTED_FIX=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --command) COMMAND="$2"; shift 2 ;;
    --error-output) ERROR_OUTPUT="$2"; shift 2 ;;
    --context) CONTEXT="$2"; shift 2 ;;
    --priority) PRIORITY="$2"; shift 2 ;;
    --reproducible) REPRODUCIBLE="$2"; shift 2 ;;
    --suggested-fix) SUGGESTED_FIX="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Validate required fields
if [[ -z "$COMMAND" || -z "$ERROR_OUTPUT" ]]; then
  echo "❌ Missing required fields: --command, --error-output"
  exit 1
fi

# Ensure directory exists
mkdir -p "$(dirname "$ERRORS_FILE")"

# Generate ID
DATE_STR=$(date +%Y%m%d)
RAND_ID=$(cat /dev/urandom | tr -dc 'A-Z0-9' | fold -w 3 | head -n 1)
ERROR_ID="ERR-${DATE_STR}-${RAND_ID}"
TIMESTAMP=$(date -Iseconds)

# Extract skill/command name from command
SKILL_NAME=$(echo "$COMMAND" | awk '{print $1}' | tr -d './')

# Build entry
cat >> "$ERRORS_FILE" << EOF

## [${ERROR_ID}] ${SKILL_NAME}

**Logged**: ${TIMESTAMP}
**Priority**: ${PRIORITY}
**Status**: pending
**Area**: infra

### Summary
Command execution failed

### Error
\`\`\`
${ERROR_OUTPUT}
\`\`\`

### Context
- Command: ${COMMAND}
- Input: ${CONTEXT:-none}

### Suggested Fix
${SUGGESTED_FIX:-Investigate and fix underlying issue.}

### Metadata
- Reproducible: ${REPRODUCIBLE}
- Related Files: none
---
EOF

echo "✅ Error logged: ${ERROR_ID}"
echo "📁 File: ${ERRORS_FILE}"
