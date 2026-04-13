#!/bin/bash
# Felix TP Manager Watchdog
# Automātiski restartē TP Manager, ja tas apstājas

PID_FILE="$HOME/.openclaw/ai_supervisor/state/tp_manager.pid"
LOG_FILE="$HOME/.openclaw/ai_supervisor/logs/watchdog.log"
TP_MANAGER="$HOME/.openclaw/ai_supervisor/felix_tp_manager.py"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if TP Manager is running
check_tp_manager() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            return 0  # Running
        fi
    fi
    return 1  # Not running
}

# Start TP Manager
start_tp_manager() {
    log "🚀 Starting TP Manager..."
    cd "$HOME/.openclaw/ai_supervisor" || exit 1
    
    # Clean up old PID file
    rm -f "$PID_FILE"
    
    # Start TP Manager in background
    nohup python3 "$TP_MANAGER" > /dev/null 2>&1 &
    NEW_PID=$!
    
    # Save PID
    echo "$NEW_PID" > "$PID_FILE"
    
    # Wait a bit and check if it started successfully
    sleep 3
    if kill -0 "$NEW_PID" 2>/dev/null; then
        log "✅ TP Manager started with PID: $NEW_PID"
        return 0
    else
        log "❌ Failed to start TP Manager"
        return 1
    fi
}

# Main watchdog loop
log "👁️ Watchdog started - monitoring TP Manager"

while true; do
    if ! check_tp_manager; then
        log "⚠️ TP Manager is not running!"
        start_tp_manager
    fi
    
    # Check every 30 seconds
    sleep 30
done
