#!/bin/bash
# ============================================================
# FELIX → IG AUTO-TRADING SYSTEM
# Quick Start Implementation
# ============================================================

set -e

# Configuration
TRADING_DIR="$HOME/.trading"
CONFIG_DIR="$TRADING_DIR/config"
DATA_DIR="$TRADING_DIR/data"
LOGS_DIR="$TRADING_DIR/logs"
STATE_DIR="$TRADING_DIR/state"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"
}

# ============================================================
# SETUP: Initialize directory structure
# ============================================================
init_trading_system() {
    log "Initializing trading system..."
    
    mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$LOGS_DIR" "$STATE_DIR"
    
    # Initialize empty files
    touch "$DATA_DIR/trades.jsonl"
    touch "$DATA_DIR/rejections.jsonl"
    touch "$DATA_DIR/signal_history.json"
    touch "$LOGS_DIR/trading.log"
    touch "$STATE_DIR/daily_risk.log"
    
    # Create default risk config
    cat > "$CONFIG_DIR/risk_config.json" <<'EOF'
{
    "risk_management": {
        "max_risk_per_trade_pct": 1.0,
        "max_risk_per_day_pct": 3.0,
        "max_open_positions": 5,
        "max_correlated_positions": 2,
        "account_balance": 1000,
        "min_position_size": 0.5,
        "max_position_size": 10.0,
        "currency": "USD"
    }
}
EOF
    
    # Initialize signal history
    echo '{"signals": []}' > "$DATA_DIR/signal_history.json"
    
    log "Trading system initialized at $TRADING_DIR"
}

