#!/data/data/com.termux/files/usr/bin/bash
# Skill Install Tool

SKILL_REF="$1"
GLOBAL="${2:-true}"
YES="${3:-true}"

if [[ -z "$SKILL_REF" ]]; then
  echo "❌ Skill reference required"
  echo "Usage: skill-install.sh 'owner/repo@skill'"
  echo ""
  echo "Examples:"
  echo "  skill-install.sh vercel-labs/agent-skills@vercel-react-best-practices"
  exit 1
fi

echo "📦 Installing skill: $SKILL_REF"
echo ""

# Build command
CMD="npx skills add $SKILL_REF"
[[ "$GLOBAL" == "true" ]] && CMD="$CMD -g"
[[ "$YES" == "true" ]] && CMD="$CMD -y"

echo "Running: $CMD"
echo ""

# Execute
if eval "$CMD"; then
  echo ""
  echo "✅ Skill installed successfully!"
  
  # Try to find where it was installed
  SKILL_DIR="$HOME/.openclaw/skills/$(echo $SKILL_REF | sed 's/.*@//')"
  if [[ -d "$SKILL_DIR" ]]; then
    echo "📁 Location: $SKILL_DIR"
  fi
else
  echo ""
  echo "❌ Installation failed"
  echo ""
  echo "Try manually:"
  echo "  $CMD"
fi
