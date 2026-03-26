# Felix → IG Auto-Trading Architecture

## System Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Telegram   │───▶│   Signal    │───▶│    Risk     │───▶│   IG Exec   │
│ Felix Room  │    │   Parser    │    │  Validator  │    │  (API/UI)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                            │                  │                  │
                            ▼                  ▼                  ▼
                      ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                      │   Signal    │    │  Position   │    │   Trade     │
                      │    Store    │    │  Checker    │    │    Log      │
                      └─────────────┘    └─────────────┘    └─────────────┘
```

---

## 1. Signal Parsing Logic

### 1.1 Input Format (Felix Signals)

Felix signals typically follow this pattern:
```
🇬🇧🇯🇵 GBPJPY
🔵 BUY

📊 Entry Zone: 192.500 - 192.800
🎯 TP1: 193.200
🎯 TP2: 193.500  
🎯 TP3: 194.000
⛔️ SL: 191.800

⚠️ Risk 1-2% per trade
```

### 1.2 Signal Parser Module

```bash
#!/bin/bash
# signal_parser.sh - Extract structured data from Felix signals

parse_felix_signal() {
    local raw_text="$1"
    local signal_id="$2"
    
    # Extract currency pair (flags + symbol)
    local pair=$(echo "$raw_text" | grep -oE '[A-Z]{6}|[A-Z]{3}/[A-Z]{3}' | head -1)
    
    # Extract direction (BUY/SELL)
    local direction=$(echo "$raw_text" | grep -oE 'BUY|SELL' | head -1)
    
    # Extract entry zone or single entry
    local entry=$(echo "$raw_text" | grep -iE 'entry|entry zone' | grep -oE '[0-9]+\.?[0-9]*' | head -1)
    local entry_high=$(echo "$raw_text" | grep -iE 'entry.*-' | grep -oE '[0-9]+\.?[0-9]*' | tail -1)
    
    # Extract stop loss
    local sl=$(echo "$raw_text" | grep -iE 'sl|stop' | grep -oE '[0-9]+\.?[0-9]*' | head -1)
    
    # Extract take profits (multiple)
    local tp1=$(echo "$raw_text" | grep -iE 'tp1|take profit 1' | grep -oE '[0-9]+\.?[0-9]*' | head -1)
    local tp2=$(echo "$raw_text" | grep -iE 'tp2|take profit 2' | grep -oE '[0-9]+\.?[0-9]*' | head -1)
    local tp3=$(echo "$raw_text" | grep -iE 'tp3|take profit 3' | grep -oE '[0-9]+\.?[0-9]*' | head -1)
    
    # Convert pair to IG format (replace / with nothing, ensure correct format)
    local ig_pair=$(echo "$pair" | tr -d '/')
    
    # Build JSON output
    cat <<EOF
{
    "signal_id": "$signal_id",
    "timestamp": "$(date -Iseconds)",
    "pair": "$pair",
    "ig_pair": "$ig_pair",
    "direction": "$direction",
    "entry": "$entry",
    "entry_range": ["$entry", "$entry_high"],
    "stop_loss": "$sl",
    "take_profits": ["$tp1", "$tp2", "$tp3"],
    "status": "parsed",
    "raw_text": "$(echo "$raw_text" | tr '\n' ' ' | sed 's/"/\\"/g')"
}
EOF
}
```

### 1.3 OCR Error Correction

```bash
#!/bin/bash
# ocr_corrector.sh - Fix common OCR mistakes