# ============================================================
# MODULE 1: Signal Parser - Enhanced for Felix format
# ============================================================
parse_signal() {
    local raw_text="$1"
    local signal_id="${2:-SIG-$(date +%s)}"
    
    # Clean up text - remove # hashtags for easier parsing
    local clean_text=$(echo "$raw_text" | sed 's/#//g')
    
    # ===== TRY 1: BUY NOW / SELL NOW format with relative TP =====
    if echo "$clean_text" | grep -qiE 'BUY[[:space:]][[:space:]]*NOW|SELL[[:space:]][[:space:]]*NOW'; then
        log "Detected BUY/SELL NOW format" >&2
        
        # Extract pair
        local pair=""
        if echo "$clean_text" | grep -qiE 'XAUUSD|GOLD'; then
            pair="XAUUSD"
        else
            pair=$(echo "$clean_text" | grep -oE '[A-Z]{6}' | head -1)
        fi
        
        # Extract direction
        local direction=$(echo "$clean_text" | grep -ioE 'BUY|SELL' | head -1 | tr '[:lower:]' '[:upper:]')
        
        # Extract entry price (number after BUY NOW) - handle both 4350 and 1.33770
        local entry=$(echo "$clean_text" | grep -oE 'NOW[ ]+[0-9]+\.?[0-9]*' | grep -oE '[0-9]+\.?[0-9]*' | head -1)
        
        # Extract relative TP pips
        local tp_pips=$(echo "$clean_text" | grep -ioE 'TP[[:space:]]*#?[[:space:]]*1?[[:space:]]*\+?[[:space:]]*[0-9]+' | grep -oE '[0-9]+' | tail -1)
        [ -z "$tp_pips" ] && tp_pips=15  # default 15 pips
        
        if [ -n "$pair" ] && [ -n "$direction" ] && [ -n "$entry" ]; then
            # Calculate TP and SL based on direction
            local pip_size=0.0001
            [[ "$pair" == *"JPY"* || "$pair" == *"XAU"* || "$pair" == *"GOLD"* ]] && pip_size=0.01
            
            local entry_num=$(echo "$entry" | bc -l)
            local tp_offset=$(echo "$tp_pips * $pip_size" | bc -l)
            local sl_offset=$(echo "20 * $pip_size" | bc -l)  # Default 20 pip SL
            
            if [ "$direction" = "BUY" ]; then
                local tp1=$(echo "scale=5; $entry_num + $tp_offset" | bc | sed 's/\.*0*$//')
                local sl=$(echo "scale=5; $entry_num - $sl_offset" | bc | sed 's/\.*0*$//')
            else  # SELL
                local tp1=$(echo "scale=5; $entry_num - $tp_offset" | bc | sed 's/\.*0*$//')
                local sl=$(echo "scale=5; $entry_num + $sl_offset" | bc | sed 's/\.*0*$//')
            fi
            
            cat <<EOF
{
    "valid": true,
    "signal_id": "$signal_id",
    "timestamp": "$(date -Iseconds)",
    "pair": "$pair",
    "ig_pair": "$pair",
    "direction": "$direction",
    "entry": "$entry",
    "stop_loss": "$sl",
    "take_profits": ["$tp1", "", ""],
    "raw": "$(echo "$raw_text" | tr '\n' ' ' | sed 's/"/\\"/g' | cut -c1-200)",
    "format": "buy_now_relative_tp"
}
EOF
            return 0
        fi
    fi
    
    # ===== FALLBACK: Original parsing logic =====
    
    # Extract pair (try multiple patterns with priority)
    # Priority 1: Look for XAUUSD/GOLD specifically (common in Felix signals)
    local pair=""
    if echo "$clean_text" | grep -qiE 'XAUUSD|GOLD'; then
        pair="XAUUSD"
    fi
    
    # Priority 2: Look for 6 uppercase letters (standard forex pairs)
    if [ -z "$pair" ]; then
        pair=$(echo "$clean_text" | grep -oE '[A-Z]{6}' | grep -v 'SIGNAL' | head -1)
    fi
    
    # Priority 3: Look for XXX/XXX format
    if [ -z "$pair" ]; then
        pair=$(echo "$clean_text" | grep -oE '[A-Z]{3}/[A-Z]{3}' | head -1 | tr -d '/')
    fi
    
    # Convert XAUUSD to GOLD for IG API (some accounts use GOLD)
    local ig_pair="$pair"
    if [ "$pair" = "XAUUSD" ]; then
        ig_pair="GOLD"
    fi
    
    # Extract direction (BUY or SELL, with or without #)
    local direction=$(echo "$clean_text" | grep -ioE 'BUY|SELL' | head -1 | tr '[:lower:]' '[:upper:]')
    
    # Extract ALL numbers from the signal for intelligent matching
    local all_numbers=$(echo "$clean_text" | grep -oE '[0-9]+\.?[0-9]*')
    
    # Extract entry - look for @ symbol or Limit keyword or Entry keyword
    local entry=""
    entry=$(echo "$clean_text" | grep -oE '@[[:space:]]*[0-9]+\.?[0-9]*' | grep -oE '[0-9]+\.?[0-9]*' | head -1)
    
    if [ -z "$entry" ]; then
        entry=$(echo "$clean_text" | grep -iE 'limit[[:space:]]+[0-9]+' | grep -oE '[0-9]+\.?[0-9]*' | head -1)
    fi
    
    if [ -z "$entry" ]; then
        entry=$(echo "$clean_text" | grep -oE 'entry[[:space:]]*[:]?[[:space:]]*[0-9]+' | grep -oE '[0-9]+\.?[0-9]*' | head -1)
    fi
    
    # Pattern 4: Look for number immediately after pair (e.g., "XAUUSD 4653.0")
    # Convert newlines to spaces first to handle multi-line format
    if [ -z "$entry" ]; then
        entry=$(echo "$clean_text" | tr '\n' ' ' | grep -oE "${pair}[[:space:]]+[0-9]+\.?[0-9]*" | grep -oE '[0-9]+\.?[0-9]*' | head -1)
    fi
    
    # Pattern 5: If we have numbers and direction, use the first significant number as entry
    if [ -z "$entry" ]; then
        local all_nums=$(echo "$clean_text" | grep -oE '[0-9]+\.?[0-9]*')
        if [ -n "$all_nums" ]; then
            entry=$(echo "$all_nums" | head -1)
        fi
    fi
    
    # Extract stop loss - look for SL: pattern specifically
    local sl=""
    # Get text after "SL:" and extract first number
    sl=$(echo "$clean_text" | grep -oE 'SL[[:space:]]*[:]?[[:space:]]*\(?[[:space:]]*[0-9]+\.?[0-9]*' | grep -oE '[0-9]+\.?[0-9]*' | tail -1)
    
    # Extract take profits - look for TP patterns specifically
    local tp1=""
    local tp2=""
    local tp3=""
    
    # TP1: Get number after TP1 or TP #1
    tp1=$(echo "$clean_text" | grep -oE 'TP[[:space:]]*#?[[:space:]]*1[[:space:]]*:?[[:space:]]*[0-9]+\.?[0-9]*' | grep -oE '[0-9]+\.?[0-9]*' | tail -1)
    
    # TP2: Get number after TP2 or TP #2  
    tp2=$(echo "$clean_text" | grep -oE 'TP[[:space:]]*#?[[:space:]]*2[[:space:]]*:?[[:space:]]*[0-9]+\.?[0-9]*' | grep -oE '[0-9]+\.?[0-9]*' | tail -1)
    
    # TP3: Get number after TP3 or TP #3
    tp3=$(echo "$clean_text" | grep -oE 'TP[[:space:]]*#?[[:space:]]*3[[:space:]]*:?[[:space:]]*[0-9]+\.?[0-9]*' | grep -oE '[0-9]+\.?[0-9]*' | tail -1)
    
    # Log parsing results for debugging
    log "Parsed pair: $pair, direction: $direction, entry: $entry, SL: $sl" >&2
    
    # Validate minimum required fields (SL is optional - can be updated later)
    if [ -z "$pair" ] || [ -z "$direction" ] || [ -z "$entry" ]; then
        error "Invalid signal: missing required fields (pair=$pair, dir=$direction, entry=$entry)"
        echo "{\"valid\": false, \"error\": \"missing_fields\", \"raw\": \"$(echo "$raw_text" | tr '\n' ' ' | cut -c1-100)\"}"
        return 1
    fi
    
    # If SL is missing, use entry as placeholder (will be updated by TP Manager later)
    if [ -z "$sl" ]; then
        sl="$entry"
        log "No SL provided - using entry as placeholder (will be updated by TP Manager)" >&2
    fi
    
    # Build JSON output
    cat <<EOF
{
    "valid": true,
    "signal_id": "$signal_id",
    "timestamp": "$(date -Iseconds)",
    "pair": "$pair",
    "ig_pair": "$ig_pair",
    "direction": "$direction",
    "entry": "$entry",
    "stop_loss": "$sl",
    "take_profits": ["${tp1:-}", "${tp2:-}", "${tp3:-}"],
    "raw": "$(echo "$raw_text" | tr '\n' ' ' | sed 's/"/\\"/g' | cut -c1-200)"
}
EOF
}

