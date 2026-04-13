# FELIX Trading System Architecture

> **F**orex **E**xecution & **L**everaged **I**nvestment E**x**pert
> 
> Viegli uzturējama un modificējama automatizēta treidinga sistēma IG brokerim.

---

## 📐 Sistēmas komponentu diagramma

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FELIX TRADING SYSTEM                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Telegram      │     │   Telegram      │     │     IG          │
│   Signal Bot    │     │   Alert Bot     │     │   Trading API   │
│   (Ieeja)       │     │   (Izeja)       │     │   (Execution)   │
└────────┬────────┘     └────────▲────────┘     └────────▲────────┘
         │                       │                       │
         │ Signal JSON           │ Notifikācijas         │ Darījumi
         │                       │                       │
┌────────▼───────────────────────┴───────────────────────┴────────┐
│                      ┌─────────────────┐                        │
│                      │  Signal Parser  │                        │
│                      │  (Parsē JSON)   │                        │
│                      └────────┬────────┘                        │
│                               │ Signal dataclass                 │
│                      ┌────────▼────────┐                        │
│                      │  Risk Manager   │                        │
│                      │  (Validācija)   │                        │
│                      └────────┬────────┘                        │
│                               │ Validēts signals                 │
│     ┌─────────────────────────┼─────────────────────────┐       │
│     │                         │                         │       │
│     ▼                         ▼                         ▼       │
│ ┌─────────┐              ┌─────────┐              ┌─────────┐   │
│ │  EPIC   │              │ Position│              │  Risk   │   │
│ │Resolver │─────────────▶│ Manager │─────────────▶│ Checker │   │
│ │         │   EPIC kods  │         │   Darījums   │         │   │
│ └─────────┘              └─────────┘              └────┬────┘   │
│                                                      │         │
│                              ┌───────────────────────┘         │
│                              ▼                                  │
│                      ┌───────────────┐                          │
│                      │  IG Executor  │                          │
│                      │  (API calls)  │                          │
│                      └───────┬───────┘                          │
│                              │ HTTP/REST                        │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    IG Markets API   │
                    │  (gateway.ig.com)   │
                    └─────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    SUPPORTING MODULES                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Config     │  │  Logger     │  │  Notification Service   │  │
│  │  (JSON)     │  │  (File/DB)  │  │  (Telegram/Console)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Datu plūsmas apraksts

### 1. Signāla saņemšana
```
Telegram Message → Signal Parser → Signal dataclass
```
- Saņem JSON formāta signālu no Telegram bota
- Parsē un validē signāla struktūru
- Izveido Signal objektu

### 2. Riska pārbaude
```
Signal → Risk Manager → Validēts/Atmests
```
- Pārbauda dienas riska limitus (maks. zaudējumi, maks. darījumi)
- Validē pozīcijas lielumu pret konta bilanci
- Pārbauda dubultu pozīciju eksistenci
- Atmet signālu, ja pārsniegti limiti

### 3. EPIC izšķiršana
```
Valūtu pāris → EPIC Resolver → IG EPIC kods
```
- Konvertē valūtu pāri (EURUSD) uz IG EPIC kodu (CS.D.EURUSD.CFD.IP)
- Izmanto konfigurācijas kartējumu
- Aizstāj alternatīvus pāru nosaukumus

### 4. Pozīcijas atvēršana
```
Validēts Signal → Position Manager → IG Executor → IG API
```
- Aprēķina pozīcijas lielumu (līgumu skaits)
- Nosaka Stop Loss un Take Profit līmeņus
- Izsaka darījumu caur IG REST API
- Saglabā pozīcijas informāciju

### 5. Notifikācijas
```
Darījuma rezultāts → Notification Service → Telegram/Logs
```
- Sūta apstiprinājumu par veiksmīgu darījumu
- Brīdina par kļūdām un problēmām
- Izsūta dienas kopsavilkumu

---

## 📁 Failu struktūras apraksts

```
~/.openclaw/
├── workspace/
│   ├── FELIX_ARCHITECTURE.md      # Šis fails - arhitektūras dokuments
│   ├── FELIX_CONFIG.md            # Konfigurācijas apraksts
│   └── FELIX_USAGE.md             # Lietošanas instrukcijas
│
└── ai_supervisor/
    ├── felix_interfaces.py        # Kopīgās interfeisa definīcijas
    ├── felix_signal_parser.sh     # Signālu parsēšanas skripts
    ├── felix_risk_manager.sh      # Riska pārvaldības skripts
    ├── felix_epic_resolver.sh     # EPIC kodu kartēšana
    ├── felix_position_manager.sh  # Pozīciju pārvaldība
    ├── felix_ig_executor.sh       # IG API izpilde
    ├── felix_notification.sh      # Notifikācijas
    └── lib/
        └── ig_api.sh              # IG API helper funkcijas

~/.trading/
├── felix_config.json              # Galvenā konfigurācija
├── felix_pairs.json               # Valūtu pāru kartējums
├── felix_positions.json           # Aktīvās pozīcijas
├── felix_history.json             # Darījumu vēsture
└── logs/
    ├── felix_$(date +%Y%m%d).log  # Dienas žurnāls
    └── felix_error.log            # Kļūdu žurnāls
```

