# FELIX IG API - TECHNICAL REFERENCE

## API Endpoints Used

### Authentication
```bash
POST https://demo-api.ig.com/gateway/deal/session
Headers:
  - X-IG-API-KEY: {api_key}
  - Content-Type: application/json
Body:
  {"identifier":"wingalot","password":"Parole@123"}

Response Headers:
  - CST: {client_session_token}
  - X-SECURITY-TOKEN: {security_token}
```

### Place Order
```bash
POST https://demo-api.ig.com/gateway/deal/positions/otc
Headers:
  - X-IG-API-KEY: {api_key}
  - CST: {cst_token}
  - X-SECURITY-TOKEN: {xst_token}
  - IG-ACCOUNT-ID: Z68R8U
  - Content-Type: application/json

Body:
{
  "epic": "CS.D.GBPJPY.CFD.IP",
  "direction": "BUY",
  "size": 0.5,
  "orderType": "MARKET",
  "timeInForce": "EXECUTE_AND_ELIMINATE",
  "guaranteedStop": false,
  "forceOpen": true,
  "currencyCode": "USD",
  "expiry": "-",
  "stopLevel": 191.800,
  "limitLevel": 193.200
}

Response:
{
  "dealReference": "ABC123XYZ"
}
```

### Get Positions
```bash
GET https://demo-api.ig.com/gateway/deal/positions
```

### Get Account
```bash
GET https://demo-api.ig.com/gateway/deal/accounts
```

## IG EPIC Mappings

| Pair | EPIC | Market Type |
|------|------|-------------|
| GBPJPY | CS.D.GBPJPY.CFD.IP | CFD |
| EURUSD | CS.D.EURUSD.CFD.IP | CFD |
| GBPUSD | CS.D.GBPUSD.CFD.IP | CFD |
| USDJPY | CS.D.USDJPY.CFD.IP | CFD |
| XAUUSD | CS.D.XAUUSD.CFD.IP | CFD |
| US30 | IX.D.DOW.DAILY.IP | Index |

## Token Management

Tokens are valid for ~5 minutes. The `ig_api.sh` script:
1. Checks for existing session in `~/.trading/state/ig_session.json`
2. Reuses if < 5 minutes old
3. Re-authenticates if expired

Session file format:
```json
{
  "cst": "...",
  "xst": "...",
  "account_id": "Z68R8U",
  "timestamp": 1234567890
}
```

## Error Handling

| Error Code | Meaning | Solution |
|------------|---------|----------|
| validation.null-not-allowed.request.expiry | Missing expiry field | Fixed by adding "expiry": "-" |
| error.security.api-key-invalid | Bad API key | Check config |
| error.security.oauth-token-invalid | Session expired | Will auto-reauth |

## Rate Limits

IG Demo API has generous limits but avoid:
- > 1 request/second sustained
- Concurrent authentication requests

## Last Verified
2026-03-19: API working, trades executing