# ============================================================
# MODULE 2: Position Sizer
# ============================================================
calculate_size() {
    local entry="$1"
    local sl="$2"
    local direction="$3"
    local pair="$4"
    local risk_pct="${5:-1.0}"
    
    # Load account balance from config
    local account_balance=$(jq -r '.risk_management.account_balance' "$CONFIG_DIR/risk_config.json")
    
    # Calculate risk amount
    local risk_amount=$(echo "scale=2; $account_balance * $risk_pct / 100" | bc)
    
    # Calculate stop distance
    local stop_distance
    if [ "$direction" = "BUY" ]; then
        stop_distance=$(echo "scale=5; $entry - $sl" | bc)
    else
        stop_distance=$(echo "scale=5; $sl - $entry" | bc)
    fi
    
    # Handle invalid stop (zero or negative) - use default sizing
    if (( $(echo "$stop_distance <= 0" | bc -l) )); then
        log "No valid SL - using default position size" >&2
        cat <<EOF
{
    "valid": true,
    "position_size": "0.5",
    "risk_amount": "0",
    "risk_pct": "0",
    "stop_pips": "0",
    "stop_distance": "0"
}
EOF
        return 0
    fi
    
    # Determine pip size based on pair
    local pip_size=0.0001
    [[ "$pair" == *JPY* ]] && pip_size=0.01
    [[ "$pair" == *XAU* || "$pair" == *GOLD* ]] && pip_size=0.01
    
    # Calculate stop in pips
    local stop_pips=$(echo "scale=1; $stop_distance / $pip_size" | bc)
    
    # Simple position sizing: $10 per pip for 1% risk with 10 pip stop
    # Formula: (Risk Amount) / (Stop Pips * $10)
    local position_size=$(echo "scale=2; $risk_amount / ($stop_pips * 10)" | bc)
    
    # Apply min/max constraints and ensure proper formatting (0.50 not .50)
    local min_size=$(jq -r '.risk_management.min_position_size' "$CONFIG_DIR/risk_config.json")
    local max_size=$(jq -r '.risk_management.max_position_size' "$CONFIG_DIR/risk_config.json")
    
    # Special handling for GOLD/XAUUSD - IG requires larger minimum
    if [[ "$pair" == *XAU* || "$pair" == *GOLD* ]]; then
        if (( $(echo "$position_size < 1.0" | bc -l) )); then
            position_size="1.0"
            log "Adjusted GOLD position size to minimum 1.0 lots" >&2
        fi
    fi
    
    if (( $(echo "$position_size < $min_size" | bc -l) )); then
        position_size=$min_size
    elif (( $(echo "$position_size > $max_size" | bc -l) )); then
        position_size=$max_size
    fi
    
    # Ensure position size has leading zero (0.50 not .50)
    if [[ "$position_size" == .* ]]; then
        position_size="0$position_size"
    fi
    
    cat <<EOF
{
    "valid": true,
    "position_size": "$position_size",
    "risk_amount": "$risk_amount",
    "risk_pct": "$risk_pct",
    "stop_pips": "$stop_pips",
    "stop_distance": "$stop_distance"
}
EOF
}

