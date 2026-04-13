#!/usr/bin/env python3
"""
Match IG positions with Telegram signals by entry price proximity
"""
import json
import subprocess
from pathlib import Path

BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
TRADING_DIR = Path.home() / ".trading"

def get_ig_positions():
    """Get current IG positions"""
    try:
        result = subprocess.run(
            ['bash', str(TRADING_DIR / 'ig_api.sh'), 'positions'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('positions', [])
    except Exception as e:
        print(f"Error: {e}")
    return []

def get_tp_manager_positions():
    """Get TP Manager positions"""
    try:
        with open(BASE_DIR / "state" / "tp_manager_state.json") as f:
            data = json.load(f)
            return data.get('positions', {})
    except:
        return {}

def main():
    ig_positions = get_ig_positions()
    local_positions = get_tp_manager_positions()
    
    print("=" * 80)
    print("IG POZĪCIJU SINHRONIZĀCIJAS PĀRBAUDE")
    print("=" * 80)
    print()
    
    # Active IG positions
    print("📊 AKTĪVĀS IG POZĪCIJAS:")
    print("-" * 80)
    
    for pos in ig_positions:
        deal_id = pos.get('position', {}).get('dealId', '')
        epic = pos.get('market', {}).get('epic', '')
        pair = epic.replace('CS.D.', '').replace('.CFD.IP', '').replace('.CFDGC.IP', '')
        direction = pos.get('position', {}).get('direction', '')
        entry = pos.get('position', {}).get('openLevel', '')
        size = pos.get('position', {}).get('dealSize', '')
        
        # Find matching local position
        local = local_positions.get(deal_id, {})
        tp1 = local.get('tp1', 'N/A')
        sl = local.get('sl', 'N/A')
        signal_id = local.get('signal_message_id', 'N/A')
        
        print(f"\n🆔 {deal_id}")
        print(f"   Pāris: {pair} {direction}")
        print(f"   Ieeja: {entry}")
        print(f"   Izmērs: {size}")
        print(f"   TP1: {tp1} | SL: {sl}")
        print(f"   Signāla ID: {signal_id}")
        
        if not sl or sl == 'N/A':
            print(f"   ⚠️  TRŪKST SL!")
    
    print()
    print("=" * 80)
    
    # Check for duplicates
    print("\n🔍 DUBLIKĀTU PĀRBAUDE:")
    print("-" * 80)
    
    seen = {}
    duplicates = []
    
    for pos in ig_positions:
        epic = pos.get('market', {}).get('epic', '')
        pair = epic.replace('CS.D.', '').replace('.CFD.IP', '').replace('.CFDGC.IP', '')
        direction = pos.get('position', {}).get('direction', '')
        deal_id = pos.get('position', {}).get('dealId', '')
        
        key = f"{pair}:{direction}"
        if key in seen:
            duplicates.append((key, seen[key], deal_id))
        else:
            seen[key] = deal_id
    
    if duplicates:
        print(f"\n⚠️  Atrasti {len(duplicates)} dublikāti:")
        for key, first_id, dup_id in duplicates:
            print(f"   {key}: {first_id} un {dup_id}")
    else:
        print("\n✅ Dublikātu nav")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
