#!/bin/bash
# AI Supervisor Watchdog - restarts the supervisor if it crashes

LOG_FILE="$HOME/.openclaw/ai_supervisor/logs/supervisor.log"
SCRIPT="$HOME/.openclaw/ai_supervisor/felix_ai_supervisor.py"

echo "[WATCHDOG] Starting AI Supervisor watchdog..."
echo "[WATCHDOG] Log file: $LOG_FILE"

while true; do
    echo "[WATCHDOG] Starting AI Supervisor at $(date)"
    
    # Start AI Supervisor in foreground (watchdog will restart if it exits)
    python3 "$SCRIPT" >> "$LOG_FILE" 2>&1
    
    EXIT_CODE=$?
    echo "[WATCHDOG] AI Supervisor exited with code $EXIT_CODE at $(date)"
    echo "[WATCHDOG] Restarting in 5 seconds..."
    sleep 5
done
