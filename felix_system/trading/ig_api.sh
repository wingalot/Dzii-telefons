#!/data/data/com.termux/files/usr/bin/bash
# IG API Client - REST API integration for IG Markets
# Demo environment: https://demo-api.ig.com/gateway/deal

set -e

CONFIG_FILE="$HOME/.trading/config/ig_config.json"
TOKEN_FILE="$HOME/.trading/state/ig_session.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[IG API]${NC} $1" >&2; }
warn() { echo -e "${YELLOW}[IG API]${NC} $1" >&2; }
error() { echo -e "${RED}[IG API]${NC} $1" >&2; }

# Check dependencies
check_deps() {
    if ! command -v curl &> /dev/null; then
        error "curl required but not installed"
        exit 1
    fi
    if ! command -v jq &> /dev/null; then
        error "jq required but not installed"
        exit 1
    fi
}

# Load config
load_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        error "Config not found: $CONFIG_FILE"
        exit 1
    fi
    API_KEY=$(jq -r '.api.key' "$CONFIG_FILE")
    USERNAME=$(jq -r '.api.username' "$CONFIG_FILE")
    PASSWORD=$(jq -r '.api.password' "$CONFIG_FILE")
    BASE_URL=$(jq -r '.api.base_url' "$CONFIG_FILE")
}

# Authenticate and get session token
authenticate() {
    log "Authenticating with IG Demo API..."
    
    local response_file=$(mktemp)
    local headers_file=$(mktemp)
    
    curl -s -D "$headers_file" -X POST \
        -H "Content-Type: application/json" \
        -H "X-IG-API-KEY: $API_KEY" \
        -d "{\"identifier\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
        "$BASE_URL/session" > "$response_file" 2>/dev/null
    
    local response=$(cat "$response_file")
    
    if [[ -z "$response" ]] || echo "$response" | grep -q "errorCode"; then
        error "Authentication failed"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
        rm -f "$response_file" "$headers_file"
        return 1
    fi
    
    # Extract tokens from headers (IG returns CST and X-SECURITY-TOKEN in headers)
    local cst=$(grep -i "^CST:" "$headers_file" | awk '{print $2}' | tr -d '\r')
    local xst=$(grep -i "^X-SECURITY-TOKEN:" "$headers_file" | awk '{print $2}' | tr -d '\r')
    local account_id=$(echo "$response" | jq -r '.currentAccountId // empty')
    
    rm -f "$response_file" "$headers_file"
    
    if [[ -z "$cst" || -z "$xst" ]]; then
        error "Failed to extract session tokens"
        return 1
    fi
    
    # Save session
    jq -n --arg cst "$cst" --arg xst "$xst" --arg account "$account_id" \
        '{cst: $cst, xst: $xst, account_id: $account, timestamp: now}' > "$TOKEN_FILE"
    
    log "Authenticated successfully (Account: $account_id)"
    echo "$response" | jq '.'
}

# Get valid session (reuse if valid, otherwise authenticate)
get_session() {
    if [[ -f "$TOKEN_FILE" ]]; then
        local timestamp=$(jq -r '.timestamp // 0' "$TOKEN_FILE")
        local now=$(date +%s)
        local age=$(echo "$now - $timestamp" | bc)
        if (( $(echo "$age < 300" | bc -l) )); then  # Token valid for 5 minutes
            jq '{cst: .cst, xst: .xst, account_id: .account_id}' "$TOKEN_FILE"
            return 0
        fi
    fi
    authenticate > /dev/null 2>&1
    jq '{cst: .cst, xst: .xst, account_id: .account_id}' "$TOKEN_FILE"
}

# Get account info
get_account() {
    local session=$(get_session)
    local cst=$(echo "$session" | jq -r '.cst')
    local xst=$(echo "$session" | jq -r '.xst')
    
    curl -s -X GET \
        -H "Content-Type: application/json" \
        -H "X-IG-API-KEY: $API_KEY" \
        -H "CST: $cst" \
        -H "X-SECURITY-TOKEN: $xst" \
        "$BASE_URL/accounts" | jq '.'
}

