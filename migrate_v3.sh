#!/bin/bash
# ============================================================
# Felix System v3.0 - Complete Migration with Re-auth
# This script performs full v3 migration including Telegram auth
# ============================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[MIGRATE]${NC} $1"; }
error() { echo -e "${RED}[MIGRATE]${NC} $1"; }
warn() { echo -e "${YELLOW}[MIGRATE]${NC} $1"; }
info() { echo -e "${BLUE}[MIGRATE]${NC} $1"; }

SUPERVISOR_DIR="$HOME/.openclaw/ai_supervisor"
WORKSPACE_DIR="$HOME/.openclaw/workspace"
TELEGRAM_DIR="$HOME/.openclaw/telegram"

main() {
    echo ""
    log "🚀 Felix System v3.0 Migration"
    echo "================================"
    echo ""
    
    # Step 1: Stop everything
    log "Step 1: Stopping all processes..."
    pkill -f "felix_signal_hub.py" 2>/dev/null || true
    pkill -f "felix_tp_manager.py" 2>/dev/null || true
    sleep 2
    
    # Step 2: Deploy v3 Signal Hub
    log "Step 2: Deploying v3 Signal Hub..."
    
    # Get v3 signal hub from backup (created during deployment)
    if [[ -f "$SUPERVISOR_DIR.backup.20260402/felix_signal_hub.py" ]]; then
        # Check if it has StringSession
        if grep -q "StringSession" "$SUPERVISOR_DIR.backup.20260402/felix_signal_hub.py"; then
            cp "$SUPERVISOR_DIR.backup.20260402/felix_signal_hub.py" "$SUPERVISOR_DIR/felix_signal_hub.py"
            log "✅ v3 Signal Hub deployed"
        else
            error "❌ Backup doesn't have v3 changes!"
            exit 1
        fi
    else
        error "❌ v3 backup not found!"
        exit 1
    fi
    
    # Step 3: Clear old session
    log "Step 3: Clearing old session files..."
    rm -f "$TELEGRAM_DIR/felix_listener.session" 2>/dev/null || true
    rm -f "$TELEGRAM_DIR/felix_listener.session-journal" 2>/dev/null || true
    log "✅ Old sessions cleared"
    
    # Step 4: Interactive Telegram authentication
    echo ""
    warn "⚠️  TELEGRAM RE-AUTHENTICATION REQUIRED"
    echo ""
    info "You will be asked to:"
    info "  1. Enter phone number: +37126225767"
    info "  2. Enter Telegram verification code"
    info "  3. Enter 2FA password (if enabled)"
    echo ""
    read -p "Press ENTER to start authentication..."
    echo ""
    
    # Run Signal Hub once interactively
    cd "$HOME"
    python3 "$SUPERVISOR_DIR/felix_signal_hub.py" &
    AUTH_PID=$!
    
    # Wait for auth to complete (user will see prompts)
    log "Signal Hub starting (PID: $AUTH_PID)..."
    log "Complete the authentication in the prompts above."
    echo ""
    read -p "After you see 'Logged in as: Nigerian', press ENTER..."
    
    # Kill the temp process
    kill $AUTH_PID 2>/dev/null || true
    sleep 2
    
    # Step 5: Deploy v3 master script
    log "Step 5: Deploying v3 master script..."
    cp "$WORKSPACE_DIR/felix_new" "$WORKSPACE_DIR/felix"
    chmod +x "$WORKSPACE_DIR/felix"
    log "✅ v3 master script deployed"
    
    # Step 6: Start v3 system
    log "Step 6: Starting v3 system..."
    echo ""
    
    # Export for memory session
    export FELIX_MEMORY_SESSION=1
    
    # Start Signal Hub as daemon
    nohup python3 "$SUPERVISOR_DIR/felix_signal_hub.py" \
        > "$SUPERVISOR_DIR/logs/signal_hub.log" 2>&1 &
echo $! > "$SUPERVISOR_DIR/state/signal_hub.pid"
    
    sleep 3
    
    if kill -0 $(cat "$SUPERVISOR_DIR/state/signal_hub.pid") 2>/dev/null; then
        log "✅ Signal Hub is running"
    else
        error "❌ Signal Hub failed to start"
        exit 1
    fi
    
    # Start TP Manager
    nohup python3 "$SUPERVISOR_DIR/felix_tp_manager.py" --daemon \
        > "$SUPERVISOR_DIR/logs/tp_manager.log" 2>&1 &
echo $! > "$SUPERVISOR_DIR/state/tp_manager.pid"
    
    sleep 2
    
    if kill -0 $(cat "$SUPERVISOR_DIR/state/tp_manager.pid") 2>/dev/null; then
        log "✅ TP Manager is running"
    else
        warn "⚠️  TP Manager may have issues"
    fi
    
    echo ""
    log "🎉 Migration complete!"
    echo ""
    info "System is now running v3.0 with:"
    info "  ✅ No SQLite locking issues"
    info "  ✅ Better error handling"
    info "  ✅ Clean architecture"
    echo ""
    info "Commands:"
    info "  bash felix status    - Check status"
    info "  bash felix logs hub  - View Signal Hub logs"
    info "  bash felix sync      - Sync positions"
    echo ""
}

main
