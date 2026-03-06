# Dzii - Android AI Agent 🤖⚡

AI asistents ar root piekļuvi Android ierīcei. Automatizē Telegram un IG Trading.

## 🚀 Jaunākās Spējas

### 📱 Telegram Automation

| Skripts | Funkcija |
|---------|----------|
| `felix-reader.sh` | Nolasa Felix VIP room signālus caur OCR |
| `felix-screenshot.sh` | Vienkāršs screenshot grabber |
| `felix-signal.sh` | Pilns signālu parsēšana ar TP/SL izvadi |

**Izmantošana:**
```bash
bash tools/workflows/felix-reader.sh
```

**Izvade:**
- Felix VIP room jaunākais trading signāls
- OCR teksts ar BUY/SELL, pāri, cenas

---

### 📈 IG Trading Automation

| Skripts | Funkcija |
|---------|----------|
| `ig-trades.sh` | Galvenā Trades sadaļa |
| `ig-orders.sh` | Pending orders (limit orderi) |
| `ig-positions.sh` | Atvērtās pozīcijas |
| `ig-closed.sh` | Aizvērtās pozīcijas |
| `ig-coord-tester.sh` | UI koordināšu tests |

**Izmantošana:**
```bash
# Atvērtās pozīcijas
bash tools/workflows/ig-positions.sh

# Pending orders
bash tools/workflows/ig-orders.sh

# Slēgtās pozīcijas
bash tools/workflows/ig-closed.sh
```

**Izvade:**
- Konta bilance (Funds, Running P&L, Available, Margin)
- Pozīciju saraksts
- Orderu statuss

---

## 🔧 Tehniskā Info

**Platforma:** Android (Lineage OS 16)  
**Root:** Magisk ✅  
**Ekrāns:** 1080x2400  
**OCR:** Tesseract  

**Koordinātes:**
- Trades tab: `x=450, y=2140` (droša zona, virs gesture bar)
- Orders tab: `x=200, y=400`
- Positions tab: `x=540, y=400`
- Closed tab: `x=850, y=400`

---

## 📂 Struktūra

```
tools/workflows/
├── felix-reader.sh      # Telegram → Felix signāli
├── felix-screenshot.sh  # Vienkāršs screenshot
├── felix-signal.sh      # Signālu parsēšana
├── ig-trades.sh         # IG Trades navigācija
├── ig-orders.sh         # IG Orders tab
├── ig-positions.sh      # IG Positions tab
├── ig-closed.sh         # IG Closed tab
└── ig-coord-tester.sh   # Koordināšu tests
```

---

## ⚡ Ātrās Komandas

```bash
# Felix jaunākais signāls
bash tools/workflows/felix-reader.sh

# IG atvērtās pozīcijas
bash tools/workflows/ig-positions.sh

# Pārbaudīt visu
bash tools/workflows/felix-reader.sh && bash tools/workflows/ig-positions.sh
```

---

**Izveidots:** 2025-03-06  
**Autors:** Dzii (OpenClaw AI)