correct_ocr_errors() {
    local text="$1"
    
    # Common OCR mistakes in trading signals
    local corrections=(
        's/BUYY/BUY/g'
        's/SELLL/SELL/g'
        's/Entryy/Entry/g'
        's/Stopp/Stop/g'
        's/0O/00/g'      # Zero vs O
        's/OO/00/g'
        's/l/1/g'        # lowercase L to 1
        's/,/./g'        # comma to dot for decimals
        's/—/-/g'        # em-dash to hyphen
        's/–/-/g'        # en-dash to hyphen
    )
    
    for correction in "${corrections[@]}"; do
        text=$(echo "$text" | sed "$correction")
    done
    
    echo "$text"
}
```

---

## 2. Risk Management Rules

### 2.1 Risk Configuration

```json
{
    "risk_management": {
        "max_risk_per_trade_pct": 1.0,
        "max_risk_per_day_pct": 3.0,
        "max_open_positions": 5,
        "max_correlated_positions": 2,
        "default_account_balance": 1000,
        "min_position_size": 0.5,
        "max_position_size": 10.0,
        "leverage": 30,
        "correlation_groups": {
            "gbp": ["GBPUSD", "GBPJPY", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD"],
            "usd": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD"],
            "jpy": ["USDJPY", "GBPJPY", "EURJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY"],
            "eur": ["EURUSD", "EURGBP", "EURJPY", "EURAUD", "EURCAD", "EURCHF", "EURNZD"]
        }
    }
}
```

### 2.2 Position Sizing Calculator

```bash
#!/bin/bash
# position_sizer.sh - Calculate position size based on risk

source risk_config.sh

calculate_position_size() {
    local account_balance="$1"
    local entry="$2"
    local stop_loss="$3"
    local direction="$4"
    local risk_pct="${5:-$MAX_RISK_PER_TRADE}"
    
    # Calculate pip/point value based on pair
    local pair="$6"
    local pip_value=$(get_pip_value "$pair")
    
    # Calculate risk amount in account currency
    local risk_amount=$(echo "$account_balance * $risk_pct / 100" | bc -l)
    
    # Calculate stop distance in price
    local stop_distance
    if [ "$direction" = "BUY" ]; then
        stop_distance=$(echo "$entry - $stop_loss" | bc -l)
    else
        stop_distance=$(echo "$stop_loss - $entry" | bc -l)
    fi
    
    # Handle negative/zero distances
    if (( $(echo "$stop_distance <= 0" | bc -l) )); then
        echo "{\"error\": \"Invalid stop loss distance\"}"
        return 1
    fi
    
    # Calculate position size in lots
    # Formula: Risk Amount / (Stop Distance in pips * Pip Value)
    local stop_pips=$(echo "$stop_distance / $pip_value" | bc -l)
    local position_size=$(echo "$risk_amount / ($stop_pips * 10)" | bc -l)
    
    # Round to nearest 0.01 lot
    position_size=$(printf "%.2f" $position_size)
    
    # Apply min/max constraints
    if (( $(echo "$position_size < $MIN_POSITION_SIZE" | bc -l) )); then
        position_size="$MIN_POSITION_SIZE"
    elif (( $(echo "$position_size > $MAX_POSITION_SIZE" | bc -l) )); then
        position_size="$MAX_POSITION_SIZE"
    fi
    
    # Output calculation details
    cat <<EOF
{
    "position_size_lots": "$position_size",
    "risk_amount": "$(printf "%.2f" $risk_amount)",
    "risk_pct": "$risk_pct",
    "stop_distance_pips": "$(printf "%.1f" $stop_pips)",
    "stop_distance_price": "$stop_distance",
    "account_balance": "$account_balance",
    "calculation_valid": true
}
EOF
}

get_pip_value() {
    local pair="$1"
    
    # Define pip values (0.0001 for most, 0.01 for JPY pairs)
    case "$pair" in
        *JPY) echo "0.01" ;;
        XAU*|GOLD*) echo "0.01" ;;
        XAG*|SILVER*) echo "0.001" ;;
        *) echo "0.0001" ;;
    esac
}
```

### 2.3 Daily Risk Tracker

```bash
#!/bin/bash
# daily_risk_tracker.sh - Track daily exposure and limits

DAILY_LOG="$HOME/.trading/daily_risk.log"

check_daily_limits() {
    local new_risk_amount="$1"
    local today=$(date +%Y-%m-%d)
    
    # Read today's total risk
    local today_risk=$(grep "^$today" "$DAILY_LOG" 2>/dev/null | cut -d: -f2 || echo "0")
    local max_daily_risk=$(jq -r '.risk_management.max_risk_per_day_pct' risk_config.json)
    local account_balance=$(get_account_balance)
    local max_daily_amount=$(echo "$account_balance * $max_daily_risk / 100" | bc -l)
    
    local new_total=$(echo "$today_risk + $new_risk_amount" | bc -l)
    
    if (( $(echo "$new_total > $max_daily_amount" | bc -l) )); then
        echo "{\"allowed\": false, \"reason\": \"Daily risk limit exceeded\", \"current\": "$today_risk", \"limit\": "$max_daily_amount\"}"
        return 1
    fi
    
    echo "{\"allowed\": true, \"new_total\": "$new_total", \"remaining\": "$(echo "$max_daily_amount - $new_total" | bc -l)\"}"
}

