# FELIX AI SUPERVISOR SYSTEM

## Izveidots: 2026-03-20
## Atjaunināts: 2026-03-20 (AI parser training)
## Status: ✅ AKTĪVS

## Kas tas ir?

Felix AI Uzraugs ir inteliģenta sistēma, kas nodrošina 100% signālu izpildi no Felix VIP Room.

### Galvenās funkcijas:

1. **Signālu uzraudzība** - Klausās Felix VIP Room kanālu Telegram
2. **Kļūdu automātiska labošana** - Ja parser neatpazīst signālu, AI mēģina to salabot
3. **Atkārtoti mēģinājumi** - Ja izpilde neizdodas, sistēma mēģina vēlreiz
4. **Pašdziedēšana** - Sistēma pati sevi restartē, ja kaut kas apstājas
5. **Paziņojumi** - Sūta Telegram paziņojumus par visiem darījumiem

## Sistēmas arhitektūra

```
Felix VIP Room (Telegram)
         ↓
Felix AI Listener (Python)
         ↓
AI Supervisor (Parser + Fixer)
         ↓
felix_trader.sh (Bash)
         ↓
IG API (REST)
         ↓
IG Broker (Darījumu izpilde)
```

## Failu struktūra

```
~/.openclaw/ai_supervisor/
├── felix_ai_supervisor.py      # Galvenais AI uzraugs
├── felix_ai_listener.py         # Telegram klausītājs ar AI
├── felix-ai                     # Kontroles skripts
├── logs/
│   ├── supervisor.log           # Galvenie logi
│   ├── signals.log              # Signālu vēsture
│   └── enhanced_listener.log    # Listener logi
├── state/
│   ├── supervisor_state.json    # Uzrauga stāvoklis
│   └── enhanced_listener.json   # Listener stāvoklis
└── fixes/
    └── applied_fixes.jsonl      - Labojumu vēsture
```

## Lietošana

### Palaist sistēmu:
```bash
felix start
```

### Pārbaudīt statusu:
```bash
felix status
```

### Skatīt logus:
```bash
felix logs
```

### Apturēt sistēmu:
```bash
felix stop
```

### Labot pēdējo noraidīto signālu:
```bash
felix fix
```

### Testēt sistēmu:
```bash
felix test
```

## Kā tas strādā

### 1. Signāla saņemšana
- Kad Felix VIP Room publicē signālu, AI Listener to saņem
- Signāls tiek nosūtīts uz AI Supervisor

### 2. Pirmā mēģinājuma izpilde
- AI Supervisor izsauc `felix_trader.sh execute`
- Ja izpilde veiksmīga → darījums reģistrēts

### 3. Kļūdu apstrāde
- Ja parsing neizdodas, AI mēģina:
  - Atpazīt signāla struktūru ar regex
  - Izgūt: Pair, Direction, Entry, SL, TP
  - Uzbūvēt standartizētu signālu
  - Mēģināt izpildi vēlreiz

### 4. Izpilde IG
- Signāls tiek konvertēts uz IG API formātu
- Tiek izsaukts MARKET order ar SL/TP
- Rezultāts tiek reģistrēts

### 5. Paziņojumi
- Veiksmīgs darījums: ✅ paziņojums Telegram
- Neveiksmīgs: ❌ paziņojums ar kļūdas aprakstu

## Statistika

Sistēma seko:
- Apstrādātie signāli
- Neizdevušies signāli
- Salabotie signāli
- Veiksmes koeficients (%)

## Drošība

- Sistēma darbojas DEMO režīmā
- Risk validators ir IZSLĒGTS (kā pieprasīts)
- Minimālā pozīcija: 0.5 loti
- Maksimālā pozīcija: 10 loti

## Problēmu risināšana

### Ja sistēma nepalaižas:
```bash
felix restart
```

### Ja signāli netiek apstrādāti:
```bash
felix fix
```

### Ja vajag manuāli testēt:
```bash
bash ~/.openclaw/workspace/felix_trader.sh parse "tavs signāls"
```

## Atjauninājumi

### 2026-03-20 (15:00)
- ✅ Izveidots AI Supervisor
- ✅ Uzlabots parser XAUUSD/GOLD signāliem
- ✅ Pievienota automātiskā kļūdu labošana
- ✅ Pievienota pašdziedēšanās
- ✅ Pievienoti Telegram paziņojumi

### 2026-03-20 (15:15) - AI Parser Training
- ✅ Izveidots trenēts AI parsers (`felix_trained_parser.py`)
- ✅ Apmācīts ar 6+ vēsturiskiem Felix formātiem
- ✅ Atbalstītie formāti:
  - Simple: `BUY XAUUSD 4653.0`
  - Limit: `Sell Limit XAUUSD @ 4721`
  - Detailed: `🚨 SIGNAL ALERT 🚨 #EURCAD Entry: 1.57680`
  - Emoji: `🇬🇧🇯🇵 GBPJPY 🔵 BUY Entry Zone: 192.500`
  - BTC: `Sell BTCUSD @ 68000`
- ✅ 5/6 testi izgājuši veiksmīgi
- ✅ AI uzraugs tagad izmanto trenēto parseri
