# IG Markets API Integration Research Report

## Executive Summary

IG Markets provides both **REST API** and **Streaming API** for programmatic trading. The API allows automation of trades, market data access, account management, and position tracking. This report covers all key aspects needed to integrate IG API for Android/Termux automation.

---

## 1. IG Markets API Overview

### Available APIs

| API Type | Purpose | Protocol |
|----------|---------|----------|
| **REST Trading API** | Execute trades, manage positions, account operations | HTTP/HTTPS (JSON) |
| **Streaming API** | Real-time price feeds, market data | Lightstreamer (WebSocket-like) |

### What You Can Do

- **Trade Execution**: Open/close positions, place orders (market, limit, stop)
- **Market Data**: Get real-time and historical prices
- **Account Management**: View balances, transaction history, open positions
- **Sentiment Analysis**: Access client sentiment data
- **Watchlists**: Manage instrument watchlists

### Asset Classes Supported

- Indices, Forex, Commodities, Shares, Options, Cryptocurrencies, Bonds, Rates

---

## 2. Authentication Methods

### API Key Authentication (Primary Method)

IG uses **API Key + Session Token** authentication (not pure OAuth):

1. **API Key**: Generated in IG web platform (one per account)
2. **Username/Password**: Your IG account credentials
3. **CST Token**: Returned after successful authentication
4. **X-SECURITY-TOKEN**: Session security token

### Session Versions

| Version | Description | Token Lifetime |
|---------|-------------|----------------|
| **v1/v2** | Simple session auth | 6 hours (extended while active) |
| **v3** | Account-specific session | 1 minute (auto-refresh required) |

**Recommendation**: Use **v2 sessions** for simplicity unless you need ISA/SIPP account access.

---

## 3. API Endpoints

### Base URLs

| Environment | URL |
|-------------|-----|
| **DEMO** | `https://demo-api.ig.com/gateway/deal` |
| **LIVE** | `https://api.ig.com/gateway/deal` |

### Key REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/session` | POST | Create session (authenticate) |
| `/session` | DELETE | Logout |
| `/positions` | GET | List open positions |
| `/positions` | POST | Open new position |
| `/positions/{dealId}` | DELETE | Close position |
| `/markets` | GET | Search markets |
| `/markets/{epic}` | GET | Get market details |
| `/prices/{epic}` | GET | Historical prices |
| `/confirms/{dealRef}` | GET | Confirm trade status |
| `/accounts` | GET | Account information |
| `/workingorders` | GET/POST | Manage working orders |

---

## 4. Rate Limits

IG imposes rate limits on API usage. Errors appear as:
- `error.public-api.exceeded-api-key-allowance`
- `error.public-api.exceeded-account-allowance`
- `error.public-api.exceeded-account-trading-allowance`
- `error.public-api.exceeded-account-historical-data-allowance`

### Limit Types

| Limit Type | Description |
|------------|-------------|
| `allowanceAccountOverall` | Per account requests per minute |
| `allowanceAccountTrading` | Per account trading requests per minute |
| `allowanceAccountHistoricalData` | Historical data points per minute |
| `allowanceApplicationOverall` | Overall app requests per minute |

**Note**: DEMO limits are lower than LIVE and can change without notice.

---

## 5. Demo Account Availability

### ✅ YES - Demo API Available

1. Login to IG web platform with **live account**
2. Use account switcher (top-left) to switch to **DEMO**
3. Go to: `My Account > Settings > API Keys`
4. Generate API key for DEMO environment
5. Use DEMO credentials:
   - Username: Your demo username
   - Password: Your demo password
   - API Key: Generated demo key
   - Base URL: `https://demo-api.ig.com/gateway/deal`

Demo accounts come with **€10,000 virtual funds** for testing.

---

## 6. Android/Termux Compatibility

### ✅ YES - Fully Compatible

Since the IG API is a standard **HTTP/HTTPS REST API**, it works perfectly from Android/Termux:

**Recommended Tools for Termux:**

| Tool | Purpose |
|------|---------|
| `curl` | Make HTTP requests to API |
| `jq` | Parse JSON responses |
| `httpie` | Alternative to curl (more user-friendly) |

**No Python Required** - You can use pure shell scripts with curl.

### Example curl Commands for Termux

#### 1. Create Session (Authenticate)

```bash
# Store credentials
USERNAME="your_demo_username"
PASSWORD="your_demo_password"
API_KEY="your_api_key"
BASE_URL="https://demo-api.ig.com/gateway/deal"

# Create session
curl -X POST \
  "${BASE_URL}/session" \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: ${API_KEY}" \
  -H "Version: 2" \
  -d "{\"identifier\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}" \
  -c cookies.txt \
  -D headers.txt

# Extract tokens from response headers
cat headers.txt | grep -i "CST\|X-SECURITY-TOKEN"
```

#### 2. Get Open Positions

