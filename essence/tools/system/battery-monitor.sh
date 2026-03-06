#!/data/data/com.termux/files/usr/bin/bash
# Battery Monitor - Standalone script
# Alerts when battery below 20%

LOG_FILE="/data/data/com.termux/files/home/.openclaw/logs/battery.log"
ALERT_SENT_FILE="/data/data/com.termux/files/home/.openclaw/.battery_alert_sent"

mkdir -p "$(dirname "$LOG_FILE")"

# Get battery info
LEVEL=$(cat /sys/class/power_supply/battery/capacity 2>/dev/null || echo "unknown")
STATUS=$(cat /sys/class/power_supply/battery/status 2>/dev/null || echo "unknown")
TEMP=$(cat /sys/class/power_supply/battery/temp 2>/dev/null || echo "unknown")
VOLTAGE=$(cat /sys/class/power_supply/battery/voltage_now 2>/dev/null || echo "unknown")

# Log current state
echo "[$(date -Iseconds)] Level: ${LEVEL}%, Status: ${STATUS}, Temp: ${TEMP}, Voltage: ${VOLTAGE}" >> "$LOG_FILE"

# Check if alert needed
if [[ "$LEVEL" != "unknown" && "$LEVEL" -lt 20 && "$STATUS" != "Charging" ]]; then
    # Check if we already sent alert recently (within 1 hour)
    if [[ -f "$ALERT_SENT_FILE" ]]; then
        LAST_ALERT=$(stat -c %Y "$ALERT_SENT_FILE" 2>/dev/null || echo 0)
        NOW=$(date +%s)
        DIFF=$((NOW - LAST_ALERT))
        
        if [[ $DIFF -lt 3600 ]]; then
            echo "Alert already sent recently (${DIFF}s ago)"
            exit 0
        fi
    fi
    
    # Send notification
    MESSAGE="⚠️ Dzii: Low Battery Alert\n\nBattery: ${LEVEL}%\nStatus: ${STATUS}\n\nPlease charge your device!"
    
    # Termux notification
    termux-notification \
        --title "⚡ Dzii: Low Battery" \
        --content "Battery at ${LEVEL}%. Please charge!" \
        --priority high \
        --vibrate 500,500,500 \
        --led-color FF0000 \
        --led-on 1000 \
        --led-off 500 2>/dev/null || echo "Termux notification failed"
    
    # TTS announcement
    termux-tts-speak "Attention. Battery is at ${LEVEL} percent. Please charge your device." 2>/dev/null || true
    
    # Log alert
    echo "[$(date -Iseconds)] ⚠️ ALERT SENT: Battery at ${LEVEL}%" >> "$LOG_FILE"
    
    # Mark alert as sent
    touch "$ALERT_SENT_FILE"
    
    # Clear alert file when charging
elif [[ "$STATUS" == "Charging" && -f "$ALERT_SENT_FILE" ]]; then
    rm -f "$ALERT_SENT_FILE"
    echo "[$(date -Iseconds)] Charging detected, alert reset" >> "$LOG_FILE"
    termux-notification --title "⚡ Dzii" --content "Charging started. Alert reset." 2>/dev/null || true
fi

# Also alert at critical 5%
if [[ "$LEVEL" != "unknown" && "$LEVEL" -lt 5 && "$STATUS" != "Charging" ]]; then
    termux-notification \
        --title "🚨 Dzii: CRITICAL BATTERY" \
        --content "Battery at ${LEVEL}%! Charge immediately!" \
        --priority high \
        --vibrate 1000,500,1000,500,1000 \
        2>/dev/null || true
fi
