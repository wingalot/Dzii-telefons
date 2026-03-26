# OpenClaw Sistēmas Dokumentācija - Android Ierīce

## 🎯 Kopsavilkums

Šī ir OpenClaw AI asistenta instalācija uz Android ierīces (POCOPHONE F1 ar LineageOS), kas darbojas caur Termux.

---

## 📁 Direktoriju Struktūra

### Galvenā konfigurācijas vieta: `~/.openclaw/`

```
~/.openclaw/
├── openclaw.json              # Galvenais konfigurācijas fails
├── .env                       # API atslēgas (KIMI_API_KEY)
├── agents/                    # Aģentu konfigurācija
│   ├── main/
│   │   ├── sessions/
│   │   └── agent/models.json  # Modeļu konfigurācija
│   └── thinker/
│       ├── sessions/
│       └── agent/models.json
├── skills/                    # Instalētās prasmes (skills)
│   ├── find-skills/
│   ├── github/
│   └── self-improving-agent/
├── credentials/               # Autentifikācijas dati
│   ├── telegram-pairing.json
│   └── discord-pairing.json
├── cron/                      # Plānotie uzdevumi
│   └── jobs.json
├── devices/                   # Pieslēgtās ierīces
│   ├── paired.json           # Pieslēgtās ierīces
│   └── pending.json          # Gaidošie pieprasījumi
├── identity/                  # Ierīces identitāte
│   ├── device.json           # Publiskā/privātā atslēga
│   └── device-auth.json
├── telegram/                  # Telegram integrācija
├── media/                     # Multivides faili
├── logs/                      # Žurnālfaili
├── memory/                    # Atmiņa (long-term)
├── subagents/                 # Subaģentu sesijas
├── workspace/                 # Galvenais darba direktorijs
│   ├── AGENTS.md             # Multi-aģentu workflows
│   ├── SOUL.md               # Personības vadlīnijas
│   ├── TOOLS.md              # Rīku konfigurācija
│   ├── IDENTITY.md           # Sistēmas identitāte
│   ├── USER.md               # Lietotāja informācija
│   ├── HEARTBEAT.md          # Sirdspuksta konfigurācija
│   ├── BOOTSTRAP.md          # Palaišanas konfigurācija
│   └── memory/               # Dienas atmiņas faili
└── workspace-thinker/         # Thinker aģenta workspace
```

### OpenClaw Pakotnes Vieta

```
~/node_modules/.pnpm/openclaw@2026.3.2_*/node_modules/openclaw/
├── openclaw.mjs              # CLI entry point
├── dist/                     # Kompilētā koda direktorijs
├── docs/                     # Oficiālā dokumentācija
├── skills/                   # 54 iebūvētas prasmes
├── extensions/               # Paplašinājumi
├── assets/                   # Resursi
├── package.json              # Pakotnes metadati
└── README.md                 # Galvenā dokumentācija
```

---

## 🔧 Pieejamie Rīki (Tools)

### Pamata Rīki

| Rīks | Apraksts | Grupa |
|------|----------|-------|
| `read` | Failu lasīšana | `group:fs` |
| `write` | Failu rakstīšana | `group:fs` |
| `edit` | Precīza teksta aizstāšana | `group:fs` |
| `apply_patch` | Strukturētu labojumu pielikšana | - |
| `exec` | Shell komandu izpilde | `group:runtime` |
| `process` | Fonas procesu pārvaldība | `group:runtime` |

### Tīmekļa Rīki

| Rīks | Apraksts | Grupa |
|------|----------|-------|
| `web_search` | Meklēšana tīmeklī (Brave/Kimi) | `group:web` |
| `web_fetch` | URL satura izgūšana | `group:web` |
| `browser` | Pārlūka kontrole | `group:ui` |

### Sakaru Rīki

| Rīks | Apraksts | Grupa |
|------|----------|-------|
| `message` | Ziņojumu sūtīšana (Telegram, Discord) | `group:messaging` |
| `nodes` | Savienoto mezglu pārvaldība | `group:nodes` |

### Automatizācijas Rīki

| Rīks | Apraksts | Grupa |
|------|----------|-------|
| `cron` | Plānotie uzdevumi | `group:automation` |
| `gateway` | Gateway vadība | `group:automation` |

### Sesiju Rīki

