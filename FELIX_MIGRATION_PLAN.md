# Felix Trading System v3.0 - Migration Plan

## Current State Analysis

### Active Components
- ✅ Signal Hub: Running (PID: 9719)
- ✅ TP Manager: Running with 10 positions
- ⚠️ 10 open positions need continuous monitoring

### Critical Issues Found
1. **SQLite Locking** - Signal Hub crashes on "database is locked"
2. **Fragmented Code** - Modules are too complex and interdependent
3. **No Clear Architecture** - Hard to modify without breaking things
4. **Missing Documentation** - Knowledge only in MEMORY.md

## Migration Steps

### Phase 1: Backup Current State (CRITICAL)
```bash
# Before any changes, backup everything
cp -r ~/.openclaw/ai_supervisor ~/.openclaw/ai_supervisor.backup.$(date +%Y%m%d)
cp -r ~/.trading/state ~/.trading/state.backup.$(date +%Y%m%d)
```

### Phase 2: Deploy New Components (One by One)

#### Step 1: Deploy Signal Hub Fix
- Replace `felix_signal_hub.py` with fixed version (MemorySession)
- Restart Signal Hub: `bash felix_new hub-stop && bash felix_new hub-start`
- Monitor logs for 5 minutes

#### Step 2: Deploy TP Manager Refactor
- Keep existing TP Manager running during deployment
- Deploy new version alongside: `felix_tp_manager_v3.py`
- Test new version with: `python3 felix_tp_manager_v3.py --sync --once`
- Switch over: `bash felix_new tp-stop && mv felix_tp_manager_v3.py felix_tp_manager.py && bash felix_new tp-start`

#### Step 3: Deploy Orchestrator
- New file: `felix_orchestrator.py`
- Test with: `bash felix_new test`
- Start: `bash felix_new orch-start`

#### Step 4: Deploy Architecture & Config
- New file: `~/.trading/felix_config.json`
- New file: `~/.openclaw/ai_supervisor/felix_interfaces.py`
- Documentation: `FELIX_ARCHITECTURE.md`

### Phase 3: Switch to New Master Script
```bash
# Backup old
mv ~/.openclaw/workspace/felix ~/.openclaw/workspace/felix_old

# Activate new
mv ~/.openclaw/workspace/felix_new ~/.openclaw/workspace/felix

# Test
bash felix status
```

### Phase 4: Cleanup
- Remove old backup files after 7 days of stable operation
- Archive old module versions

## Rollback Plan

If anything goes wrong:
```bash
# Emergency rollback
bash felix kill  # Stop all new processes
cp -r ~/.openclaw/ai_supervisor.backup.*/* ~/.openclaw/ai_supervisor/
bash felix_old start  # Restart old system
```

## Testing Checklist

Before considering migration complete:
- [ ] Signal Hub receives Telegram messages without "database locked" errors
- [ ] TP Manager tracks all 10 existing positions correctly
- [ ] New position opens when Felix sends signal
- [ ] TP1/TP2/TP3 hits are detected and acted upon
- [ ] SL hits close positions
- [ ] Notifications sent to Telegram
- [ ] No errors in logs for 24 hours

## Post-Migration Monitoring

Check these every hour for first 24h:
```bash
bash felix status          # Component health
bash felix logs hub | tail # Recent Signal Hub activity
bash felix logs tp | tail  # Recent TP Manager activity
```

## Known Limitations of New System

1. **Position Closing**: IG API hedging mode still requires manual close
2. **Demo Mode**: All positions use 1.0 lot (no risk management)
3. **Single Account**: Only supports one IG account
4. **No Backtesting**: No historical signal analysis

## Future Improvements

1. Add proper risk management (1% per trade)
2. Implement position sizing based on volatility
3. Add more asset classes (crypto, indices)
4. Create web dashboard for monitoring
5. Add backtesting framework

---

**Migration started:** 2026-04-02 11:15 GMT+3  
**Expected completion:** 2026-04-02 12:00 GMT+3  
**Responsible:** Dzii (AI)
