# OpenClaw Skills - Pilns Pārskats Android Ierīcei

## 📊 Kopējā Statistika

- **User-installed skills**: 3 (atrodas `~/.openclaw/skills/`)
- **Built-in skills**: 54 (atrodas `node_modules/openclaw/skills/`)
- **Kopā pieejamas**: 57+ skills

---

## 🔧 User-Installed Skills (3)

### 1. **find-skills**
- **Apraksts**: Palīdz atrast un instalēt skills no OpenClaw ekosistēmas
- **Lietojums**: Meklēt skills pēc atslēgvārdiem, instalēt jaunas spējas
- **Komandas**:
  - `npx skills find [query]` - Meklēt skills
  - `npx skills add <package>` - Instalēt skill
  - `npx skills check` - Pārbaudīt atjauninājumus
- **Android piemērotība**: ⭐⭐⭐⭐⭐ (ļoti noderīga)

### 2. **github**
- **Apraksts**: GitHub CLI (gh) integrācija PR, issues un CI darbībām
- **Lietojums**: Pārvaldīt GitHub repozitorijus, pārbaudīt PR statusu, skatīt workflow runs
- **Komandas**:
  - `gh pr checks 55 --repo owner/repo`
  - `gh run list --repo owner/repo --limit 10`
  - `gh api repos/owner/repo/pulls/55`
- **Android piemērotība**: ⭐⭐⭐ (der, ja strādā ar kodu)

### 3. **self-improvement**
- **Apraksts**: Reģistrē kļūdas un mācīšanās pieredzi uzlabošanai
- **Lietojums**: Saglabāt kļūdas, lietotāju korekcijas, funkciju pieprasījumus
- **Faili**: `~/.openclaw/workspace/.learnings/LEARNINGS.md`, `ERRORS.md`, `FEATURE_REQUESTS.md`
- **Android piemērotība**: ⭐⭐⭐⭐⭐ (ļoti ieteicama)

---

## 📱 Android-Noderīgākās Built-in Skills

### 🌤️ **weather** ⭐⭐⭐⭐⭐
- **Apraksts**: Laika apstākļu prognozes bez API atslēgas
- **Lietojums**: Pārbaudīt laiku jebkurā pilsētā
- **Komandas**:
  - `curl "wttr.in/Riga?format=3"` - Pašreizējais laiks
  - `curl "wttr.in/Riga"` - 3 dienu prognoze
  - `curl "wttr.in/Riga?format=v2"` - Nedēļas prognoze
- **Android**: Ideāla - tikai curl vajadzīgs

### 🎵 **spotify-player** ⭐⭐⭐⭐
- **Apraksts**: Spotify kontrole terminālī
- **Lietojums**: Atskaņot, pauzēt, meklēt mūziku
- **Prasības**: Spotify Premium, `spogo` vai `spotify_player`
- **Komandas**:
  - `spogo play`, `spogo pause`, `spogo next`
  - `spogo search track "query"`
- **Android**: Vajadzīga instalācija (nav brew)

### 📸 **camsnap** ⭐⭐⭐⭐
- **Apraksts**: RTSP/ONVIF kameru attēlu/video ierakstīšana
- **Lietojums**: Uzņemt kadru no IP kameras
- **Prasības**: `camsnap`, `ffmpeg`
- **Android**: Var strādāt ar tīkla kamerām

### 🎞️ **canvas** ⭐⭐⭐⭐⭐
- **Apraksts**: HTML satura attēlošana uz savienotām ierīcēm
- **Lietojums**: Rādīt vizualizācijas, spēles, paneļus
- **Android**: Atbalsta Android ierīces kā canvas mērķus!

### 🎙️ **openai-whisper** ⭐⭐⭐⭐
- **Apraksts**: Lokāla runas-tekstā pārveide
- **Lietojums**: Transkribēt audio failus
- **Komandas**:
  - `whisper /path/audio.mp3 --model medium --output_format txt`
- **Android**: Noderīga audio transkripcijai

### 🧾 **summarize** ⭐⭐⭐⭐⭐
- **Apraksts**: URL, PDF un YouTube kopsavilkumi
- **Lietojums**: Ātri uzzināt, par ko ir saite/video
- **Prasības**: `summarize` CLI, API atslēga
- **Android**: Ideāla ziņu/artikulu kopsavilkumiem

### 🎞️ **video-frames** ⭐⭐⭐
- **Apraksts**: Video kadru izvilkšana ar ffmpeg
- **Lietojums**: Iegūt kadru no video noteiktā laika
- **Prasības**: `ffmpeg`
- **Android**: Der, ja ir ffmpeg

