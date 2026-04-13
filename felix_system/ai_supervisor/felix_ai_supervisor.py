#!/usr/bin/env python3
"""
FELIX AI SUPERVISOR - FIXED VERSION
Fixed issues:
1. Signal queue processing - now processes ONE signal at a time
2. Direction parsing - enforced strict parsing and verification
3. TP Manager registration - proper position tracking
4. Duplicate prevention - signal deduplication
5. Rate limiting - prevents multiple rapid executions
"""

import os
import sys
import json
import asyncio
import logging
import subprocess
import re
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

# Import trained parser
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from felix_trained_parser import ai_parse_signal_trained
except ImportError:
    ai_parse_signal_trained = None

# Import shared state
try:
    import shared_state
except ImportError:
    shared_state = None

# Configuration
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
LOG_DIR = BASE_DIR / "logs"
STATE_DIR = BASE_DIR / "state"
FIXES_DIR = BASE_DIR / "fixes"

# Paths to existing components
FELIX_LISTENER = Path.home() / ".openclaw" / "telegram" / "felix_auto_trader.py"
FELIX_TRADER = Path.home() / ".openclaw" / "workspace" / "felix_trader.sh"
IG_API = Path.home() / ".trading" / "ig_api.sh"
DATA_DIR = Path.home() / ".trading" / "data"

# Setup logging
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(FIXES_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AI-SUPERVISOR] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "supervisor.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# SIGNAL QUEUE MANAGER - FIXED VERSION
# ============================================================================

