# Felix TP Manager - Refaktorizācijas Atskaite

## Darba rezultāts

Kods ir pilnībā pārrakstīts ar skaidru klasu struktūru un ~800 rindām labāk lasāma koda.

---

## Jaunā Arhitektūra

```
┌─────────────────────────────────────────────────────────────┐
│                     TPManager                              │
│                  (orchestrator)                            │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────┬───────┴───────┬─────────────┐
        ▼             ▼               ▼             ▼
   ┌────────┐   ┌─────────┐   ┌───────────┐  ┌──────────┐
   │Tracker │   │TPLogic  │   │  IGSync   │  │ Notifier │
   │(state) │   │(rules)  │   │  (API)    │  │(telegram)│
   └────────┘   └─────────┘   └───────────┘  └──────────┘
        │             │               │             │
   ┌────────┐   ┌───────────┐   ┌───────────┐      │
   │ JSON   │   │  Parser   │   │FileWatcher│      │
   │ File   │   │(signals)  │   │(inboxes)  │      │
   └────────┘   └───────────┘   └───────────┘      │
                                                    ▼
                                            ┌─────────────┐
                                            │ send_notif  │
                                            │  .py        │
                                            └─────────────┘
```

---

## Klases un Atbildības

### 1. PositionTracker
**Atbildība:** Pozīciju uzskaite un datu glabāšana

```python
- register(position)          # Reģistrēt jaunu pozīciju
- get_open_positions()        # Atgriezt atvērtās pozīcijas
- close_position(deal_id)     # Aizvērt pozīciju
- partial_close(deal_id)      # Daļēji aizvērt (TP2)
- save() / _load()            # JSON persistēšana
```

### 2. TPLogic  
**Atbildība:** TP/SL lēmumu pieņemšana

```python
- check_conditions(pos, price)     # Pārbaudīt nosacījumus
- _check_tp1_hit()                 # TP1 pārbaude
- _check_tp2_hit()                 # TP2 pārbaude (SL → BE)
- _check_tp3_hit()                 # TP3 pārbaude
- _check_fallback()                # 50% retracement pārbaude
- _check_sl_hit()                  # SL pārbaude
```

### 3. IGSync
**Atbildība:** Sinhronizācija ar IG API

```python
- get_positions()              # Iegūt atvērtās pozīcijas
- get_market_price(epic)       # Pašreizējā cena
- close_position(deal_id)      # Aizvērt pozīciju IG
- epic_to_pair(epic)           # Epic → Pair konversija
```

### 4. Notifier
**Atbildība:** Telegram paziņojumi

```python
- notify_position_closed()     # Pozīcijas aizvēršana
- notify_partial_close()       # Daļēja aizvēršana (TP2)
- notify_unknown_position()    # Brīdinājums par nezināmu pozīciju
```

### 5. Palīgklases

| Klase | Atbildība |
|-------|-----------|
| `SignalParser` | Telegram signālu parsēšana |
| `FileWatcher` | Inbox failu uzraudzība |
| `Position` | Dataclass pozīcijas datiem |
| `ManagerState` | Kopējā stāvokļa dataclass |

---

## Datu Glabāšana (JSON)

```json
{
  "started": "2026-04-02T11:14:00",
  "last_update": "2026-04-02T11:20:00",
  "positions_closed": 5,
  "tp1_hits": 3,
  "tp2_hits": 2,
  "tp3_hits": 1,
  "sl_hits": 1,
  "positions": {
    "DIAAAABBBCCC": {
      "deal_id": "DIAAAABBBCCC",
      "pair": "EURUSD",
      "direction": "BUY",
      "entry": 1.0850,
      "current_sl": 1.0800,
      "tp1": 1.0900,
      "tp2": 1.0950,
      "tp3": 1.1000,
      "tp1_hit": true,
      "tp2_hit": true,
      ...
    }
  }
}
```

---

## Kļūdu Apstrāde

```python
# Katrā komponentā try/except ar fallback:

try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Error: {e}")
    # Sistēma turpina darboties
    return default_value

# Galvenajā ciklā:
while running:
    try:
        await main_loop_iteration()
    except Exception as e:
        logger.error(f"Main loop error: {e}", exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL)  # Turpina
```

---

## Funkcionalitātes Saglabāšana

| Funkcionalitāte | Jaunā implementācija |
|-----------------|----------------------|
| TP1 hit | `TPLogic._check_tp1_hit()` - markē kā sasniegtu |
| TP2 hit | `TPLogic._check_tp2_hit()` + `Notifier.notify_partial_close()` + SL → BE |
| TP3 hit | `TPLogic._check_tp3_hit()` + pilna aizvēršana |
| Fallback | `TPLogic._check_fallback()` - 50% retracement |
| SL hit | `TPLogic._check_sl_hit()` + aizvēršana |
| IG Sync | `IGSync` klasē + `sync_ig_positions()` |
| Telegram | `Notifier` klase |
| Signālu parsēšana | `SignalParser` klase |
| Limit order aktivācija | `handle_activated_update()` |
| Felix CLOSE signāls | `handle_close_update()` |

---

## Priekšrocības salīdzinājumā ar veco kodu

| Aspekts | Vecais kods | Jaunais kods |
|---------|-------------|--------------|
| Koda garums | ~1000 rindas | ~800 rindas |
| Klases | 1 (monolīts) | 8 (modulārs) |
| Atbildību sajaukums | Augsts | Zems |
| Testējamība | Grūta | Viegla |
| Docstrings | Minimālas | Visur |
| Tipu hints | Nē | Jā |
| Kļūdu apstrāde | Daļēja | Pilnīga |
| Datu validācija | Nē | @dataclass |

---

## Lietošana

```bash
# Startēt ar IG sinhronizāciju
python3 felix_tp_manager.py --sync

# Startēt bez sinhronizācijas
python3 felix_tp_manager.py
```

## Stāvokļa fails
`~/.openclaw/ai_supervisor/state/tp_manager_state.json`
