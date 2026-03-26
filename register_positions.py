#!/data/data/com.termux/files/usr/bin/env python3
"""Register existing IG positions in TP Manager state"""
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
STATE_FILE = BASE_DIR / "state" / "tp_manager_state.json"

# New positions from recent trades
NEW_POSITIONS = {
    "DIAAAAWXYRJAMAD": {"pair": "XAUUSD", "direction": "BUY", "entry": 4402.23, "size": 0.5, "epic": "CS.D.CFDGOLD.CFDGC.IP"},
    "DIAAAAWXYQ73CAE": {"pair": "EURUSD", "direction": "BUY", "entry": 11571.4, "size": 1.0, "epic": "CS.D.EURUSD.CFD.IP"},
    "DIAAAAWXYQ5NDA8": {"pair": "GBPUSD", "direction": "SELL", "entry": 1.33711, "size": 1.0, "epic": "CS.D.GBPUSD.CFD.IP"},
    "DIAAAAWXYRBGGBC": {"pair": "USDJPY", "direction": "SELL", "entry": 159.065, "size": 0.5, "epic": "CS.D.USDJPY.CFD.IP"},
    "DIAAAAWXYQ9JVAG": {"pair": "AUDUSD", "direction": "BUY", "entry": 0.69454, "size": 1.0, "epic": "CS.D.AUDUSD.CFD.IP"},
    "DIAAAAWXYQUBAAZ": {"pair": "EURGBP", "direction": "BUY", "entry": 0.86535, "size": 1.0, "epic": "CS.D.EURGBP.CFD.IP"},
    "DIAAAAWXYQYS7A3": {"pair": "GBPJPY", "direction": "BUY", "entry": 212.710, "size": 0.5, "epic": "CS.D.GBPJPY.CFD.IP"},
    "DIAAAAWXYQ6KQAJ": {"pair": "EURJPY", "direction": "SELL", "entry": 184.052, "size": 0.5, "epic": "CS.D.EURJPY.CFD.IP"},
    "DIAAAAWXYREHAAN": {"pair": "USDCAD", "direction": "BUY", "entry": 1.37805, "size": 1.0, "epic": "CS.D.USDCAD.CFD.IP"},
    "DIAAAAWXYQ6L3AJ": {"pair": "NZDUSD", "direction": "SELL", "entry": 0.58006, "size": 1.0, "epic": "CS.D.NZDUSD.CFD.IP"},
}

def calculate_tp_levels(pair, direction, entry, size):
    """Calculate TP levels for a position"""
    # Pip value calculation
    if pair in ["XAUUSD"]:
        pip_size = 1.0  # $1 for gold
        tp1_pips = 10
        tp2_pips = 20  
        tp3_pips = 50
    elif "JPY" in pair:
        pip_size = 0.01
        tp1_pips = 10
        tp2_pips = 20
        tp3_pips = 40
    else:
        pip_size = 0.0001
        tp1_pips = 10
        tp2_pips = 20
        tp3_pips = 40
    
    if direction == "BUY":
        tp1 = entry + (tp1_pips * pip_size)
        tp2 = entry + (tp2_pips * pip_size)
        tp3 = entry + (tp3_pips * pip_size)
        sl = entry - (15 * pip_size)
    else:  # SELL
        tp1 = entry - (tp1_pips * pip_size)
        tp2 = entry - (tp2_pips * pip_size)
        tp3 = entry - (tp3_pips * pip_size)
        sl = entry + (15 * pip_size)
    
    return round(tp1, 5), round(tp2, 5), round(tp3, 5), round(sl, 5)

# Load existing state
with open(STATE_FILE) as f:
    state = json.load(f)

now = datetime.now().isoformat()
registered = 0

for deal_id, data in NEW_POSITIONS.items():
    if deal_id in state.get('positions', {}):
        print(f"⚠️ {deal_id} already registered")
        continue
    
    tp1, tp2, tp3, sl = calculate_tp_levels(
        data['pair'], data['direction'], data['entry'], data['size']
    )
    
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
        'sl_moved_to_tp1': False,
        'opened_at': now,
        'tp2_peak_price': None
    }
    registered += 1
    print(f"✅ Registered {data['pair']} {data['direction']} - TP1:{tp1} TP2:{tp2} TP3:{tp3} SL:{sl}")

state['last_update'] = now

# Save state
with open(STATE_FILE, 'w') as f:
    json.dump(state, f, indent=2)

print(f"\n🎯 Registered {registered} new positions in TP Manager")