# Get open positions
get_positions() {
    local session=$(get_session)
    local cst=$(echo "$session" | jq -r '.cst')
    local xst=$(echo "$session" | jq -r '.xst')
    
    curl -s -X GET \
        -H "Content-Type: application/json" \
        -H "X-IG-API-KEY: $API_KEY" \
        -H "CST: $cst" \
        -H "X-SECURITY-TOKEN: $xst" \
        "$BASE_URL/positions" | jq '.'
}

# Search for market
search_market() {
    local query="$1"
    local session=$(get_session)
    local cst=$(echo "$session" | jq -r '.cst')
    local xst=$(echo "$session" | jq -r '.xst')
    
    curl -s -X GET \
        -H "Content-Type: application/json" \
        -H "X-IG-API-KEY: $API_KEY" \
        -H "CST: $cst" \
        -H "X-SECURITY-TOKEN: $xst" \
        "$BASE_URL/markets?searchTerm=$query" | jq '.'
}

# Get market details
get_market() {
    local epic="$1"
    local session=$(get_session)
    local cst=$(echo "$session" | jq -r '.cst')
    local xst=$(echo "$session" | jq -r '.xst')
    
    curl -s -X GET \
        -H "Content-Type: application/json" \
        -H "X-IG-API-KEY: $API_KEY" \
        -H "CST: $cst" \
        -H "X-SECURITY-TOKEN: $xst" \
        "$BASE_URL/markets/$epic" | jq '.'
}

# Place order
place_order() {
    local epic="$1"
    local direction="$2"  # BUY or SELL
    local size="$3"
    local stop_level="${4:-}"
    local limit_level="${5:-}"
    local order_type="${6:-MARKET}"  # MARKET or LIMIT
    local entry_price="${7:-}"  # For LIMIT orders
    
    # Extract currency from epic or use pair-specific logic
    local pair=$(echo "$epic" | sed 's/CS.D.//;s/.CFD.IP//;s/.CFD//')
    local currency_code="EUR"  # Default fallback
    
    # Determine counter currency from pair
    case "$pair" in
        *JPY) currency_code="JPY" ;;
        *USD) currency_code="USD" ;;
        *EUR) currency_code="EUR" ;;
        *GBP) currency_code="GBP" ;;
        *CAD) currency_code="CAD" ;;
        *AUD) currency_code="AUD" ;;
        *CHF) currency_code="CHF" ;;
        *NZD) currency_code="NZD" ;;
        *GOLD*|XAUUSD) currency_code="USD" ;;
        *SILVER*|XAGUSD) currency_code="USD" ;;
        *BITCOIN*|BTCUSD) currency_code="USD" ;;
        *) currency_code="EUR" ;;
    esac
    
    local session=$(get_session)
    local cst=$(echo "$session" | jq -r '.cst')
    local xst=$(echo "$session" | jq -r '.xst')
    local account_id=$(echo "$session" | jq -r '.account_id')
    
    # Build base order JSON
    local order
    if [[ "$order_type" == "LIMIT" && -n "$entry_price" ]]; then
        # LIMIT order
        order='{
            "type": "LIMIT",
            "epic": "'"$epic"'",
            "direction": "'"$direction"'",
            "size": '"$size"',
            "orderType": "LIMIT",
            "level": '"$entry_price"',
            "timeInForce": "GOOD_TILL_CANCELLED",
            "guaranteedStop": false,
            "currencyCode": "'"$currency_code"'",
            "expiry": "-"
        }'
        log "Placing LIMIT $direction order: $epic @ $entry_price, Size: $size"
    else
        # MARKET order (default)
        order='{
            "epic": "'"$epic"'",
            "direction": "'"$direction"'",
            "size": '"$size"',
            "orderType": "MARKET",
            "timeInForce": "EXECUTE_AND_ELIMINATE",
            "guaranteedStop": false,
            "forceOpen": true,
            "currencyCode": "'"$currency_code"'",
            "expiry": "-"
        }'
        log "Placing MARKET $direction order: $epic, Size: $size"
    fi
    
    # Add stop if provided
    if [[ -n "$stop_level" ]]; then
        order=$(echo "$order" | jq --arg sl "$stop_level" '. + {stopLevel: ($sl | tonumber)}')
    fi
    
    # Add limit if provided
    if [[ -n "$limit_level" ]]; then
        order=$(echo "$order" | jq --arg tp "$limit_level" '. + {limitLevel: ($tp | tonumber)}')
    fi
    
    log "Placing $direction order: $epic, Size: $size, Currency: $currency_code"
    
    # Determine endpoint based on order type
    local endpoint="$BASE_URL/positions/otc"
    if [[ "$order_type" == "LIMIT" ]]; then
        endpoint="$BASE_URL/workingorders"
        log "Using workingorders endpoint for LIMIT order"
    fi
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "X-IG-API-KEY: $API_KEY" \
        -H "CST: $cst" \
        -H "X-SECURITY-TOKEN: $xst" \
        -H "IG-ACCOUNT-ID: $account_id" \
        -d "$order" \
        "$endpoint" 2>/dev/null)
    
    if echo "$response" | grep -q "errorCode"; then
        error "Order failed"
        echo "$response" | jq '.'
        return 1
    fi
    
    log "Order placed successfully!"
    
    # Verify the order via confirms endpoint
    local deal_ref=$(echo "$response" | jq -r '.dealReference // empty')
    if [[ -n "$deal_ref" ]]; then
        log "Verifying order with deal reference: $deal_ref"
        sleep 1  # Give IG time to process
        local confirms=$(curl -s -X GET \
            -H "Content-Type: application/json" \
            -H "X-IG-API-KEY: $API_KEY" \
            -H "CST: $cst" \
            -H "X-SECURITY-TOKEN: $xst" \
            "$BASE_URL/confirms/$deal_ref" 2>/dev/null)
        
        # Check if confirms shows ACCEPTED status
        if echo "$confirms" | jq -e '.dealStatus == "ACCEPTED"' > /dev/null 2>&1; then
            local deal_id=$(echo "$confirms" | jq -r '.dealId // empty')
            log "Order verified! Deal ID: $deal_id"
            # Return merged response with confirms data
            echo "$response" | jq --argjson confirms "$confirms" '. + {confirms: $confirms, verified: true}'
            return 0
        else
            local error_code=$(echo "$confirms" | jq -r '.errorCode // .status // .reason // "UNKNOWN"')
            error "Order verification failed: $error_code"
            echo "$response" | jq --argjson confirms "$confirms" '. + {confirms: $confirms, verified: false}'
            return 1
        fi
    fi
    
    echo "$response" | jq '.'
}

