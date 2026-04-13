#!/usr/bin/env python3
"""
FELIX TP MANAGER - FIXED VERSION
Key fixes:
1. Proper position registration from signals
2. Handle missing signal data gracefully
3. Sync with IG positions correctly
4. Prevent duplicate position registration
"""

import os
import sys
import json
import time
import asyncio
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum

# Setup paths
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
TRADING_DIR = Path.home() / ".trading"
STATE_FILE = BASE_DIR / "state" / "tp_manager_state.json"
LOG_FILE = BASE_DIR / "logs" / "tp_manager.log"
PID_FILE = BASE_DIR / "tp_manager.pid"
IG_API_SCRIPT = TRADING_DIR / "ig_api.sh"
SIGNAL_QUEUE_FILE = BASE_DIR / "state" / "signal_queue.json"
UPDATE_INBOX = BASE_DIR / "state" / "signal_update.json"

# Epic to pair mapping
EPIC_MAP = {
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
    'CS.D.USDCHF.CFD.IP': 'USDCHF',
    'CS.D.EURAUD.CFD.IP': 'EURAUD',
    'CS.D.CHFJPY.CFD.IP': 'CHFJPY',
    'CS.D.AUDJPY.CFD.IP': 'AUDJPY',
    'CS.D.CADJPY.CFD.IP': 'CADJPY',
    'CS.D.NZDJPY.CFD.IP': 'NZDJPY',
    'CS.D.EURCAD.CFD.IP': 'EURCAD',
    'CS.D.GBPAUD.CFD.IP': 'GBPAUD',
    'CS.D.GBPCAD.CFD.IP': 'GBPCAD',
}