log_risk_taken() {
    local risk_amount="$1"
    local today=$(date +%Y-%m-%d)
    
    echo "$today:$risk_amount" >> "$DAILY_LOG"
}
```

---

## 3. Position Validation

### 3.1 Position Checker Module

```bash
#!/bin/bash
# position_checker.sh - Check for existing/conflicting positions

IG_POSITIONS_FILE="$HOME/.trading/ig_positions.json"

check_existing_position() {
    local pair="$1"
    local direction="$2"
    
    # Refresh positions from IG
    fetch_ig_positions
    
    # Check for exact same pair position
    local existing=$(jq --arg pair "$pair" '.positions[] | select(.market.instrumentName | contains($pair))' "$IG_POSITIONS_FILE")
    
    if [ -n "$existing" ]; then
        local existing_direction=$(echo "$existing" | jq -r '.position.direction')
        
        if [ "$existing_direction" = "$direction" ]; then
            echo "{\"duplicate\": true, \"reason\": \"Same direction position exists\", \"existing_position\": $existing}"
            return 1
        else
            echo "{\"conflict\": true, \"reason\": \"Opposite position exists - hedge detected\", \"existing_position\": $existing}"
            return 1
        fi
    fi
    
    # Check correlation limits
    check_correlation_limits "$pair"
}

check_correlation_limits() {
    local pair="$1"
    
    local correlation_group=""
    local correlation_json=$(jq -c '.risk_management.correlation_groups' risk_config.json)
    
    # Find which group this pair belongs to
    for group in gbp usd jpy eur; do
        if echo "$correlation_json" | jq -e --arg pair "$pair" --arg group "$group" '.[$group] | contains([$pair])' >/dev/null 2>&1; then
            correlation_group="$group"
            break
        fi
    done
    
    if [ -n "$correlation_group" ]; then
        local max_correlated=$(jq -r '.risk_management.max_correlated_positions' risk_config.json)
        local current_correlated=$(jq --arg group "$correlation_group" '[.positions[] | select(.market.instrumentName | test($group; "i"))] | length' "$IG_POSITIONS_FILE")
        
        if [ "$current_correlated" -ge "$max_correlated" ]; then
            echo "{\"correlation_limit\": true, \"reason\": \"Max correlated positions for $correlation_group reached\", \"current\": $current_correlated, \"limit\": $max_correlated}"
            return 1
        fi
    fi
    
    echo "{\"valid\": true, \"correlation_group\": "$correlation_group\"}"
}

fetch_ig_positions() {
    # This would call IG API or UI automation to get current positions
    # For now, placeholder that would integrate with actual IG fetch
    :
}
```

### 3.2 Signal Deduplication

```bash
#!/bin/bash
# signal_dedup.sh - Prevent processing same signal twice

SIGNAL_HISTORY="$HOME/.trading/signal_history.json"

is_duplicate_signal() {
    local pair="$1"
    local direction="$2"
    local entry="$3"
    
    local window_minutes=60
    local since=$(date -d "$window_minutes minutes ago" +%s)
    
    # Check for similar signals in last hour
    local duplicate=$(jq --arg pair "$pair" \
                        --arg direction "$direction" \
                        --arg entry "$entry" \
                        --argjson since "$since" \
        '[.signals[] | select(.timestamp | fromdateiso8601 >= $since) | 
          select(.pair == $pair and .direction == $direction and .entry == $entry)] | length' \
        "$SIGNAL_HISTORY")
    
    if [ "$duplicate" -gt 0 ]; then
        echo "{\"duplicate\": true, \"reason\": \"Similar signal processed in last hour\"}"
        return 1
    fi
    
    echo "{\"duplicate\": false}"
}

record_signal() {
    local signal_json="$1"
    
    # Add to history, keeping last 1000 signals
    jq --argjson new "$signal_json" '.signals += [$new] | .signals = .signals[-1000:]' \
        "$SIGNAL_HISTORY" > "$SIGNAL_HISTORY.tmp" && mv "$SIGNAL_HISTORY.tmp" "$SIGNAL_HISTORY"
}
```

---

## 4. Execution Flow

### 4.1 Main Trading Controller

```bash
#!/bin/bash
# trading_controller.sh - Main execution orchestrator

CONFIG_DIR="$HOME/.trading"
LOG_FILE="$CONFIG_DIR/trading.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