# Close position
close_position() {
    local deal_id="$1"
    local direction="$2"  # Opposite of original
    local size="$3"
    
    local session=$(get_session)
    local cst=$(echo "$session" | jq -r '.cst')
    local xst=$(echo "$session" | jq -r '.xst')
    local account_id=$(echo "$session" | jq -r '.account_id')
    
    # First verify position exists
    log "Checking position: $deal_id"
    local check_response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        -H "X-IG-API-KEY: $API_KEY" \
        -H "CST: $cst" \
        -H "X-SECURITY-TOKEN: $xst" \
        -H "IG-ACCOUNT-ID: $account_id" \
        -H "Version: 2" \
        "$BASE_URL/positions/$deal_id" 2>/dev/null)
    
    if echo "$check_response" | grep -q "errorCode"; then
        error "Position not found: $deal_id"
        echo "$check_response" | jq '.'
        return 1
    fi
    
    # Get position details for closing
    local epic=$(echo "$check_response" | jq -r '.market.epic')
    local orig_direction=$(echo "$check_response" | jq -r '.position.direction')
    local orig_size=$(echo "$check_response" | jq -r '.position.size')
    local currency=$(echo "$check_response" | jq -r '.position.currency')
    
    # Determine close direction
    if [[ "$orig_direction" == "BUY" ]]; then
        direction="SELL"
    else
        direction="BUY"
    fi
    
    # Use requested size for partial close, or full size if not specified
    local close_size="${3:-$orig_size}"
    
    log "Closing $orig_direction position ($deal_id) with $direction order (size: $close_size)"
    
    # Place opposing order to close
    local order='{
        "epic": "'"$epic"'",
        "direction": "'"$direction"'",
        "size": '"$close_size"',
        "orderType": "MARKET",
        "timeInForce": "EXECUTE_AND_ELIMINATE",
        "forceOpen": false,
        "guaranteedStop": false,
        "expiry": "-",
        "currencyCode": "'"$currency"'"
    }'
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "X-IG-API-KEY: $API_KEY" \
        -H "CST: $cst" \
        -H "X-SECURITY-TOKEN: $xst" \
        -H "IG-ACCOUNT-ID: $account_id" \
        -d "$order" \
        "$BASE_URL/positions/otc" 2>/dev/null)
    
    if echo "$response" | grep -q "errorCode"; then
        error "Failed to close position"
        echo "$response" | jq '.'
        return 1
    fi
    
    log "Close order placed successfully!"
    echo "$response" | jq '.'
}