### Moduļu atbildības

| Modulis | Funkcija | Faili |
|---------|----------|-------|
| **Signal Parser** | Parsē Telegram signālus | `felix_signal_parser.sh` |
| **Risk Manager** | Riska kontrole un limiti | `felix_risk_manager.sh` |
| **EPIC Resolver** | Valūtu pāru → EPIC kartējums | `felix_epic_resolver.sh` |
| **Position Manager** | Pozīciju atvēršana/aizvēršana | `felix_position_manager.sh` |
| **IG Executor** | API komunikācija | `felix_ig_executor.sh` |
| **Notification** | Paziņojumi un alerti | `felix_notification.sh` |

---

## ⚙️ Konfigurācijas parametri

### `felix_config.json` struktūra

```json
{
  "system": {
    "name": "FELIX",
    "version": "1.0.0",
    "mode": "live|demo",
    "timezone": "Europe/Riga"
  },
  "ig_api": {
    "base_url": "https://demo-api.ig.com/gateway/deal",
    "api_key": "your_api_key",
    "username": "your_username",
    "password": "your_password",
    "account_id": "your_account_id"
  },
  "risk_management": {
    "max_daily_loss": 50.0,
    "max_daily_trades": 10,
    "max_concurrent_positions": 5,
    "default_risk_percent": 2.0,
    "min_risk_reward_ratio": 1.5
  },
  "trading": {
    "default_lot_size": 0.01,
    "default_tp_percent": 2.0,
    "default_sl_percent": 1.0,
    "use_trailing_stop": false,
    "trailing_stop_distance": 1.0
  },
  "notifications": {
    "telegram_bot_token": "your_bot_token",
    "telegram_chat_id": "your_chat_id",
    "notify_on_trade": true,
    "notify_on_error": true,
    "notify_daily_summary": true
  }
}
```

### Parametru apraksts

#### IG API konfigurācija
| Parametrs | Tips | Apraksts |
|-----------|------|----------|
| `base_url` | string | API endpoints (demo/live) |
| `api_key` | string | IG API atslēga |
| `username` | string | IG konta lietotājvārds |
| `password` | string | IG konta parole |
| `account_id` | string | Tirdzniecības konta ID |

#### Riska iestatījumi
| Parametrs | Tips | Apraksts |
|-----------|------|----------|
| `max_daily_loss` | number | Maks. zaudējumi dienā (€) |
| `max_daily_trades` | integer | Maks. darījumu skaits dienā |
| `max_concurrent_positions` | integer | Maks. vienlaicīgās pozīcijas |
| `default_risk_percent` | number | Riska % no konta uz darījumu |
| `min_risk_reward_ratio` | number | Minimālā risk/attiecība |

#### Treidinga iestatījumi
| Parametrs | Tips | Apraksts |
|-----------|------|----------|
| `default_lot_size` | number | Noklusējuma līguma lielums |
| `default_tp_percent` | number | Noklusējuma TP % |
| `default_sl_percent` | number | Noklusējuma SL % |
| `use_trailing_stop` | boolean | Izmantot trailing stop |
| `trailing_stop_distance` | number | Trailing stop distance % |

---

## 🔄 Datu plūsmas sekvences diagramma

```
Telegram    Signal      Risk      EPIC     Position    IG        Notification
   │        Parser    Manager  Resolver   Manager   Executor      Service
   │          │          │         │          │          │            │
   │──JSON──▶│          │         │          │          │            │
   │         │─Signal──▶│         │          │          │            │
   │         │          │─Check──▶│          │          │            │
   │         │          │◀─Pass───│          │          │            │
   │         │          │────────EPIC───────▶│          │            │
   │         │          │         │◀─Code────│          │            │
   │         │          │────────────────────│─Create──▶│            │
   │         │          │         │          │◀─Order───│            │
   │         │          │         │          │────────Execute──────▶│
   │         │          │         │          │◀─Result──────────────│
   │◀────────────────────────────────────────────────────────Alert──│
   │         │          │         │          │          │            │
```

---

## 🛡️ Drošības prasības

1. **API atslēgas** - glabājas tikai `~/.trading/felix_config.json`, 600 permissions
2. **Logs** - nekad nelogot pilnas API atbildes ar sensitīvu info
3. **Validācija** - visi signāli tiek validēti pirms izpildes
4. **Riska limiti** - hard limiti, kas neļauj pārsniegt zaudējumus

---

## 📝 Versiju vēsture

| Versija | Datums | Izmaiņas |
|---------|--------|----------|
| 1.0.0 | 2026-04-02 | Sākotnējā versija |
