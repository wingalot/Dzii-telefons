#!/data/data/com.termux/files/usr/bin/bash
# Learning Logger - Logs learnings to .learnings/LEARNINGS.md

LEARNINGS_FILE="${LEARNINGS_FILE:-/data/data/com.termux/files/home/.openclaw/workspace-thinker/.learnings/LEARNINGS.md}"

# Parse arguments
CATEGORY=""
SUMMARY=""
DETAILS=""
PRIORITY="medium"
AREA=""
RELATED_FILES=""
TAGS=""
PATTERN_KEY=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --category) CATEGORY="$2"; shift 2 ;;
    --summary) SUMMARY="$2"; shift 2 ;;
    --details) DETAILS="$2"; shift 2 ;;
    --priority) PRIORITY="$2"; shift 2 ;;
    --area) AREA="$2"; shift 2 ;;
    --related-files) RELATED_FILES="$2"; shift 2 ;;
    --tags) TAGS="$2"; shift 2 ;;
    --pattern-key) PATTERN_KEY="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Validate required fields
if [[ -z "$CATEGORY" || -z "$SUMMARY" || -z "$DETAILS" ]]; then
  echo "❌ Missing required fields: --category, --summary, --details"
  exit 1
fi

# Ensure directory exists
mkdir -p "$(dirname "$LEARNINGS_FILE")"

# Generate ID
DATE_STR=$(date +%Y%m%d)
RAND_ID=$(cat /dev/urandom | tr -dc 'A-Z0-9' | fold -w 3 | head -n 1)
LEARNING_ID="LRN-${DATE_STR}-${RAND_ID}"
TIMESTAMP=$(date -Iseconds)

# Build entry
cat >> "$LEARNINGS_FILE" << EOF

## [${LEARNING_ID}] ${CATEGORY}

**Logged**: ${TIMESTAMP}
**Priority**: ${PRIORITY}
**Status**: pending
**Area**: ${AREA:-general}

### Summary
${SUMMARY}

### Details
${DETAILS}

### Suggested Action
Review and promote if broadly applicable.

### Metadata
- Source: user_feedback
- Related Files: ${RELATED_FILES:-none}
- Tags: ${TAGS:-none}
EOF

if [[ -n "$PATTERN_KEY" ]]; then
  echo "- Pattern-Key: ${PATTERN_KEY}" >> "$LEARNINGS_FILE"
  echo "- Recurrence-Count: 1" >> "$LEARNINGS_FILE"
  echo "- First-Seen: ${TIMESTAMP:0:10}" >> "$LEARNINGS_FILE"
  echo "- Last-Seen: ${TIMESTAMP:0:10}" >> "$LEARNINGS_FILE"
fi

echo "---" >> "$LEARNINGS_FILE"

echo "✅ Learning logged: ${LEARNING_ID}"
echo "📁 File: ${LEARNINGS_FILE}"
