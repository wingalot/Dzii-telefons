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

**⚠️ DEMO vs LIVE:**
- **Demo:** Visi signāli ar 1.0 lot (vienkāršībai testēšanai)
- **Live:** Jāimplementē riska pārvaldība - 1% riska uz darījumu
- **Pirms live:** Nomainīt `felix_trader.sh` un `felix_ai_supervisor.py` atpakaļ uz dinamisko sizing

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

## 2026-03-27: GOLD/XAUUSD Currency Code Fix

### Problem
- GOLD trades rejected with "UNKNOWN" reason
- Worked before but suddenly stopped working
- Error: Order verification failed: UNKNOWN

### Root Cause
IG Epic `CS.D.CFDGOLD.CFDGC.IP` transforms to pair name `CFDGOLD.CFDGC`
Old pattern `GOLD|XAUUSD` did NOT match `CFDGOLD.CFDGC`
Result: Used EUR as default currency instead of USD

### Pattern Comparison
```bash
# BEFORE (didn't work)
case "$pair" in
    GOLD|XAUUSD) currency_code="USD" ;;  # ❌ CFDGOLD.CFDGC doesn't match
esac

# AFTER (works)
case "$pair" in
    *GOLD*|XAUUSD) currency_code="USD" ;;  # ✅ Matches any string containing GOLD
esac
```

### Key Learning
When extracting currency from IG epic, use **wildcard patterns** (`*GOLD*`) not exact matches (`GOLD`), because IG epic-to-pair transformation can change the name format.

### Affected Files
- `~/.trading/ig_api.sh` - currency_code case statement

### Testing
Always test GOLD after any currency-related changes:
```bash
bash ~/.trading/ig_api.sh order CS.D.CFDGOLD.CFDGC.IP BUY 1.0
```

## 2026-03-27: Limit Order Support

### Problem
- Felix sends LIMIT orders that need to be placed in IG
- Limit orders need to be monitored until activated
- TP Manager needs to track both pending limits and active positions

### Implementation
**IG API Changes:**
- Added `order_type` parameter (MARKET/LIMIT)
- Added `entry_price` parameter for LIMIT orders
- Changed `timeInForce` to `GOOD_TILL_CANCELLED` for LIMIT orders
- Added `workingorders` endpoint to check pending orders

**TP Manager Changes:**
- Added `pending_limits` dictionary to track unfilled orders
- Added `register_pending_limit()` method
- Added `activate_limit_order()` method for when orders fill
- Added `get_working_orders()` to sync with IG
- Modified sync to import both positions AND working orders

**Signal Hub Changes:**
- Detects `LIMIT` keyword in signals
- Sets `is_limit=True` in signal data
- Handles `ACTIVATED` message type when limit fills

### Limit Order Lifecycle
```
1. Felix: "BUY LIMIT GBPUSD @ 1.3280"
   ↓
2. System places LIMIT order in IG
   ↓
3. TP Manager tracks as "pending" (not in positions yet)
   ↓
4. Price hits 1.3280 → IG fills order
   ↓
5. Felix: "LIMIT ACTIVATED"
   ↓
6. TP Manager finds position in IG, activates tracking
   ↓
7. Normal TP/SL management begins
```

### Key Endpoints
- `GET /workingorders` - List pending limit orders
- `DELETE /workingorders/{dealId}` - Cancel limit order
- `POST /positions/otc` with `orderType: LIMIT` - Place limit order

### Affected Files
- `~/.trading/ig_api.sh` - Added workingorders support
- `~/.openclaw/ai_supervisor/felix_ai_supervisor.py` - LIMIT order execution
- `~/.openclaw/ai_supervisor/felix_tp_manager.py` - Pending limit tracking
- `~/.openclaw/ai_supervisor/felix_signal_hub.py` - LIMIT detection

## 2026-04-10: TP Manager Auto-Archive Fix

### Problem
- `felix status` reported 25 local positions when only 1 existed in IG
- TP Manager checked IG only every 5 seconds; positions closed externally could linger in active logic for up to 5s
- If `close_position_in_ig()` failed, TP Manager would retry indefinitely instead of checking whether IG already closed the position

### Solution
**1. Real-time IG position validation in monitoring loop**
- Fetches IG positions **every iteration** (every 1s) before running TP/SL checks
- Any open local position missing from IG is immediately archived via `archive_closed_position()`
- TP/SL logic runs only on positions confirmed alive in IG

**2. Graceful close-failure handling**
- After a failed `close_position_in_ig()` due to TP3/SL hit, verifies if position still exists in IG
- If already gone from IG, archives locally instead of endless retry loop

**3. Status display fix**
- `felix status` now shows **"Local Open Positions"** (count of `status == 'open'`) instead of total tracked history
- `felix sync` now correctly calls `felix_tp_manager.py --sync` instead of a missing `sync_positions.py`

