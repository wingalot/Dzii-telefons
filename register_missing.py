import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
STATE_FILE = BASE_DIR / "state" / "tp_manager_state.json"

# Missing positions from IG
MISSING = {
    "DIAAAAWX8EM7TAR": {"pair": "XAUUSD", "direction": "BUY", "entry": 4539.94, "size": 0.5, "epic": "CS.D.CFDGOLD.CFDGC.IP"},
    "DIAAAAWX8G2A4AG": {"pair": "GBPUSD", "direction": "BUY", "entry": 1.33931, "size": 1.0, "epic": "CS.D.GBPUSD.CFD.IP"},
    "DIAAAAWX8KSWQA7": {"pair": "XAUUSD", "direction": "BUY", "entry": 4555.36, "size": 0.5, "epic": "CS.D.CFDGOLD.CFDGC.IP"},
    "DIAAAAWX8J29AAZ": {"pair": "XAUUSD", "direction": "BUY", "entry": 4554.32, "size": 0.5, "epic": "CS.D.CFDGOLD.CFDGC.IP"},
}

def calculate_tp_levels(pair, direction, entry, size):
    if pair == "XAUUSD":
        pip_size = 1.0
        tp1_pips, tp2_pips, tp3_pips, sl_pips = 10, 20, 50, 15
    elif "JPY" in pair:
        pip_size = 0.01
        tp1_pips, tp2_pips, tp3_pips, sl_pips = 10, 20, 40, 15
    else:
        pip_size = 0.0001
        tp1_pips, tp2_pips, tp3_pips, sl_pips = 10, 20, 40, 15
    
    if direction == "BUY":
        tp1 = entry + (tp1_pips * pip_size)
        tp2 = entry + (tp2_pips * pip_size)
        tp3 = entry + (tp3_pips * pip_size)
        sl = entry - (sl_pips * pip_size)
    else:
        tp1 = entry - (tp1_pips * pip_size)
        tp2 = entry - (tp2_pips * pip_size)
        tp3 = entry - (tp3_pips * pip_size)
        sl = entry + (sl_pips * pip_size)
    
    return round(tp1, 5), round(tp2, 5), round(tp3, 5), round(sl, 5)

with open(STATE_FILE) as f:
    state = json.load(f)

now = datetime.now().isoformat()
registered = 0

for deal_id, data in MISSING.items():
    if deal_id in state.get('positions', {}):
        print(f"⚠️ {deal_id} already registered")
        continue
    
    tp1, tp2, tp3, sl = calculate_tp_levels(data['pair'], data['direction'], data['entry'], data['size'])
    
    state['positions'][deal_id] = {
        'deal_id': deal_id,
        'pair': data['pair'],
        'direction': data['direction'],
        'entry': data['entry'],
        'initial_sl': sl,
        'current_sl': sl,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'size': data['size'],
        'epic': data['epic'],
        'status': 'open',
        'tp1_hit': False,
        'tp2_hit': False,
        'tp3_hit': False,
        'sl_hit': False,
        'sl_moved_to_tp1': False,
        'sl_moved_to_tp2': False,
        'opened_at': now,
        'tp2_peak_price': None
    }
    registered += 1
    print(f"✅ Registered {data['pair']} {data['direction']} @ {data['entry']} | TP1:{tp1} TP2:{tp2} TP3:{tp3}")

state['last_update'] = now
with open(STATE_FILE, 'w') as f:
    json.dump(state, f, indent=2)

print(f"\n🎯 Registered {registered} missing positions")
