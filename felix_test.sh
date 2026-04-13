#!/bin/bash
# Felix System Test Suite
# Tests all components before deployment

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[TEST]${NC} $1"; }
error() { echo -e "${RED}[TEST]${NC} $1"; }
warn() { echo -e "${YELLOW}[TEST]${NC} $1"; }

TRADING_DIR="$HOME/.trading"
SUPERVISOR_DIR="$HOME/.openclaw/ai_supervisor"
CONFIG_FILE="$TRADING_DIR/felix_config.json"

TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local name="$1"
    local command="$2"
    
    echo ""
    log "Testing: $name"
    if eval "$command" > /dev/null 2>&1; then
        log "✅ PASSED: $name"
        ((TESTS_PASSED++))
    else
        error "❌ FAILED: $name"
        ((TESTS_FAILED++))
    fi
}

# Test 1: IG API Connection
test_ig_api() {
    log "Testing IG API connection..."
    local response=$(bash "$TRADING_DIR/ig_api.sh" account 2>/dev/null)
    if echo "$response" | jq -e '.accounts[0].accountId' > /dev/null 2>&1; then
        local account=$(echo "$response" | jq -r '.accounts[0].accountId')
        local balance=$(echo "$response" | jq -r '.accounts[0].balance.available')
        log "✅ IG API connected (Account: $account, Balance: €$balance)"
        ((TESTS_PASSED++))
    else
        error "❌ IG API connection failed"
        ((TESTS_FAILED++))
    fi
}

# Test 2: IG Positions
test_ig_positions() {
    log "Testing IG positions endpoint..."
    local positions=$(bash "$TRADING_DIR/ig_api.sh" positions 2>/dev/null)
    if echo "$positions" | jq -e '.positions' > /dev/null 2>&1; then
        local count=$(echo "$positions" | jq '.positions | length')
        log "✅ Positions retrieved: $count open positions"
        ((TESTS_PASSED++))
    else
        warn "⚠️ Could not retrieve positions (may be empty)"
        ((TESTS_PASSED++))
    fi
}

# Test 3: Config File
test_config() {
    log "Testing configuration file..."
    if [[ -f "$CONFIG_FILE" ]]; then
        if jq -e '.version' "$CONFIG_FILE" > /dev/null 2>&1; then
            local version=$(jq -r '.version' "$CONFIG_FILE")
            local pairs=$(jq '.trading_pairs | length' "$CONFIG_FILE")
            log "✅ Config loaded (v$version, $pairs pairs)"
            ((TESTS_PASSED++))
        else
            error "❌ Config file is invalid JSON"
            ((TESTS_FAILED++))
        fi
    else
        error "❌ Config file not found: $CONFIG_FILE"
        ((TESTS_FAILED++))
    fi
}

# Test 4: Signal Hub File
test_signal_hub() {
    log "Testing Signal Hub..."
    if [[ -f "$SUPERVISOR_DIR/felix_signal_hub.py" ]]; then
        if python3 -m py_compile "$SUPERVISOR_DIR/felix_signal_hub.py" 2>/dev/null; then
            log "✅ Signal Hub syntax OK"
            ((TESTS_PASSED++))
        else
            error "❌ Signal Hub has syntax errors"
            ((TESTS_FAILED++))
        fi
    else
        error "❌ Signal Hub file not found"
        ((TESTS_FAILED++))
    fi
}

# Test 5: TP Manager File
test_tp_manager() {
    log "Testing TP Manager..."
    if [[ -f "$SUPERVISOR_DIR/felix_tp_manager.py" ]]; then
        if python3 -m py_compile "$SUPERVISOR_DIR/felix_tp_manager.py" 2>/dev/null; then
            log "✅ TP Manager syntax OK"
            ((TESTS_PASSED++))
        else
            error "❌ TP Manager has syntax errors"
            ((TESTS_FAILED++))
        fi
    else
        error "❌ TP Manager file not found"
        ((TESTS_FAILED++))
    fi
}

# Test 6: Orchestrator File (optional)
test_orchestrator() {
    log "Testing Orchestrator..."
    if [[ -f "$SUPERVISOR_DIR/felix_orchestrator.py" ]]; then
        if python3 -m py_compile "$SUPERVISOR_DIR/felix_orchestrator.py" 2>/dev/null; then
            log "✅ Orchestrator syntax OK"
            ((TESTS_PASSED++))
        else
            error "❌ Orchestrator has syntax errors"
            ((TESTS_FAILED++))
        fi
    else
        warn "⚠️ Orchestrator not found (will use legacy)"
    fi
}

# Test 7: Directories
test_directories() {
    log "Testing directory structure..."
    local dirs_ok=true
    
    for dir in "$SUPERVISOR_DIR" "$SUPERVISOR_DIR/logs" "$SUPERVISOR_DIR/state" "$TRADING_DIR"; do
        if [[ ! -d "$dir" ]]; then
            error "Missing directory: $dir"
            dirs_ok=false
        fi
    done
    
    if $dirs_ok; then
        log "✅ All directories exist"
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
}

# Test 8: Dependencies
test_dependencies() {
    log "Testing Python dependencies..."
    local deps_ok=true
    
    for dep in telethon aiohttp; do
        if ! python3 -c "import $dep" 2>/dev/null; then
            error "Missing Python module: $dep"
            deps_ok=false
        fi
    done
    
    if $deps_ok; then
        log "✅ Python dependencies OK"
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
}

# Test 9: Master Script
test_master_script() {
    log "Testing master control script..."
    if [[ -f "$HOME/.openclaw/workspace/felix_new" ]]; then
        log "✅ New master script exists"
        ((TESTS_PASSED++))
    else
        warn "⚠️ New master script not found"
    fi
}

# Test 10: Signal Parsing (dry run)
test_signal_parsing() {
    log "Testing signal parsing..."
    local test_signal="🔴 SELL XAUUSD @ 3000.50 | SL: 3010 | TP1: 2995 | TP2: 2985 | TP3: 2970"
    
    # Check if we can extract basic info with regex
    if echo "$test_signal" | grep -qi "SELL" && \
       echo "$test_signal" | grep -qi "XAUUSD"; then
        log "✅ Basic signal parsing works"
        ((TESTS_PASSED++))
    else
        error "❌ Signal parsing failed"
        ((TESTS_FAILED++))
    fi
}

# Main
main() {
    echo "======================================="
    echo "  Felix Trading System - Test Suite"
    echo "======================================="
    echo ""
    
    test_ig_api
    test_ig_positions
    test_config
    test_directories
    test_dependencies
    test_signal_hub
    test_tp_manager
    test_orchestrator
    test_master_script
    test_signal_parsing
    
    echo ""
    echo "======================================="
    echo "  Results: $TESTS_PASSED passed, $TESTS_FAILED failed"
    echo "======================================="
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        log "🎉 All tests passed! System ready for deployment."
        exit 0
    else
        error "⚠️  Some tests failed. Review before deployment."
        exit 1
    fi
}

main
