#!/bin/bash
# ============================================================
# Felix System v3.0 - Integration Script
# Deploys all refactored components
# ============================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
error() { echo -e "${RED}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[DEPLOY]${NC} $1"; }
info() { echo -e "${BLUE}[DEPLOY]${NC} $1"; }

SUPERVISOR_DIR="$HOME/.openclaw/ai_supervisor"
WORKSPACE_DIR="$HOME/.openclaw/workspace"
TRADING_DIR="$HOME/.trading"

deploy() {
    echo ""
    log "🚀 Felix System v3.0 Deployment"
    echo "================================"
    echo ""
    
    # Phase 1: Validate all components exist
    log "Phase 1: Validating components..."
    
    local components_ok=true
    
    [[ -f "$SUPERVISOR_DIR/felix_signal_hub.py" ]] || { error "Missing: felix_signal_hub.py"; components_ok=false; }
    [[ -f "$SUPERVISOR_DIR/felix_orchestrator.py" ]] || { warn "Missing: felix_orchestrator.py (optional)"; }
    [[ -f "$SUPERVISOR_DIR/felix_tp_manager.py" ]] || { error "Missing: felix_tp_manager.py"; components_ok=false; }
    [[ -f "$WORKSPACE_DIR/felix_new" ]] || { error "Missing: felix_new (master script)"; components_ok=false; }
    [[ -f "$TRADING_DIR/felix_config.json" ]] || { warn "Missing: felix_config.json"; }
    
    if ! $components_ok; then
        error "❌ Component validation failed"
        exit 1
    fi
    
    log "✅ Components validated"
    echo ""
    
    # Phase 2: Create backup
    log "Phase 2: Creating backup..."
    local backup_dir="$HOME/.openclaw/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    cp -r "$SUPERVISOR_DIR"/*.py "$backup_dir/" 2>/dev/null || true
    cp "$WORKSPACE_DIR/felix" "$backup_dir/felix_old" 2>/dev/null || true
    log "✅ Backup created: $backup_dir"
    echo ""
    
    # Phase 3: Stop current system
    log "Phase 3: Stopping current system..."
    
    # Stop signal hub
    if [[ -f "$SUPERVISOR_DIR/state/signal_hub.pid" ]]; then
        local pid=$(cat "$SUPERVISOR_DIR/state/signal_hub.pid" 2>/dev/null)
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null || true
            rm -f "$SUPERVISOR_DIR/state/signal_hub.pid"
            log "✅ Signal Hub stopped"
        fi
    fi
    
    # Stop TP Manager
    if [[ -f "$SUPERVISOR_DIR/state/tp_manager.pid" ]]; then
        local pid=$(cat "$SUPERVISOR_DIR/state/tp_manager.pid" 2>/dev/null)
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null || true
            rm -f "$SUPERVISOR_DIR/state/tp_manager.pid"
            log "✅ TP Manager stopped"
        fi
    fi
    
    # Kill any remaining processes
    pkill -f "felix_.*\.py" 2>/dev/null || true
    sleep 2
    log "✅ All processes stopped"
    echo ""
    
    # Phase 4: Deploy new master script
    log "Phase 4: Deploying new master script..."
    if [[ -f "$WORKSPACE_DIR/felix" ]]; then
        mv "$WORKSPACE_DIR/felix" "$WORKSPACE_DIR/felix_v2_backup"
        log "✅ Old felix script backed up"
    fi
    mv "$WORKSPACE_DIR/felix_new" "$WORKSPACE_DIR/felix"
    chmod +x "$WORKSPACE_DIR/felix"
    log "✅ New master script deployed"
    echo ""
    
    # Phase 5: Create required directories
    log "Phase 5: Creating directories..."
    mkdir -p "$SUPERVISOR_DIR/signals"
    mkdir -p "$SUPERVISOR_DIR/orders"
    mkdir -p "$SUPERVISOR_DIR/positions"
    mkdir -p "$SUPERVISOR_DIR/logs"
    mkdir -p "$SUPERVISOR_DIR/state"
    log "✅ Directories created"
    echo ""
    
    # Phase 6: Verify Python syntax
    log "Phase 6: Verifying Python syntax..."
    
    local syntax_ok=true
    
    if ! python3 -m py_compile "$SUPERVISOR_DIR/felix_signal_hub.py" 2>/dev/null; then
        error "❌ felix_signal_hub.py has syntax errors"
        syntax_ok=false
    fi
    
    if ! python3 -m py_compile "$SUPERVISOR_DIR/felix_tp_manager.py" 2>/dev/null; then
        error "❌ felix_tp_manager.py has syntax errors"
        syntax_ok=false
    fi
    
    if [[ -f "$SUPERVISOR_DIR/felix_orchestrator.py" ]]; then
        if ! python3 -m py_compile "$SUPERVISOR_DIR/felix_orchestrator.py" 2>/dev/null; then
            error "❌ felix_orchestrator.py has syntax errors"
            syntax_ok=false
        fi
    fi
    
    if ! $syntax_ok; then
        error "❌ Syntax validation failed - deployment aborted"
        exit 1
    fi
    
    log "✅ Syntax verified"
    echo ""
    
    # Phase 7: Start new system
    log "Phase 7: Starting new system..."
    echo ""
    
    # Export environment variable for memory session
    export FELIX_MEMORY_SESSION=1
    
    # Start Signal Hub
    log "Starting Signal Hub..."
    cd "$HOME"
    nohup python3 "$SUPERVISOR_DIR/felix_signal_hub.py" > "$SUPERVISOR_DIR/logs/signal_hub.log" 2>&1 &
echo $! > "$SUPERVISOR_DIR/state/signal_hub.pid"
    sleep 3
    
    if kill -0 $(cat "$SUPERVISOR_DIR/state/signal_hub.pid") 2>/dev/null; then
        log "✅ Signal Hub started"
    else
        error "❌ Signal Hub failed to start - check logs"
        exit 1
    fi
    
    # Start TP Manager
    log "Starting TP Manager..."
    nohup python3 "$SUPERVISOR_DIR/felix_tp_manager.py" --daemon > "$SUPERVISOR_DIR/logs/tp_manager.log" 2>&1 &
echo $! > "$SUPERVISOR_DIR/state/tp_manager.pid"
    sleep 2
    
    if kill -0 $(cat "$SUPERVISOR_DIR/state/tp_manager.pid") 2>/dev/null; then
        log "✅ TP Manager started"
    else
        warn "⚠️ TP Manager may have issues - check logs"
    fi
    
    # Start Orchestrator if exists
    if [[ -f "$SUPERVISOR_DIR/felix_orchestrator.py" ]]; then
        log "Starting Orchestrator..."
        nohup python3 "$SUPERVISOR_DIR/felix_orchestrator.py" --daemon > "$SUPERVISOR_DIR/logs/orchestrator.log" 2>&1 &
echo $! > "$SUPERVISOR_DIR/state/orchestrator.pid"
        log "✅ Orchestrator started"
    fi
    
    echo ""
    log "🎉 Deployment complete!"
    echo ""
    info "Next steps:"
    info "  1. Run: felix status"
    info "  2. Run: felix logs hub    # Check Signal Hub"
    info "  3. Run: felix sync        # Sync positions"
    info "  4. Monitor for 5 minutes"
    echo ""
    info "Rollback if needed:"
    info "  cp -r $backup_dir/* $SUPERVISOR_DIR/"
}

# Main
deploy