process_signal() {
    local raw_signal="$1"
    local signal_id=$(uuidgen 2>/dev/null || echo "SIG-$(date +%s)")
    
    log "=== Processing Signal $signal_id ==="
    
    # Step 1: Parse signal
    log "Step 1: Parsing signal..."
    local parsed=$(parse_felix_signal "$raw_signal" "$signal_id")
    
    if [ $? -ne 0 ] || [ -z "$parsed" ]; then
        log "ERROR: Failed to parse signal"
        record_rejection "$signal_id" "parse_error" "$raw_signal"
        return 1
    fi
    
    log "Parsed: $(echo "$parsed" | jq -c '.pair, .direction, .entry')"
    
    # Step 2: Deduplication check
    log "Step 2: Checking for duplicates..."
    local pair=$(echo "$parsed" | jq -r '.pair')
    local direction=$(echo "$parsed" | jq -r '.direction')
    local entry=$(echo "$parsed" | jq -r '.entry')
    
    local dup_check=$(is_duplicate_signal "$pair" "$direction" "$entry")
    if echo "$dup_check" | jq -e '.duplicate' >/dev/null; then
        log "REJECTED: Duplicate signal"
        record_rejection "$signal_id" "duplicate" "$parsed"
        return 1
    fi
    
    # Step 3: Position validation
    log "Step 3: Validating position..."
    local pos_check=$(check_existing_position "$pair" "$direction")
    if echo "$pos_check" | jq -e '.duplicate or .conflict or .correlation_limit' >/dev/null; then
        log "REJECTED: $(echo "$pos_check" | jq -r '.reason')"
        record_rejection "$signal_id" "position_conflict" "$parsed" "$pos_check"
        return 1
    fi
    
    # Step 4: Risk calculation
    log "Step 4: Calculating position size..."
    local account_balance=$(get_account_balance)
    local sl=$(echo "$parsed" | jq -r '.stop_loss')
    
    local sizing=$(calculate_position_size "$account_balance" "$entry" "$sl" "$direction" "1.0" "$pair")
    
    if echo "$sizing" | jq -e '.error' >/dev/null; then
        log "ERROR: Position sizing failed - $(echo "$sizing" | jq -r '.error')"
        return 1
    fi
    
    local position_size=$(echo "$sizing" | jq -r '.position_size_lots')
    log "Position size: $position_size lots"
    
    # Step 5: Daily risk check
    log "Step 5: Checking daily risk limits..."
    local risk_amount=$(echo "$sizing" | jq -r '.risk_amount')
    local risk_check=$(check_daily_limits "$risk_amount")
    
    if echo "$risk_check" | jq -e '.allowed == false' >/dev/null; then
        log "REJECTED: Daily risk limit"
        record_rejection "$signal_id" "daily_limit" "$parsed"
        return 1
    fi
    
    # Step 6: Execute trade
    log "Step 6: Executing trade..."
    local tp1=$(echo "$parsed" | jq -r '.take_profits[0]')
    local tp2=$(echo "$parsed" | jq -r '.take_profits[1]')
    
    local execution=$(execute_trade "$pair" "$direction" "$entry" "$position_size" "$sl" "$tp1" "$tp2")
    
    if echo "$execution" | jq -e '.success' >/dev/null; then
        log "SUCCESS: Trade executed"
        
        # Record in logs
        record_trade "$signal_id" "$parsed" "$sizing" "$execution"
        log_risk_taken "$risk_amount"
        record_signal "$parsed"
        
        # Send notification
        notify_trade "✅ Trade Executed\n$pair $direction\nSize: $position_size lots\nEntry: $entry\nSL: $sl"
        
        return 0
    else
        log "ERROR: Execution failed - $(echo "$execution" | jq -r '.error')"
        record_rejection "$signal_id" "execution_failed" "$parsed" "$execution"
        return 1
    fi
}
```

### 4.2 Execution Adapter (API vs UI)

```bash
#!/bin/bash
# execution_adapter.sh - API execution for ALL pairs

execute_trade() {
    local pair="$1"
    local direction="$2"
    local entry="$3"
    local size="$4"
    local sl="$5"
    local tp1="$6"
    local tp2="$7"
    
    log "Executing $direction $pair via IG API"
    execute_via_api "$pair" "$direction" "$entry" "$size" "$sl" "$tp1" "$tp2"
}

execute_via_api() {
    # ... API execution for all pairs ...
}