class SignalQueueManager:
    """Manages signal queue with proper locking and deduplication"""
    
    def __init__(self):
        self.queue_file = STATE_DIR / "signal_queue.json"
        self.lock = threading.Lock()
        self.processed_signals: set = set()  # Track recently processed signal IDs
        self.last_execution_time: float = 0  # Rate limiting
        self.min_execution_interval: float = 2.0  # Minimum 2 seconds between executions
        
    def load_queue(self) -> List[Dict]:
        """Load signal queue from file"""
        if not self.queue_file.exists():
            return []
        try:
            with open(self.queue_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            return []
    
    def save_queue(self, queue: List[Dict]):
        """Save signal queue to file (call only when lock already held)"""
        with open(self.queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
    
    def get_next_signal(self) -> Optional[Dict]:
        """Get next unprocessed signal with rate limiting"""
        with self.lock:
            # Rate limiting check
            current_time = time.time()
            time_since_last = current_time - self.last_execution_time
            if time_since_last < self.min_execution_interval:
                logger.info(f"Rate limiting: waiting {self.min_execution_interval - time_since_last:.1f}s")
                return None
            
            queue = self.load_queue()
            
            # Find first unprocessed signal
            for signal in queue:
                signal_id = signal.get('id')
                
                # Skip already processed signals
                if signal.get('processed'):
                    continue
                
                # Skip recently processed signals (deduplication)
                if signal_id and signal_id in self.processed_signals:
                    logger.info(f"Skipping duplicate signal {signal_id}")
                    signal['processed'] = True
                    signal['processed_at'] = datetime.now().isoformat()
                    signal['success'] = False
                    signal['details'] = 'duplicate_skipped'
                    self.save_queue(queue)
                    continue
                
                return signal
            
            return None
    
    def mark_processed(self, signal_id: Any, success: bool, details: str = ""):
        """Mark signal as processed"""
        with self.lock:
            queue = self.load_queue()
            for signal in queue:
                if signal.get('id') == signal_id:
                    signal['processed'] = True
                    signal['processed_at'] = datetime.now().isoformat()
                    signal['success'] = success
                    signal['details'] = details
                    break
            
            self.save_queue(queue)
            
            # Add to processed set for deduplication (keep last 100)
            if signal_id:
                self.processed_signals.add(signal_id)
                while len(self.processed_signals) > 100:
                    # Remove oldest (arbitrary since it's a set)
                    try:
                        self.processed_signals.pop()
                    except KeyError:
                        break
            
            # Update execution time for rate limiting
            self.last_execution_time = time.time()
    
    def cleanup_old_signals(self, max_age_hours: int = 24):
        """Remove old processed signals from queue"""
        with self.lock:
            queue = self.load_queue()
            now = datetime.now()
            
            new_queue = []
            for signal in queue:
                # Keep unprocessed signals
                if not signal.get('processed'):
                    new_queue.append(signal)
                    continue
                
                # Keep recent processed signals (for reference)
                try:
                    processed_at = datetime.fromisoformat(signal.get('processed_at', ''))
                    age_hours = (now - processed_at).total_seconds() / 3600
                    if age_hours < max_age_hours:
                        new_queue.append(signal)
                except:
                    new_queue.append(signal)
            
            removed = len(queue) - len(new_queue)
            if removed > 0:
                logger.info(f"Cleaned up {removed} old signals from queue")
                self.save_queue(new_queue)

# ============================================================================
# DIRECTION PARSER - STRICT VERSION
# ============================================================================

class DirectionParser:
    """Strict direction parsing with validation"""
    
    VALID_DIRECTIONS = {'BUY', 'SELL'}
    
    @staticmethod
    def parse_direction(text: str) -> Optional[str]:
        """
        Parse direction from signal text with strict validation.
        Returns 'BUY' or 'SELL' or None if not found/ambiguous.
        """
        if not text:
            return None
        
        text_upper = text.upper()
        
        # Count occurrences
        buy_count = text_upper.count('BUY')
        sell_count = text_upper.count('SELL')
        
        # Check for emoji indicators
        green_emoji = bool(re.search(r'[🟢🟩📈]', text))  # Green = BUY
        red_emoji = bool(re.search(r'[🔴🟥📉]', text))    # Red = SELL
        
        # Check for Limit/Stop indicators
        buy_limit = bool(re.search(r'(?i)buy\s+limit', text))
        sell_limit = bool(re.search(r'(?i)sell\s+limit', text))
        buy_stop = bool(re.search(r'(?i)buy\s+stop', text))
        sell_stop = bool(re.search(r'(?i)sell\s+stop', text))
        
        logger.info(f"Direction parsing: BUY count={buy_count}, SELL count={sell_count}")
        logger.info(f"Emoji: green={green_emoji}, red={red_emoji}")
        
        # Determine direction with priority
        if sell_count > buy_count:
            return 'SELL'
        elif buy_count > sell_count:
            return 'BUY'
        
        # Equal counts or both zero - use emoji and other indicators
        if sell_limit or red_emoji:
            return 'SELL'
        if buy_limit or green_emoji:
            return 'BUY'
        
        # Fallback: single occurrence
        if sell_count == 1 and buy_count == 0:
            return 'SELL'
        if buy_count == 1 and sell_count == 0:
            return 'BUY'
        
        # Ambiguous case
        logger.warning(f"Ambiguous direction: BUY={buy_count}, SELL={sell_count}")
        return None
    
    @staticmethod
    def verify_direction(parsed_direction: str, original_text: str) -> bool:
        """Verify parsed direction matches original text indicators"""
        if parsed_direction not in DirectionParser.VALID_DIRECTIONS:
            return False
        
        text_upper = original_text.upper()
        
        # For SELL signals, ensure no BUY indicators
        if parsed_direction == 'SELL':
            if 'BUY' in text_upper and text_upper.index('BUY') < text_upper.index('SELL'):
                # BUY appears before SELL - might be a false positive
                if 'SELL' in text_upper:
                    return True  # SELL is present, trust it
            if 'SELL' not in text_upper:
                return False
        
        # For BUY signals, ensure no SELL indicators
        if parsed_direction == 'BUY':
            if 'SELL' in text_upper and text_upper.index('SELL') < text_upper.index('BUY'):
                if 'BUY' in text_upper:
                    return True
            if 'BUY' not in text_upper:
                return False
        
        return True

# ============================================================================
# POSITION TRACKER
# ============================================================================

class PositionTracker:
    """Tracks positions to prevent duplicates and verify execution"""
    
    def __init__(self):
        self.positions_file = STATE_DIR / "tracked_positions.json"
        self.open_positions: Dict[str, Dict] = {}
        self.load()
    
    def load(self):
        """Load tracked positions"""
        if self.positions_file.exists():
            try:
                with open(self.positions_file, 'r') as f:
                    self.open_positions = json.load(f)
            except Exception as e:
                logger.error(f"Error loading positions: {e}")
                self.open_positions = {}
    
    def save(self):
        """Save tracked positions"""
        with open(self.positions_file, 'w') as f:
            json.dump(self.open_positions, f, indent=2)
    
    def has_position(self, pair: str, direction: str) -> bool:
        """Check if we already have an open position for pair/direction"""
        key = f"{pair}_{direction}"
        return key in self.open_positions
    
    def add_position(self, deal_id: str, pair: str, direction: str, 
                     entry: float, sl: float, tps: List[float], 
                     signal_id: Optional[str] = None):
        """Add a new position to tracking"""
        key = f"{pair}_{direction}"
        self.open_positions[key] = {
            'deal_id': deal_id,
            'pair': pair,
            'direction': direction,
            'entry': entry,
            'sl': sl,
            'tps': tps,
            'signal_id': signal_id,
            'opened_at': datetime.now().isoformat()
        }
        self.save()
        logger.info(f"Added position to tracker: {key} -> {deal_id}")
    
    def remove_position(self, pair: str, direction: str):
        """Remove position from tracking"""
        key = f"{pair}_{direction}"
        if key in self.open_positions:
            del self.open_positions[key]
            self.save()
    
    def sync_with_ig(self):
        """Sync tracked positions with actual IG positions"""
        try:
            result = subprocess.run(
                ['bash', str(IG_API), 'positions'],
                capture_output=True,
                text=True,
                timeout=10
            )
            data = json.loads(result.stdout)
            ig_positions = data.get('positions', [])
            
            # Build set of active deal IDs
            active_deal_ids = set()
            for pos in ig_positions:
                deal_id = pos.get('position', {}).get('dealId')
                if deal_id:
                    active_deal_ids.add(deal_id)
            
            # Remove tracked positions that are no longer in IG
            removed = []
            for key, pos in list(self.open_positions.items()):
                if pos.get('deal_id') not in active_deal_ids:
                    removed.append(key)
                    del self.open_positions[key]
            
            if removed:
                logger.info(f"Removed closed positions from tracker: {removed}")
                self.save()
                
        except Exception as e:
            logger.error(f"Error syncing with IG: {e}")

# ============================================================================
# MAIN SUPERVISOR - FIXED VERSION
# ============================================================================

class FixedFelixSupervisor:
    """Fixed version of Felix AI Supervisor"""
    
    def __init__(self):
        self.state_file = STATE_DIR / "supervisor_state.json"
        self.queue_manager = SignalQueueManager()
        self.direction_parser = DirectionParser()
        self.position_tracker = PositionTracker()
        
        self.state = {
            "started": datetime.now().isoformat(),
            "signals_processed": 0,
            "signals_failed": 0,
            "signals_skipped": 0,
            "patches_applied": [],
            "last_check": None
        }
        self.load_state()
    
    def load_state(self):
        """Load supervisor state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    loaded = json.load(f)
                    self.state.update(loaded)
            except Exception as e:
                logger.error(f"Error loading state: {e}")
    
    def save_state(self):
        """Save supervisor state"""
        self.state["last_check"] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def ai_parse_signal(self, raw_text: str) -> Dict[str, Any]:
        """AI-powered signal parser with strict direction handling"""
        logger.info("🧠 AI parsing signal...")
        
        # Use trained parser if available
        if ai_parse_signal_trained:
            result = ai_parse_signal_trained(raw_text)
        else:
            # Fallback to basic parsing
            result = self._basic_parse(raw_text)
        
        # STRICT: Override direction with our strict parser
        strict_direction = self.direction_parser.parse_direction(raw_text)
        if strict_direction:
            if result.get('direction') != strict_direction:
                logger.warning(f"Direction mismatch! Parser: {result.get('direction')}, Strict: {strict_direction}")
                logger.warning(f"Using strict direction: {strict_direction}")
                result['direction'] = strict_direction
        else:
            logger.error("Could not determine direction from signal!")
            result['valid'] = False
            result['error'] = 'direction_ambiguous'
        
        # Verify direction matches text
        if not self.direction_parser.verify_direction(result.get('direction', ''), raw_text):
            logger.error("Direction verification failed!")
            result['valid'] = False
            result['error'] = 'direction_verification_failed'
        
        logger.info(f"Parsed: pair={result.get('pair')}, direction={result.get('direction')}, entry={result.get('entry')}")
        
        return result
    
    def _basic_parse(self, text: str) -> Dict[str, Any]:
        """Basic signal parsing as fallback"""
        text_upper = text.upper()
        
        # Extract pair
        pair = None
        if 'XAUUSD' in text_upper or 'GOLD' in text_upper:
            pair = 'XAUUSD'
        else:
            match = re.search(r'\b([A-Z]{6})\b', text)
            if match:
                pair = match.group(1)
        
        # Extract direction
        direction = self.direction_parser.parse_direction(text)
        
        # Extract entry price
        entry = None
        patterns = [
            r'(?:ENTRY|@)\s*:?\s*([0-9]+\.?[0-9]*)',
            r'(?:BUY|SELL)\s+NOW\s+([0-9]+\.?[0-9]*)',
            r'(?:BUY|SELL)\s+[A-Z]+\s+([0-9]+\.?[0-9]*)',
            r'@\s*([0-9]+\.?[0-9]*)',
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
        
        return {
            'valid': bool(pair and direction and entry),
            'pair': pair,
            'direction': direction,
            'entry': entry,
            'stop_loss': sl,
            'take_profits': tps,
            'raw': text
        }
    
    def execute_trade_direct(self, parsed: Dict[str, Any]) -> tuple[bool, str]:
        """
        Execute trade directly via IG API with position tracking.
        FIXED: Proper direction handling and duplicate prevention.
        """
        pair = parsed.get('pair')
        direction = parsed.get('direction')
        entry = parsed.get('entry')
        size = parsed.get('size', '1.0')
        signal_id = parsed.get('signal_id')
        
        # Validate direction
        if direction not in ('BUY', 'SELL'):
            logger.error(f"Invalid direction: {direction}")
            return False, f"invalid_direction: {direction}"
        
        # Sync with IG first to ensure no stale data
        self.position_tracker.sync_with_ig()
        
        # Check for duplicate position
        if self.position_tracker.has_position(pair, direction):
            logger.warning(f"Already have open {direction} position for {pair}")
            return False, "duplicate_position"
        
        # Check IG positions directly
        try:
            result = subprocess.run(
                ['bash', str(IG_API), 'positions'],
                capture_output=True,
                text=True,
                timeout=10
            )
            data = json.loads(result.stdout)
            ig_positions = data.get('positions', [])
            
            # Count positions for this pair
            pair_positions = [p for p in ig_positions 
                           if (pair in p.get('market', {}).get('epic', '') or
                               (pair == 'XAUUSD' and 'GOLD' in p.get('market', {}).get('epic', '')))]
            
            if len(pair_positions) > 0:
                logger.warning(f"Found {len(pair_positions)} existing positions for {pair}")
                # Check if direction matches
                for pos in pair_positions:
                    if pos.get('position', {}).get('direction') == direction:
                        logger.error(f"Already have {direction} position for {pair} in IG!")
                        return False, "position_already_exists_in_ig"
            
        except Exception as e:
            logger.warning(f"Could not check IG positions: {e}")
        
        # Adjust size for GOLD
        if pair and ('XAU' in pair or pair == 'GOLD'):
            try:
                if float(size) < 1.0:
                    size = '1.0'
                    logger.info(f"🥇 Adjusted GOLD position size to minimum 1.0 lots")
            except:
                size = '1.0'
        
        # Determine currency
        if 'JPY' in (pair or ''):
            currency = 'JPY'
        elif pair in ('XAUUSD', 'GOLD', 'BTCUSD'):
            currency = 'USD'
        elif pair and len(pair) == 6:
            currency = pair[3:]
        else:
            currency = 'USD'
        
        # Map pair to IG epic
        epic_map = {
            'XAUUSD': 'CS.D.CFDGOLD.CFDGC.IP',
            'GOLD': 'CS.D.CFDGOLD.CFDGC.IP',
            'BTCUSD': 'CS.D.BITCOIN.CFD.IP',
            'EURUSD': 'CS.D.EURUSD.CFD.IP',
            'GBPUSD': 'CS.D.GBPUSD.CFD.IP',
            'USDJPY': 'CS.D.USDJPY.CFD.IP',
            'GBPJPY': 'CS.D.GBPJPY.CFD.IP',
            'AUDUSD': 'CS.D.AUDUSD.CFD.IP',
            'USDCAD': 'CS.D.USDCAD.CFD.IP',
            'EURGBP': 'CS.D.EURGBP.CFD.IP',
        }
        epic = epic_map.get(pair, f'CS.D.{pair}.CFD.IP')
        
        logger.info(f"🚀 Executing: {pair} {direction} @ {entry}, size={size}")
        logger.info(f"   Epic: {epic}, Currency: {currency}")
        
        try:
            # Build command
            is_limit = parsed.get('is_limit', False)
            order_type = 'LIMIT' if is_limit else 'MARKET'
            
            cmd = ['bash', str(IG_API), 'order', epic, direction, str(size)]
            
            if is_limit and entry:
                cmd.extend(['', '', order_type, str(entry)])
                logger.info(f"📌 LIMIT order at {entry}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # Only use stdout for JSON parsing (stderr contains log messages)
            output = result.stdout.strip()
            error_output = result.stderr.strip()
            
            # Debug logging
            logger.debug(f"IG stdout length: {len(output)}")
            logger.debug(f"IG stderr length: {len(error_output)}")
            if output:
                logger.debug(f"IG stdout preview: {output[:200]}")
            
            if error_output:
                logger.debug(f"IG API logs: {error_output[:200]}")
            
            # Check for success
            if '"dealStatus": "ACCEPTED"' in output or '"status": "OPEN"' in output:
                logger.info(f"✅ Trade executed successfully!")
                
                # Extract deal ID - parse only stdout (not stderr)
                deal_id = None
                try:
                    response = json.loads(output)
                    # First try direct dealId
                    deal_id = response.get('dealId')
                    # If not found, try confirms.dealId (IG API returns it this way)
                    if not deal_id and 'confirms' in response:
                        deal_id = response['confirms'].get('dealId')
                    if not deal_id:
                        # Try affectedDeals array
                        affected = response.get('confirms', {}).get('affectedDeals', [])
                        if affected:
                            deal_id = affected[0].get('dealId')
                except Exception as e:
                    logger.warning(f"Could not extract deal_id: {e}")
                    logger.debug(f"Output was: {output[:500]}")
                
                # Track position
                if deal_id:
                    sl = parsed.get('stop_loss')
                    tps = parsed.get('take_profits', [])
                    self.position_tracker.add_position(
                        deal_id, pair, direction, entry, sl, tps, signal_id
                    )
                
                return True, output
            else:
                logger.error(f"❌ Trade failed: {output[:500]}")
                if error_output:
                    logger.error(f"IG Error: {error_output[:500]}")
                return False, output
                
        except Exception as e:
            logger.error(f"❌ Execution error: {e}")
            return False, str(e)
    
    def process_single_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Process a single signal with full validation.
        FIXED: One signal at a time, no batch processing.
        Uses pre-parsed data from Signal Hub if available.
        """
        signal_id = signal.get('id')
        signal_text = signal.get('text', '')
        
        logger.info("=" * 60)
        logger.info(f"🚀 PROCESSING SIGNAL {signal_id}")
        logger.info("=" * 60)
        logger.info(f"Text: {signal_text[:100]}...")
        
        # Check if Signal Hub already parsed this signal
        extracted_data = signal.get('extracted_data', {})
        if extracted_data and extracted_data.get('valid') and extracted_data.get('pair'):
            logger.info(f"✅ Using pre-parsed data from Signal Hub")
            parsed = {
                'valid': True,
                'pair': extracted_data.get('pair'),
                'direction': extracted_data.get('direction'),
                'entry': extracted_data.get('entry'),
                'stop_loss': extracted_data.get('sl'),
                'take_profits': extracted_data.get('tp_levels', []),
                'is_limit': extracted_data.get('is_limit', False),
                'signal_id': signal_id,
                'raw': signal_text
            }
            # Validate direction
            if not parsed['direction']:
                strict_direction = self.direction_parser.parse_direction(signal_text)
                if strict_direction:
                    parsed['direction'] = strict_direction
                    logger.info(f"Direction from strict parser: {strict_direction}")
                else:
                    logger.error("No direction found!")
                    parsed['valid'] = False
        else:
            # Parse signal manually
            parsed = self.ai_parse_signal(signal_text)
        
        if not parsed.get('valid'):
            error = parsed.get('error', 'unknown')
            logger.error(f"❌ Signal parsing failed: {error}")
            self.queue_manager.mark_processed(signal_id, False, f"parse_error: {error}")
            self.state['signals_failed'] += 1
            return False
        
        # Verify parsed data
        pair = parsed.get('pair')
        direction = parsed.get('direction')
        entry = parsed.get('entry')
        sl = parsed.get('stop_loss')
        
        logger.info(f"Parsed: {pair} {direction} @ {entry}, SL={sl}")
        
        # Check for missing critical fields
        if not all([pair, direction, entry]):
            missing = []
            if not pair: missing.append('pair')
            if not direction: missing.append('direction')
            if not entry: missing.append('entry')
            logger.error(f"❌ Missing required fields: {missing}")
            self.queue_manager.mark_processed(signal_id, False, f"missing_fields: {missing}")
            self.state['signals_failed'] += 1
            return False
        
        # Execute trade
        success, output = self.execute_trade_direct(parsed)
        
        if success:
            logger.info(f"✅ Signal executed successfully!")
            self.queue_manager.mark_processed(signal_id, True, "executed")
            self.state['signals_processed'] += 1
        else:
            logger.error(f"❌ Signal execution failed: {output}")
            # Mark as processed even if failed (to prevent infinite retry)
            if "position_already_exists" in str(output):
                logger.warning(f"⚠️ Marking signal {signal_id} as processed (position exists)")
                self.queue_manager.mark_processed(signal_id, True, "position_already_exists_skipped")
            else:
                self.queue_manager.mark_processed(signal_id, False, f"execution_failed: {str(output)[:100]}")
            self.state['signals_failed'] += 1
        
        self.save_state()
        return success
    
    def run_signal_processor(self):
        """
        Main signal processing loop.
        FIXED: Process ONE signal at a time with proper delays.
        """
        logger.info("=" * 60)
        logger.info("🤖 FIXED SIGNAL PROCESSOR STARTED")
        logger.info("=" * 60)
        logger.info("Processing one signal at a time with rate limiting...")
        
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while True:
            try:
                # Get next signal
                signal = self.queue_manager.get_next_signal()
                
                if signal is None:
                    # No signals to process, wait and retry
                    time.sleep(2)
                    consecutive_errors = 0  # Reset error counter on successful iteration
                    continue
                
                # Process this signal
                result = self.process_single_signal(signal)
                consecutive_errors = 0  # Reset error counter on successful processing
                
                # Wait before processing next signal (rate limiting)
                logger.info("Waiting before next signal...")
                time.sleep(3)
                
                # Periodic cleanup
                if self.state['signals_processed'] % 10 == 0:
                    try:
                        self.queue_manager.cleanup_old_signals()
                        self.position_tracker.sync_with_ig()
                    except Exception as cleanup_error:
                        logger.warning(f"Cleanup error (non-critical): {cleanup_error}")
                
            except KeyboardInterrupt:
                logger.info("Processor stopped by user")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Processor error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical("Too many consecutive errors, stopping processor")
                    break
                time.sleep(5)
    
    def get_status(self) -> Dict[str, Any]:
        """Get supervisor status"""
        queue = self.queue_manager.load_queue()
        unprocessed = sum(1 for s in queue if not s.get('processed'))
        
        return {
            'status': 'active',
            'started': self.state.get('started'),
            'signals_processed': self.state.get('signals_processed', 0),
            'signals_failed': self.state.get('signals_failed', 0),
            'signals_skipped': self.state.get('signals_skipped', 0),
            'queue_size': len(queue),
            'unprocessed_signals': unprocessed,
            'tracked_positions': len(self.position_tracker.open_positions),
            'last_check': self.state.get('last_check')
        }

# ============================================================================
# MAIN ENTRY POINTS
# ============================================================================

def run_processor():
    """Run the fixed signal processor"""
    supervisor = FixedFelixSupervisor()
    supervisor.run_signal_processor()

def run_single_signal(signal_id: int):
    """Process a single signal by ID (for testing)"""
    supervisor = FixedFelixSupervisor()
    queue = supervisor.queue_manager.load_queue()
    
    for signal in queue:
        if signal.get('id') == signal_id:
            logger.info(f"Processing signal {signal_id}...")
            result = supervisor.process_single_signal(signal)
            print(f"\nResult: {'SUCCESS' if result else 'FAILED'}")
            return
    
    print(f"Signal {signal_id} not found in queue")

def get_status():
    """Print supervisor status"""
    supervisor = FixedFelixSupervisor()
    status = supervisor.get_status()
    print(json.dumps(status, indent=2))

def clean_queue():
    """Clean old signals from queue"""
    supervisor = FixedFelixSupervisor()
    supervisor.queue_manager.cleanup_old_signals(max_age_hours=1)
    print("Queue cleaned")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Fixed Felix AI Supervisor')
    parser.add_argument('--run', action='store_true', help='Run signal processor')
    parser.add_argument('--process', type=int, help='Process specific signal ID')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--clean', action='store_true', help='Clean old signals')
    
    args = parser.parse_args()
    
    if args.run:
        run_processor()
    elif args.process:
        run_single_signal(args.process)
    elif args.status:
        get_status()
    elif args.clean:
        clean_queue()
    else:
        run_processor()  # Default: run processor
