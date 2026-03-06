#!/data/data/com.termux/files/usr/bin/bash
# Skill Check Tool - Check for updates

echo "🔍 Checking installed skills..."
echo ""

SKILLS_DIR="$HOME/.openclaw/skills"

echo "Installed skills:"
for dir in "$SKILLS_DIR"/*/; do
  if [[ -d "$dir" ]]; then
    SKILL_NAME=$(basename "$dir")
    META_FILE="$dir/_meta.json"
    SKILL_FILE="$dir/skill.json"
    
    if [[ -f "$META_FILE" ]]; then
      VERSION=$(grep -o '"version"[^}]*' "$META_FILE" | grep -o '[0-9.]*' | head -1)
      echo "  📦 $SKILL_NAME @ $VERSION"
    elif [[ -f "$SKILL_FILE" ]]; then
      VERSION=$(grep -o '"version"[^}]*' "$SKILL_FILE" | grep -o '[0-9.]*' | head -1)
      echo "  📦 $SKILL_NAME @ $VERSION"
    else
      echo "  📦 $SKILL_NAME (version unknown)"
    fi
  fi
done

echo ""
echo "💡 To check for updates: npx skills check"
echo "💡 To update all: npx skills update"