get_ig_epic() {
    local pair="$1"
    
    # ALL pairs supported via API
    declare -A epics=(
        # Majors
        ["EURUSD"]="CS.D.EURUSD.CFD.IP"
        ["GBPUSD"]="CS.D.GBPUSD.CFD.IP"
        ["USDJPY"]="CS.D.USDJPY.CFD.IP"
        ["AUDUSD"]="CS.D.AUDUSD.CFD.IP"
        ["USDCAD"]="CS.D.USDCAD.CFD.IP"
        # Crosses
        ["GBPJPY"]="CS.D.GBPJPY.CFD.IP"
        ["EURJPY"]="CS.D.EURJPY.CFD.IP"
        ["EURGBP"]="CS.D.EURGBP.CFD.IP"
        ["GBPCAD"]="CS.D.GBPCAD.CFD.IP"
        ["GBPAUD"]="CS.D.GBPAUD.CFD.IP"
        # Commodities
        ["XAUUSD"]="CS.D.XAUUSD.CFD.IP"
        ["XAGUSD"]="CS.D.XAGUSD.CFD.IP"
        # Indices
        ["US30"]="IX.D.DOW.DAILY.IP"
        ["NAS100"]="IX.D.NASDAQ.DAILY.IP"
    )
    
    echo "${epics[$pair]:-CS.D.${pair}.CFD.IP}"
}
```

---

## 5. Error Handling and Recovery

### 5.1 Error Handler Module

```bash
#!/bin/bash
# error_handler.sh - Centralized error handling and recovery

ERROR_LOG="$HOME/.trading/errors.log"
RECOVERY_ATTEMPTS="$HOME/.trading/recovery_attempts"

handle_error() {
    local error_type="$1"
    local context="$2"
    local signal_id="${3:-unknown}"
    
    log_error "$error_type" "$context" "$signal_id"
    
    case "$error_type" in
        "api_timeout")
            recovery_fallback_to_ui "$context"
            ;;
        "ui_stuck")
            recovery_restart_app "$context"
            ;;
        "position_fetch_failed")
            recovery_use_cached_positions "$context"
            ;;
        "invalid_signal")
            # No recovery - just log and skip
            return 1
            ;;
        "execution_partial")
            recovery_check_partial_fill "$context"
            ;;
        "network_error")
            recovery_retry_with_backoff "$context"
            ;;
        *)
            log "Unknown error type: $error_type"
            return 1
            ;;
    esac
}

log_error() {
    local error_type="$1"
    local context="$2"
    local signal_id="$3"
    
    cat >> "$ERROR_LOG" <<EOF
{
    "timestamp": "$(date -Iseconds)",
    "signal_id": "$signal_id",
    "error_type": "$error_type",
    "context": "$context",
    "stack": "$(caller 0)"
}
EOF
}

recovery_fallback_to_ui() {
    local context="$1"
    log "RECOVERY: Falling back to UI automation"
    # Re-trigger execution via UI
    execute_via_ui_from_context "$context"
}

recovery_restart_app() {
    log "RECOVERY: Restarting IG app"
    bash ~/phone_control.sh open-app com.iggroup.android.cfd
    sleep 3
}

recovery_retry_with_backoff() {
    local context="$1"
    local attempt=$(cat "$RECOVERY_ATTEMPTS" 2>/dev/null || echo "0")
    
    if [ "$attempt" -lt 3 ]; then
        local delay=$((2 ** attempt))
        log "RECOVERY: Retry attempt $attempt, waiting ${delay}s"
        sleep $delay
        echo $((attempt + 1)) > "$RECOVERY_ATTEMPTS"
        # Retry the operation
        return 0
    else
        log "RECOVERY: Max retries exceeded"
        echo "0" > "$RECOVERY_ATTEMPTS"
        return 1
    fi
}

cleanup_on_exit() {
    # Clean up temp files
    rm -f "$HOME/.trading/temp_*.json"
    
    # Close IG app if running
    # adb shell am force-stop com.iggroup.android.cfd 2>/dev/null
    
    log "Cleanup completed"
}

trap cleanup_on_exit EXIT
```

### 5.2 Circuit Breaker

```bash
#!/bin/bash
# circuit_breaker.sh - Prevent cascade failures

CIRCUIT_STATE_FILE="$HOME/.trading/circuit_state"
FAILURE_THRESHOLD=5
RECOVERY_TIME=300  # 5 minutes

