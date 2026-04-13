#!/bin/bash
# AI Supervisor Auto-Restarter
# Runs AI Supervisor continuously, restarting if it crashes

echo "[$(date)] AI Supervisor restarter starting..."

cd "$HOME/.openclaw/ai_supervisor"

while true; do
    echo "[$(date)] Starting AI Supervisor..."
    
    # Run AI Supervisor
    python3 felix_ai_supervisor.py
    
    EXIT_CODE=$?
    echo "[$(date)] AI Supervisor exited with code $EXIT_CODE"
    
    # Check if there are unprocessed signals
    UNPROCESSED=$(python3 -c "import json; d=json.load(open('state/signal_queue.json')); print(sum(1 for s in d if not s.get('processed')))" 2>/dev/null || echo "0")
    echo "[$(date)] Unprocessed signals: $UNPROCESSED"
    
    # Short delay before restart
    echo "[$(date)] Restarting in 3 seconds..."
    sleep 3
done
