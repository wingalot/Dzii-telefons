#!/usr/bin/env python3
"""
SHARED STATE MODULE
Centralized state management for all Felix AI components
- Signal Hub, TP Manager, AI Supervisor all read/write here
- Ensures consistency across the system
"""

import json
import os
import fcntl
from datetime import datetime
from pathlib import Path

SHARED_STATE_FILE = Path.home() / ".openclaw" / "ai_supervisor" / "state" / "shared_state.json"

def _load_state():
    """Load shared state from file"""
    if SHARED_STATE_FILE.exists():
        try:
            with open(SHARED_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "schema_version": "2.0",
        "last_updated": datetime.now().isoformat(),
        "active_signals": {},
        "signal_history": [],
        "ig_positions": {},
        "pending_orders": {},
        "stats": {
            "total_signals": 0,
            "executed": 0,
            "rejected": 0,
            "closed_tp": 0,
            "closed_sl": 0,
            "closed_manual": 0
        }
    }

def _save_state(state):
    """Save shared state to file with locking"""
    state['last_updated'] = datetime.now().isoformat()
    with open(SHARED_STATE_FILE, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(state, f, indent=2)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

# Public API
def get_state():
    """Get current shared state"""
    return _load_state()

def register_signal(signal_data, source="signal_hub"):
    """Register a new signal in shared state"""
    state = _load_state()
    signal_id = signal_data.get('id') or signal_data.get('signal_id')
    
    if not signal_id:
        return False
    
    state['active_signals'][signal_id] = {
        'pair': signal_data.get('pair'),
        'direction': signal_data.get('direction'),
        'entry': signal_data.get('entry'),
        'sl': signal_data.get('sl'),
        'tp_levels': signal_data.get('tp_levels', []),
        'is_limit': signal_data.get('is_limit', False),
        'status': 'pending',
        'source': source,
        'registered_at': datetime.now().isoformat(),
        'deal_id': None,
        'closed': False
    }
    state['stats']['total_signals'] += 1
    _save_state(state)
    return True

def update_signal_execution(signal_id, deal_id, execution_data):
    """Update signal with execution results"""
    state = _load_state()
    
    if signal_id in state['active_signals']:
        state['active_signals'][signal_id]['deal_id'] = deal_id
        state['active_signals'][signal_id]['status'] = 'executed'
        state['active_signals'][signal_id]['executed_at'] = datetime.now().isoformat()
        state['active_signals'][signal_id]['execution'] = execution_data
        
        # Also register in ig_positions
        if deal_id:
            state['ig_positions'][deal_id] = {
                'signal_id': signal_id,
                'pair': state['active_signals'][signal_id]['pair'],
                'direction': state['active_signals'][signal_id]['direction'],
                'status': 'open'
            }
        
        state['stats']['executed'] += 1
        _save_state(state)
        return True
    return False

def register_position(deal_id, position_data):
    """Register a position from IG"""
    state = _load_state()
    
    state['ig_positions'][deal_id] = {
        'pair': position_data.get('pair'),
        'direction': position_data.get('direction'),
        'entry': position_data.get('entry'),
        'size': position_data.get('size'),
        'status': 'open',
        'registered_at': datetime.now().isoformat(),
        'signal_id': position_data.get('signal_id')
    }
    _save_state(state)

def close_position(deal_id, reason, close_price=None):
    """Mark position as closed"""
    state = _load_state()
    
    if deal_id in state['ig_positions']:
        state['ig_positions'][deal_id]['status'] = 'closed'
        state['ig_positions'][deal_id]['close_reason'] = reason
        state['ig_positions'][deal_id]['close_price'] = close_price
        state['ig_positions'][deal_id]['closed_at'] = datetime.now().isoformat()
        
        # Update signal status too
        signal_id = state['ig_positions'][deal_id].get('signal_id')
        if signal_id and signal_id in state['active_signals']:
            state['active_signals'][signal_id]['closed'] = True
            state['active_signals'][signal_id]['status'] = f'closed_{reason}'
        
        # Update stats
        if 'tp' in reason.lower():
            state['stats']['closed_tp'] += 1
        elif 'sl' in reason.lower():
            state['stats']['closed_sl'] += 1
        else:
            state['stats']['closed_manual'] += 1
        
        _save_state(state)
        return True
    return False

def get_unknown_positions(deal_ids_from_ig):
    """Find positions in IG that don't belong to our signals"""
    state = _load_state()
    unknown = []
    
    for deal_id in deal_ids_from_ig:
        # Check if this deal_id is tracked
        is_tracked = (
            deal_id in state['ig_positions'] or
            any(sig.get('deal_id') == deal_id for sig in state['active_signals'].values())
        )
        if not is_tracked:
            unknown.append(deal_id)
    
    return unknown

def sync_with_ig(ig_positions_list):
    """Sync shared state with actual IG positions"""
    state = _load_state()
    ig_deal_ids = [p.get('position', {}).get('dealId') for p in ig_positions_list]
    
    # Find positions we track that are closed in IG
    for deal_id in list(state['ig_positions'].keys()):
        if state['ig_positions'][deal_id].get('status') == 'open':
            if deal_id not in ig_deal_ids:
                # Position closed externally
                state['ig_positions'][deal_id]['status'] = 'closed'
                state['ig_positions'][deal_id]['close_reason'] = 'external'
                state['ig_positions'][deal_id]['closed_at'] = datetime.now().isoformat()
    
    # Find positions in IG we don't know about
    known_deal_ids = set(state['ig_positions'].keys())
    known_deal_ids.update(sig.get('deal_id') for sig in state['active_signals'].values() if sig.get('deal_id'))
    
    for ig_pos in ig_positions_list:
        deal_id = ig_pos.get('position', {}).get('dealId')
        if deal_id not in known_deal_ids:
            # Unknown position - register as orphan
            market = ig_pos.get('market', {})
            pos = ig_pos.get('position', {})
            state['ig_positions'][deal_id] = {
                'pair': market.get('instrumentName', '').replace('/', ''),
                'direction': pos.get('direction'),
                'entry': pos.get('openLevel'),
                'size': pos.get('dealSize'),
                'status': 'open_orphan',
                'epic': market.get('epic'),
                'orphan': True,
                'detected_at': datetime.now().isoformat()
            }
    
    _save_state(state)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        state = get_state()
        print(json.dumps(state, indent=2))