# Map currency pair to IG EPIC - ALL PAIRS SUPPORTED VIA API
get_epic_for_pair() {
    local pair="$1"
    case "$pair" in
        # Major pairs
        "EURUSD"|"EUR/USD") echo "CS.D.EURUSD.CFD.IP" ;;
        "GBPUSD"|"GBP/USD") echo "CS.D.GBPUSD.CFD.IP" ;;
        "USDJPY"|"USD/JPY") echo "CS.D.USDJPY.CFD.IP" ;;
        "AUDUSD"|"AUD/USD") echo "CS.D.AUDUSD.CFD.IP" ;;
        "USDCAD"|"USD/CAD") echo "CS.D.USDCAD.CFD.IP" ;;
        "USDCHF"|"USD/CHF") echo "CS.D.USDCHF.CFD.IP" ;;
        "NZDUSD"|"NZD/USD") echo "CS.D.NZDUSD.CFD.IP" ;;
        # Cross pairs
        "EURGBP"|"EUR/GBP") echo "CS.D.EURGBP.CFD.IP" ;;
        "EURJPY"|"EUR/JPY") echo "CS.D.EURJPY.CFD.IP" ;;
        "GBPJPY"|"GBP/JPY") echo "CS.D.GBPJPY.CFD.IP" ;;
        "AUDJPY"|"AUD/JPY") echo "CS.D.AUDJPY.CFD.IP" ;;
        "CADJPY"|"CAD/JPY") echo "CS.D.CADJPY.CFD.IP" ;;
        "CHFJPY"|"CHF/JPY") echo "CS.D.CHFJPY.CFD.IP" ;;
        "NZDJPY"|"NZD/JPY") echo "CS.D.NZDJPY.CFD.IP" ;;
        "EURAUD"|"EUR/AUD") echo "CS.D.EURAUD.CFD.IP" ;;
        "EURCAD"|"EUR/CAD") echo "CS.D.EURCAD.CFD.IP" ;;
        "EURNZD"|"EUR/NZD") echo "CS.D.EURNZD.CFD.IP" ;;
        "GBPAUD"|"GBP/AUD") echo "CS.D.GBPAUD.CFD.IP" ;;
        "GBPCAD"|"GBP/CAD") echo "CS.D.GBPCAD.CFD.IP" ;;
        "GBPNZD"|"GBP/NZD") echo "CS.D.GBPNZD.CFD.IP" ;;
        "AUDCAD"|"AUD/CAD") echo "CS.D.AUDCAD.CFD.IP" ;;
        "AUDNZD"|"AUD/NZD") echo "CS.D.AUDNZD.CFD.IP" ;;
        "NZDCAD"|"NZD/CAD") echo "CS.D.NZDCAD.CFD.IP" ;;
        "EURCHF"|"EUR/CHF") echo "CS.D.EURCHF.CFD.IP" ;;
        "GBPCHF"|"GBP/CHF") echo "CS.D.GBPCHF.CFD.IP" ;;
        "AUDCHF"|"AUD/CHF") echo "CS.D.AUDCHF.CFD.IP" ;;
        "CADCHF"|"CAD/CHF") echo "CS.D.CADCHF.CFD.IP" ;;
        "NZDCHF"|"NZD/CHF") echo "CS.D.NZDCHF.CFD.IP" ;;
        # Commodities - using demo-compatible EPICs
        "XAUUSD"|"GOLD"|"XAU/USD") echo "CS.D.CFDGOLD.CFDGC.IP" ;;  # Demo account uses this for Spot Gold
        "XAGUSD"|"SILVER"|"XAG/USD") echo "CS.D.CFDGOLD.CFDGC.IP" ;;  # Use gold EPIC for now
        # Cryptocurrencies
        "BTCUSD"|"BITCOIN"|"BTC/USD") echo "CS.D.BITCOIN.CFD.IP" ;;
        "TAOUSD"|"TAO") echo "CS.D.TAO.CFD.IP" ;;
        # Indices
        "US30"|"DOW"|"DJ30") echo "IX.D.DOW.DAILY.IP" ;;
        "US500"|"SP500"|"SPX") echo "IX.D.SPTRD.DAILY.IP" ;;
        "NAS100"|"NASDAQ"|"NDX") echo "IX.D.NASDAQ.DAILY.IP" ;;
        "UK100"|"FTSE") echo "IX.D.FTSE.DAILY.IP" ;;
        "GER40"|"DAX") echo "IX.D.DAX.DAILY.IP" ;;
        *) echo "" ;;
    esac
}