```bash
CST="your_cst_token"
SECURITY_TOKEN="your_security_token"

curl -X GET \
  "${BASE_URL}/positions" \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: ${API_KEY}" \
  -H "CST: ${CST}" \
  -H "X-SECURITY-TOKEN: ${SECURITY_TOKEN}" \
  -H "Version: 2" | jq .
```

#### 3. Open a Position (Market Order)

```bash
# Open BUY position on Gold
curl -X POST \
  "${BASE_URL}/positions" \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: ${API_KEY}" \
  -H "CST: ${CST}" \
  -H "X-SECURITY-TOKEN: ${SECURITY_TOKEN}" \
  -H "Version: 2" \
  -d '{
    "currencyCode": "USD",
    "direction": "BUY",
    "epic": "CS.D.USCGC.TODAY.IP",
    "orderType": "MARKET",
    "expiry": "DFB",
    "forceOpen": false,
    "guaranteedStop": false,
    "size": 1.0,
    "limitDistance": null,
    "stopDistance": null
  }' | jq .
```

#### 4. Search Markets

```bash
curl -X GET \
  "${BASE_URL}/markets?searchTerm=gold" \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: ${API_KEY}" \
  -H "CST: ${CST}" \
  -H "X-SECURITY-TOKEN: ${SECURITY_TOKEN}" \
  -H "Version: 1" | jq .
```

#### 5. Close Position

```bash
DEAL_ID="your_deal_id"

curl -X DELETE \
  "${BASE_URL}/positions/${DEAL_ID}" \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: ${API_KEY}" \
  -H "CST: ${CST}" \
  -H "X-SECURITY-TOKEN: ${SECURITY_TOKEN}" \
  -H "Version: 1" \
  -d '{
    "dealId": "'${DEAL_ID}'",
    "direction": "SELL",
    "orderType": "MARKET",
    "size": 1.0
  }' | jq .
```

---

## 7. Alternative: IG FIX API

### FIX API Availability

IG does offer **FIX API** for institutional clients, but:

- **Not available** for standard retail accounts
- Requires **professional client status**
- Higher minimum account balance
- Different onboarding process

**For your use case**, the REST API is the better choice.

---

## 8. Step-by-Step Guide: First API Trade

### Prerequisites

- IG live account (to access demo)
- Termux with curl and jq installed:
  ```bash
  pkg install curl jq
  ```

### Step 1: Generate API Key

1. Login to IG web platform: https://www.ig.com
2. Switch to DEMO account (account switcher top-left)
3. Go to: **My Account > Settings > API Keys**
4. Enter key name (e.g., "TermuxTrading")
5. Click **GENERATE NEW KEY**
6. **SAVE THE KEY** - it won't be shown again

### Step 2: Get Demo Credentials

1. Note your **demo username** (different from live)
2. Know your **demo password**
3. API key from Step 1

### Step 3: Test Authentication Script

Create file `ig_auth.sh`:

```bash
#!/bin/bash

# IG API Configuration
export IG_USERNAME="YOUR_DEMO_USERNAME"
export IG_PASSWORD="YOUR_DEMO_PASSWORD"
export IG_API_KEY="YOUR_API_KEY"
export IG_BASE_URL="https://demo-api.ig.com/gateway/deal"

# Authenticate
echo "Authenticating..."
RESPONSE=$(curl -s -X POST \
  "${IG_BASE_URL}/session" \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: ${IG_API_KEY}" \
  -H "Version: 2" \
  -d "{\"identifier\":\"${IG_USERNAME}\",\"password\":\"${IG_PASSWORD}\"}" \
  -D -)

# Extract tokens
CST=$(echo "$RESPONSE" | grep -i "CST:" | awk '{print $2}' | tr -d '\r')
SECURITY_TOKEN=$(echo "$RESPONSE" | grep -i "X-SECURITY-TOKEN:" | awk '{print $2}' | tr -d '\r')

echo "CST: $CST"
echo "X-SECURITY-TOKEN: $SECURITY_TOKEN"

# Save to file for later use
echo "export CST=$CST" > ig_session.sh
echo "export SECURITY_TOKEN=$SECURITY_TOKEN" >> ig_session.sh

echo "Session saved to ig_session.sh"
```

Run: `bash ig_auth.sh`

### Step 4: Test Market Search

Create file `ig_search.sh`:

```bash
#!/bin/bash

source ig_session.sh

export IG_API_KEY="YOUR_API_KEY"
export IG_BASE_URL="https://demo-api.ig.com/gateway/deal"

echo "Searching for Gold..."
curl -s -X GET \
  "${IG_BASE_URL}/markets?searchTerm=gold" \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: ${IG_API_KEY}" \
  -H "CST: ${CST}" \
  -H "X-SECURITY-TOKEN: ${SECURITY_TOKEN}" \
  -H "Version: 1" | jq '.markets[0] | {epic, instrumentName, bid, offer}'
```

