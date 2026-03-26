# FIX SUPPORTED PAIRS - TODO FOR NEXT SESSION

## Problem Summary
Demo account 'wingalot' only supports EURUSD and GBPUSD via API.
All JPY pairs and cross rates get REJECTED.

## Solution Plan

### Option 1: Hybrid Execution (RECOMMENDED)
Modify `felix_trader.sh` to:
1. Detect pair type
2. Route supported pairs (EURUSD, GBPUSD) via API
3. Route unsupported pairs (JPY, crosses) via UI automation

### Implementation

#### Step 1: Create Pair Router Function
Add to `~/.openclaw/workspace/felix_trader.sh`:

```bash
# Determine execution method based on pair
get_execution_method() {
    local pair="$1"
    
    # API-supported pairs
    case "$pair" in
        "EURUSD"|"GBPUSD")
            echo "api"
            ;;
        "GBPJPY"|"USDJPY"|"GBPCAD"|"XAUUSD"|"GOLD"|"US30"|"NAS100")
            echo "ui"
            ;;
        *)
            # Default to UI for unknown pairs
            echo "ui"
            ;;
    esac
}
```

#### Step 2: Modify Main Execution Flow
Update `process_felix_signal()` to:

```bash
# Step 4: Execute based on pair type
local method=$(get_execution_method "$pair")
log "Execution method: $method"

if [ "$method" = "api" ]; then
    log "Step 4: Executing via IG API..."
    local execution=$(execute_trade_api "$pair" "$direction" "$size" "$entry" "$sl" "$tp")
else
    log "Step 4: Executing via UI automation..."
    local execution=$(execute_trade_ui "$pair" "$direction" "$size" "$entry" "$sl" "$tp")
fi
```

#### Step 3: Test UI Automation
Verify `execute_trade_ui()` works for:
- [ ] GBPJPY
- [ ] USDJPY
- [ ] GBPCAD

### Option 2: Add XAUUSD Support
Test if XAUUSD works via API:
```bash
curl -s -X POST \
  -H "X-IG-API-KEY: $API_KEY" \
  -H "CST: $CST" \
  -H "X-SECURITY-TOKEN: $XST" \
  -H "IG-ACCOUNT-ID: Z68R8U" \
  -d '{"epic":"CS.D.XAUUSD.CFD.IP","direction":"BUY","size":0.5,"orderType":"MARKET","timeInForce":"EXECUTE_AND_ELIMINATE","currencyCode":"USD","guaranteedStop":false,"forceOpen":true,"expiry":"-"}' \
  "https://demo-api.ig.com/gateway/deal/positions/otc"
```

### Option 3: Live Account
If user provides LIVE credentials:
1. Update `ig_config.json` with live credentials
2. Test all pairs
3. Live account typically has full market access

## Commands for Next Session

```bash
# Test current API support
test_pair() {
    local epic="$1"
    local name="$2"
    echo "Testing $name ($epic)..."
    REF=$(curl -s -X POST \
      -H "Content-Type: application/json" \
      -H "X-IG-API-KEY: $(jq -r '.api.key' ~/.trading/config/ig_config.json)" \
      -H "CST: $(jq -r '.cst' ~/.trading/state/ig_session.json)" \
      -H "X-SECURITY-TOKEN: $(jq -r '.xst' ~/.trading/state/ig_session.json)" \
      -H "IG-ACCOUNT-ID: Z68R8U" \
      -d "{\"epic\":\"$epic\",\"direction\":\"BUY\",\"size\":1,\"orderType\":\"MARKET\",\"timeInForce\":\"EXECUTE_AND_ELIMINATE\",\"currencyCode\":\"USD\",\"guaranteedStop\":false,\"forceOpen\":true,\"expiry\":\"-\"}" \
      "https://demo-api.ig.com/gateway/deal/positions/otc" 2>/dev/null | jq -r '.dealReference // "FAILED"')
    
    sleep 1
    curl -s -X GET \
      -H "X-IG-API-KEY: $(jq -r '.api.key' ~/.trading/config/ig_config.json)" \
      -H "CST: $(jq -r '.cst' ~/.trading/state/ig_session.json)" \
      -H "X-SECURITY-TOKEN: $(jq -r '.xst' ~/.trading/state/ig_session.json)" \
      "https://demo-api.ig.com/gateway/deal/confirms/$REF" 2>/dev/null | jq -r '.dealStatus'
}

# Test all pairs
test_pair "CS.D.EURUSD.CFD.IP" "EURUSD"
test_pair "CS.D.GBPUSD.CFD.IP" "GBPUSD"
test_pair "CS.D.GBPJPY.CFD.IP" "GBPJPY"
test_pair "CS.D.USDJPY.CFD.IP" "USDJPY"
test_pair "CS.D.GBPCAD.CFD.IP" "GBPCAD"
test_pair "CS.D.XAUUSD.CFD.IP" "XAUUSD"
```

## Success Criteria

- [ ] EURUSD works via API ✅ (already works)
- [ ] GBPUSD works via API ✅ (already works)
- [ ] GBPJPY works via UI ⚠️ (needs testing)
- [ ] USDJPY works via UI ⚠️ (needs testing)
- [ ] GBPCAD works via UI ⚠️ (needs testing)
- [ ] System automatically routes based on pair
- [ ] All executions logged properly

## Files to Modify

1. `~/.openclaw/workspace/felix_trader.sh`
   - Add `get_execution_method()` function
   - Modify `process_felix_signal()` to use router

2. `~/.trading/ig_api.sh`
   - Add EPIC mappings for new pairs

3. Memory files
   - Update supported pairs list

---
Priority: HIGH
Estimated Time: 30-60 minutes
