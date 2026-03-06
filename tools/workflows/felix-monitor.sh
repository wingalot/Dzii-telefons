#!/data/data/com.termux/files/usr/bin/bash
# Felix Monitor - Optimized loop with smart recovery and minimal logging
# Modes: loop (default), single (for cron)

set -uo pipefail

# ===== KONFIGURĀCIJA =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_SCRIPT="${SCRIPT_DIR}/felix-check.sh"
AI_SCRIPT="${SCRIPT_DIR}/felix-smart-screenshot.sh"
STATE_DIR="${HOME}/.felix"
LOG_FILE="${STATE_DIR}/monitor.log"
PID_FILE="${STATE_DIR}/monitor.pid"

# Defaults
CHECK_INTERVAL=${CHECK_INTERVAL:-10}        # Sekundes starp checkiem
MAX_BACKOFF=${MAX_BACKOFF:-300}              # Max backoff (5 min)
LOG_LEVEL=${LOG_LEVEL:-1}                    # 0=silent, 1=signals only, 2=normal, 3=verbose
RECOVERY_INTERVAL=${RECOVERY_INTERVAL:-60}   # Cik bieži mēģināt recovery

# State
CONSECUTIVE_ERRORS=0
LAST_RECOVERY=0
SIGNALS_FOUND=0
START_TIME=$(date +%s)

# ===== FUNKCIJAS =====

# Logging ar līmeņiem
log() {
    local level=$1
    shift
    local msg="$*"
    local ts=$(date '+%H:%M:%S')
    
    # Pārbaudām vai log līmenis atļauj
    [[ $level -gt $LOG_LEVEL ]] && return
    
    # Ierakstām failā
    echo "[$ts] $msg" >> "$LOG_FILE"
    
    # Uz ekrāna (tikai important)
    if [[ $level -le 1 ]] && [[ -t 1 ]]; then
        echo "[$ts] $msg"
    fi
}

# Rotējam log failu ja ir par lielu (>100KB)
rotate_log() {
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt 102400 ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        touch "$LOG_FILE"
        log 2 "Log rotated"
    fi
}

# PID faila pārvaldība
acquire_lock() {
    if [[ -f "$PID_FILE" ]]; then
        local old_pid=$(cat "$PID_FILE" 2>/dev/null || echo 0)
        if kill -0 "$old_pid" 2>/dev/null; then
            echo "⚠️ Monitor already running (PID: $old_pid)"
            exit 1
        else
            # Stale PID file
            rm -f "$PID_FILE"
        fi
    fi
    echo $$ > "$PID_FILE"
}

release_lock() {
    rm -f "$PID_FILE"
}

# Cleanup on exit
cleanup() {
    log 2 "Monitor stopping"
    release_lock
    exit 0
}
trap cleanup EXIT INT TERM

# Aprēķinām backoff laiku pēc error skaita
calculate_backoff() {
    local errors=$1
    local backoff=$((CHECK_INTERVAL * (2 ** errors)))
    [[ $backoff -gt $MAX_BACKOFF ]] && backoff=$MAX_BACKOFF
    echo $backoff
}

# Recovery mehānisms - restartē Telegram ja ir problēmas
attempt_recovery() {
    local now=$(date +%s)
    local time_since_last=$((now - LAST_RECOVERY))
    
    [[ $time_since_last -lt $RECOVERY_INTERVAL ]] && return 1
    
    log 2 "Attempting recovery..."
    LAST_RECOVERY=$now
    
    # Aizveram Telegram
    su -c "am force-stop org.telegram.messenger.web" 2>/dev/null || true
    sleep 2
    
    # Pārbaudām vai check script strādā pēc recovery
    if bash "$CHECK_SCRIPT" > /dev/null 2>&1; then
        log 2 "Recovery successful"
        CONSECUTIVE_ERRORS=0
        return 0
    else
        log 1 "Recovery failed"
        return 1
    fi
}