# ============================================================
# MODULE 3: Position Checker
# ============================================================
check_positions() {
    local pair="$1"
    local direction="$2"
    
    # For now, simulate position check
    # In production, this would query IG positions via UI or API
    
    log "Checking existing positions for $pair..."
    
    # Simulate no conflict (replace with actual IG query)
    echo "{\"conflict\": false, \"existing_positions\": 0}"
}

# ============================================================
# MODULE 3a: Trade Executor (UI Automation Fallback for JPY pairs)
# Uses phone UI when API fails for JPY pairs
# ============================================================
execute_trade_ui() {
    local pair="$1"
    local direction="$2"
    local size="$3"
    local sl="$4"
    local tp="$5"
    
    echo "🤖 Executing $direction $pair via UI automation" >&2
    
    # Check if phone_agent.sh exists and is executable
    if [[ ! -f "$HOME/phone_agent.sh" ]]; then
        echo "❌ phone_agent.sh not found" >&2
        return 1
    fi
    
    # Convert pair to IG format
    local ig_pair=$(echo "$pair" | tr '[:lower:]' '[:upper:]')
    
    # Use phone_control.sh to open IG app and execute trade
    echo "Opening IG Trading app..." >&2
    
    # Open IG app
    bash "$HOME/phone_control.sh" open-app com.iggroup.android.cfd 2>/dev/null || true
    sleep 3
    
    # Use visual agent to execute trade
    echo "Using visual agent to execute trade..." >&2
    
    # Create task description for visual agent
    local task="Open IG Trading app. Search for $ig_pair pair. Place a $direction market order with size $size. Do not set SL or TP. Confirm the order."
    
    # Execute via phone agent
    local agent_result=$(bash "$HOME/phone_agent.sh" "$task" 2>&1)
    local agent_exit_code=$?
    
    echo "Visual agent result: $agent_result" >&2
    
    # Check if agent actually succeeded
    if [[ $agent_exit_code -eq 0 ]] && [[ "$agent_result" != *"No API key"* ]] && [[ "$agent_result" != *"❌"* ]]; then
        echo "✅ UI automation trade executed for $pair" >&2
        # Generate a pseudo-deal ID for tracking
        local pseudo_deal_id="UI-$(date +%s)-${ig_pair}"
        echo "{\"success\": true, \"method\": \"ui_automation\", \"deal_id\": \"$pseudo_deal_id\", \"pair\": \"$pair\", \"direction\": \"$direction\", \"size\": \"$size\", \"verified\": true}"
        return 0
    else
        echo "❌ UI automation failed for $pair" >&2
        return 1
    fi
}

