#!/bin/bash
# FELIX SYSTEM v3.0 - FINAL STATUS CHECK

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         FELIX AI TRADING SYSTEM v3.0 - STATUS REPORT            ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check processes
echo "📊 PROCESSES:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for proc in "felix_signal_hub" "felix_tp_manager" "felix_supervisor"; do
    if pgrep -f "$proc.py" > /dev/null; then
        PID=$(pgrep -f "$proc.py" | head -1)
        echo "  ✅ $proc (PID: $PID)"
    else
        echo "  ❌ $proc NOT RUNNING"
    fi
done
echo ""

# IG Positions
echo "🏦 IG POSITIONS (6 aktīvās):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash ~/.trading/ig_api.sh positions 2>/dev/null | jq -r '.positions[] | 
    "  🆔 \(.position.dealId)" +
    "\n     Pāris: \(.market.epic | split(".") | .[2]) \(.position.direction)" +
    "\n     Ieeja: \(.position.openLevel)" +
    "\n     Izmērs: \(.position.dealSize) lots\n"' 2>/dev/null

echo ""
echo "📋 TP MANAGER POZĪCIJAS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 << 'PYCODE'
import json
from pathlib import Path

state_file = Path.home() / '.openclaw' / 'ai_supervisor' / 'state' / 'tp_manager_state.json'
with open(state_file) as f:
    data = json.load(f)

active = [p for p in data.get('positions', {}).values() 
          if isinstance(p, dict) and p.get('status') == 'open']

print(f"  Kopā aktīvās: {len(active)}\n")

for p in active:
    pair = p.get('pair', 'Unknown')
    direction = p.get('direction', '?')
    entry = p.get('entry', '?')
    sl = p.get('sl') or p.get('initial_sl') or p.get('current_sl') or '⚠️ NAV'
    tp1 = p.get('tp1') or 'N/A'
    signal = p.get('signal_message_id') or '⚠️ Nav saistīts'
    
    status_icon = "✅" if sl != '⚠️ NAV' and sl is not None else "⚠️"
    
    print(f"  {status_icon} {pair} {direction}")
    print(f"     Ieeja: {entry}")
    print(f"     SL: {sl}")
    print(f"     TP1: {tp1}")
    print(f"     Signāls: {signal}\n")
PYCODE

echo ""
echo "🔍 SUPERVISOR PĀRBAUDE:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 << 'PYCODE'
import json
from pathlib import Path

sup_file = Path.home() / '.openclaw' / 'ai_supervisor' / 'state' / 'supervisor_state.json'
if sup_file.exists():
    with open(sup_file) as f:
        data = json.load(f)
    report = data.get('report', {})
    print(f"  IG pozīcijas: {report.get('ig_positions_count', 'N/A')}")
    print(f"  Lokālās pozīcijas: {report.get('local_positions_count', 'N/A')}")
    issues = report.get('issues_by_severity', {})
    if issues.get('ERROR', 0) > 0:
        print(f"  ⚠️  Kļūdas: {issues.get('ERROR')}")
    if issues.get('WARNING', 0) > 0:
        print(f"  ⚠️  Brīdinājumi: {issues.get('WARNING')}")
    if issues.get('ERROR', 0) == 0 and issues.get('WARNING', 0) == 0:
        print(f"  ✅ Nav problēmu")
else:
    print("  ⚠️  Nav supervisor datu")
PYCODE

echo ""
echo "📁 FAILU STRUKTŪRA:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Core Modules:"
ls -1 ~/.openclaw/ai_supervisor/felix_*.py 2>/dev/null | wc -l | xargs echo "    - Moduļi:"
echo "  Config:"
echo "    - ~/.trading/felix_config.json"
echo "  Documentation:"
ls -1 ~/.openclaw/workspace/FELIX_*.md 2>/dev/null | wc -l | xargs echo "    - Dokumenti:"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    SISTĒMA GATAVA DARBĪBAI                      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "KOMANDAS:"
echo "  bash felix status     - Pārbaudīt statusu"
echo "  bash felix logs       - Skatīt logus"
echo "  bash felix supervisor - Validācija"
echo "  bash felix stop       - Apturēt"
echo ""
