# IG Markets API Documentation for AI Supervisor

## Base URLs
- **Demo:** `https://demo-api.ig.com/gateway/deal`
- **Live:** `https://api.ig.com/gateway/deal`

## Authentication

### Session Tokens
After authentication, IG returns 2 tokens in headers:
- `CST` - Client Security Token
- `X-SECURITY-TOKEN` - Session token

Required headers for all requests:
- `X-IG-API-KEY: {your_api_key}`
- `CST: {cst_token}`
- `X-SECURITY-TOKEN: {xst_token}`
- `Version: 2` (for most endpoints)

## Endpoints

### 1. Authentication
```http
POST /session
Headers:
  Content-Type: application/json
  X-IG-API-KEY: {api_key}
Body:
  {"identifier":"{username}","password":"{password}"}
```

### 2. Get Positions
```http
GET /positions
Headers:
  X-IG-API-KEY: {api_key}
  CST: {cst}
  X-SECURITY-TOKEN: {xst}
```

### 3. Open Position
```http
POST /positions/otc
Headers:
  Content-Type: application/json
  X-IG-API-KEY: {api_key}
  CST: {cst}
  X-SECURITY-TOKEN: {xst}
  IG-ACCOUNT-ID: {account_id}
  Version: 2
Body:
  {
    "epic": "CS.D.GBPUSD.CFD.IP",
    "expiry": "-",
    "direction": "BUY",
    "size": 1,
    "orderType": "MARKET",
    "timeInForce": "EXECUTE_AND_ELIMINATE",
    "forceOpen": true,
    "guaranteedStop": false,
    "currencyCode": "USD"
  }
```

### 4. Close Position ⭐ CRITICAL
```http
POST /positions/otc
Headers:
  Content-Type: application/json
  X-IG-API-KEY: {api_key}
  CST: {cst}
  X-SECURITY-TOKEN: {xst}
  IG-ACCOUNT-ID: {account_id}
  Version: 2
Body:
  {
    "epic": "CS.D.GBPUSD.CFD.IP",
    "expiry": "-",
    "direction": "SELL",           // Opposite of original
    "size": 1,
    "orderType": "MARKET",
    "timeInForce": "EXECUTE_AND_ELIMINATE",
    "forceOpen": false,            // ⭐ ESSENTIAL for closing!
    "guaranteedStop": false,
    "currencyCode": "USD"
  }
```

**IMPORTANT:** Use `forceOpen: false` to close position. Using `true` creates hedge!

### 5. Verify Order
```http
GET /confirms/{dealReference}
Headers:
  X-IG-API-KEY: {api_key}
  CST: {cst}
  X-SECURITY-TOKEN: {xst}
```

## Common Errors & Solutions

### error.security.api-key-invalid
- **Cause:** API key expired or invalid
- **Solution:** Generate new API key from IG settings

### validation.null-not-allowed.request
- **Cause:** Missing required field in request body
- **Solution:** Check all required fields are provided

### validation.null-not-allowed.request.guaranteedStop
- **Cause:** Missing `guaranteedStop` field
- **Solution:** Add `"guaranteedStop": false`

### validation.null-not-allowed.request.currencyCode
- **Cause:** Missing `currencyCode` field
- **Solution:** Add `"currencyCode": "USD"` (counter currency)

### Position returns "AMENDED" instead of "CLOSED"
- **Cause:** Using PUT method or `forceOpen: true`
- **Solution:** Use POST with `forceOpen: false`

## Currency Codes
Always use counter currency:
- EURUSD → USD
- GBPUSD → USD
- USDJPY → JPY
- XAUUSD → USD

## EPIC Codes
- EURUSD: `CS.D.EURUSD.CFD.IP`
- GBPUSD: `CS.D.GBPUSD.CFD.IP`
- USDJPY: `CS.D.USDJPY.CFD.IP`
- XAUUSD: `CS.D.CFDGOLD.CFDGC.IP`

## Position Status Values
- `OPENED` - New position created
- `AMENDED` - Position modified (NOT closed)
- `CLOSED` - Position successfully closed
- `ACCEPTED` - Order accepted
- `REJECTED` - Order rejected

## AI Supervisor Actions

When fixing IG API errors:
1. Check error code in response
2. Match against known errors above
3. Apply corresponding fix
4. Retry with corrected parameters
5. Verify via confirms endpoint
6. Log result
