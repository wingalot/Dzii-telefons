#!/usr/bin/env python3
"""
Manual position sync - assign TP/SL from signals to IG positions
"""
import json
from pathlib import Path

BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
STATE_FILE = BASE_DIR / "state" / "tp_manager_state.json"
SIGNAL_QUEUE = BASE_DIR / "state" / "signal_queue.json"

# Load current state
with open(STATE_FILE) as f:
    state = json.load(f)

# Load signals
with open(SIGNAL_QUEUE) as f:
    signals = json.load(f)

# IG positions (manual entry from current IG state) - UPDATED 2026-04-06
# Only 2 positions currently open in IG: EURUSD, NZDJPY
ig_positions = [
    {"deal_id": "DIAAAAWY8KAFKAQ", "pair": "EURUSD", "direction": "BUY", "entry": 1.15201, "size": 1.0},
    {"deal_id": "DIAAAAW2K2ZHRAR", "pair": "NZDJPY", "direction": "BUY", "entry": 91.431, "size": 0.5},
]

# Find matching signals with good data
signal_data = {
    "EURUSD": {"sl": 1.1427, "tp1": 1.1544, "tp2": 1.1565, "tp3": 1.1631, "size": 1.0},  # From signal 9266
    "NZDJPY": {"sl": 90.7, "tp1": 91.525, "tp2": 91.668, "tp3": 92.134, "size": 0.5},  # From signal 9474
}

# Register positions with TP/SL
state["positions"] = {}  # Clear old positions
for pos in ig_positions:
    pair = pos["pair"]
    deal_id = pos["deal_id"]
    
    if pair in signal_data:
        data = signal_data[pair]
        state["positions"][deal_id] = {
            "deal_id": deal_id,
            "pair": pair,
            "direction": pos["direction"],
            "entry": pos["entry"],
            "size": data["size"],
            "epic": f"CS.D.{pair}.CFD.IP",
            "initial_sl": data["sl"],
            "current_sl": data["sl"],
            "tp1": data["tp1"],
            "tp2": data["tp2"],
            "tp3": data["tp3"],
            "tp1_hit": False,
            "tp2_hit": False,
            "tp3_hit": False,
            "status": "open",
            "imported_from_ig": True
        }
        print(f"✅ Registered {pair}: SL={data['sl']}, TP1={data['tp1']}, TP2={data['tp2']}, TP3={data['tp3']}")
    else:
        print(f"⚠️ No signal data for {pair}")

# Save state
with open(STATE_FILE, 'w') as f:
    json.dump(state, f, indent=2)

print(f"\n🎉 Sync complete! Registered {len(state['positions'])} positions")