# Setup logging
os.makedirs(BASE_DIR / "logs", exist_ok=True)
os.makedirs(BASE_DIR / "state", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [TP-MANAGER-FIXED] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Trading position data class"""
    deal_id: str
    pair: str
    direction: str  # 'BUY' or 'SELL'
    entry: float
    size: float
    epic: str
    initial_sl: Optional[float] = None
    current_sl: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    tp3: Optional[float] = None
    status: str = "open"
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    sl_hit: bool = False
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None
    close_reason: Optional[str] = None
    close_price: Optional[float] = None
    signal_id: Optional[str] = None  # Link to original signal

    def __post_init__(self):
        if self.opened_at is None:
            self.opened_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


class FixedTPManager:
    """Fixed TP Manager with proper position tracking"""

    def __init__(self):
        self.state_file = STATE_FILE
        self.positions: Dict[str, Position] = {}
        self.signal_queue_file = SIGNAL_QUEUE_FILE
        self.ig_api = IG_API_SCRIPT

        # Statistics
        self.stats = {
            'started': datetime.now().isoformat(),
            'positions_closed': 0,
            'tp1_hits': 0,
            'tp2_hits': 0,
            'tp3_hits': 0,
            'sl_hits': 0
        }

        self.load_state()

    def load_state(self):
        """Load state from JSON file"""
        if not self.state_file.exists():
            logger.info("No existing state, starting fresh")
            return

        try:
            with open(self.state_file) as f:
                data = json.load(f)

            # Load positions
            for deal_id, pos_data in data.get('positions', {}).items():
                self.positions[deal_id] = Position.from_dict(pos_data)

            # Load stats
            for key in ['positions_closed', 'tp1_hits', 'tp2_hits', 'tp3_hits', 'sl_hits']:
                if key in data:
                    self.stats[key] = data[key]

            logger.info(f"Loaded {len(self.positions)} positions from state")

        except Exception as e:
            logger.error(f"Error loading state: {e}")
            self.positions = {}

    def save_state(self):
        """Save state to JSON file"""
        try:
            data = {
                **self.stats,
                'last_update': datetime.now().isoformat(),
                'positions': {
                    deal_id: pos.to_dict()
                    for deal_id, pos in self.positions.items()
                }
            }

            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def get_signal_from_queue(self, signal_id: str) -> Optional[Dict]:
        """Get signal data from queue by ID"""
        if not self.signal_queue_file.exists():
            return None

        try:
            with open(self.signal_queue_file) as f:
                queue = json.load(f)

            for signal in queue:
                if str(signal.get('id')) == str(signal_id):
                    return signal

        except Exception as e:
            logger.error(f"Error reading signal queue: {e}")

        return None

    def extract_signal_data(self, signal: Dict) -> Optional[Dict]:
        """Extract trading data from signal"""
        try:
            extracted = signal.get('extracted_data', {})

            # Handle different signal formats
            pair = extracted.get('pair')
            direction = extracted.get('direction')
            entry = extracted.get('entry')
            sl = extracted.get('sl')
            tps = extracted.get('tp_levels', [])
            is_limit = extracted.get('is_limit', False)

            # If extracted_data is empty, try parsing from text
            if not pair:
                text = signal.get('text', '')
                parsed = self._parse_signal_text(text)
                if parsed:
                    pair = parsed.get('pair')
                    direction = parsed.get('direction')
                    entry = parsed.get('entry')
                    sl = parsed.get('sl')
                    tps = parsed.get('tp_levels', [])

            if not all([pair, direction]):
                return None

            return {
                'pair': pair,
                'direction': direction,
                'entry': entry,
                'sl': sl,
                'tps': tps,
                'is_limit': is_limit
            }

        except Exception as e:
            logger.error(f"Error extracting signal data: {e}")
            return None

    def _parse_signal_text(self, text: str) -> Optional[Dict]:
        """Parse signal from text"""
        text_upper = text.upper()

        # Extract pair
        pair = None
        if 'XAUUSD' in text_upper or 'GOLD' in text_upper:
            pair = 'XAUUSD'
        else:
            match = re.search(r'\b([A-Z]{6})\b', text_upper)
            if match:
                pair = match.group(1)

        # Extract direction
        direction = None
        if 'SELL' in text_upper:
            direction = 'SELL'
        elif 'BUY' in text_upper:
            direction = 'BUY'

        # Extract entry
        entry = None
        patterns = [
            r'(?:ENTRY|@)\s*:?\s*([0-9]+\.?[0-9]*)',
            r'(?:BUY|SELL)\s+NOW\s+([0-9]+\.?[0-9]*)',
            r'(?:BUY|SELL)\s+[A-Z]+\s+([0-9]+\.?[0-9]*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text_upper)
            if match:
                try:
                    entry = float(match.group(1))
                    break
                except:
                    pass

        # Extract SL
        sl = None
        sl_match = re.search(r'SL\s*:?\s*([0-9]+\.?[0-9]*)', text_upper)
        if sl_match:
            try:
                sl = float(sl_match.group(1))
            except:
                pass

        # Extract TPs
        tps = []
        for i in range(1, 4):
            tp_match = re.search(rf'TP\s*#?\s*{i}\s*:?\s*([0-9]+\.?[0-9]*)', text_upper)
            if tp_match:
                try:
                    tps.append(float(tp_match.group(1)))
                except:
                    pass

        if pair and direction:
            return {
                'pair': pair,
                'direction': direction,
                'entry': entry,
                'sl': sl,
                'tp_levels': tps
            }

        return None

    def epic_to_pair(self, epic: str) -> str:
        """Convert IG epic to currency pair"""
        return EPIC_MAP.get(epic, epic)

    def process_updates(self):
        """Process signal updates from Signal Hub (SL/TP adjustments)"""
        if not UPDATE_INBOX.exists():
            return
        
        try:
            with open(UPDATE_INBOX) as f:
                update = json.load(f)
            
            if update.get('processed'):
                return
            
            data = update.get('extracted_data', {})
            pair = data.get('pair')
            new_sl = data.get('new_sl')
            new_tps = data.get('new_tp_levels', [])
            
            if not pair:
                return
            
            # Find matching OPEN position
            updated = False
            for pos in self.positions.values():
                if pos.status == 'open' and pos.pair == pair:
                    if new_sl:
                        pos.current_sl = float(new_sl)
                        pos.initial_sl = float(new_sl)
                        logger.info(f"🔧 Updated SL for {pair} ({pos.deal_id}): {new_sl}")
                    if new_tps:
                        if len(new_tps) > 0:
                            pos.tp1 = float(new_tps[0])
                        if len(new_tps) > 1:
                            pos.tp2 = float(new_tps[1])
                        if len(new_tps) > 2:
                            pos.tp3 = float(new_tps[2])
                        logger.info(f"🔧 Updated TP levels for {pair} ({pos.deal_id}): {new_tps}")
                    updated = True
                    break
            
            if updated:
                self.save_state()
                # Mark update as processed
                update['processed'] = True
                update['status'] = 'processed'
                with open(UPDATE_INBOX, 'w') as f:
                    json.dump(update, f, indent=2)
            else:
                logger.warning(f"⚠️ Update for {pair}: no matching open position found")
                
        except Exception as e:
            logger.error(f"Error processing updates: {e}")

    def _get_ig_positions(self) -> List[Dict]:
        """Fetch current positions from IG API"""
        try:
            result = subprocess.run(
                ['bash', str(self.ig_api), 'positions'],
                capture_output=True,
                text=True,
                timeout=10
            )
            data = json.loads(result.stdout)
            return data.get('positions', [])
        except Exception as e:
            logger.error(f"Error fetching IG positions: {e}")
            return []

    def _is_position_in_ig(self, deal_id: str) -> bool:
        """Quick check if a specific position still exists in IG"""
        ig_positions = self._get_ig_positions()
        active_deal_ids = {p.get('position', {}).get('dealId') for p in ig_positions}
        return deal_id in active_deal_ids

    def archive_closed_position(self, deal_id: str, reason: str):
        """Archive a position that is no longer in IG"""
        if deal_id in self.positions and self.positions[deal_id].status == 'open':
            logger.info(f"📦 Archiving {deal_id} - reason: {reason}")
            self.positions[deal_id].status = 'closed'
            self.positions[deal_id].close_reason = reason
            self.positions[deal_id].closed_at = datetime.now().isoformat()
            self.save_state()

    def sync_with_ig(self):
        """
        Sync positions with IG and register any missing ones.
        FIXED: Properly handle positions without signals.
        """
        logger.info("🔄 Syncing with IG positions...")

        try:
            ig_positions = self._get_ig_positions()
            logger.info(f"Found {len(ig_positions)} positions in IG")

            # Build set of OPEN tracked deal IDs (only skip if actually open)
            open_deal_ids = {k for k, v in self.positions.items() if v.status == 'open'}

            # Process each IG position
            for ig_pos in ig_positions:
                pos_data = ig_pos.get('position', {})
                market_data = ig_pos.get('market', {})

                deal_id = pos_data.get('dealId')
                epic = market_data.get('epic')
                direction = pos_data.get('direction')
                entry = pos_data.get('openLevel')
                size = pos_data.get('dealSize')

                if not deal_id:
                    continue

                # Skip already OPEN tracked positions
                if deal_id in open_deal_ids:
                    continue

                # Check if position was previously closed - don't reopen if just closed
                if deal_id in self.positions:
                    pos = self.positions[deal_id]
                    # Don't reopen if closed due to TP/SL hit (would create loop)
                    if pos.close_reason in ['tp3_hit', 'sl_hit']:
                        logger.info(f"   Skipping {deal_id} - was closed by {pos.close_reason}")
                        continue
                    # For other closures, reopen after delay
                    if pos.closed_at:
                        from datetime import datetime
                        try:
                            closed_time = datetime.fromisoformat(pos.closed_at)
                            seconds_ago = (datetime.now() - closed_time).total_seconds()
                            if seconds_ago < 30:  # Don't reopen within 30 seconds
                                logger.info(f"   Skipping {deal_id} - closed {seconds_ago:.0f}s ago")
                                continue
                        except:
                            pass
                    logger.info(f"🔄 Re-opening position in IG: {deal_id}")
                    self.positions[deal_id].status = 'open'
                    self.positions[deal_id].closed_at = None
                    self.positions[deal_id].close_reason = None
                    continue

                # NEW POSITION - register it
                pair = self.epic_to_pair(epic)

                logger.info(f"🆕 New position found in IG: {deal_id}")
                logger.info(f"   {direction} {pair} @ {entry}")

                # Try to find matching signal
                signal_data = self._find_matching_signal(pair, direction, entry)

                if signal_data:
                    logger.info(f"   ✓ Matched to signal")
                    sl = signal_data.get('sl')
                    tps = signal_data.get('tps', [])
                else:
                    logger.warning(f"   ⚠️ No matching signal found - importing from IG")
                    sl = pos_data.get('stopLevel')
                    tps = []

                # Create and register position
                position = Position(
                    deal_id=deal_id,
                    pair=pair,
                    direction=direction,
                    entry=float(entry) if entry else 0.0,
                    size=float(size) if size else 0.5,
                    epic=epic,
                    initial_sl=float(sl) if sl else None,
                    current_sl=float(sl) if sl else None,
                    tp1=float(tps[0]) if len(tps) > 0 else None,
                    tp2=float(tps[1]) if len(tps) > 1 else None,
                    tp3=float(tps[2]) if len(tps) > 2 else None,
                    signal_id=signal_data.get('signal_id') if signal_data else None
                )

                self.positions[deal_id] = position
                logger.info(f"   ✓ Position registered")

            # Check for closed positions
            active_deal_ids = {p.get('position', {}).get('dealId') for p in ig_positions}
            for deal_id in list(self.positions.keys()):
                if deal_id not in active_deal_ids and self.positions[deal_id].status == 'open':
                    self.archive_closed_position(deal_id, 'closed_externally')

            self.save_state()
            logger.info(f"✅ Sync complete. Tracking {len(self.positions)} positions.")

        except Exception as e:
            logger.error(f"Error syncing with IG: {e}")

    def _find_matching_signal(self, pair: str, direction: str, entry: Any) -> Optional[Dict]:
        """Find signal matching the position"""
        if not self.signal_queue_file.exists():
            return None

        try:
            with open(self.signal_queue_file) as f:
                queue = json.load(f)

            # Look for matching processed signals
            for signal in reversed(queue):
                if not signal.get('processed'):
                    continue

                extracted = signal.get('extracted_data', {})
                sig_pair = extracted.get('pair')
                sig_direction = extracted.get('direction')

                # Check match
                if sig_pair == pair and sig_direction == direction:
                    return {
                        'signal_id': signal.get('id'),
                        'sl': extracted.get('sl'),
                        'tps': extracted.get('tp_levels', [])
                    }

        except Exception as e:
            logger.error(f"Error finding matching signal: {e}")

        return None

    def check_tp_sl(self, position: Position) -> Optional[str]:
        """
        Check if TP or SL hit for a position.
        Returns action if triggered, None otherwise.
        """
        try:
            # Get current price using 'market' command
            result = subprocess.run(
                ['bash', str(self.ig_api), 'market', position.epic],
                capture_output=True,
                text=True,
                timeout=10
            )
            price_data = json.loads(result.stdout)

            # Prices are in snapshot object
            snapshot = price_data.get('snapshot', {})
            bid = float(snapshot.get('bid', 0))
            offer = float(snapshot.get('offer', 0))

            # Use appropriate price based on direction
            if position.direction == 'BUY':
                current_price = bid  # For SELL to close
                # Check TP hits (price went above TP)
                if position.tp1 and not position.tp1_hit and current_price >= position.tp1:
                    return 'tp1_hit'
                if position.tp2 and not position.tp2_hit and current_price >= position.tp2:
                    return 'tp2_hit'
                if position.tp3 and not position.tp3_hit and current_price >= position.tp3:
                    return 'tp3_hit'
                # Check SL hit
                if position.current_sl and current_price <= position.current_sl:
                    return 'sl_hit'
            else:  # SELL
                current_price = offer  # For BUY to close
                # Check TP hits (price went below TP)
                if position.tp1 and not position.tp1_hit and current_price <= position.tp1:
                    return 'tp1_hit'
                if position.tp2 and not position.tp2_hit and current_price <= position.tp2:
                    return 'tp2_hit'
                if position.tp3 and not position.tp3_hit and current_price <= position.tp3:
                    return 'tp3_hit'
                # Check SL hit
                if position.current_sl and current_price >= position.current_sl:
                    return 'sl_hit'

        except Exception as e:
            logger.error(f"Error checking TP/SL for {position.deal_id}: {e}")

        return None

    def close_position_in_ig(self, position: Position, reason: str) -> bool:
        """Close position in IG via API"""
        try:
            logger.info(f"🔒 Closing {position.pair} in IG ({reason})")
            result = subprocess.run(
                ['bash', str(self.ig_api), 'close', position.deal_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"   ✓ Position closed in IG")
                return True
            else:
                logger.error(f"   ✗ Failed to close: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"   ✗ Error closing position: {e}")
            return False

    def handle_tp_hit(self, position: Position, tp_level: int):
        """Handle TP hit for a position"""
        logger.info(f"🎯 TP{tp_level} hit for {position.pair} ({position.deal_id})")

        if tp_level == 1:
            # TP1: No action (per new logic)
            position.tp1_hit = True
            self.stats['tp1_hits'] += 1
            logger.info(f"   TP1 - no action (monitoring)")
        elif tp_level == 2:
            # TP2: Move SL to BE + Close 50% (per new logic)
            position.tp2_hit = True
            self.stats['tp2_hits'] += 1
            position.current_sl = position.entry  # Move SL to entry/BE
            logger.info(f"   TP2 - SL moved to entry {position.entry}")
            # TODO: Close 50% of position
        elif tp_level == 3:
            # TP3: Close entire position
            position.tp3_hit = True
            self.stats['tp3_hits'] += 1
            self.stats['positions_closed'] += 1

            # Close in IG first
            if self.close_position_in_ig(position, 'TP3 hit'):
                position.status = 'closed'
                position.close_reason = 'tp3_hit'
                position.closed_at = datetime.now().isoformat()
            else:
                # Check if IG closed it already despite API error
                if not self._is_position_in_ig(position.deal_id):
                    logger.info(f"   Position already closed in IG, archiving")
                    self.archive_closed_position(position.deal_id, 'tp3_hit')
                else:
                    logger.error(f"   Failed to close position in IG, will retry")

        self.save_state()

    def handle_sl_hit(self, position: Position):
        """Handle SL hit for a position"""
        logger.info(f"🛑 SL hit for {position.pair} ({position.deal_id})")

        position.sl_hit = True
        self.stats['sl_hits'] += 1
        self.stats['positions_closed'] += 1

        # Close in IG first
        if self.close_position_in_ig(position, 'SL hit'):
            position.status = 'closed'
            position.close_reason = 'sl_hit'
            position.closed_at = datetime.now().isoformat()
        else:
            # Check if IG closed it already despite API error
            if not self._is_position_in_ig(position.deal_id):
                logger.info(f"   Position already closed in IG, archiving")
                self.archive_closed_position(position.deal_id, 'sl_hit')
            else:
                logger.error(f"   Failed to close position in IG, will retry")

        self.save_state()

    def run_monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("=" * 60)
        logger.info("🚀 FIXED TP MANAGER STARTED")
        logger.info("=" * 60)
        
        loop_counter = 0
        
        while True:
            try:
                loop_counter += 1
                
                # Sync with IG every 5 iterations (full sync including new positions)
                if loop_counter % 5 == 0:
                    self.sync_with_ig()
                
                # EVERY iteration: process updates and fetch IG positions
                self.process_updates()
                ig_positions = self._get_ig_positions()
                active_deal_ids = {p.get('position', {}).get('dealId') for p in ig_positions}
                
                for deal_id in list(self.positions.keys()):
                    pos = self.positions[deal_id]
                    if pos.status == 'open' and deal_id not in active_deal_ids:
                        self.archive_closed_position(deal_id, 'closed_externally')
                
                # Check TP/SL only for positions that are CONFIRMED to still exist in IG
                open_positions = [
                    p for p in self.positions.values()
                    if p.status == 'open' and p.deal_id in active_deal_ids
                ]
                
                for position in open_positions:
                    action = self.check_tp_sl(position)
                    
                    if action == 'tp1_hit':
                        self.handle_tp_hit(position, 1)
                    elif action == 'tp2_hit':
                        self.handle_tp_hit(position, 2)
                    elif action == 'tp3_hit':
                        self.handle_tp_hit(position, 3)
                    elif action == 'sl_hit':
                        self.handle_sl_hit(position)
                
                # Save state periodically
                if loop_counter % 10 == 0:
                    self.save_state()
                
                time.sleep(1)  # Check every second
                
            except KeyboardInterrupt:
                logger.info("TP Manager stopped by user")
                break
            except Exception as e:
                logger.error(f"TP Manager error: {e}")
                time.sleep(5)

    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        open_positions = [p for p in self.positions.values() if p.status == 'open']

        return {
            'status': 'active',
            'started': self.stats.get('started'),
            'open_positions': len(open_positions),
            'total_positions': len(self.positions),
            'tp1_hits': self.stats.get('tp1_hits', 0),
            'tp2_hits': self.stats.get('tp2_hits', 0),
            'tp3_hits': self.stats.get('tp3_hits', 0),
            'sl_hits': self.stats.get('sl_hits', 0),
            'positions': [p.to_dict() for p in open_positions]
        }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    manager = FixedTPManager()
    manager.run_monitoring_loop()


def get_status():
    """Print status"""
    manager = FixedTPManager()
    status = manager.get_status()
    print(json.dumps(status, indent=2))


def sync_now():
    """Sync with IG immediately"""
    manager = FixedTPManager()
    manager.sync_with_ig()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fixed TP Manager')
    parser.add_argument('--run', action='store_true', help='Run monitoring loop')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--sync', action='store_true', help='Sync with IG')

    args = parser.parse_args()

    if args.status:
        get_status()
    elif args.sync:
        sync_now()
    else:
        main()
