#!/data/data/com.termux/files/usr/bin/bash
# Skill Search Tool

QUERY="$1"
INTERACTIVE="${2:-false}"

if [[ -z "$QUERY" ]]; then
  echo "❌ Query required"
  echo "Usage: skill-search.sh 'react performance'"
  exit 1
fi

echo "🔍 Searching skills for: $QUERY"
echo ""

# Check if npx is available
if ! command -v npx &> /dev/null; then
  echo "⚠️  npx not found. Using curl fallback..."
  
  # Fallback: search via skills.sh API
  curl -s "https://skills.sh/api/search?q=$(echo "$QUERY" | sed 's/ /+/g')" 2>/dev/null | \
    awk -F'"' '/"name":|"description":|"install":/ {
      gsub(/^[ \t]+/, "")
      print
    }' | head -30
else
  # Use skills CLI
  if [[ "$INTERACTIVE" == "true" ]]; then
    npx skills find "$QUERY"
  else
    npx skills find "$QUERY" 2>&1 | head -50
  fi
fi

echo ""
echo "💡 To install: npx skills add <owner/repo@skill>"