| Rīks | Apraksts | Grupa |
|------|----------|-------|
| `sessions_list` | Aktīvo sesiju saraksts | `group:sessions` |
| `sessions_history` | Sesiju vēsture | `group:sessions` |
| `sessions_send` | Ziņojumu sūtīšana sesijai | `group:sessions` |
| `session_status` | Pašreizējās sesijas statuss | `group:sessions` |
| `subagents` | Subaģentu pārvaldība | - |

### Papildu Rīki

| Rīks | Apraksts |
|------|----------|
| `tts` | Teksta runā pārveide |
| `canvas` | Canvas prezentācija/A2UI |
| `browser` | Pārlūka kontrole (snapshot, act, navigate) |

---

## 📱 Android-Specifiskas Iespējas

### Platformas Parametri

```
OS:           Linux 4.19.325-cip126-st10-gfda5811c2c00 (arm64)
Platforma:    Android (LineageOS, rootēts)
Lietotājs:    u0_a157 (Termux)
Shell:        /data/data/com.termux/files/usr/bin/bash
Node.js:      v24.13.0
OpenClaw:     2026.3.2
```

### Termux Integrācija

- **Darbības vieta**: `/data/data/com.termux/files/home/`
- **Pieejamības līmenis**: Ierobežots (Android sandbox)
- **Tīkla piekļuve**: Pieejama caur `inet` grupu
- **Root piekļuve**: Pieejama caur `su` komandu (LineageOS)

### Android Mezgla (Node) Iespējas

Saskaņā ar dokumentāciju, Android ierīce var darboties kā **companion node** (nevis Gateway hosts):

#### Savienojums
- Savienojas ar Gateway caur WebSocket (`ws://<host>:18789`)
- Atklāšana caur mDNS/NSD vai manuāla konfigurācija
- Automātiska pārsavienošanās pēc pirmās savienošanās

#### Pieejamās Komandu Ģimenes

| Komandu Ģimene | Apraksts | Pieejamība |
|----------------|----------|------------|
| `chat.*` | Čata vēsture un ziņojumi | ✅ |
| `canvas.*` | Canvas navigācija, eval, snapshot | ✅ (foreground) |
| `canvas.a2ui.*` | A2UI push/reset | ✅ (foreground) |
| `camera.*` | Kameras uzņemšana/video | ✅ (foreground + permissions) |
| `screen.*` | Ekrāna ierakstīšana | ✅ (foreground) |
| `device.*` | Ierīces statuss, info, permissions | ✅ |
| `notifications.*` | Paziņojumu pārvaldība | ✅ |
| `photos.*` | Jaunākās fotogrāfijas | ✅ |
| `contacts.*` | Kontaktu meklēšana/pievienošana | ✅ |
| `calendar.*` | Kalendāra notikumi | ✅ |
| `motion.*` | Aktivitāte/pedometrs | ✅ |
| `app.update` | Aplikācijas atjaunināšana | ✅ |

#### Balss Iespējas
- Mikrofona ieslēgšana/izslēgšana
- Transkripcijas uzņemšana
- TTS atskaņošana (ElevenLabs vai sistēmas TTS)

---

## 🔌 Gateway Konfigurācija

### Pašreizējā Konfigurācija (`~/.openclaw/openclaw.json`)

```json
{
  "env": {
    "KIMI_API_KEY": "sk-kimi-..."
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "kimi-coding/k2p5"
      },
      "workspace": "/data/data/com.termux/files/home/.openclaw/workspace"
    },
    "list": [
      {
        "id": "thinker",
        "name": "Thinker",
        "model": "kimi-coding/k2p5"
      }
    ]
  },
  "browser": {
    "enabled": false
  },
  "commands": {
    "native": "auto",
    "restart": true
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "dmPolicy": "open",
      "allowFrom": ["*"],
      "botToken": "8026525412:AA...",
      "groupPolicy": "open",
      "streaming": "partial"
    }
  },
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback",
    "auth": {
      "mode": "token",
      "token": "b35f8925..."
    }
  }
}
```

### Gateway Režīmi

| Režīms | Apraksts |
|--------|----------|
| `local` | Lokālais režīms (noklusējums) |
| `tailnet` | Tailscale tīkla režīms |

### Bind Opcijas

| Opcija | Apraksts |
|--------|----------|
| `loopback` | Tikai localhost (127.0.0.1) |
| `tailnet` | Tailscale interfeiss |
| `all` | Visi interfeisi (0.0.0.0) |

---

## 📚 Instalētās Prasmes (Skills)

### Lietotāja Prasmes (`~/.openclaw/skills/`)

