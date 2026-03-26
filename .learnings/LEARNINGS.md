## [LRN-20250324-001] IG API Position Close Fix

**Logged**: 2026-03-24T17:50:00+02:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
IG API DELETE /positions/otc/{dealId} endpoint returns 404. The correct method is to place an opposing market order to close positions.

### Details
**Problem:**
- Old approach: `DELETE /positions/otc/{dealId}` with body containing direction/size
- Result: HTTP 404 error, positions not closed
- Deal IDs from positions endpoint were valid (verified via GET /positions/{dealId})

**Root Cause:**
IG API changed or the DELETE endpoint doesn't work as documented for CFD positions. The proper method is to place a new order in the opposite direction with `forceOpen: false`.

**Solution:**
1. First verify position exists via `GET /positions/{dealId}`
2. Extract position details: epic, direction, size, currency
3. Determine opposite direction (BUY→SELL, SELL→BUY)
4. Place opposing order via `POST /positions/otc` with:
   - `forceOpen: false` (required)
   - `expiry: "-"` (required for spot/CFD)
   - `currencyCode` (required)
   - `guaranteedStop: false`

### Code Change
```bash
# OLD (broken)
curl -X DELETE \
  -d '{"direction": "BUY", "size": 1.0, "orderType": "MARKET"}' \
  "$BASE_URL/positions/otc/$deal_id"

# NEW (working)
# 1. Verify position
curl -X GET "$BASE_URL/positions/$deal_id"

# 2. Place opposing order
curl -X POST \
  -d '{
    "epic": "CS.D.GBPUSD.CFD.IP",
    "direction": "BUY",
    "size": 1.0,
    "orderType": "MARKET",
    "timeInForce": "EXECUTE_AND_ELIMINATE",
    "forceOpen": false,
    "guaranteedStop": false,
    "expiry": "-",
    "currencyCode": "USD"
  }' \
  "$BASE_URL/positions/otc"
```

### Files Modified
- `~/.trading/ig_api.sh` - `close_position()` function rewritten

### Verification
Successfully closed 20 positions that were stuck open for days.

### Resolution
- **Resolved**: 2026-03-24T17:50:00+02:00
- **Commit**: Manual edit to ig_api.sh
- **Notes**: All 20 positions closed successfully, confirmed via positions endpoint returning empty array

### Metadata
- Source: conversation
- Related Files: ~/.trading/ig_api.sh
- Tags: ig-api, trading, positions, fix
- Pattern-Key: ig-api.close-position

---
