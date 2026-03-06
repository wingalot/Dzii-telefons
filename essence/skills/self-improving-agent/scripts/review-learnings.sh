#!/data/data/com.termux/files/usr/bin/bash
# Learning Reviewer - Reviews pending learnings

LEARNINGS_DIR="${LEARNINGS_DIR:-/data/data/com.termux/files/home/.openclaw/workspace-thinker/.learnings}"
FILTER="pending"
PRIORITY=""
AREA=""
COUNT_ONLY=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --filter) FILTER="$2"; shift 2 ;;
    --priority) PRIORITY="$2"; shift 2 ;;
    --area) AREA="$2"; shift 2 ;;
    --count-only) COUNT_ONLY=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

echo "📚 Learning Review"
echo "=================="

for file in "$LEARNINGS_DIR"/*.md; do
  [[ -f "$file" ]] || continue
  
  FILENAME=$(basename "$file")
  echo ""
  echo "📁 $FILENAME"
  echo "---"
  
  if [[ "$COUNT_ONLY" == true ]]; then
    if [[ "$FILTER" == "all" ]]; then
      COUNT=$(grep -c "^## \[" "$file" 2>/dev/null || echo 0)
    else
      COUNT=$(grep -B5 "Status\*\*: ${FILTER}" "$file" 2>/dev/null | grep -c "^## \[" || echo 0)
    fi
    echo "Count: $COUNT"
  else
    # Show entries
    awk -v status_filter="$FILTER" -v priority_filter="$PRIORITY" '
      /^## \[/ { entry=$0; in_entry=1; buf="" }
      in_entry { buf = buf $0 "\n" }
      /^---$/ && in_entry {
        if (status_filter == "all" || buf ~ "Status\\*\\*: " status_filter) {
          if (priority_filter == "" || buf ~ "Priority\\*\\*: " priority_filter) {
            print entry
            print buf
            print "---"
          }
        }
        in_entry=0
      }
    ' "$file" | head -50
  fi
done

echo ""
echo "💡 Review complete. Use skill-extractor to promote valuable learnings."