# Viens check cikls
run_check() {
    local start_ts=$(date +%s)
    
    # Palaižam check
    local check_output
    local check_exit
    
    check_output=$(bash "$CHECK_SCRIPT" 2>&1)
    check_exit=$?
    
    local duration=$(( $(date +%s) - start_ts ))
    
    # Analizējam rezultātu
    case $check_exit in
        0)
            # Nav izmaiņu
            CONSECUTIVE_ERRORS=0
            
            # Log tikai ja verbose
            if [[ "$check_output" == *"NO_CHANGE"* ]]; then
                local hash=$(echo "$check_output" | grep "NO_CHANGE" | cut -d: -f2 | tr -d ' ')
                log 3 "No change (hash:${hash:0:8}) ${duration}s"
            else
                log 3 "No change ${duration}s"
            fi
            return 0
            ;;
            
        1)
            # Jauns signāls!
            CONSECUTIVE_ERRORS=0
            SIGNALS_FOUND=$((SIGNALS_FOUND + 1))
            
            local hash=$(echo "$check_output" | grep "NEW_SIGNAL" | cut -d: -f2 | tr -d ' ')
            log 0 "🚨 NEW SIGNAL DETECTED! (hash:${hash:0:8})"
            
            # Izsaucam AI
            log 1 "📸 Processing signal..."
            local ai_output
            local ai_exit
            
            ai_output=$(bash "$AI_SCRIPT" 2>&1)
            ai_exit=$?
            
            if [[ $ai_exit -eq 0 ]]; then
                log 0 "✅ Signal processed successfully"
                # Izvadām parsēto info
                local signal_info=$(cat "${STATE_DIR}/signal.json" 2>/dev/null | grep -oE '"type":"[^"]+"|"pair":"[^"]+"' | head -2 | tr '\n' ' ' || echo "")
                [[ -n "$signal_info" ]] && log 0 "📊 $signal_info"
            else
                log 1 "⚠️ Signal processing returned $ai_exit"
            fi
            
            return 1
            ;;
            
        2)
            # Error - nepieciešams recovery
            CONSECUTIVE_ERRORS=$((CONSECUTIVE_ERRORS + 1))
            log 1 "❌ Check error (count: $CONSECUTIVE_ERRORS)"
            
            # Mēģinām recovery pēc 3 erroriem
            if [[ $CONSECUTIVE_ERRORS -ge 3 ]]; then
                attempt_recovery
            fi
            
            return 2
            ;;
            
        *)
            # Nezināms exit code
            CONSECUTIVE_ERRORS=$((CONSECUTIVE_ERRORS + 1))
            log 1 "⚠️ Unknown exit code: $check_exit"
            return 2
            ;;
    esac
}

# Statistikas izvade
print_stats() {
    local runtime=$(( $(date +%s) - START_TIME ))
    local hours=$((runtime / 3600))
    local mins=$(((runtime % 3600) / 60))
    
    echo ""
    echo "📊 Monitor Stats:"
    echo "   Runtime: ${hours}h ${mins}m"
    echo "   Signals: $SIGNALS_FOUND"
    echo "   Errors:  $CONSECUTIVE_ERRORS (current streak)"
    echo "   Log:     $LOG_FILE"
    echo ""
}

# ===== GALVENĀ LOĢIKA =====
main() {
    local mode="${MODE:-loop}"
    
    # Init
    mkdir -p "$STATE_DIR"
    rotate_log
    acquire_lock
    
    log 2 "Monitor started (interval: ${CHECK_INTERVAL}s, log_level: $LOG_LEVEL)"
    
    if [[ "$mode" == "single" ]]; then
        # Viens check un beidz (cron mode)
        run_check
        exit $?
    fi
    
    # Loop mode
    echo "🟢 Felix Monitor running"
    echo "   Interval: ${CHECK_INTERVAL}s"
    echo "   Log level: $LOG_LEVEL (0=critical, 1=signals, 2=normal, 3=verbose)"
    echo "   Press Ctrl+C to stop"
    echo ""
    
    while true; do
        local loop_start=$(date +%s)
        
        # Izpildām check
        run_check
        local check_status=$?
        
        # Aprēķinām cik ilgi jāgaida
        local elapsed=$(( $(date +%s) - loop_start ))
        local wait_time
        
        if [[ $check_status -eq 2 ]] && [[ $CONSECUTIVE_ERRORS -gt 0 ]]; then
            # Error - backoff
            wait_time=$(calculate_backoff $CONSECUTIVE_ERRORS)
            log 2 "Backing off: ${wait_time}s (error #$CONSECUTIVE_ERRORS)"
        else
            # Normāls intervals
            wait_time=$CHECK_INTERVAL
        fi
        
        # Noņemam jau pavadīto laiku
        wait_time=$((wait_time - elapsed))
        [[ $wait_time -lt 1 ]] && wait_time=1
        
        sleep $wait_time
    done
}

# Signal handlers
trap 'print_stats; exit 0' USR1

main "$@"
