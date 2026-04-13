#!/bin/bash
# Felix Hybrid v2.5 - Best of both worlds
# Uses v2 Signal Hub (SQLite) + v3 TP Manager + v3 Orchestrator

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[HYBRID]${NC} $1"; }
error() { echo -e "${RED}[HYBRID]${NC} $1"; }
warn() { echo -e "${YELLOW}[HYBRID]${NC} $1"; }
info() { echo -e "${BLUE}[HYBRID]${NC} $1"; }

SUPERVISOR_DIR="$HOME/.openclaw/ai_supervisor"

main() {
    echo ""
    log "🚀 Felix Hybrid v2.5 Deployment"
    echo "================================"
    echo ""
    
    # Stop everything
    log "Stopping all processes..."
    pkill -f "felix_signal_hub.py" 2>/dev/null || true
    pkill -f "felix_tp_manager.py" 2>/dev/null || true
    sleep 2
    
    # Restore v2 Signal Hub (from backup)
    log "Restoring v2 Signal Hub..."
    if [[ -f "$SUPERVISOR_DIR.backup.20260402/felix_signal_hub.py" ]]; then
        # Check if it's v2 (no StringSession)
        if ! grep -q "StringSession" "$SUPERVISOR_DIR.backup.20260402/felix_signal_hub.py"; then
            cp "$SUPERVISOR_DIR.backup.20260402/felix_signal_hub.py" "$SUPERVISOR_DIR/felix_signal_hub.py"
            log "✅ v2 Signal Hub restored"
        else
            error "❌ Backup has v3 code, using current v2 file"
        fi
    fi
    
    # Keep v3 TP Manager
    log "Using v3 TP Manager (refactored)..."
    
    # Keep v3 interfaces
    log "Using v3 Interfaces..."
    
    # Create hybrid master script
    log "Creating hybrid master script..."
    cat > "$HOME/.openclaw/workspace/felix" << 'EOF'
#!/bin/bash
# Felix Hybrid v2.5 - Master Control

cd "$HOME"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[FELIX]${NC} $1"; }
warn() { echo -e "${YELLOW}[FELIX]${NC} $1"; }
error() { echo -e "${RED}[FELIX]${NC} $1"; }
info() { echo -e "${CYAN}[FELIX]${NC} $1"; }

SUPERVISOR_DIR="$HOME/.openclaw/ai_supervisor"
PID_DIR="$SUPERVISOR_DIR/state"

cmd_start() {
    log "Starting Felix Hybrid v2.5..."
    
    mkdir -p "$PID_DIR"
    mkdir -p "$SUPERVISOR_DIR/logs"
    
    # Start Signal Hub (v2 - SQLite, but working)
    if [[ -f "$PID_DIR/signal_hub.pid" ]]; then
        kill $(cat "$PID_DIR/signal_hub.pid") 2>/dev/null || true
        rm -f "$PID_DIR/signal_hub.pid"
        sleep 1
    fi
    
    nohup python3 "$SUPERVISOR_DIR/felix_signal_hub.py" > "$SUPERVISOR_DIR/logs/signal_hub.log" 2>&1 &
echo $! > "$PID_DIR/signal_hub.pid"
    sleep 3
    
    if kill -0 $(cat "$PID_DIR/signal_hub.pid") 2>/dev/null; then
        log "✅ Signal Hub (v2) running"
    else
        error "❌ Signal Hub failed"
        return 1
    fi
    
    # Start TP Manager (v3 - refactored)
    pkill -f "felix_tp_manager.py" 2>/dev/null || true
    sleep 1
    
    nohup python3 "$SUPERVISOR_DIR/felix_tp_manager.py" --daemon > "$SUPERVISOR_DIR/logs/tp_manager.log" 2>&1 &
echo $! > "$PID_DIR/tp_manager.pid"
    sleep 2
    
    if kill -0 $(cat "$PID_DIR/tp_manager.pid") 2>/dev/null; then
        log "✅ TP Manager (v3) running"
    else
        warn "⚠️ TP Manager may need sync"
    fi
    
    log "🎉 Hybrid system started!"
    info "v2 Signal Hub + v3 TP Manager"
}

cmd_stop() {
    log "Stopping system..."
    
    if [[ -f "$PID_DIR/signal_hub.pid" ]]; then
        kill $(cat "$PID_DIR/signal_hub.pid") 2>/dev/null || true
        rm -f "$PID_DIR/signal_hub.pid"
    fi
    
    if [[ -f "$PID_DIR/tp_manager.pid" ]]; then
        kill $(cat "$PID_DIR/tp_manager.pid") 2>/dev/null || true
        rm -f "$PID_DIR/tp_manager.pid"
    fi
    
    pkill -f "felix_signal_hub.py" 2>/dev/null || true
    pkill -f "felix_tp_manager.py" 2>/dev/null || true
    
    log "✅ System stopped"
}

cmd_status() {
    log "System Status"
    echo "============="
    
    if [[ -f "$PID_DIR/signal_hub.pid" ]] && kill -0 $(cat "$PID_DIR/signal_hub.pid") 2>/dev/null; then
        log "🟢 Signal Hub (v2): RUNNING"
    else
        error "🔴 Signal Hub (v2): STOPPED"
    fi
    
    if [[ -f "$PID_DIR/tp_manager.pid" ]] && kill -0 $(cat "$PID_DIR/tp_manager.pid") 2>/dev/null; then
        log "🟢 TP Manager (v3): RUNNING"
    else
        error "🔴 TP Manager (v3): STOPPED"
    fi
}

cmd_logs() {
    tail -f "$SUPERVISOR_DIR/logs/signal_hub.log" "$SUPERVISOR_DIR/logs/tp_manager.log" 2>/dev/null
}

case "${1:-}" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    restart) cmd_stop; sleep 2; cmd_start ;;
    status) cmd_status ;;
    logs) cmd_logs ;;
    *) echo "Usage: felix {start|stop|restart|status|logs}" ;;
esac
EOF
    chmod +x "$HOME/.openclaw/workspace/felix"
    
    log "✅ Hybrid master script created"
    echo ""
    log "🎉 Deployment complete!"
    echo ""
    info "This hybrid uses:"
    info "  ✅ v2 Signal Hub (works now, no re-auth needed)"
    info "  ✅ v3 TP Manager (refactored, cleaner code)"
    info "  ✅ v3 Interfaces (shared types)"
    info "  ✅ v3 Config (centralized settings)"
    echo ""
    info "Start with: bash felix start"
}

main