### 📄 **nano-pdf** ⭐⭐⭐⭐
- **Apraksts**: PDF rediģēšana ar dabiskas valodas instrukcijām
- **Lietojums**: Labot PDF bez speciālas programmatūras
- **Komandas**:
  - `nano-pdf edit file.pdf 1 "Change title to 'New Title'"`
- **Android**: Noderīga dokumentu apstrādei

### 💬 **discord** ⭐⭐⭐⭐
- **Apraksts**: Discord ziņojumu sūtīšana/rediģēšana
- **Lietojums**: Sūtīt ziņojumus Discord serveros
- **Prasības**: Discord token konfigurācijā
- **Android**: Laba Discord integrācijai

### 💬 **slack** ⭐⭐⭐⭐
- **Apraksts**: Slack ziņojumu pārvaldība
- **Lietojums**: Sūtīt, rediģēt, pin ziņojumus Slack
- **Prasības**: Slack bot token
- **Android**: Laba Slack integrācijai

### 📝 **notion** ⭐⭐⭐⭐
- **Apraksts**: Notion API integrācija
- **Lietojums**: Izveidot/lasīt lapas, datubāzes
- **Prasības**: `NOTION_API_KEY` env
- **Android**: Noderīga piezīmju vadībai

### 💎 **obsidian** ⭐⭐⭐⭐⭐
- **Apraksts**: Obsidian vault darbs
- **Lietojums**: Meklēt, izveidot, pārvietot piezīmes
- **Prasības**: `obsidian-cli`
- **Android**: Ideāla, ja lieto Obsidian

### 🎮 **gog** ⭐⭐⭐
- **Apraksts**: Google Workspace CLI (Gmail, Calendar, Drive, Sheets, Docs)
- **Lietojums**: Sūtīt epastus, pārvaldīt kalendāru, Sheets
- **Prasības**: OAuth iestatīšana, `gog`
- **Android**: Noderīga Google pakalpojumiem

### 🧵 **tmux** ⭐⭐⭐⭐
- **Apraksts**: Tmux sesiju tālvadība
- **Lietojums**: Vadīt interaktīvas CLI sesijas
- **Prasības**: `tmux`
- **Android**: Noderīga ilgstošiem procesiem

### ♊️ **gemini** ⭐⭐⭐⭐
- **Apraksts**: Google Gemini CLI
- **Lietojums**: AI jautājumi un atbildes
- **Prasības**: `gemini` CLI
- **Android**: AI asistents terminālī

### 🖼️ **openai-image-gen** ⭐⭐⭐
- **Apraksts**: Attēlu ģenerēšana caur OpenAI API
- **Lietojums**: Ģenerēt attēlus pēc promptiem
- **Prasības**: `OPENAI_API_KEY`, `python3`
- **Android**: Noderīga attēlu ģenerēšanai

### 🧲 **gifgrep** ⭐⭐⭐
- **Apraksts**: GIF meklēšana un lejupielāde
- **Lietojums**: Atrast un lejupielādēt GIF
- **Prasības**: `gifgrep`
- **Android**: Noderīga GIF meklēšanai

### 📋 **trello** ⭐⭐⭐
- **Apraksts**: Trello API integrācija
- **Lietojums**: Pārvaldīt Trello boards, lists, cards
- **Prasības**: `TRELLO_API_KEY`, `TRELLO_TOKEN`
- **Android**: Noderīga uzdevumu pārvaldei

### 🔒 **healthcheck** ⭐⭐⭐⭐⭐
- **Apraksts**: Drošības auditi un riska novērtējums
- **Lietojums**: Pārbaudīt sistēmas drošību, atjauninājumus
- **Komandas**:
  - `openclaw security audit`
  - `openclaw update status`
- **Android**: Ļoti ieteicama drošībai

### 🛠️ **skill-creator** ⭐⭐⭐⭐⭐
- **Apraksts**: Jaunu skills izveide un pārvalde
- **Lietojums**: Izveidot savas skills
- **Android**: Noderīga pielāgotu skills veidošanai

---

## 🍎 Platform-Specifiskās Skills (Nav piemērotas Android)

Šīs skills ir paredzētas macOS/iOS un **nedarbosies** uz Android:

