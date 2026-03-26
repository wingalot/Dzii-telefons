# FELIX SYSTEM - QUICK STATUS

## 🟢 SYSTEM ACTIVE

**Auto-Trader:** RUNNING (PID varies)
**Last Trade:** 2026-03-19 16:26
**Mode:** DEMO
**Risk Validator:** OFF
**Auto-Execute:** ON

## Essential Commands

```bash
# Status
bash ~/.openclaw/workspace/felix_trader.sh status
tail -5 ~/.trading/logs/felix_listener.log

# Restart listener
pkill -f felix_auto_trader; sleep 2; python3 ~/.openclaw/telegram/felix_auto_trader.py --listen

# Manual trade
bash ~/.openclaw/workspace/felix_trader.sh execute "SIGNAL TEXT"
```

## Key Files
- Trader: `~/.openclaw/workspace/felix_trader.sh`
- Listener: `~/.openclaw/telegram/felix_auto_trader.py`
- IG API: `~/.trading/ig_api.sh`
- Config: `~/.trading/config/ig_config.json`
- Trades: `~/.trading/data/trades.jsonl`

## Credentials Available
- IG Demo: wingalot @ demo-api.ig.com
- Telegram: MTProto session active
- Felix Channel: -1001998353092

## Remember
- Risk validator is OFF (per user request)
- All Felix signals auto-execute
- Demo account - no real money