# Get working orders (pending limit orders)
get_working_orders() {
    local session=$(get_session)
    local cst=$(echo "$session" | jq -r '.cst')
    local xst=$(echo "$session" | jq -r '.xst')
    
    curl -s -X GET \
        -H "Content-Type: application/json" \
        -H "X-IG-API-KEY: $API_KEY" \
        -H "CST: $cst" \
        -H "X-SECURITY-TOKEN: $xst" \
        -H "Version: 2" \
        "$BASE_URL/workingorders" | jq '.'
}

# Delete working order (cancel limit order)
delete_working_order() {
    local deal_id="$1"
    
    local session=$(get_session)
    local cst=$(echo "$session" | jq -r '.cst')
    local xst=$(echo "$session" | jq -r '.xst')
    
    log "Cancelling working order: $deal_id"
    
    local response=$(curl -s -X DELETE \
        -H "Content-Type: application/json" \
        -H "X-IG-API-KEY: $API_KEY" \
        -H "CST: $cst" \
        -H "X-SECURITY-TOKEN: $xst" \
        -H "IG-ACCOUNT-ID: $account_id" \
        -H "Version: 2" \
        "$BASE_URL/workingorders/$deal_id" 2>/dev/null)
    
    echo "$response" | jq '.'
}
main() {
    check_deps
    load_config
    
    case "$1" in
        "auth"|"login")
            authenticate
            ;;
        "account")
            get_account
            ;;
        "positions")
            get_positions
            ;;
        "search")
            search_market "$2"
            ;;
        "market")
            get_market "$2"
            ;;
        "order")
            # Usage: order EPIC DIRECTION SIZE [STOP] [TP] [ORDER_TYPE] [ENTRY_PRICE]
            place_order "$2" "$3" "$4" "$5" "$6" "$7" "$8"
            ;;
        "close")
            close_position "$2" "$3" "$4"
            ;;
        "epic")
            get_epic_for_pair "$2"
            ;;
        "workingorders")
            get_working_orders
            ;;
        "cancel")
            delete_working_order "$2"
            ;;
        *)
            echo "Usage: $0 {auth|account|positions|workingorders|search|market|order|close|epic|cancel}"
            echo ""
            echo "Examples:"
            echo "  $0 auth                              # Authenticate"
            echo "  $0 account                           # Get account info"
            echo "  $0 positions                         # List open positions"
            echo "  $0 workingorders                     # List pending limit orders"
            echo "  $0 search EURUSD                     # Search market"
            echo "  $0 epic GBPJPY                       # Get EPIC code"
            echo "  $0 order CS.D.EURUSD.CFD.IP BUY 1    # Place buy order"
            echo "  $0 cancel DEAL_ID                    # Cancel limit order"
            ;;
    esac
}

main "$@"