check_circuit() {
    local current_state=$(cat "$CIRCUIT_STATE_FILE" 2>/dev/null || echo "CLOSED")
    local failure_count=$(jq -r '.failure_count // 0' "$CIRCUIT_STATE_FILE" 2>/dev/null || echo "0")
    local last_failure=$(jq -r '.last_failure // 0' "$CIRCUIT_STATE_FILE" 2>/dev/null || echo "0")
    local now=$(date +%s)
    
    case "$current_state" in
        "OPEN")
            if [ $((now - last_failure)) -gt $RECOVERY_TIME ]; then
                log "Circuit breaker: Moving to HALF_OPEN"
                echo '{"state": "HALF_OPEN", "failure_count": 0}' > "$CIRCUIT_STATE_FILE"
                return 0
            else
                log "Circuit breaker: OPEN - blocking execution"
                return 1
            fi
            ;;
        "HALF_OPEN")
            log "Circuit breaker: HALF_OPEN - allowing test execution"
            return 0
            ;;
        "CLOSED")
            return 0
            ;;
    esac
}

record_success() {
    echo '{"state": "CLOSED", "failure_count": 0}' > "$CIRCUIT_STATE_FILE"
}

record_failure() {
    local failure_count=$(jq -r '.failure_count // 0' "$CIRCUIT_STATE_FILE" 2>/dev/null || echo "0")
    local new_count=$((failure_count + 1))
    
    if [ "$new_count" -ge "$FAILURE_THRESHOLD" ]; then
        log "Circuit breaker: Opening circuit after $new_count failures"
        echo "{\"state\": \"OPEN\", \"failure_count\": $new_count, \"last_failure\": $(date +%s)}" > "$CIRCUIT_STATE_FILE"
    else
        echo "{\"state\": \"CLOSED\", \"failure_count\": $new_count}" > "$CIRCUIT_STATE_FILE"
    fi
}
```

---

## 6. Trade Logging and Reporting

### 6.1 Trade Logger

```bash
#!/bin/bash
# trade_logger.sh - Comprehensive trade logging

TRADE_LOG="$HOME/.trading/trades.jsonl"
REJECTION_LOG="$HOME/.trading/rejections.jsonl"

record_trade() {
    local signal_id="$1"
    local signal_data="$2"
    local sizing_data="$3"
    local execution_data="$4"
    
    local record=$(cat <<EOF
{
    "timestamp": "$(date -Iseconds)",
    "signal_id": "$signal_id",
    "signal": $signal_data,
    "sizing": $sizing_data,
    "execution": $execution_data,
    "status": "executed",
    "pnl": null,
    "exit_timestamp": null
}
EOF
)
    
    echo "$record" >> "$TRADE_LOG"
}

record_rejection() {
    local signal_id="$1"
    local reason="$2"
    local signal_data="$3"
    local additional_data="${4:-null}"
    
    local record=$(cat <<EOF
{
    "timestamp": "$(date -Iseconds)",
    "signal_id": "$signal_id",
    "reason": "$reason",
    "signal": $signal_data,
    "additional": $additional_data
}
EOF
)
    
    echo "$record" >> "$REJECTION_LOG"
}

update_trade_pnl() {
    local deal_ref="$1"
    local pnl="$2"
    local exit_time="$(date -Iseconds)"
    
    # Update the trade record with P&L
    # Note: In practice, use jq to modify JSONL properly
    log "Updating P&L for $deal_ref: $pnl"
}

generate_daily_report() {
    local date="${1:-$(date +%Y-%m-%d)}"
    
    local trades=$(grep "\"timestamp\":\"$date" "$TRADE_LOG")
    local rejections=$(grep "\"timestamp\":\"$date" "$REJECTION_LOG")
    
    local total_trades=$(echo "$trades" | wc -l)
    local total_rejections=$(echo "$rejections" | wc -l)
    
    cat <<EOF
📊 Daily Trading Report - $date
═══════════════════════════════
Trades Executed: $total_trades
Signals Rejected: $total_rejections

Active Positions: $(get_open_position_count)
Daily Risk Used: $(get_daily_risk_used)%

Recent Trades:
$(echo "$trades" | tail -5 | jq -r '"\(.timestamp) | \(.signal.pair) \(.signal.direction) | Size: \(.sizing.position_size_lots)"')
EOF
}
```

### 6.2 Notification System

```bash
#!/bin/bash
# notifications.sh - Send trade notifications

