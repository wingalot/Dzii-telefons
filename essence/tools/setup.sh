#!/data/data/com.termux/files/usr/bin/bash
# Setup script for Dzii Tools
# Run once to configure auto-start and optimizations

echo "⚡ Dzii Tools Setup"
echo "==================="

# 1. Create necessary directories
echo "Creating directories..."
mkdir -p ~/.openclaw/workspace-thinker/.learnings
mkdir -p ~/.openclaw/logs
mkdir -p ~/.termux/boot

# 2. Create initial learning files
echo "Initializing learning files..."
touch ~/.openclaw/workspace-thinker/.learnings/LEARNINGS.md
touch ~/.openclaw/workspace-thinker/.learnings/ERRORS.md
touch ~/.openclaw/workspace-thinker/.learnings/FEATURE_REQUESTS.md

# Add headers if empty
[[ ! -s ~/.openclaw/workspace-thinker/.learnings/LEARNINGS.md ]] && echo "# Learnings Log\n\n## Format\nSee self-improving-agent skill documentation.\n" > ~/.openclaw/workspace-thinker/.learnings/LEARNINGS.md

[[ ! -s ~/.openclaw/workspace-thinker/.learnings/ERRORS.md ]] && echo "# Errors Log\n\n## Format\nSee self-improving-agent skill documentation.\n" > ~/.openclaw/workspace-thinker/.learnings/ERRORS.md

[[ ! -s ~/.openclaw/workspace-thinker/.learnings/FEATURE_REQUESTS.md ]] && echo "# Feature Requests\n\n## Format\nSee self-improving-agent skill documentation.\n" > ~/.openclaw/workspace-thinker/.learnings/FEATURE_REQUESTS.md

# 3. Make scripts executable
echo "Setting permissions..."
chmod +x ~/tools/system/*.sh 2>/dev/null || true
chmod +x ~/tools/web/*.sh 2>/dev/null || true
chmod +x ~/.openclaw/skills/self-improving-agent/scripts/*.sh 2>/dev/null || true
chmod +x ~/.termux/boot/openclaw-autostart.sh 2>/dev/null || true

# 4. Install Termux:Boot if not present
echo ""
echo "📱 Next Steps (Manual):"
echo "----------------------"
echo "1. Install Termux:Boot app from F-Droid"
echo "2. Open Termux:Boot once to grant permissions"
echo "3. Run: termux-wake-lock (to prevent sleep)"
echo "4. Add Termux to battery optimization whitelist:"
echo "   Settings > Apps > Termux > Battery > Unrestricted"
echo ""
echo "🔋 Battery alerts require Termux:API"
echo "   Install: pkg install termux-api"
echo ""
echo "✅ Setup complete!"
