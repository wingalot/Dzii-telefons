#!/usr/bin/env python3
import sys
sys.path.insert(0, '/data/data/com.termux/files/home/.openclaw/ai_supervisor')
from felix_signal_hub import SignalHub
import re

hub = SignalHub()

# Test with actual problematic signal
test_signals = [
    {
        "name": "EURUSD detailed",
        "text": "**🚨 SIGNAL ALERT 🚨**\n\n**🌐 #EURUSD**\n\n**📊 Trade Details:**\ud83d\udcc8**#BUY**\n\n**⚪️ Entry Point:** **1.15580**\n**🔴 Stop Loss (SL): **1.15230\n\n**🟢 Take Profit 1 (TP1):** 1.15730\n**🟢 Take Profit 2 (TP2):** 1.16190\n**🟢 Take Profit 3 (TP3): **1.16720"
    },
    {
        "name": "Simple BUY NOW",
        "text": "XAUUSD BUY NOW 4450\nSet TP1 +30 Pips"
    }
]

for test in test_signals:
    print(f"\n=== {test['name']} ===")
    text = test['text']
    
    pair = hub._extract_pair(text)
    direction = 'BUY' if 'BUY' in text.upper() else 'SELL'
    entry = hub._extract_entry(text)
    sl = hub._extract_sl(text, entry)
    tp = hub._extract_tp_levels(text, entry)
    
    print(f"Pair: {pair}")
    print(f"Direction: {direction}")
    print(f"Entry: {entry}")
    print(f"SL: {sl}")
    print(f"TP: {tp}")
    print(f"Valid: {all([pair, direction, entry, sl])}")
