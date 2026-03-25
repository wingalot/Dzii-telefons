# Felix AI Trading System - Permanent Fixes & Learnings

## Critical Configuration

### 1. IG API Currency Code
**ALWAYS use counter currency, NOT account currency!**

| Pair | Wrong | Correct |
|------|-------|---------|
| GBPJPY | EUR or USD ❌ | **JPY** ✅ |
| USDJPY | EUR or USD ❌ | **JPY** ✅ |
| EURJPY | EUR or USD ❌ | **JPY** ✅ |
| EURUSD | EUR ❌ | **USD** ✅ |
| GBPUSD | USD ✅ | **USD** ✅ |
| XAUUSD | EUR ❌ | **USD** ✅ |

**Code:** `currency_code` extracted from pair (last 3 letters for JPY, last 3 for others)

### 2. Position Sizing by Pair Type
```
XAUUSD/GOLD: min 0.5 lots
JPY pairs:   min 0.5 lots  
Other forex: min 1.0 lots
```

### 3. Order Verification
**Always verify via confirms endpoint after placing order!**
- Check `dealStatus == "ACCEPTED"`
- Don't trust dealReference alone
- Log verification result

### 4. SL/TP Handling
- **NOT sent to IG API** (causes rejection)
- Used only for local TP Manager monitoring
- IG positions opened without stops
- Local system tracks and manages TP levels

### 5. EPIC Codes
Standard format: `CS.D.{PAIR}.CFD.IP`
- GBPJPY: `CS.D.GBPJPY.CFD.IP`
- EURUSD: `CS.D.EURUSD.CFD.IP`
- XAUUSD: `CS.D.CFDGOLD.CFDGC.IP` (special case)

## System Files

Key files modified (permanent fixes):
- `~/.openclaw/workspace/felix_trader.sh` - Main trading logic
- `~/.trading/ig_api.sh` - IG API client with verification
- `~/.openclaw/ai_supervisor/felix_ai_supervisor.py` - Error handling

## Testing Checklist

After any changes, test:
1. ✅ EURUSD (major pair)
2. ✅ GBPJPY (JPY pair)
3. ✅ XAUUSD (commodity)
4. ✅ Confirm verification works
5. ✅ SL/TP not sent to IG

## Session History

**2026-03-24: JPY Pair Fix**
- Problem: JPY pairs rejected with "UNKNOWN" reason
- Root cause: Wrong currency_code (was USD, should be JPY)
- Solution: Extract counter currency from pair automatically
- Result: All pairs now execute successfully

**Key Learning:** IG API requires counter currency, not account currency!


## 2026-03-25: Position Closing Issue

### Problem
- Cannot close positions via API - status returns AMENDED instead of CLOSED
- IG Demo account has hedging mode enabled
- PUT /positions/otc/{dealId} creates opposite position instead of closing

### Attempted Solutions
1. DELETE method - returns validation.null-not-allowed.request
2. PUT method - returns AMENDED status (creates hedge)
3. Disable hedgingMode via /accounts/preferences - returns SUCCESS but positions still not closable

### Workaround
Close positions manually via IG Trading app or website.

### Future Investigation Needed
- Check if hedging mode change requires re-login or session refresh
- Check if there's a specific force close parameter
- Check if demo account has different behavior than live


## 2026-03-25: Position Closing Solution

### Problem
- PUT /positions/otc/{dealId} returns "AMENDED" (creates hedge position)
- DELETE method returns validation error
- Positions not actually closing

### Solution
Use POST /positions/otc with forceOpen: false

### Correct Close Method
```bash
curl -X POST \
  -H "X-IG-API-KEY: $API_KEY" \
  -H "CST: $CST" \
  -H "X-SECURITY-TOKEN: $XST" \
  -H "IG-ACCOUNT-ID: $ACCOUNT" \
  -H "Version: 2" \
  -d '{
    "epic": "CS.D.GBPUSD.CFD.IP",
    "expiry": "-",
    "direction": "SELL",
    "size": 1,
    "orderType": "MARKET",
    "timeInForce": "EXECUTE_AND_ELIMINATE",
    "forceOpen": false,
    "guaranteedStop": false,
    "currencyCode": "USD"
  }' \
  "https://demo-api.ig.com/gateway/deal/positions/otc"
```

### Key Parameters
- `forceOpen: false` - ESSENTIAL! Closes position instead of hedging
- `timeInForce: "EXECUTE_AND_ELIMINATE"` - Close immediately
- `direction` - Opposite of original position
- `guaranteedStop: false` - Required field
- `currencyCode` - Required field (counter currency)

### Verification
Check confirms endpoint for status: "CLOSED" ✅