### Step 5: Place First Trade

Create file `ig_trade.sh`:

```bash
#!/bin/bash

source ig_session.sh

export IG_API_KEY="YOUR_API_KEY"
export IG_BASE_URL="https://demo-api.ig.com/gateway/deal"

# Gold epic (Daily Funded Bet)
EPIC="CS.D.USCGC.TODAY.IP"
SIZE=0.5  # Small size for testing

echo "Opening BUY position on Gold..."
RESPONSE=$(curl -s -X POST \
  "${IG_BASE_URL}/positions" \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: ${IG_API_KEY}" \
  -H "CST: ${CST}" \
  -H "X-SECURITY-TOKEN: ${SECURITY_TOKEN}" \
  -H "Version: 2" \
  -d "{
    \"currencyCode\": \"USD\",
    \"direction\": \"BUY\",
    \"epic\": \"${EPIC}\",
    \"orderType\": \"MARKET\",
    \"expiry\": \"DFB\",
    \"forceOpen\": false,
    \"guaranteedStop\": false,
    \"size\": ${SIZE}
  }")

echo "Response:"
echo "$RESPONSE" | jq .

# Extract deal reference
DEAL_REF=$(echo "$RESPONSE" | jq -r '.dealReference')
echo "Deal Reference: $DEAL_REF"

# Check confirmation
sleep 2
echo "Checking confirmation..."
curl -s -X GET \
  "${IG_BASE_URL}/confirms/${DEAL_REF}" \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: ${IG_API_KEY}" \
  -H "CST: ${CST}" \
  -H "X-SECURITY-TOKEN: ${SECURITY_TOKEN}" \
  -H "Version: 1" | jq .
```

### Step 6: Check Positions

Create file `ig_positions.sh`:

```bash
#!/bin/bash

source ig_session.sh

export IG_API_KEY="YOUR_API_KEY"
export IG_BASE_URL="https://demo-api.ig.com/gateway/deal"

echo "Open positions:"
curl -s -X GET \
  "${IG_BASE_URL}/positions" \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: ${IG_API_KEY}" \
  -H "CST: ${CST}" \
  -H "X-SECURITY-TOKEN: ${SECURITY_TOKEN}" \
  -H "Version: 2" | jq '.positions[] | {epic: .market.epic, direction: .position.direction, size: .position.size, openLevel: .position.openLevel}'
```

---

## 9. Integration with Your Existing Setup

### Replacing UI Automation with API Calls

| Current (ADB/UI) | New (API) |
|-----------------|-----------|
| Screenshot + OCR for positions | `GET /positions` endpoint |
| Tap to view orders | `GET /workingorders` endpoint |
| Tap to execute trade | `POST /positions` endpoint |
| Swipe to close position | `DELETE /positions/{dealId}` |
| Read prices from screen | `GET /prices/{epic}` or Streaming API |

### Recommended Architecture

```
Telegram Signal → OpenClaw → curl API call → IG API → Trade executed
                     ↓
              Check positions (GET /positions)
                     ↓
              Confirm trade (GET /confirms/{dealRef})
```

---

## 10. Important Notes & Limitations

### Restrictions

- ❌ **No Direct Market Access (DMA)** via API
- ❌ **No share price information** (shares trading available but without live prices)
- ⚠️ **One API key per account**
- ⚠️ **Demo limits are stricter** than live

### Session Management

- Sessions expire after ~6 hours of inactivity
- Tokens auto-extend while actively using
- Must re-authenticate after connection reset

### Error Handling

Common errors:
- `KeyError: CST` → Wrong credentials or using DEMO creds on LIVE endpoint
- `REJECT_CFD_ORDER_ON_SPREADBET_ACCOUNT` → Wrong expiry format (use `DFB` for spread bets, `-` for CFDs)
- `unauthorised.access.to.equity.exception` → Trying to access restricted market

### Support Contacts

- API Support: **webapisupport@ig.com**
- Status Page: https://status.ig.com/
- Community: https://community.ig.com/

---

## 11. Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| REST API | ✅ Available | Full trading functionality |
| Streaming API | ✅ Available | Real-time prices via Lightstreamer |
| Demo Account | ✅ Available | €10k virtual funds |
| Android/Termux | ✅ Compatible | Use curl + jq |
| FIX API | ❌ Retail not eligible | Institutional only |
| Rate Limits | ⚠️ Yes | Higher limits on LIVE |

### Recommendation

**Migrate from UI automation to REST API** - it's faster, more reliable, and doesn't depend on screen coordinates or UI state. The API can be fully controlled via shell scripts in Termux without Python.

---

## Resources

- IG Labs: https://labs.ig.com/ (currently experiencing some issues)
- Python Library: https://github.com/ig-python/trading-ig
- Documentation: https://trading-ig.readthedocs.io/
- Status: https://status.ig.com/

---

*Report generated: 2026-03-06*
