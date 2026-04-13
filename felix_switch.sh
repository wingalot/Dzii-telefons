#!/bin/bash
# Felix System - Version Switcher
# Easily switch between v2 (old) and v3 (new) versions

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[SWITCH]${NC} $1"; }
error() { echo -e "${RED}[SWITCH]${NC} $1"; }
warn() { echo -e "${YELLOW}[SWITCH]${NC} $1"; }
info() { echo -e "${BLUE}[SWITCH]${NC} $1"; }

WORKSPACE="$HOME/.openclaw/workspace"
SUPERVISOR="$HOME/.openclaw/ai_supervisor"

cmd_v2() {
    log "Switching to Felix v2.0 (Legacy)..."
    
    # Stop v3
    pkill -f "felix_signal_hub.py" 2>/dev/null || true
    pkill -f "felix_tp_manager.py" 2>/dev/null || true
    pkill -f "felix_orchestrator.py" 2>/dev/null || true
    sleep 2
    
    # Restore v2 master script
    if [[ -f "$WORKSPACE/felix_v2_backup" ]]; then
        cp "$WORKSPACE/felix_v2_backup" "$WORKSPACE/felix"
        chmod +x "$WORKSPACE/felix"
    fi
    
    # Restore v2 signal hub
    if [[ -f "$SUPERVISOR/felix_signal_hub.py.v2" ]]; then
        cp "$SUPERVISOR/felix_signal_hub.py.v2" "$SUPERVISOR/felix_signal_hub.py"
    fi
    
    log "✅ Switched to v2.0 (Legacy)"
    info "Start with: bash felix start"
}

cmd_v3() {
    log "Switching to Felix v3.0 (Modern)..."
    
    # Stop v2
    pkill -f "felix_signal_hub.py" 2>/dev/null || true
    pkill -f "felix_tp_manager.py" 2>/dev/null || true
    sleep 2
    
    # Deploy v3 master script (backup current first)
    if [[ -f "$WORKSPACE/felix" ]] && [[ ! -f "$WORKSPACE/felix_v2_backup" ]]; then
        cp "$WORKSPACE/felix" "$WORKSPACE/felix_v2_backup"
    fi
    
    # Copy v3 master script
    cp "$WORKSPACE/felix_new" "$WORKSPACE/felix"
    chmod +x "$WORKSPACE/felix"
    
    # V3 signal hub is already in place
    
    log "✅ Switched to v3.0 (Modern)"
    warn "⚠️  Remember: v3 requires Telegram re-authorization!"
    info "Run: python3 ~/.openclaw/ai_supervisor/felix_signal_hub.py (interactive)"
    info "Then: bash felix start"
}

cmd_status() {
    echo ""
    echo "Felix Version Status"
    echo "===================="
    echo ""
    
    # Check which version is active
    if grep -q "v3.0" "$WORKSPACE/felix" 2>/dev/null; then
        log "Current: v3.0 (Modern)"
    elif grep -q "v2.0" "$WORKSPACE/felix" 2>/dev/null; then
        info "Current: v2.0 (Legacy)"
    else
        warn "Unknown version"
    fi
    
    echo ""
    info "Available versions:"
    ls -la "$WORKSPACE/felix"* 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes)"}'
    
    echo ""
    info "Backups:"
    ls -la ~/.openclaw/backups/ 2>/dev/null | tail -5 | awk '{print "  " $9}' || echo "  None"
}

cmd_help() {
    echo "Felix Version Switcher"
    echo "======================"
    echo ""
    echo "Usage: bash felix_switch.sh [command]"
    echo ""
    echo "Commands:"
    echo "  v2       Switch to v2.0 (Legacy, SQLite session)"
    echo "  v3       Switch to v3.0 (Modern, MemorySession)"
    echo "  status   Show current version and backups"
    echo "  help     Show this help"
    echo ""
    echo "v2.0 (Legacy):"
    echo "  + No re-auth needed"
    echo "  + Battle-tested"
    echo "  - SQLite locking issues"
    echo ""
    echo "v3.0 (Modern):"
    echo "  + No SQLite locks"
    echo "  + Better error handling"
    echo "  + Cleaner architecture"
    echo "  - Requires Telegram re-auth"
    echo ""
}

case "${1:-help}" in
    v2) cmd_v2 ;;
    v3) cmd_v3 ;;
    status) cmd_status ;;
    help|--help|-h) cmd_help ;;
    *) cmd_help ;;
esac
