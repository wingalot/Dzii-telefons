#!/bin/bash
# Close duplicate positions via IG API

echo "=============================================="
echo "DUBLIKĀTU POZĪCIJU AIZVĒRŠANA"
echo "=============================================="
echo ""

# Get IG credentials
API_KEY=$(jq -r '.api.key' ~/.trading/config/ig_config.json)

# Get session tokens
SESSION=$(bash ~/.trading/ig_api.sh account 2>/dev/null)
CST=$(echo "$SESSION" | jq -r '.cst // empty')
XST=$(echo "$SESSION" | jq -r '.xst // empty')

if [ -z "$CST" ] || [ -z "$XST" ]; then
    echo "❌ Nevarēja iegūt sesiju"
    exit 1
fi

echo "✅ Sesija iegūta"
echo ""

# Close USDCAD duplicate (DIAAAAWZJWQHEA4 - older one at 1.39154)
echo "🔴 Aizveram USDCAD SELL @ 1.39154 (DIAAAAWZJWQHEA4)..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: $API_KEY" \
  -H "CST: $CST" \
  -H "X-SECURITY-TOKEN: $XST" \
  -d '{
    "epic": "CS.D.USDCAD.CFD.IP",
    "direction": "BUY",
    "size": 1,
    "orderType": "MARKET",
    "timeInForce": "EXECUTE_AND_ELIMINATE",
    "forceOpen": false,
    "guaranteedStop": false,
    "currencyCode": "CAD"
  }' \
  "https://demo-api.ig.com/gateway/deal/positions/otc" | jq -r '.dealReference // .errorCode'

echo ""

# Close GOLD duplicate (DIAAAAW28RN2LAV - older one at 4610.79)
echo "🔴 Aizveram GOLD BUY @ 4610.79 (DIAAAAW28RN2LAV)..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-IG-API-KEY: $API_KEY" \
  -H "CST: $CST" \
  -H "X-SECURITY-TOKEN: $XST" \
  -d '{
    "epic": "CS.D.CFDGOLD.CFDGC.IP",
    "direction": "SELL",
    "size": 1,
    "orderType": "MARKET",
    "timeInForce": "EXECUTE_AND_ELIMINATE",
    "forceOpen": false,
    "guaranteedStop": false,
    "currencyCode": "USD"
  }' \
  "https://demo-api.ig.com/gateway/deal/positions/otc" | jq -r '.dealReference // .errorCode'

echo ""
echo "=============================================="
echo "Gatavs! Pārbaudiet IG Trading app."
echo "=============================================="
