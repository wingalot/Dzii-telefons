# FELIX AUTO-TRADING SYSTEM - MEMORY

## System Overview
**Purpose:** Automated trading from Felix VIP Room signals → IG Broker execution
**Status:** ACTIVE AND RUNNING
**Environment:** DEMO (IG Demo API)
**Risk Level:** HIGH (Risk validator DISABLED per user request)

## Credentials & Access

### IG Demo API
- **Username:** wingalot
- **Password:** Parole@123
- **API Key:** 7b7d5b1ba7913167fe049fa8e2c331eb4131202d
- **Environment:** demo
- **Base URL:** https://demo-api.ig.com/gateway/deal
- **Account ID:** Z68R8U (CFD account)
- **Balance:** ~€99,596 (Demo)
- **Currency:** EUR

### Telegram MTProto
- **API_ID:** 39214400
- **API_HASH:** ce1b295d4cc19db6c9f9804bc8b88c9c
- **Phone:** +37126225767
- **Session:** ~/.openclaw/telegram/felix_listener.session (ACTIVE)
- **Target Channel:** Felix | VIP room (ID: -1001998353092)

### Telegram Bot (Notifications)
- **Token:** 8026525412:AAFcU003bT_AsyGu7zFDbAhYELxQ2mJwQjs
- **User ID:** 395239117 (Nigerian Prince / Elvis)

## File Locations

### Core Scripts
- **Main Trader:** `~/.openclaw/workspace/felix_trader.sh`
- **IG API Client:** `~/.trading/ig_api.sh`
- **Telegram Listener:** `~/.openclaw/telegram/felix_auto_trader.py`
- **Legacy Listener:** `~/.openclaw/telegram/felix_listener.py`

### Configuration
- **IG Config:** `~/.trading/config/ig_config.json`
- **Risk Config:** `~/.trading/config/risk_config.json`

### Data & Logs
- **Trade Log:** `~/.trading/data/trades.jsonl`
- **Rejection Log:** `~/.trading/data/rejections.jsonl`
- **Listener Log:** `~/.trading/logs/felix_listener.log`
- **Trading Log:** `~/.trading/logs/trading.log`

## How It Works

### 1. Signal Detection (Telegram)
- Python script (`felix_auto_trader.py`) runs 24/7
- Connects via MTProto to Telegram
- Listens to Felix | VIP room channel
- Detects trading signals containing:
  - BUY or SELL direction
  - Currency pair (GBPJPY, EURUSD, etc.)

### 2. Signal Parsing
- Extracts: Pair, Direction, Entry, SL, TP
- Validates minimum required fields
- Converts pair to IG EPIC format

### 3. Position Sizing
- Account balance: €10,000 (configurable)
- Risk per trade: 1% (configurable)
- Min position: 0.5 lots
- Max position: 10 lots
- Formula: Risk Amount / (Stop Pips × $10)

### 4. Trade Execution (IG API)
- Authenticates with CST/XST tokens
- Places MARKET order via REST API
- Sets stop loss and take profit levels
- Returns deal reference

### 5. Notifications
- Sends confirmation to user's Telegram
- Logs all trades to JSONL file

## Current Configuration

### Enabled Features
- ✅ Auto-execute: ENABLED
- ✅ IG API Executor: ACTIVE
- ✅ Telegram Listener: RUNNING
- ✅ Position Sizer: ACTIVE

### Disabled Features
- ❌ Risk Validator: DISABLED (per user request)
- ❌ Position Conflict Check: DISABLED
- ❌ Correlation Limits: DISABLED

### Trading Parameters
```json
{
  "max_risk_per_trade_pct": 1.0,
  "max_risk_per_day_pct": 3.0,
  "max_open_positions": 5,
  "max_correlated_positions": 2,
  "account_balance": 10000,
  "min_position_size": 0.5,
  "max_position_size": 10.0,
  "confirmation_required": false,
  "auto_execute": true
}
```

## Supported Currency Pairs

| Pair | IG EPIC |
|------|---------|
| GBPJPY | CS.D.GBPJPY.CFD.IP |
| EURUSD | CS.D.EURUSD.CFD.IP |
| GBPUSD | CS.D.GBPUSD.CFD.IP |
| USDJPY | CS.D.USDJPY.CFD.IP |
| XAUUSD/GOLD | CS.D.XAUUSD.CFD.IP |

## Commands Reference

### Check System Status
```bash
bash ~/.openclaw/workspace/felix_trader.sh status
```

### Check Listener
```bash
tail -f ~/.trading/logs/felix_listener.log
pgrep -f felix_auto_trader  # Check if running
```

### Manual Trade Execution
```bash
bash ~/.openclaw/workspace/felix_trader.sh execute "🇬🇧🇯🇵 GBPJPY 🔵 BUY Entry: 192.500 SL: 191.800 TP: 193.200"
```

### Start/Stop Listener
```bash
# Stop
pkill -f felix_auto_trader

# Start
python3 ~/.openclaw/telegram/felix_auto_trader.py --listen
```

### IG API Commands
```bash
bash ~/.trading/ig_api.sh account      # Account info
bash ~/.trading/ig_api.sh positions    # Open positions
bash ~/.trading/ig_api.sh epic GBPJPY  # Get EPIC code
```

## Important Notes

1. **This is a DEMO account** - No real money at risk
2. **Risk validator is DISABLED** - All signals will be executed
3. **Auto-execute is ENABLED** - No manual confirmation required
4. **Minimum position size is 0.5 lots** - IG requirement
5. **Session persists** - Telegram session doesn't expire

## Troubleshooting

### If listener stops working:
1. Check if process is running: `pgrep -f felix_auto_trader`
2. Check logs: `tail ~/.trading/logs/felix_listener.log`
3. Kill and restart if needed

### If IG API fails:
1. Check credentials in `~/.trading/config/ig_config.json`
2. Verify demo session is active
3. Check account balance

### If trades fail:
1. Check `~/.trading/data/rejections.jsonl`
2. Verify position size ≥ 0.5 lots
3. Check stop distance is valid

## Last Updated
2026-03-19 16:30 EET
System Status: ✅ ACTIVE