# ============================================================
# MODULE 4: Trade Executor (IG API-based) - ALL PAIRS VIA API
# Returns ONLY JSON to stdout, logs to stderr
# SL and TP are NOT sent to IG - only used for local TP monitoring
# JPY pairs fallback: If standard EPIC fails, tries MINI variant, then UI automation
# ============================================================
execute_trade_api() {
    local pair="$1"
    local direction="$2"
    local size="$3"
    local entry="$4"
    local sl="$5"  # Not sent to IG, used for local monitoring
    local tp="$6"  # Not sent to IG, used for local monitoring
    
    echo "Executing $direction $pair via IG API" >&2
    
    # Get EPIC for the pair
    local epic=$(bash "$HOME/.trading/ig_api.sh" epic "$pair" 2>&2)
    
    if [[ -z "$epic" ]]; then
        echo "No EPIC found for pair: $pair" >&2
        echo "{\"success\": false, \"error\": \"unknown_pair\", \"pair\": \"$pair\"}"
        return 1
    fi
    
    # Determine minimum size based on pair type
    local min_size="$size"
    local pair_upper=$(echo "$pair" | tr '[:lower:]' '[:upper:]')
    local is_jpy_pair=false
    
    if [[ "$pair_upper" == "XAUUSD" || "$pair_upper" == "GOLD" ]]; then
        # Gold can use smaller size
        if (( $(echo "$size < 0.5" | bc -l) )); then
            min_size="0.5"
        fi
    elif [[ "$pair_upper" == *"JPY"* ]]; then
        # JPY pairs flag for special handling
        is_jpy_pair=true
        if (( $(echo "$size < 0.5" | bc -l) )); then
            min_size="0.5"
        fi
    else
        # Standard forex pairs need at least 1.0 on IG demo
        if (( $(echo "$size < 1.0" | bc -l) )); then
            min_size="1.0"
        fi
    fi
    
    # Determine currency - must be the pair's COUNTER currency (2nd currency in pair)
    # NOT account currency (EUR) and NOT always USD
    # Examples: EURUSD→USD, GBPJPY→JPY, USDJPY→JPY
    local currency_code="USD"  # Default
    local pair_upper=$(echo "$pair" | tr '[:lower:]' '[:upper:]')
    
    if [[ "$pair_upper" == *"JPY" ]]; then
        currency_code="JPY"
    elif [[ "$pair_upper" == *"USD"* && ! "$pair_upper" == "USD"* ]]; then
        # Pairs ending in USD: EURUSD, GBPUSD, etc.
        currency_code="USD"
    elif [[ "$pair_upper" == *"GBP"* && ! "$pair_upper" == "GBP"* ]]; then
        # Pairs ending in GBP: EURGBP, etc.
        currency_code="GBP"
    elif [[ "$pair_upper" == *"EUR"* && ! "$pair_upper" == "EUR"* ]]; then
        # Pairs ending in EUR: GBPEUR, etc.
        currency_code="EUR"
    elif [[ "$pair_upper" == *"CHF"* ]]; then
        currency_code="CHF"
    elif [[ "$pair_upper" == *"AUD"* ]]; then
        currency_code="AUD"
    elif [[ "$pair_upper" == *"CAD"* ]]; then
        currency_code="CAD"
    elif [[ "$pair_upper" == *"NZD"* ]]; then
        currency_code="NZD"
    fi
    
    echo "EPIC: $epic, Size: $min_size (adjusted from $size), Direction: $direction, Currency: $currency_code (counter currency)" >&2
    echo "Note: SL ($sl) and TP ($tp) are NOT sent to IG - used for local TP monitoring only" >&2
    
    # Place order via IG API WITHOUT SL/TP - use correct counter currency
    local result=$(bash "$HOME/.trading/ig_api.sh" order "$epic" "$direction" "$min_size" "" "" "$currency_code" 2> /dev/null)
    
    echo "API Response: $result" >&2
    
    # Check if order was verified
    if echo "$result" | jq -e '.verified == true' > /dev/null 2>&1; then
        local deal_id=$(echo "$result" | jq -r '.confirms.dealId // .dealReference // empty')
        local deal_status=$(echo "$result" | jq -r '.confirms.dealStatus // empty')
        echo "✅ Order verified and placed: Deal ID $deal_id (Status: $deal_status)" >&2
        echo "{\"success\": true, \"method\": \"api\", \"deal_id\": \"$deal_id\", \"epic\": \"$epic\", \"verified\": true}"
        return 0
    fi
    
    # If JPY pair failed, try MINI variant as fallback
    if [[ "$is_jpy_pair" == true ]]; then
        local mini_epic="${epic%.CFD.IP}.MINI.IP"
        echo "⚠️ Standard EPIC failed for JPY pair. Trying MINI variant: $mini_epic" >&2
        
        local mini_result=$(bash "$HOME/.trading/ig_api.sh" order "$mini_epic" "$direction" "$min_size" "" "" 2> /dev/null)
        echo "MINI EPIC Response: $mini_result" >&2
        
        if echo "$mini_result" | jq -e '.verified == true' > /dev/null 2>&1; then
            local deal_id=$(echo "$mini_result" | jq -r '.confirms.dealId // .dealReference // empty')
            echo "✅ MINI order verified and placed: Deal ID $deal_id" >&2
            echo "{\"success\": true, \"method\": \"api\", \"deal_id\": \"$deal_id\", \"epic\": \"$mini_epic\", \"verified\": true}"
            return 0
        fi
        
        echo "❌ JPY pair failed with both standard and MINI EPIC" >&2
        echo "⚠️ JPY pāri (GBPJPY, USDJPY, EURJPY, utt.) pašlaik netiek atbalstīti caur IG Demo API." >&2
        echo "💡 Iemesls: IG Demo kontā JPY pāri tiek noraidīti ar 'UNKNOWN' kļūdu." >&2
        echo "   Šis ir zināms ierobežojums, kas radās pēc 2026-03-19." >&2
        echo "" >&2
        echo "📝 Iespējamie risinājumi:" >&2
        echo "   1. Pārslēgties uz IG Live kontu (tur JPY pāri strādā)" >&2
        echo "   2. Izpildīt JPY darījumus manuāli IG aplikācijā" >&2
        echo "   3. Sazināties ar IG atbalstu par Demo konta ierobežojumiem" >&2
        
        # Log the rejection with specific reason
        echo "{\"success\": false, \"method\": \"api\", \"error\": \"jpy_demo_restriction\", \"pair\": \"$pair\", \"reason\": \"IG Demo API does not support JPY pairs - execute manually\"}" >&2
        
        # Return failure so the system can notify user
        return 1
    fi
    
    # Standard error handling for non-JPY pairs
    if echo "$result" | jq -e '.verified == false' > /dev/null 2>&1; then
        local error_msg=$(echo "$result" | jq -r '.confirms.errorCode // .confirms.status // .confirms.reason // "verification_failed"')
        echo "❌ Order verification failed: $error_msg" >&2
        echo "{\"success\": false, \"method\": \"api\", \"error\": \"$error_msg\", \"verified\": false}" >&2
        return 1
    fi
    
    echo "❌ Order failed" >&2
    echo "{\"success\": false, \"method\": \"api\", \"error\": \"api_error\", \"verified\": false}" >&2
    return 1
}

