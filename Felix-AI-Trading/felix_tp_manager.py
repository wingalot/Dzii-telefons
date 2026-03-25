#!/usr/bin/env python3
"""
FELIX TP MANAGER - FIXED VERSION
Manages take profits and stop losses for IG positions
"""

import os
import sys
import json
import time
import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
TRADING_DIR = Path.home() / ".trading"
STATE_FILE = BASE_DIR / "state" / "tp_manager_state.json"
LOG_FILE = BASE_DIR / "logs" / "tp_manager.log"
PID_FILE = BASE_DIR / "tp_manager.pid"
IG_API = TRADING_DIR / "ig_api.sh"

# Files for communication with Signal Hub
SIGNAL_INBOX = BASE_DIR / "state" / "new_signal.json"
TP_MANAGER_TRIGGER = BASE_DIR / "state" / "trigger_tp_manager"

# Settings
TP_FALLBACK_PERCENT = 0.5  # 50%
CHECK_INTERVAL = 5  # seconds

# Setup logging
os.makedirs(BASE_DIR / "logs", exist_ok=True)
os.makedirs(BASE_DIR / "state", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [TP-MANAGER] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TPManager:
    """Manages TP/SL levels for IG positions"""
    
    def __init__(self):
        self.state_file = STATE_FILE
        self.positions = {}
        self.pending_signals = []
        self.load_state()
    
    def load_state(self):
        """Load manager state"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                self.state = json.load(f)
                self.positions = self.state.get('positions', {})
        else:
            self.state = {
                'started': datetime.now().isoformat(),
                'positions_closed': 0,
                'tp1_hits': 0,
                'tp2_hits': 0,
                'tp3_hits': 0,
                'sl_hits': 0
            }
            self.positions = {}
    
    def save_state(self):
        """Save manager state"""
        self.state['positions'] = self.positions
        self.state['last_update'] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def check_for_trigger(self):
        """Check if Signal Hub triggered us"""
        if Path(TP_MANAGER_TRIGGER).exists():
            try:
                Path(TP_MANAGER_TRIGGER).unlink()
                return True
            except:
                pass
        return False
    
    def check_for_new_signals(self):
        """Check for new signals from Signal Hub"""
        if not Path(SIGNAL_INBOX).exists():
            return None
        
        try:
            with open(SIGNAL_INBOX) as f:
                signal = json.load(f)
            
            # Mark as processed by removing file
            try:
                Path(SIGNAL_INBOX).unlink()
            except:
                pass
            
            return signal
        except Exception as e:
            logger.error(f"Error reading signal inbox: {e}")
            return None
    
    def register_position(self, deal_id, pair, direction, entry, sl, tp_levels, size, epic):
        """Register a new position for TP tracking"""
        self.positions[deal_id] = {
            'deal_id': deal_id,
            'pair': pair,
            'direction': direction,
            'entry': float(entry),
            'initial_sl': float(sl) if sl else None,
            'current_sl': float(sl) if sl else None,
            'tp1': float(tp_levels[0]) if len(tp_levels) > 0 and tp_levels[0] else None,
            'tp2': float(tp_levels[1]) if len(tp_levels) > 1 and tp_levels[1] else None,
            'tp3': float(tp_levels[2]) if len(tp_levels) > 2 and tp_levels[2] else None,
            'size': float(size),
            'epic': epic,
            'status': 'open',
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'sl_hit': False,
            'sl_moved_to_tp1': False,  # Between TP1-TP2
            'sl_moved_to_tp2': False,  # Between TP2-TP3
            'opened_at': datetime.now().isoformat(),
            'tp2_peak_price': None
        }
        self.save_state()
        logger.info(f"📊 Position registered: {direction} {pair} @ {entry}")
        logger.info(f"  TP1={tp_levels[0] if len(tp_levels) > 0 else None}, TP2={tp_levels[1] if len(tp_levels) > 1 else None}, TP3={tp_levels[2] if len(tp_levels) > 2 else None}")
    
    def get_ig_positions(self):
        """Get current open positions from IG"""
        try:
            result = subprocess.run(
                ['bash', str(IG_API), 'positions'],
                capture_output=True,
                text=True,
                timeout=10
            )
            data = json.loads(result.stdout)
            return data.get('positions', [])
        except Exception as e:
            logger.error(f"Failed to get IG positions: {e}")
            return []
    
    def get_market_price(self, epic):
        """Get current market price"""
        try:
            result = subprocess.run(
                ['bash', str(IG_API), 'market', epic],
                capture_output=True,
                text=True,
                timeout=10
            )
            data = json.loads(result.stdout)
            bid = float(data.get('snapshot', {}).get('bid', 0))
            ask = float(data.get('snapshot', {}).get('offer', 0))
            if bid > 0 and ask > 0:
                return (bid + ask) / 2
            return None
        except Exception as e:
            logger.error(f"Failed to get price for {epic}: {e}")
            return None
    
    def close_position(self, deal_id, epic, direction, size, reason):
        """Close position via IG API"""
        try:
            close_direction = 'SELL' if direction == 'BUY' else 'BUY'
            result = subprocess.run(
                ['bash', str(IG_API), 'close', deal_id, close_direction, str(size)],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if '"dealId"' in result.stdout or '"dealReference"' in result.stdout:
                logger.info(f"✅ Position closed: {deal_id} [{reason}]")
                return True
            else:
                logger.error(f"❌ Failed to close: {result.stdout}")
                return False
        except Exception as e:
            logger.error(f"❌ Error closing position: {e}")
            return False
    
    def check_tp_sl_conditions(self, deal_id, current_price):
        """Check TP and SL conditions for a position - NEW TRAILING LOGIC"""
        pos = self.positions[deal_id]
        direction = pos['direction']
        entry = pos['entry']
        current_sl = pos.get('current_sl')
        tp1 = pos.get('tp1')
        tp2 = pos.get('tp2')
        tp3 = pos.get('tp3')
        
        # Check SL hit first (highest priority)
        if current_sl and not pos.get('sl_hit'):
            if direction == 'BUY':
                sl_hit = current_price <= current_sl
            else:  # SELL
                sl_hit = current_price >= current_sl
            
            if sl_hit:
                pos['sl_hit'] = True
                logger.info(f"🛑 SL HIT: {pos['pair']} @ {current_price} (SL: {current_sl})")
                self.state['sl_hits'] = self.state.get('sl_hits', 0) + 1
                self.save_state()
                return 'close_sl'
        
        # BUY: price goes up, SELL: price goes down
        if direction == 'BUY':
            tp1_hit = tp1 and current_price >= tp1
            tp2_hit = tp2 and current_price >= tp2
            tp3_hit = tp3 and current_price >= tp3
            # Between TP1 and TP2
            between_tp1_tp2 = tp1 and tp2 and tp1 <= current_price < tp2
            # Between TP2 and TP3
            between_tp2_tp3 = tp2 and tp3 and tp2 <= current_price < tp3
        else:  # SELL
            tp1_hit = tp1 and current_price <= tp1
            tp2_hit = tp2 and current_price <= tp2
            tp3_hit = tp3 and current_price <= tp3
            # Between TP1 and TP2 (for SELL: tp1 > current_price >= tp2)
            between_tp1_tp2 = tp1 and tp2 and tp1 >= current_price > tp2
            # Between TP2 and TP3 (for SELL: tp2 > current_price >= tp3)
            between_tp2_tp3 = tp2 and tp3 and tp2 >= current_price > tp3
        
        # TP1 hit - only mark it, NOTHING happens to SL
        if tp1_hit and not pos['tp1_hit']:
            pos['tp1_hit'] = True
            logger.info(f"🎯 TP1 HIT: {pos['pair']} @ {current_price}")
            self.state['tp1_hits'] += 1
            self.save_state()
        
        # Between TP1 and TP2 - move SL to TP1
        if pos['tp1_hit'] and between_tp1_tp2 and not pos.get('sl_moved_to_tp1'):
            pos['sl_moved_to_tp1'] = True
            pos['current_sl'] = tp1
            logger.info(f"📈 Between TP1-TP2: {pos['pair']} @ {current_price}")
            logger.info(f"  SL moved to TP1 ({tp1}) - locking TP1 profits!")
            self.save_state()
        
        # TP2 hit - only mark it, SL stays at TP1
        if tp2_hit and not pos['tp2_hit']:
            pos['tp2_hit'] = True
            pos['tp2_peak_price'] = current_price
            logger.info(f"🎯🎯 TP2 HIT: {pos['pair']} @ {current_price}")
            self.state['tp2_hits'] += 1
            self.save_state()
        
        # Between TP2 and TP3 - move SL to TP2
        if pos['tp2_hit'] and between_tp2_tp3 and not pos.get('sl_moved_to_tp2'):
            pos['sl_moved_to_tp2'] = True
            pos['current_sl'] = tp2
            logger.info(f"📈📈 Between TP2-TP3: {pos['pair']} @ {current_price}")
            logger.info(f"  SL moved to TP2 ({tp2}) - locking TP2 profits!")
            self.save_state()
        
        # TP3 hit - close position
        if tp3_hit and not pos['tp3_hit']:
            pos['tp3_hit'] = True
            logger.info(f"🎯🎯🎯 TP3 HIT: {pos['pair']} @ {current_price}")
            self.state['tp3_hits'] += 1
            self.save_state()
            return 'close_tp3'
        
        return 'hold'
    
    def epic_to_pair(self, epic):
        """Convert IG epic to pair"""
        epic_map = {
            'CS.D.CFDGOLD.CFDGC.IP': 'XAUUSD',
            'CS.D.CFDGOLD.CFD.IP': 'XAUUSD',
            'CS.D.EURUSD.CFD.IP': 'EURUSD',
            'CS.D.GBPUSD.CFD.IP': 'GBPUSD',
            'CS.D.USDJPY.CFD.IP': 'USDJPY',
            'CS.D.GBPJPY.CFD.IP': 'GBPJPY',
            'CS.D.EURJPY.CFD.IP': 'EURJPY',
            'CS.D.AUDUSD.CFD.IP': 'AUDUSD',
            'CS.D.NZDUSD.CFD.IP': 'NZDUSD',
            'CS.D.USDCAD.CFD.IP': 'USDCAD',
            'CS.D.EURGBP.CFD.IP': 'EURGBP',
        }
        return epic_map.get(epic)
    
    def find_position_by_signal(self, pair, direction):
        """Find position in IG that matches signal"""
        ig_positions = self.get_ig_positions()
        
        for ig_pos in ig_positions:
            pos_data = ig_pos.get('position', {})
            market_data = ig_pos.get('market', {})
            
            epic = market_data.get('epic', '')
            pos_pair = self.epic_to_pair(epic)
            pos_direction = pos_data.get('direction')
            
            if pos_pair == pair and pos_direction == direction:
                return {
                    'deal_id': pos_data.get('dealId'),
                    'epic': epic,
                    'entry': pos_data.get('openLevel'),
                    'sl': pos_data.get('stopLevel'),
                    'size': pos_data.get('dealSize')
                }
        return None
    
    async def run(self):
        """Main TP manager loop"""
        logger.info("=" * 60)
        logger.info("🎯 FELIX TP MANAGER (FIXED VERSION)")
        logger.info("=" * 60)
        logger.info("Monitoring TP/SL for all positions...")
        logger.info(f"Check interval: {CHECK_INTERVAL}s")
        
        while True:
            try:
                # Check for new signal
                new_signal = self.check_for_new_signals()
                
                if new_signal:
                    logger.info(f"📨 New signal received: {new_signal['id']}")
                    
                    # Extract signal info
                    text = new_signal.get('text', '')
                    
                    # Parse TP levels from signal
                    import re
                    pair_match = re.search(r'(EURUSD|GBPUSD|USDJPY|GBPJPY|EURJPY|AUDUSD|NZDUSD|USDCAD|EURGBP|XAUUSD|GOLD)', text.upper())
                    direction_match = re.search(r'(BUY|SELL)', text.upper())
                    
                    if pair_match and direction_match:
                        pair = pair_match.group(1)
                        if pair == 'GOLD':
                            pair = 'XAUUSD'
                        direction = direction_match.group(1)
                        
                        # Extract entry price
                        entry_match = re.search(r'(?:BUY|SELL)\s+NOW\s+([\d.]+)', text.upper())
                        entry = float(entry_match.group(1)) if entry_match else None
                        
                        # Check for relative TP format (+15 Pips, +30 Pips)
                        relative_tp_match = re.search(r'TP\d*\s*\+?(\d+)\s*PIPS?', text.upper())
                        
                        tp_levels = []
                        if relative_tp_match and entry:
                            # Calculate absolute TP from relative pips
                            tp_pips = int(relative_tp_match.group(1))
                            pip_size = 0.01 if 'XAU' in pair or 'JPY' in pair else 0.0001
                            if direction == 'BUY':
                                tp1 = entry + (tp_pips * pip_size)
                            else:
                                tp1 = entry - (tp_pips * pip_size)
                            tp_levels = [str(tp1)]
                            logger.info(f"  Relative TP: +{tp_pips} pips = {tp1}")
                        else:
                            # Extract absolute TP levels
                            tp_levels = re.findall(r'TP\d*[\s:#]*([\d.]+)', text)
                        
                        # Extract SL
                        sl_match = re.search(r'SL[\s:#]*([\d.]+)', text.upper())
                        sl = sl_match.group(1) if sl_match else None
                        
                        # Wait a bit for position to be opened in IG
                        logger.info("⏳ Waiting for position to appear in IG...")
                        await asyncio.sleep(10)
                        
                        # Find the position
                        ig_pos = self.find_position_by_signal(pair, direction)
                        
                        if ig_pos:
                            logger.info(f"✅ Found IG position: {ig_pos['deal_id']}")
                            self.register_position(
                                ig_pos['deal_id'],
                                pair,
                                direction,
                                ig_pos['entry'],
                                ig_pos['sl'] or sl,
                                tp_levels,
                                ig_pos['size'],
                                ig_pos['epic']
                            )
                        else:
                            logger.warning(f"⚠️ Position not found in IG for {pair} {direction}")
                
                # Monitor existing positions
                for deal_id in list(self.positions.keys()):
                    pos = self.positions[deal_id]
                    
                    if pos['status'] == 'closed':
                        continue
                    
                    # Check if still open in IG
                    ig_positions = self.get_ig_positions()
                    ig_deal_ids = [p.get('position', {}).get('dealId') for p in ig_positions]
                    
                    if deal_id not in ig_deal_ids:
                        logger.info(f"📤 Position {deal_id} closed externally")
                        pos['status'] = 'closed'
                        self.save_state()
                        continue
                    
                    # Get price and check conditions
                    current_price = self.get_market_price(pos['epic'])
                    if current_price is None:
                        continue
                    
                    action = self.check_tp_sl_conditions(deal_id, current_price)
                    
                    if action == 'close_sl':
                        success = self.close_position(deal_id, pos['epic'], pos['direction'], pos['size'], 'SL HIT')
                        if success:
                            pos['status'] = 'closed'
                            pos['closed_at'] = datetime.now().isoformat()
                            pos['close_price'] = current_price
                            pos['close_reason'] = 'sl_hit'
                            self.state['positions_closed'] += 1
                            self.save_state()
                    
                    elif action == 'close_tp3':
                        success = self.close_position(deal_id, pos['epic'], pos['direction'], pos['size'], 'TP3')
                        if success:
                            pos['status'] = 'closed'
                            pos['closed_at'] = datetime.now().isoformat()
                            pos['close_price'] = current_price
                            pos['close_reason'] = 'tp3_hit'
                            self.state['positions_closed'] += 1
                            self.save_state()
                    
                    elif action == 'close_fallback':
                        success = self.close_position(deal_id, pos['epic'], pos['direction'], pos['size'], 'FALLBACK')
                        if success:
                            pos['status'] = 'closed'
                            pos['closed_at'] = datetime.now().isoformat()
                            pos['close_price'] = current_price
                            pos['close_reason'] = 'fallback'
                            self.state['positions_closed'] += 1
                            self.save_state()
                
                # Sleep before next check
                await asyncio.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(CHECK_INTERVAL)

def write_pid():
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def remove_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

def main():
    write_pid()
    try:
        manager = TPManager()
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        logger.info("🛑 TP Manager stopped")
    finally:
        remove_pid()

if __name__ == "__main__":
    main()