notify_trade() {
    local message="$1"
    local priority="${2:-normal}"
    
    # Telegram notification via OpenClaw
    message send --message "$message"
    
    # Also send to device notifications
    send_device_notification "$message"
}

send_device_notification() {
    local message="$1"
    
    # Use Android notification via termux-notification
    if command -v termux-notification >/dev/null; then
        termux-notification --title "Trading Bot" --content "$message"
    fi
}

notify_error() {
    local error="$1"
    notify_trade "❌ ERROR: $error" "high"
}

notify_daily_summary() {
    local report=$(generate_daily_report)
    notify_trade "$report"
}
```

---

## 7. Integration with OpenClaw

### 7.1 Telegram Message Handler

```bash
#!/bin/bash
# telegram_handler.sh - Handle incoming Felix signals

FELIX_ROOM_ID="-1001234567890"  # Update with actual room ID

handle_telegram_message() {
    local message_text="$1"
    local chat_id="$2"
    
    # Only process messages from Felix room
    if [ "$chat_id" != "$FELIX_ROOM_ID" ]; then
        return 0
    fi
    
    # Check if message contains trading signal
    if echo "$message_text" | grep -qiE 'BUY|SELL.*[0-9]+\.[0-9]+.*TP.*SL'; then
        log "Detected trading signal in Felix room"
        process_signal "$message_text"
    fi
}
```

### 7.2 Cron/Scheduler Setup

```bash
#!/bin/bash
# setup_scheduler.sh - Setup automated tasks

setup_cron_jobs() {
    local cron_file="$HOME/.trading/crontab"
    
    cat > "$cron_file" <<'EOF'
# Trading Bot Scheduled Tasks

# Daily report at 22:00
0 22 * * * bash $HOME/.trading/notifications.sh notify_daily_summary

# Reset daily risk counter at midnight
0 0 * * * > $HOME/.trading/daily_risk.log

# Position sync every 5 minutes
*/5 * * * * bash $HOME/.trading/position_checker.sh sync_positions

# Health check every hour
0 * * * * bash $HOME/.trading/health_check.sh
EOF
    
    crontab "$cron_file"
}
```

---

## 8. Directory Structure

```
~/.trading/
├── config/
│   ├── risk_config.json       # Risk management settings
│   └── ig_credentials.enc     # Encrypted IG API credentials
├── scripts/
│   ├── signal_parser.sh       # Parse Felix signals
│   ├── position_sizer.sh      # Calculate position sizes
│   ├── position_checker.sh    # Validate positions
│   ├── trading_controller.sh  # Main orchestrator
│   ├── execution_adapter.sh   # API/UI execution
│   ├── error_handler.sh       # Error recovery
│   ├── circuit_breaker.sh     # Circuit breaker pattern
│   └── trade_logger.sh        # Logging
├── data/
│   ├── signal_history.json    # Processed signals
│   ├── ig_positions.json      # Current IG positions
│   ├── trades.jsonl           # Trade log
│   └── rejections.jsonl       # Rejected signals log
├── logs/
│   ├── trading.log            # General log
│   ├── errors.log             # Error log
│   └── api_calls.log          # API request/response
└── state/
    ├── circuit_state          # Circuit breaker state
    ├── daily_risk.log         # Today's risk usage
    └── last_session.json      # Session info
```

---

## 9. Implementation Priority

| Phase | Components | Priority |
|-------|-----------|----------|
| 1 | Signal parser, Position sizer, Basic UI execution | HIGH |
| 2 | Position validation, Trade logging, Notifications | HIGH |
| 3 | Risk tracking, Error handling, Circuit breaker | MEDIUM |
| 4 | IG API integration, Advanced reporting | LOW |

---

## 10. Security Considerations

1. **Credential Storage**: Use Android Keystore or encrypted files for API keys
2. **Signal Verification**: Verify signals from trusted source only
3. **Position Limits**: Hard limits on max exposure
4. **Audit Trail**: All actions logged with timestamps
5. **Kill Switch**: Manual override to stop all trading

```bash
# Emergency stop
emergency_stop() {
    log "EMERGENCY STOP ACTIVATED"
    echo '{"state": "OPEN", "emergency": true}' > "$CIRCUIT_STATE_FILE"
    # Close all open positions if needed
    notify_trade "🚨 EMERGENCY STOP ACTIVATED"
}
```