| Prasme | Apraksts | Atrašanās vieta |
|--------|----------|-----------------|
| `find-skills` | Prasmju meklēšana un instalēšana | `~/.openclaw/skills/find-skills/` |
| `github` | GitHub CLI integrācija | `~/.openclaw/skills/github/` |
| `self-improving-agent` | Mācīšanās no kļūdām | `~/.openclaw/skills/self-improving-agent/` |

### Sistēmas Prasmes (54 iebūvētās)

| Prasme | Apraksts | Kategorija |
|--------|----------|------------|
| `weather` | Laika apstākļi | Informācija |
| `healthcheck` | Drošības auditi | Drošība |
| `canvas` | Canvas vadība | UI |
| `browser` | Pārlūka kontrole | Web |
| `discord` | Discord integrācija | Messaging |
| `github` | GitHub CLI | Development |
| `notion` | Notion integrācija | Productivity |
| `obsidian` | Obsidian integrācija | Productivity |
| `slack` | Slack integrācija | Messaging |
| `spotify-player` | Spotify kontrole | Media |
| `tmux` | Tmux sesijas | Terminal |
| `trello` | Trello integrācija | Productivity |
| `voice-call` | Balss zvani | Communication |
| `web_search` | Tīmekļa meklēšana | Web |
| ...un 40+ citas | | |

---

## 🤖 Modeļu Konfigurācija

### Kimi Coding Provider

```json
{
  "providers": {
    "kimi-coding": {
      "baseUrl": "https://api.kimi.com/coding/",
      "api": "anthropic-messages",
      "models": [
        {
          "id": "k2p5",
          "name": "Kimi for Coding",
          "reasoning": true,
          "input": ["text", "image"],
          "cost": {
            "input": 0,
            "output": 0,
            "cacheRead": 0,
            "cacheWrite": 0
          },
          "contextWindow": 262144,
          "maxTokens": 32768
        }
      ]
    }
  }
}
```

---

## 🔐 Drošība un Autentifikācija

### Ierīces Pāru veidošana (Pairing)

Sistēma izmanto publiskās/privātās atslēgu pāru veidošanu:

```json
{
  "deviceId": "d1fb7ad9b9226101d48ba119422c459b506dda9dfd2013ddd2763319e0b7f90b",
  "publicKeyPem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAd2JXc79Aw8a8TGHslqEkzyzjpzipsqZLiQJfPLsHS0Q=\n-----END PUBLIC KEY-----\n",
  "privateKeyPem": "-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIDVtJ0zaZpKWN8JK2XwHLkcvXo6VEgeHED+BIGFIktTa\n-----END PRIVATE KEY-----\n"
}
```

### Scopes (Tiesības)

| Scope | Apraksts |
|-------|----------|
| `operator.admin` | Pilna administrēšana |
| `operator.read` | Lasīšanas piekļuve |
| `operator.write` | Rakstīšanas piekļuve |
| `operator.approvals` | Apstiprinājumi |
| `operator.pairing` | Ierīču pāru veidošana |

---

## ⚡ Kas Ir Iespējams Šobrīd

### ✅ Pilnībā Funkcionē

1. **AI Asistents ar Kimi k2p5 modeli**
   - Teksta un attēlu apstrāde
   - 262K konteksta logs
   - Reasoning iespējas

2. **Telegram Integrācija**
   - Ziņojumu sūtīšana/saņemšana
   - DM un grupu atbalsts
   - Partial streaming

3. **Failu Sistēmas Pārvaldība**
   - Lasīšana/rakstīšana/dzēšana
   - Failu rediģēšana
   - Patch pielikšana

4. **Shell Komandas**
   - Komandu izpilde
   - Fonas procesi
   - Elevated (root) piekļuve caur `su`

5. **Tīmekļa Meklēšana**
   - Brave/Kimi meklēšana
   - URL satura izgūšana

6. **Subaģenti**
   - Fonas uzdevumi
   - Automātiska rezultātu paziņošana

7. **Atmiņas Sistēma**
   - Long-term atmiņa
   - Dienas atmiņas faili
   - Mācīšanās no kļūdām

### ⚠️ Ierobežots/Neieslēgts

1. **Pārlūka Kontrole**
   - Konfigurācijā `enabled: false`
   - Var ieslēgt, ja nepieciešams

2. **Gateway**
   - Darbojas `loopback` režīmā
   - Nav piekļuves no ārpuses

3. **Canvas**
   - Pieejams caur Gateway (ja konfigurēts)

4. **Cron**
   - Konfigurēts, bet bez aktīviem uzdevumiem