| Skill | Iemesls |
|-------|---------|
| **apple-notes** | macOS/iOS only |
| **apple-reminders** | macOS/iOS only |
| **bear-notes** | macOS only app |
| **bluebubbles** | iMessage macOS only |
| **imsg** | iMessage macOS only |
| **things-mac** | macOS only app |
| **wacli** | macOS only |
| **sonoscli** | Prasa specifisku hardware |
| **spotify_player** | Daļēji var strādāt, bet labāk spogo |

---

## 📊 Skills pēc Kategorijas

### 🗣️ Komunikācija
- discord, slack, gog (Gmail), voice-call

### 📝 Produktivitāte
- notion, obsidian, trello, github, gh-issues

### 🎬 Media
- spotify-player, openai-whisper, openai-image-gen, video-frames, camsnap, canvas, gifgrep

### 🌐 Web/Search
- weather, summarize, blogwatcher, xurl

### 🔧 Sistēma/Dev
- healthcheck, tmux, skill-creator, coding-agent, session-logs

### 📄 Dokumenti
- nano-pdf, nano-banana-pro

### 🤖 AI/LLM
- gemini, openai-whisper-api, oracle

### 🏠 Smart Home
- openhue (Philips Hue), mcporter

### 🎮 Gaming/Fun
- eightctl, goplaces, songsee, peekaboo, ordercli

### 📱 Platform-specific
- apple-notes, apple-reminders, bear-notes, bluebubbles, imsg, things-mac

---

## ✅ Ieteikumi Android Ierīcei

### 🌟 **Obligāti Instalēt** (Top 5)
1. **healthcheck** - Sistēmas drošības pārbaudes
2. **self-improvement** - Kļūdu un mācību reģistrēšana
3. **weather** - Laika apstākļi bez API
4. **summarize** - Ātri kopsavilkumi
5. **skill-creator** - Savu skills veidošana

### ⭐ **Ļoti Ieteicamas**
- **obsidian** - Ja lieto Obsidian piezīmes
- **canvas** - HTML satura attēlošana
- **discord/slack** - Ja aktīvi lieto šos servisus
- **notion** - Ja lieto Notion
- **openai-whisper** - Audio transkripcijai
- **tmux** - Ilgstošiem procesiem

### 📝 **Pēc Vajadzības**
- **github** - Ja strādā ar kodu
- **spotify-player** - Ja lieto Spotify
- **trello** - Ja lieto Trello
- **gog** - Ja aktīvi lieto Google pakalpojumus
- **nano-pdf** - Ja bieži rediģē PDF

---

## 🔧 Kā Instalēt Skills

### No skills.sh ekosistēmas:
```bash
npx skills find [atslēgvārds]
npx skills add owner/repo@skill-name -g -y
```

### Manuāli uz Android (Termux):
```bash
# 1. Atrast skill GitHub repozitorijā
# 2. Klonēt uz ~/.openclaw/skills/
git clone https://github.com/owner/skill-name.git ~/.openclaw/skills/skill-name

# 3. Pārliecināties, ka ir SKILL.md
ls ~/.openclaw/skills/skill-name/SKILL.md
```

### Kompilēt/instalēt CLI rīkus (piemēram, spogo):
```bash
# Ja ir Go
pkg install golang
go install github.com/xxx/yyy@latest

# Ja ir Python
pip install package-name

# Caur termux repositories
pkg install [package]
```

---

## ⚠️ Zināmi Ierobežojumi Android

1. **Nav Homebrew** - Daudziem skills vajag brew installāciju, kas nav pieejama Android
2. **Bīnāro trūkums** - Daži CLI rīki nav pieejami ARM/Android
3. **OAuth grūtības** - Dažiem Google pakalpojumiem grūti iestatīt OAuth
4. **Fonā strādājoši procesi** - Android var nogalināt ilgstošus procesus

---

## 📈 Kopumā

Android ar Termux un OpenClaw var izmantot **lielāko daļu** no skills funkcionalitātes. Galvenās priekšrocības:
- ✅ Pilnīga shell piekļuve
- ✅ Root pieejams (ja vajag)
- ✅ Python, Node.js, Go darbojas
- ✅ curl, wget, jq utt. pieejami
- ✅ API integrācijas strādā

Galvenie izaicinājumi:
- ⚠️ Daži macOS-specific tools nav pieejami
- ⚠️ Dažreiz jākompilē no source
- ⚠️ Ierobežots atmiņas/CPU resurss salīdzinājumā ar desktop

---

*Pārskats sagatavots: 2026-03-06*
*Dzii - OpenClaw AI Assistant on POCOPHONE F1*
