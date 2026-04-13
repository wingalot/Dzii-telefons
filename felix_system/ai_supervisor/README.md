# Felix AI Supervisor - Orchestrator

Vienkāršots orķestrators tirdzniecības signālu apstrādei.

## Struktūra

```
~/.openclaw/ai_supervisor/
├── felix_orchestrator.py    # Galvenais orķestrators
├── config.json              # Konfigurācija (epic kodi utt.)
├── signals/                 # Ienākošie signāli
├── orders/                  # IG API orderi
├── positions/               # TP Manager pozīcijas
└── logs/                    # Logi
```

## Darbības princips

1. **Signal Hub** izveido JSON failu `signals/` direktorijā
2. **Orchestrator** apstrādā signālu un izveido:
   - Orderi `orders/` → IG API
   - Pozīciju `positions/` → TP Manager
3. Ienākošais fails tiek dzēsts

## Signāla formāts

```json
{
  "id": "unique_signal_id",
  "text": "BUY EURUSD @ 1.0850\nSL: 1.0800\nTP1: 1.0900\nTP2: 1.0950",
  "timestamp": "2024-01-01T12:00:00"
}
```

## Parsēšana

Atbalstītie formāti:
- **Pāris**: EURUSD, GBPUSD, USDJPY, XAUUSD, GOLD
- **Virziens**: BUY / SELL (case insensitive)
- **Ieejas cena**: `@ 1.0850` vai `__1.0850__`
- **SL**: `SL: 1.0800` vai `Stop Loss: 1.0800`
- **TP**: `TP1: 1.0900`, `Take Profit 1: 1.0900`, `TP2:`, `TP3:`

## Lietošana

### Nepārtrauktais režīms:
```bash
python3 ~/.openclaw/ai_supervisor/felix_orchestrator.py
```

### Viena signāla apstrāde:
```bash
python3 ~/.openclaw/ai_supervisor/felix_orchestrator.py "BUY EURUSD @ 1.0850 SL: 1.0800 TP1: 1.0900"
```

### No Python:
```python
from felix_orchestrator import process_single_signal

result = process_single_signal("BUY EURUSD @ 1.0850 SL: 1.0800 TP1: 1.0900")
print(result)
```

## Izejas faili

### Orders (`orders/SIG_xxx_order.json`)
```json
{
  "epic": "CS.D.EURUSD.CFD.IP",
  "direction": "BUY",
  "size": 1.0,
  "order_type": "LIMIT",
  "level": 1.0850,
  "stop_level": 1.0800,
  "limit_level": 1.0900,
  "tp2": 1.0950,
  "tp3": null
}
```

### Positions (`positions/SIG_xxx_position.json`)
```json
{
  "signal_id": "SIG_xxx",
  "epic": "CS.D.EURUSD.CFD.IP",
  "pair": "EURUSD",
  "direction": "BUY",
  "status": "PENDING"
}
```

## Integrācija ar citiem moduļiem

### IG API modulis
- Nolasa `orders/*.json`
- Izpilda orderi
- Raksta rezultātu `orders/*_result.json`

### TP Manager
- Nolasa `positions/*.json`
- Seko līdz TP līmeņiem
- Atjauno statusu