---

## 🛠️ Noderīgas Komandas

### Gateway Vadība

```bash
# Gateway palaišana
openclaw gateway --port 18789 --verbose

# Gateway statuss
openclaw gateway status

# Gateway restart
openclaw gateway restart
```

### Ierīču Vadība

```bash
# Ierīču saraksts
openclaw devices list

# Pieprasījuma apstiprināšana
openclaw devices approve <requestId>

# Pieprasījuma noraidīšana
openclaw devices reject <requestId>
```

### Mezglu Vadība

```bash
# Mezglu statuss
openclaw nodes status

# Komandas izsaukšana uz mezglu
openclaw nodes invoke --node "<node>" --command <command> --params '{}'

# Kameru uzņemšana
openclaw nodes invoke --node "<Android>" --command camera.snap

# Ekrāna ierakstīšana
openclaw nodes invoke --node "<Android>" --command screen.record
```

### Prasmju Vadība

```bash
# Prasmju meklēšana
npx skills find <query>

# Prasmes instalēšana
npx skills add <owner/repo@skill> -g -y

# Prasmju atjaunināšana
npx skills update
```

---

## 📋 Android-Specifiskas Komandas

### Sistēmas Kontrole

```bash
# WiFi ieslēgšana/izslēgšana
bash ~/phone_control.sh wifi on|off

# Bluetooth ieslēgšana/izslēgšana
bash ~/phone_control.sh bluetooth on|off

# Ekrāna spilgtums
bash ~/phone_control.sh brightness 255

# Baterijas līmenis
bash ~/phone_control.sh battery
```

### Aplikāciju Vadība

```bash
# Aplikācijas atvēršana
bash ~/phone_control.sh open-app com.google.android.youtube

# YouTube meklēšana
bash ~/phone_control.sh youtube-search "lofi music"

# URL atvēršana
bash ~/phone_control.sh open-url "https://google.com"

# WhatsApp ziņa
bash ~/phone_control.sh whatsapp-send 919876543210 "Hello"
```

### Zvani un SMS

```bash
# Zvans
bash ~/phone_control.sh call 9876543210

# SMS sūtīšana
bash ~/phone_control.sh send-sms 9876543210 "Hello"
```

### Vizuālais Aģents

```bash
# Kompleksu uzdevumu izpilde
bash ~/phone_agent.sh "Your task description"
```

---

## 🔧 Root Piekļuves Priekšrocības

Kā rootēta ierīce (LineageOS), šī sistēma var:

1. **Pilna Sistēmas Kontrole**
   - Piekļuve visām sistēmas daļām
   - Custom modifikāciju instalēšana
   - Sistēmas failu rediģēšana

2. **Paplašināta Termux Funkcionalitāte**
   - Root komandas caur `su`
   - Sistēmas līmeņa skripti
   - Custom kernel moduļi

3. **Uzlabota Automatizācija**
   - Aplikāciju freeze/unfreeze
   - Sistēmas pakalpojumu vadība
   - Custom cron uzdevumi

---

## 📊 Sistēmas Resursi

| Komponents | Vērtība |
|------------|---------|
| CPU | ARM64 |
| RAM | Atkarīgs no ierīces |
| Krātuve | Ierīces iekšējā atmiņa |
| OS | LineageOS (Android) |
| Kernel | 4.19.325 |
| Node.js | v24.13.0 |
| OpenClaw | 2026.3.2 |

---

## 🔗 Noderīgas Saites

- **OpenClaw Dokumentācija**: `~/node_modules/.pnpm/openclaw*/node_modules/openclaw/docs/`
- **Oficiālā Repo**: https://github.com/openclaw/openclaw
- **Skills Ekosistēma**: https://skills.sh/
- **Kimi API**: https://api.kimi.com/coding/

---

## 📝 Piezīmes

1. **Termux Ierobežojumi**: Android 10+ ierobežo Termux piekļuvi dažām sistēmas daļām
2. **Baterijas Optimizācija**: Android var izslēgt Termux fonā - jāizslēdz baterijas optimizācija
3. **Root Atbildība**: Ar root piekļuvi jābūt uzmanīgam - var sabojāt sistēmu
4. **Atmiņas Pārvaldība**: OpenClaw izmanto `~/.openclaw/` krātuvi konfigurācijai un atmiņai

---

*Dokumentācija izveidota: 2026-03-06*
*OpenClaw Versija: 2026.3.2*
*Platforma: Android (LineageOS) + Termux*
