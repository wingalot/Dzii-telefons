#!/data/data/com.termux/files/usr/bin/bash
# Brave Search Tool
# Uses API key from TOOLS.md or environment

API_KEY="${BRAVE_API_KEY:-BSA05ihIMkD4Na1zjew3q7MqLswohKs}"
QUERY="$1"
COUNT="${2:-10}"
FRESHNESS="${3:-}"
COUNTRY="${4:-US}"

if [[ -z "$QUERY" ]]; then
  echo "❌ Query required"
  echo "Usage: brave-search.sh 'query' [count] [freshness] [country]"
  exit 1
fi

# Build URL
URL="https://api.search.brave.com/res/v1/web/search?q=$(echo "$QUERY" | sed 's/ /%20/g')&count=${COUNT}"
[[ -n "$FRESHNESS" ]] && URL="${URL}&freshness=${FRESHNESS}"
[[ -n "$COUNTRY" ]] && URL="${URL}&country=${COUNTRY}"

# Make request
echo "🔍 Searching: $QUERY"
RESPONSE=$(curl -s "$URL" \
  -H "Accept: application/json" \
  -H "X-Subscription-Token: $API_KEY" 2>/dev/null)

# Parse and display results
echo "$RESPONSE" | awk '
  /"title":/ { 
    gsub(/.*"title": "/, "")
    gsub(/",*$/, "")
    print ""
    print "📌 " $0
  }
  /"url":/ {
    gsub(/.*"url": "/, "")
    gsub(/",*$/, "")
    print "🔗 " $0
  }
  /"description":/ {
    gsub(/.*"description": "/, "")
    gsub(/".*$/, "")
    print "💬 " $0
  }
' | head -100

echo ""
echo "✅ Search complete"
