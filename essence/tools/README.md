# ⚡ Dzii Tools - Android Automation Suite

Structured tool collection for Android device automation via OpenClaw.

## 📁 Directory Structure

```
~/tools/
├── index.json              # Tool registry
├── schemas/                # JSON validation schemas
│   ├── tool_definition.json
│   └── skill_definition.json
├── system/                 # Android system control
├── ai/                     # AI/ML & self-improvement
├── web/                    # Web APIs & search
├── media/                  # Screenshots, audio, video
└── comms/                  # Messaging & notifications
```

## 🔧 Available Tools

### System (Android Control)
| Tool | Description | Root Required |
|------|-------------|---------------|
| `device-screenshot` | Capture screen | ✅ |
| `device-input` | Tap, swipe, keys | ✅ |
| `app-manager` | List/launch/stop apps | ✅ |

### AI (Self-Improvement & Discovery)
| Tool | Description |
|------|-------------|
| `learning-logger` | Log corrections & knowledge |
| `error-logger` | Log command failures |
| `skill-extractor` | Create skills from learnings |
| `learning-reviewer` | Review pending learnings |
| `skill-search` | 🔍 Find skills from ecosystem |
| `skill-install` | ⬇️ Install skills |
| `skill-check` | 📋 List installed skills |

### Web
| Tool | Description |
|------|-------------|
| `brave-search` | Web search via Brave API |
| `gh-cli` | 🐙 GitHub CLI wrapper |

## 🚀 Quick Start

```bash
# System control
bash ~/tools/system/device-screenshot.sh /sdcard/cap.png
bash ~/tools/system/device-input.sh tap 540 1200
bash ~/tools/system/app-manager.sh list third-party

# AI logging
bash ~/.openclaw/skills/self-improving-agent/scripts/log-learning.sh \
  --category correction --summary "Fixed X" --details "Must use Y"

# Skill discovery
dzii ai find "react performance"
dzii ai install vercel-labs/agent-skills@vercel-react-best-practices
dzii ai check

# Web search
bash ~/tools/web/brave-search.sh "query" 5

# GitHub
dzii web github pr list --repo owner/repo
dzii web github run list --repo owner/repo
```

## 📦 Installed Skills

- **self-improving-agent** @ `~/.openclaw/skills/self-improving-agent/`
  - Continuous improvement via error/learning logging
- **find-skills** @ `~/.openclaw/skills/find-skills/`
  - Discover and install skills from the ecosystem
- **github** @ `~/.openclaw/skills/github/`
  - GitHub CLI integration for PRs, issues, CI runs

## 🔑 Configuration

API keys stored in: `~/.openclaw/workspace-thinker/TOOLS.md`

## 📝 Adding New Tools

1. Create `tool.<name>.json` in appropriate category folder
2. Create executable script
3. Update `index.json`
4. Validate against schema

---
*Auto-managed by Dzii ⚡*