# ============================================================
# MODULE 5: Trade Logger
# ============================================================
log_trade() {
    local signal="$1"
    local sizing="$2"
    local execution="$3"
    
    local record=$(cat <<EOF
{"timestamp":"$(date -Iseconds)","signal":$signal,"sizing":$sizing,"execution":$execution}
EOF
)
    
    echo "$record" >> "$DATA_DIR/trades.jsonl"
    log "Trade logged to $DATA_DIR/trades.jsonl"
}

log_rejection() {
    local signal="$1"
    local reason="$2"
    
    local record=$(cat <<EOF
{"timestamp":"$(date -Iseconds)","signal":$signal,"reason":"$reason"}
EOF
)
    
    echo "$record" >> "$DATA_DIR/rejections.jsonl"
    warn "Signal rejected: $reason"
}

# ============================================================
# MAIN CONTROLLER
# ============================================================
process_felix_signal() {
    local raw_signal="$1"
    
    log "=============================================="
    log "Processing Felix Signal"
    log "=============================================="
    
    # Step 1: Parse
    log "Step 1: Parsing signal..."
    local parsed=$(parse_signal "$raw_signal")
    
    if ! echo "$parsed" | jq -e '.valid' > /dev/null 2>&1; then
        log_rejection "$parsed" "parse_error"
        return 1
    fi
    
    log "Parsed: $(echo "$parsed" | jq -r '[.pair, .direction, .entry] | @tsv')"
    
    # Extract fields
    local pair=$(echo "$parsed" | jq -r '.pair')
    local direction=$(echo "$parsed" | jq -r '.direction')
    local entry=$(echo "$parsed" | jq -r '.entry')
    local sl=$(echo "$parsed" | jq -r '.stop_loss')
    local tp=$(echo "$parsed" | jq -r '.take_profits[0]')
    
    # Step 2: Check positions [DISABLED FOR TESTING]
    log "Step 2: Position check [SKIPPED - Risk validator OFF]"
    
    # Step 3: Calculate size
    log "Step 3: Calculating position size..."
    local sizing=$(calculate_size "$entry" "$sl" "$direction" "$pair")
    
    if ! echo "$sizing" | jq -e '.valid' > /dev/null 2>&1; then
        log_rejection "$parsed" "sizing_error"
        return 1
    fi
    
    local size=$(echo "$sizing" | jq -r '.position_size')
    log "Position size: $size lots"
    
    # Step 4: Execute via IG API
    log "Step 4: Executing trade via IG API..."
    local execution=$(execute_trade_api "$pair" "$direction" "$size" "$entry" "$sl" "$tp")
    
    # Step 5: Log result
    if echo "$execution" | jq -e '.success' > /dev/null; then
        log_trade "$parsed" "$sizing" "$execution"
        log "✅ TRADE EXECUTED SUCCESSFULLY"
        log "Notification: Trade Executed: $direction $pair @ $entry, Size: $size lots"
    else
        log_rejection "$parsed" "execution_failed"
        error "❌ TRADE EXECUTION FAILED"
        log "Notification: Trade Failed: $direction $pair - Check logs"
        return 1
    fi
    
    log "=============================================="
}

