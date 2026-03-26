# FELIX AI TRADING SYSTEM - HEARTBEAT TASKS
# Šīs ir regulāras pārbaudes, ko veic AI

## Uzdevumi:

### 1. Pārbaudīt Felix AI uzrauga statusu
# Command: bash ~/.openclaw/workspace/felix status
# Interval: Every 5 minutes
# Alert if: AI supervisor is not running

### 2. Pārbaudīt jaunos noraidītos signālus
# Command: tail -5 ~/.trading/data/rejections.jsonl
# Interval: Every 2 minutes
# Action: Mēģināt labot ar AI

### 3. Pārbaudīt atvērtās pozīcijas IG
# Command: bash ~/.trading/ig_api.sh positions
# Interval: Every 10 minutes
# Alert if: Unexpected positions or errors
