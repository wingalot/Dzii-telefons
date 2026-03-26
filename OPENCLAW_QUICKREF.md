# OpenClaw Quick Reference - Android

## 🚀 ātras Komandas

### Gateway
```bash
openclaw gateway status          # Statuss
openclaw gateway start           # Palaišana
openclaw gateway stop            # Apturēšana
openclaw gateway restart         # Restartēšana
```

### Ierīces
```bash
openclaw devices list            # Saraksts
openclaw devices approve <id>    # Apstiprināt
openclaw devices reject <id>     # Noraidīt
```

### Mezgli (Android)
```bash
openclaw nodes status
openclaw nodes invoke --node "<Android>" --command camera.snap
openclaw nodes invoke --node "<Android>" --command screen.record --params '{"durationMs":5000}'
```

## 📱 Phone Control

### Sistēma
```bash
bash ~/phone_control.sh wifi on|off
bash ~/phone_control.sh bluetooth on|off
bash ~/phone_control.sh brightness 0-255
bash ~/phone_control.sh battery
bash ~/phone_control.sh screenshot
```

### Aplikācijas
```bash
bash ~/phone_control.sh open-app <package>
bash ~/phone_control.sh youtube-search "query"
bash ~/phone_control.sh open-url "https://..."
bash ~/phone_control.sh whatsapp-send <number> "message"
```

### Komunikācija
```bash
bash ~/phone_control.sh call <number>
bash ~/phone_control.sh send-sms <number> "message"
```

## 🔧 Rīku Profili

| Profils | Pieejamie Rīki |
|---------|----------------|
| `minimal` | Tikai `session_status` |
| `coding` | `group:fs`, `group:runtime`, `group:sessions`, `group:memory`, `image` |
| `messaging` | `group:messaging`, `sessions_list`, `sessions_history`, `sessions_send`, `session_status` |
| `full` | Visi rīki |

## 📁 Svarīgākās Vietas

| Vieta | Saturs |
|-------|--------|
| `~/.openclaw/openclaw.json` | Galvenā konfigurācija |
| `~/.openclaw/workspace/` | Darba direktorijs |
| `~/.openclaw/skills/` | Instalētās prasmes |
| `~/.openclaw/agents/` | Aģentu konfigurācija |
| `~/.openclaw/credentials/` | API atslēgas |
| `~/.openclaw/devices/` | Pieslēgtās ierīces |

## 🤖 Skills

### Meklēt
```bash
npx skills find <query>
```

### Instalēt
```bash
npx skills add <owner/repo@skill> -g -y
```

## 📊 Konfigurācija

### Gateway (`~/.openclaw/openclaw.json`)
```json
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback"
  }
}
```

### Rīki
```json
{
  "tools": {
    "profile": "full",
    "allow": ["browser", "canvas"],
    "deny": ["group:runtime"]
  }
}
```

## 🔐 Android Node Komandas

| Komanda | Apraksts |
|---------|----------|
| `chat.history` | Čata vēsture |
| `chat.send` | Sūtīt ziņu |
| `canvas.navigate` | Canvas navigācija |
| `canvas.snapshot` | Canvas ekrānuzņēmums |
| `camera.snap` | Foto uzņemšana |
| `camera.clip` | Video ierakstīšana |
| `screen.record` | Ekrāna ieraksts |
| `device.status` | Ierīces statuss |
| `notifications.list` | Paziņojumi |
| `photos.latest` | Jaunākās bildes |

## ⚡ Svarīgi

- **Modelis**: `kimi-coding/k2p5`
- **API**: Kimi Coding API
- **Platforma**: Android (LineageOS) + Termux
- **Node.js**: v24.13.0
- **OpenClaw**: 2026.3.2
- **Gateway ports**: 18789

## 🔗 Dokumentācija

- Full docs: `~/.openclaw/workspace/OPENCLAW_SYSTEM_DOCS.md`
- OpenClaw docs: `~/node_modules/.pnpm/openclaw*/node_modules/openclaw/docs/`
- Skills: https://skills.sh/

---
*Quick ref for OpenClaw on Android*
