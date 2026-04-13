#!/bin/bash
# Felix System v3.0 - Re-authorization helper
# Run this to re-authorize Telegram session after MemorySession migration

echo "Felix Signal Hub - Telegram Re-authorization"
echo "============================================="
echo ""
echo "After migrating to MemorySession (to fix SQLite locks),"
echo "you need to re-authorize the Telegram session."
echo ""
echo "Running Signal Hub in interactive mode..."
echo "You will be asked to enter phone number and verification code."
echo ""

SUPERVISOR_DIR="$HOME/.openclaw/ai_supervisor"

cd "$HOME"

# Stop any running hub
pkill -f "felix_signal_hub.py" 2>/dev/null || true
rm -f "$SUPERVISOR_DIR/state/signal_hub.pid"
sleep 1

# Run interactively
python3 "$SUPERVISOR_DIR/felix_signal_hub.py" --setup
