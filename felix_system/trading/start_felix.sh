#!/data/data/com.termux/files/usr/bin/bash
# Start Felix Auto-Trading System

echo "🚀 Starting Felix Auto-Trading System..."

# Kill any existing listeners
pkill -f felix_auto_trader 2>/dev/null
sleep 2

# Start listener in background
setsid python3 ~/.openclaw/telegram/felix_auto_trader.py --listen >> ~/.trading/logs/felix_listener.log 2>&1 < /dev/null &

sleep 3
PID=$(pgrep -f felix_auto_trader | head -1)

if [ -n "$PID" ]; then
    echo "✅ Listener started (PID: $PID)"
    echo "$PID" > ~/.trading/felix_listener.pid
    echo ""
    echo "📊 Status:"
    tail -5 ~/.trading/logs/felix_listener.log | grep -E "Monitoring|Auto|Listening" || echo "Check logs..."
else
    echo "❌ Failed to start listener"
fi