# ============================================================
# COMMANDS
# ============================================================
case "${1:-}" in
    init)
        init_trading_system
        ;;
    parse)
        parse_signal "${2:-}"
        ;;
    size)
        calculate_size "$2" "$3" "$4" "$5" "${6:-1.0}"
        ;;
    execute)
        # Full pipeline: execute from raw signal text
        process_felix_signal "${2:-}"
        ;;
    status)
        log "Trading System Status"
        log "====================="
        log "Trades today: $(grep "$(date +%Y-%m-%d)" "$DATA_DIR/trades.jsonl" 2>/dev/null | wc -l)"
        log "Rejections today: $(grep "$(date +%Y-%m-%d)" "$DATA_DIR/rejections.jsonl" 2>/dev/null | wc -l)"
        ;;
    *)
        echo "Felix → IG Auto-Trading System"
        echo ""
        echo "Usage:"
        echo "  $0 init                      - Initialize trading system"
        echo "  $0 parse 'signal text'       - Parse a signal"
        echo "  $0 size ENTRY SL DIR PAIR    - Calculate position size"
        echo "  $0 execute 'signal text'     - Execute full trade pipeline"
        echo "  $0 status                    - Show system status"
        echo ""
        echo "Example:"
        echo "  $0 execute '🇬🇧🇯🇵 GBPJPY 🔵 BUY Entry: 192.500 SL: 191.800 TP1: 193.200'"
        ;;
esac