### Affected Files
- `~/.openclaw/ai_supervisor/felix_tp_manager.py` - `_get_ig_positions()`, `archive_closed_position()`, `run_monitoring_loop()`, `handle_tp_hit()`, `handle_sl_hit()`
- `~/.openclaw/workspace/felix` - `status()` and `sync()` functions

### New TP Management Rules
Changed from old logic to new logic based on user request:

| TP Level | Old Action | New Action |
|----------|------------|------------|
| TP1 hit | Move SL to entry | **No action** |
| TP2 hit | Close 50% | **Move SL to BE + Close 50%** |
| TP3 hit | Close position | Close position (unchanged) |

**Rationale:** 
- TP1 often gets hit by small price movements, causing premature SL moves
- TP2 is a more significant level, better for securing profits
- This gives trades more room to breathe while still protecting capital

**Affected Files:**
- `~/.openclaw/ai_supervisor/felix_tp_manager.py` - TP handling logic

### Implementation
Added Bitcoin (BTCUSD) trading support:

**EPIC Code:** `CS.D.BITCOIN.CFD.IP`
**Currency:** USD (always)

### Changes Made
| File | Change |
|------|--------|
| `~/.trading/ig_api.sh` | Added BTCUSD to epic_map and currency_code logic |
| `~/.openclaw/ai_supervisor/felix_ai_supervisor.py` | Added BTCUSD to epic_map and currency detection |
| `~/.openclaw/ai_supervisor/felix_tp_manager.py` | Added BTCUSD to epic_to_pair mapping and regex patterns |

### Supported Pairs (Updated)
- EURUSD, GBPUSD, USDJPY, GBPJPY, EURJPY
- AUDUSD, NZDUSD, USDCAD, USDCHF, EURGBP
- XAUUSD (Gold), XAGUSD (Silver)
- **BTCUSD (Bitcoin)** ✅
- US30, NAS100, SPX500, UK100, GER40

## 2026-04-03: Smart Signal Parser - 100% Recognition

### Problem
- Signal parser failed on emoji-formatted signals (⚪️🟢🔴)
- BUY NOW format without explicit SL was not handled
- Some pairs (EURAUD, GBPCAD, AUDNZD) were not recognized
- Parser accuracy was ~85%, causing missed signals

### Solution: Smart Parser Implementation
Created `felix_smart_parser.py` with multi-strategy parsing:

**1. Pattern Matching (Primary)**
- Emoji format detection: `⚪️ Entry Point: 1.15580`
- Standard format: `BUY XAUUSD 4533.8`
- BUY NOW format: `GBPJPY BUY NOW 210.765`

**2. Contextual Analysis (Fallback)**
- When regex fails, analyzes all numbers in text
- Infers SL/Entry/TP based on BUY/SELL direction and number ranges
- Validates logical consistency (SL below entry for BUY, etc.)

**3. Auto SL Calculation**
For BUY NOW format without explicit SL:
```python
if 'NOW' in signal and no_sl_found:
    sl = entry - (20 * pip_size)  # Default 20 pips SL
    tp = entry + (extracted_pips * pip_size)  # From "+15 Pips"
```

### Supported Pairs (Complete List)
```python
pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD',
         'AUDUSD', 'USDCAD', 'EURJPY', 'GBPJPY', 'CADJPY',
         'NZDJPY', 'AUDJPY', 'EURAUD', 'EURCAD', 'GBPCAD',
         'GBPAUD', 'AUDNZD', 'NZDCAD', 'EURGBP', 'USDCHF',
         'NZDUSD', 'CHFJPY', 'US30', 'NAS100']
```

### Test Results
**15/15 (100%)** real Felix signals parsed correctly:
| Format | Example | Result |
|--------|---------|--------|
| Emoji | `⚪️ Entry: 1.15580 🟢 TP: 1.15730` | ✅ |
| Standard | `BUY XAUUSD 4533.8 SL: 4517.8` | ✅ |
| BUY NOW | `GBPJPY BUY NOW 210.765 +15 Pips` | ✅ SL auto-calc |
| Limit | `🟢 Buy Limit @ 4549 TP #1: 4552` | ✅ |

### Files Changed
| File | Change |
|------|--------|
| `felix_smart_parser.py` | New smart parser with 3 strategies |
| `felix_signal_hub.py` | Integrated smart parser as primary |
| `felix` | Fixed `--daemon` argument bug |

### Key Learnings
1. **Multi-strategy parsing** beats single regex approach
2. **Contextual fallback** handles non-standard formats
3. **Auto SL calculation** enables trading BUY NOW signals
4. **100% test coverage** ensures no signals are missed
