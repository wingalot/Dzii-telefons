#!/data/data/com.termux/files/usr/bin/bash
# Felix VIP Room Signal Listener
# Watches for trading signals and executes them via IG API

TRADING_DIR="$HOME/.trading"
LOG_FILE="$TRADING_DIR/logs/felix_listener.log"
FELIX_TRADER="$HOME/.openclaw/workspace/felix_trader.sh"

# Felix VIP Room channel ID
FELIX_CHANNEL_ID="-1001998353092"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Process signal from Telegram
process_signal() {
    local signal_text="$1"
    local message_id="$2"
    
    log "Received signal (msg_id: $message_id)"
    log "Signal: $signal_text"
    
    # Check if it's a Felix signal (contains flags and BUY/SELL)
    if echo "$signal_text" | grep -qE '(BUY|SELL)' && echo "$signal_text" | grep -qE '[A-Z]{6}'; then
        log "✅ Valid Felix signal detected - executing..."
        
        # Execute trade
        local result=$(bash "$FELIX_TRADER" execute "$signal_text" 2>&1)
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            log "✅ Trade executed successfully"
            # Send confirmation to user
            message send --message "✅ Auto-executed Felix signal:\n$signal_text"
        else
            log "❌ Trade execution failed"
            message send --message "❌ Failed to execute Felix signal - check logs"
        fi
    else
        log "⏭️ Not a valid trading signal, skipping"
    fi
}

# Main loop - poll for new messages
main() {
    log "=== Felix Signal Listener Started ==="
    log "Auto-execute: ENABLED"
    log "Risk validator: DISABLED"
    
    if [ -z "$FELIX_CHANNEL_ID" ]; then
        log "⚠️ WARNING: FELIX_CHANNEL_ID not set!"
        log "Please set the Felix VIP room channel ID in this script."
        exit 1
    fi
    
    log "Monitoring channel: $FELIX_CHANNEL_ID"
    log "Use Ctrl+C to stop"
    
    # Note: In production, this would use Telegram Bot API getUpdates
    # or be triggered by OpenClaw's message handler
    
    log "Listener ready. Waiting for signals..."
}

# If signal text provided as argument, process it directly
if [ -n "$1" ]; then
    process_signal "$1" "manual"
else
    main
fi
