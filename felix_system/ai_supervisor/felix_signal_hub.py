#!/usr/bin/env python3
"""
FELIX SIGNAL HUB - ENHANCED VERSION
Central coordinator that distributes signals to all components
- Listens to Felix Telegram channel
- Handles initial signals AND updates (TP hits, SL hits, adjustments)
- Tracks message relationships via reply_to
- Updates TP Manager state for position lifecycle management

Message Types Handled:
1. Initial Signals (BUY/SELL) - New position
2. TP Hit Messages (TP1/TP2/TP3 Hit) - Update position state
3. SL Hit Messages - Position closed by SL
4. Adjusted Messages - TP/SL/Entry changes
5. Limit Order Activated - Limit becomes market order
6. Cancelled Messages - Position cancelled
7. Breakeven Instructions - Move SL to entry
"""

import os
import sys
import json
import asyncio
import logging
import subprocess
import re
from datetime import datetime
from pathlib import Path
from telethon import TelegramClient, events

# Import LLM parser fallback
try:
    from felix_smart_parser import smart_parse_signal
except ImportError:
    def smart_parse_signal(text):
        return {"valid": False}  # Fallback

# Import shared state
sys.path.insert(0, str(Path(__file__).parent))
try:
    import shared_state
except ImportError:
    shared_state = None

# Configuration
API_ID = YOUR_API_ID_HERE
API_HASH = 'YOUR_API_HASH_HERE'
PHONE = 'YOUR_PHONE_HERE'
TARGET_CHANNEL = 'YOUR_CHANNEL_NAME'
CHANNEL_ID = YOUR_CHANNEL_ID

# Paths
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
TRADING_DIR = Path.home() / ".trading"
SESSION_FILE = Path.home() / ".openclaw" / "telegram" / "felix_listener.session"
STATE_FILE = BASE_DIR / "state" / "signal_hub.json"
LOG_FILE = BASE_DIR / "logs" / "signal_hub.log"
PID_FILE = BASE_DIR / "signal_hub.pid"

# Signal files (for inter-process communication)
SIGNAL_INBOX = BASE_DIR / "state" / "new_signal.json"
UPDATE_INBOX = BASE_DIR / "state" / "signal_update.json"
TP_MANAGER_TRIGGER = BASE_DIR / "state" / "trigger_tp_manager"

# Setup logging
os.makedirs(BASE_DIR / "logs", exist_ok=True)
os.makedirs(BASE_DIR / "state", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [SIGNAL-HUB] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MessageType:
    """Message type constants"""
    INITIAL_SIGNAL = "initial_signal"      # BUY/SELL new position
    TP_HIT = "tp_hit"                      # TP1/TP2/TP3 hit
    SL_HIT = "sl_hit"                      # Stop loss hit
    ADJUSTED = "adjusted"                  # TP/SL/Entry modified
    ACTIVATED = "activated"                # Limit order activated
    CANCELLED = "cancelled"                # Signal/Order cancelled
    BREAKEVEN = "breakeven"                # Move SL to breakeven
    CLOSE = "close"                        # Close position (NEW!)
    UPDATE = "update"                      # Generic update
    UNKNOWN = "unknown"                    # Unrecognized


class SignalHub:
    """Central signal coordinator with update handling"""
    
    def __init__(self):
        self.client = None
        self.last_message_id = 0
        self.message_registry = {}  # message_id -> signal_info
        self.pair_to_message = {}   # pair_direction -> message_id
        self.load_state()
    
    def load_state(self):
        """Load hub state including message registry"""
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                state = json.load(f)
                self.last_message_id = state.get('last_message_id', 0)
                self.message_registry = state.get('message_registry', {})
                self.pair_to_message = state.get('pair_to_message', {})
        else:
            self.last_message_id = 0
            self.message_registry = {}
            self.pair_to_message = {}
    
    def save_state(self):
        """Save hub state"""
        with open(STATE_FILE, 'w') as f:
            json.dump({
                'last_message_id': self.last_message_id,
                'last_check': datetime.now().isoformat(),
                'message_registry': self.message_registry,
                'pair_to_message': self.pair_to_message
            }, f, indent=2, default=str)
    
    def classify_message(self, text, reply_to_msg_id=None):
        """
        Classify message type based on content
        Returns: (message_type, extracted_data)
        """
        if not text:
            return MessageType.UNKNOWN, {}
        
        text_upper = text.upper()
        
        # Check for TP Hit patterns
        tp_patterns = [
            r'TP\s*#?\s*1.*HIT',
            r'TP1.*HIT',
            r'FIRST.*TAKE.*PROFIT.*HIT',
            r'TP\s*#?\s*2.*HIT',
            r'TP2.*HIT',
            r'TP\s*#?\s*3.*HIT', 
            r'TP3.*HIT',
            r'TP\d*.*HIT.*PIPS',
        ]
        for pattern in tp_patterns:
            if re.search(pattern, text_upper):
                tp_level = 1
                if 'TP2' in text_upper or 'TP #2' in text_upper:
                    tp_level = 2
                elif 'TP3' in text_upper or 'TP #3' in text_upper:
                    tp_level = 3
                
                # Extract pair if present
                pair = self._extract_pair(text)
                pips = self._extract_pips(text)
                
                return MessageType.TP_HIT, {
                    'tp_level': tp_level,
                    'pair': pair,
                    'pips': pips,
                    'reply_to': reply_to_msg_id
                }
        
        # Check for SL Hit patterns
        sl_patterns = [
            r'SL\s*HIT',
            r'STOP.*LOSS.*HIT',
            r'STOP-LOSS.*HIT',
            r'CLOSED.*STOP-LOSS',
        ]
        for pattern in sl_patterns:
            if re.search(pattern, text_upper):
                pair = self._extract_pair(text)
                pips = self._extract_pips(text)
                return MessageType.SL_HIT, {
                    'pair': pair,
                    'pips': pips,
                    'reply_to': reply_to_msg_id
                }
        
        # Check for Breakeven instruction
        breakeven_patterns = [
            r'MOVE.*STOP.*BREAKEVEN',
            r'MOVE.*SL.*BREAKEVEN',
            r'STOPLOSS.*BREAKEVEN',
            r'SL.*BREAKEVEN',
        ]
        for pattern in breakeven_patterns:
            if re.search(pattern, text_upper):
                pair = self._extract_pair(text)
                return MessageType.BREAKEVEN, {
                    'pair': pair,
                    'reply_to': reply_to_msg_id
                }
        
        # Check for Adjusted/Updated patterns
        adjusted_patterns = [
            r'^\s*ADJUSTED',
            r'UPDATED.*ENTRY',
            r'ENTRY.*INCORRECT',
            r'ADJUSTED.*TP',
            r'ADJUSTED.*SL',
            r'NEW.*TP',
            r'NEW.*SL',
            r'TP.*ADJUSTED',
            r'SL.*ADJUSTED',
        ]
        for pattern in adjusted_patterns:
            if re.search(pattern, text_upper):
                pair = self._extract_pair(text)
                new_entry = self._extract_entry(text)
                # Pass entry to SL extraction for sanity check
                new_sl = self._extract_sl(text, new_entry)
                new_tp = self._extract_tp_levels(text, new_entry)
                
                return MessageType.ADJUSTED, {
                    'pair': pair,
                    'new_tp_levels': new_tp,
                    'new_sl': new_sl,
                    'new_entry': new_entry,
                    'reply_to': reply_to_msg_id,
                    'original_text': text
                }
        
        # Check for Activated (limit order)
        activated_patterns = [
            r'LIMIT.*ACTIVATED',
            r'ORDER.*ACTIVATED',
            r'BUY LIMIT.*ACTIVATED',
            r'SELL LIMIT.*ACTIVATED',
        ]
        for pattern in activated_patterns:
            if re.search(pattern, text_upper):
                pair = self._extract_pair(text)
                entry = self._extract_entry(text)
                return MessageType.ACTIVATED, {
                    'pair': pair,
                    'entry': entry,
                    'reply_to': reply_to_msg_id
                }
        
        # Check for Cancelled
        cancelled_patterns = [
            r'CANCEL.*LIMIT',
            r'CANCEL.*ORDER',
            r'CANCEL.*ALL',
            r'SIGNAL.*CANCELLED',
            r'ORDER.*CANCELLED',
        ]
        for pattern in cancelled_patterns:
            if re.search(pattern, text_upper):
                pair = self._extract_pair(text)
                return MessageType.CANCELLED, {
                    'pair': pair,
                    'reply_to': reply_to_msg_id
                }
        
        # Check for Close/Exit patterns (NEW!)
        close_patterns = [
            r'CLOSE.*POSITION',
            r'CLOSE.*NOW',
            r'CLOSE.*ALL',
            r'EXIT.*POSITION',
            r'EXIT.*NOW',
            r'EXIT.*ALL',
            r'CLOSE.*TRADE',
            r'BOOK.*PROFIT',
            r'TAKE.*PROFIT.*NOW',
        ]
        for pattern in close_patterns:
            if re.search(pattern, text_upper):
                pair = self._extract_pair(text)
                pips = self._extract_pips(text)
                return MessageType.CLOSE, {
                    'pair': pair,
                    'pips': pips,
                    'reply_to': reply_to_msg_id
                }
        
        # Check for Initial Signal (BUY/SELL with pair)
        if self._is_trading_signal(text):
            # Use smart parser for better extraction
            parsed = smart_parse_signal(text)
            
            # Map to expected format
            signal_data = {
                'pair': parsed.get('pair'),
                'direction': parsed.get('direction'),
                'entry': parsed.get('entry'),
                'tp_levels': parsed.get('tp_levels', []),
                'sl': parsed.get('sl'),
                'is_limit': 'LIMIT' in text_upper,
                'original_text': text,
                'parser_format': parsed.get('format', 'unknown'),
                'valid': parsed.get('valid', False)
            }
            
            # Log if using contextual/best_effort parsing
            if parsed.get('format') in ['contextual', 'best_effort']:
                logger.warning(f"Using {parsed.get('format')} parsing for signal - results may be approximate")
                if parsed.get('note'):
                    logger.warning(f"  Note: {parsed.get('note')}")
            
            return MessageType.INITIAL_SIGNAL, signal_data
        
        return MessageType.UNKNOWN, {'reply_to': reply_to_msg_id}
    
    def _is_trading_signal(self, text):
        """Check if message is an initial trading signal"""
        if not text:
            return False
        
        text_upper = text.upper()
        
        # Must have BUY or SELL
        has_direction = "BUY" in text_upper or "SELL" in text_upper
        
        # Quick pair check
        pairs = ["GBPJPY", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", 
                 "GOLD", "XAGUSD", "US30", "NAS100", "SPX500",
                 "NZDUSD", "AUDUSD", "USDCAD", "USDCHF", "EURGBP",
                 "EURJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY",
                 "EURAUD", "EURCAD", "EURNZD", "GBPAUD", "GBPCAD",
                 "GBPNZD", "AUDCAD", "AUDNZD", "NZDCAD", "EURCHF",
                 "GBPCHF", "AUDCHF", "CADCHF", "NZDCHF", "BTCUSD",
                 "TAOUSD", "GBPCAD", "CADJPY", "USDJPY"]
        has_pair = any(pair in text_upper for pair in pairs)
        
        return has_direction and has_pair
    
    def _extract_pair(self, text):
        """Extract currency pair from text"""
        if not text:
            return None
        
        text_upper = text.upper()
        
        # Priority order - longer pairs first to avoid partial matches
        pairs = ["GBPJPY", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", 
                 "NZDUSD", "AUDUSD", "USDCAD", "USDCHF", "EURGBP",
                 "EURJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY",
                 "EURAUD", "EURCAD", "EURNZD", "GBPAUD", "GBPCAD",
                 "GBPNZD", "AUDCAD", "AUDNZD", "NZDCAD", "EURCHF",
                 "GBPCHF", "AUDCHF", "CADCHF", "NZDCHF", "BTCUSD",
                 "TAOUSD", "XAGUSD", "US30", "NAS100", "SPX500"]
        
        for pair in pairs:
            if pair in text_upper:
                if pair == "GOLD":
                    return "XAUUSD"
                return pair
        
        # Try hashtag format like #XAUUSD
        hashtag_match = re.search(r'#([A-Z]{6,})', text_upper)
        if hashtag_match:
            return hashtag_match.group(1)
        
        return None
    
    def _extract_entry(self, text):
        """Extract entry price from text - enhanced for emoji format"""
        if not text:
            return None
        
        text_upper = text.upper()
        
        patterns = [
            r'⚪[\s\w]*ENTRY[\s\w]*POINT[\s\w]*[:\s]+(\d+\.?\d*)',
            r'⚪[\s\w]*ENTRY[\s\w]*[:\s]+(\d+\.?\d*)',
            r'ENTRY[\s\w]*POINT[\s\w]*[:\s]+(\d+\.?\d*)',
            r'ENTRY[:\s]+(\d+\.?\d*)',
            r'(?:BUY|SELL)\s+[A-Z]{3,}\s+(\d+\.?\d*)',
            r'(?:BUY|SELL)(?:\s+NOW)?\s+(\d+\.?\d*)',
            r'@\s*(\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_upper)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        
        # FALLBACK: Clean markdown and try again
        text_clean = text_upper.replace('**', ' ').replace('__', ' ')
        for pattern in patterns:
            match = re.search(pattern, text_clean)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        
        return None
    
    def _extract_tp_levels(self, text, entry_price=None):
        """Extract TP levels from text - with sanity check against entry"""
        if not text:
            return []
        
        tps = []
        text_upper = text.upper()
        
        # Pattern 1: 🟢 Take Profit X (TPX): 1.2345 (emoji format FIRST - most reliable)
        # Match lines with green circle emoji followed by TP info and price
        # Handle both: 🟢 Take Profit 1 (TP1): 1.15730 and 🟢 Take Profit 1 (TP1):** 1.15730
        tp_matches = re.findall(r'🟢[^\n]*TP\d*[^\n]*[:\*\s]+(\d+\.?\d*)', text)
        if tp_matches:
            tps = [float(tp) for tp in tp_matches if self._is_valid_price(tp)]
            if tps:
                logger.info(f"  Found {len(tps)} TP levels from emoji format")
        
        # Pattern 2: 🤑TP1: 1.2345 (money mouth emoji format)
        if not tps:
            tp_matches = re.findall(r'🤑TP\d*[\s:]*([\d.]{3,})', text_upper)
            tps = [float(tp) for tp in tp_matches if self._is_valid_price(tp)]
        
        # Pattern 3: TP1: 1.2345, TP2: 1.2350 (standard format)
        # CRITICAL: Require at least 1 digit + decimal + 1 digit to avoid matching "1" from "TP1"
        if not tps:
            tp_matches = re.findall(r'TP\s*#?\s*\d*[\s:]+([\d]+\.[\d]{2,})', text_upper)
            tps = [float(tp) for tp in tp_matches if self._is_valid_price(tp)]
        
        # Sanity check: TP should be reasonable distance from entry
        if tps and entry_price:
            # For forex, TP should be 0.1% to 5% away from entry (10-500 pips)
            min_tp = entry_price * 0.995  # 0.5% below entry
            max_tp = entry_price * 1.05   # 5% above entry
            
            # For JPY pairs, adjust
            if entry_price > 50:  # JPY pair
                min_tp = entry_price * 0.995
                max_tp = entry_price * 1.05
            
            valid_tps = []
            for tp in tps:
                if min_tp <= tp <= max_tp:
                    valid_tps.append(tp)
                else:
                    logger.warning(f"TP {tp} rejected: too far from entry {entry_price} (valid range: {min_tp:.5f}-{max_tp:.5f})")
            
            if len(valid_tps) < len(tps):
                logger.warning(f"Rejected {len(tps) - len(valid_tps)} invalid TP levels")
            
            tps = valid_tps
        
        # Check for relative TP (+15 Pips) - only if no absolute TPs found
        if not tps and entry_price:
            relative_match = re.search(r'SET\s+TP\d*\s*\+(\d+)\s*PIPS', text_upper)
            if relative_match:
                tp_pips = int(relative_match.group(1))
                pip_size = 0.01 if entry_price > 50 else 0.0001
                direction = 1 if 'BUY' in text_upper else -1
                tps = [entry_price + (tp_pips * pip_size * direction)]
                logger.info(f"  Using relative TP: +{tp_pips} pips = {tps[0]}")
        
        return tps
    
    def _extract_sl(self, text, entry_price=None):
        """Extract stop loss from text - enhanced for emoji format"""
        if not text:
            return None
        
        text_upper = text.upper()
        
        # Pattern 1: 🔴 emoji format (most reliable for Felix signals)
        # Handle: 🔴 Stop Loss (SL): 1.15230 or 🔴 Stop Loss (SL):** 1.15230
        match = re.search(r'🔴[^\n]*SL[^\n]*[:\*\s]+(\d+\.?\d*)', text)
        if match:
            price = match.group(1)
            if self._is_valid_price(price):
                if entry_price:
                    sl_val = float(price)
                    sl_range = entry_price * 0.05  # Allow 5% range
                    if abs(sl_val - entry_price) <= sl_range:
                        return sl_val
                else:
                    return float(price)
        
        # Pattern 2: **STOP LOSS (SL)**: 1.31420
        match = re.search(r'\*\*STOP LOSS[^*]*\*\*[:\s]+([\d.]+)', text_upper)
        if match:
            price = match.group(1)
            if self._is_valid_price(price):
                return float(price)
        
        # Pattern 3: SL: 1.31420
        match = re.search(r'SL[:\s]+([\d.]+)', text_upper)
        if match:
            price = match.group(1)
            if self._is_valid_price(price):
                return float(price)
        
        return None
    def _extract_pips(self, text):
        """Extract pip count from text"""
        if not text:
            return None
        
        patterns = [
            r'([+-]?\d+)\s*PIPS?',
            r'([+-]?\d+)\s*PIP',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                try:
                    return int(match.group(1))
                except:
                    pass
        return None
    
    def _is_valid_price(self, price_str):
        """Check if string is a valid price"""
        try:
            price = float(price_str)
            return price > 0
        except:
            return False
    
    def register_signal(self, message_id, signal_data):
        """Register a new signal in the registry, or detect as update if duplicate entry"""
        pair = signal_data.get('pair')
        direction = signal_data.get('direction')
        entry = signal_data.get('entry')
        new_sl = signal_data.get('sl')
        key = f"{pair}_{direction}"
        
        # Check for duplicate entry (same pair/direction with similar entry price)
        existing_msg_id = self.pair_to_message.get(key)
        if existing_msg_id and str(existing_msg_id) in self.message_registry:
            existing = self.message_registry[str(existing_msg_id)]
            existing_entry = existing.get('entry')
            
            # Check time difference - if less than 5 minutes, it's likely a duplicate
            existing_time = datetime.fromisoformat(existing.get('created_at', '2000-01-01T00:00:00'))
            time_diff = (datetime.now() - existing_time).total_seconds()
            
            # If entry prices match (or both are None - market orders), check for updates
            if existing_entry == entry or (existing_entry and entry and abs(existing_entry - entry) < 0.01):
                logger.info(f"🔄 Duplicate entry detected: {key} @ {entry}")
                logger.info(f"   Existing signal: Msg {existing_msg_id}")
                
                # Check if new signal has additional/more complete data
                existing_sl = existing.get('sl')
                new_tp_levels = signal_data.get('tp_levels', [])
                existing_tp_count = len(existing.get('tp_levels', []))
                new_tp_count = len(new_tp_levels)
                
                # If new signal has SL but existing doesn't -> UPDATE
                if new_sl and not existing_sl:
                    logger.info(f"   📝 Adding SL {new_sl} to existing signal")
                    existing['sl'] = new_sl
                    if new_tp_count > existing_tp_count:
                        existing['tp_levels'] = new_tp_levels
                        logger.info(f"   📝 Adding {new_tp_count - existing_tp_count} additional TP levels")
                    existing['updates'].append({
                        'type': 'sl_added',
                        'timestamp': datetime.now().isoformat(),
                        'new_sl': new_sl,
                        'source_msg': message_id
                    })
                    self.save_state()
                    return 'update', existing_msg_id
                
                # If new signal has MORE TP levels -> UPDATE (full signal after partial)
                if new_tp_count > existing_tp_count:
                    logger.info(f"   📝 Adding {new_tp_count - existing_tp_count} additional TP levels")
                    existing['tp_levels'] = new_tp_levels
                    # Also update SL if it's different/better
                    if new_sl and existing_sl and new_sl != existing_sl:
                        logger.info(f"   📝 Updating SL from {existing_sl} to {new_sl}")
                        existing['sl'] = new_sl
                    existing['updates'].append({
                        'type': 'tps_added',
                        'timestamp': datetime.now().isoformat(),
                        'new_tp_count': new_tp_count,
                        'source_msg': message_id
                    })
                    self.save_state()
                    return 'update', existing_msg_id
                
                # If both have SL but different values -> UPDATE
                if new_sl and existing_sl and new_sl != existing_sl:
                    logger.info(f"   📝 Updating SL from {existing_sl} to {new_sl}")
                    existing['sl'] = new_sl
                    existing['updates'].append({
                        'type': 'sl_updated',
                        'timestamp': datetime.now().isoformat(),
                        'old_sl': existing_sl,
                        'new_sl': new_sl,
                        'source_msg': message_id
                    })
                    self.save_state()
                    return 'update', existing_msg_id
                
                # If less than 5 minutes and no new data, it's a duplicate
                if time_diff < 300:  # 5 minutes
                    logger.warning(f"⚠️ DUPLICATE SIGNAL REJECTED: {key} @ {entry}")
                    logger.warning(f"   Previous signal was only {time_diff:.0f}s ago (Msg {existing_msg_id})")
                    return 'duplicate', existing_msg_id
        
        # Register as new signal
        self.message_registry[str(message_id)] = {
            'message_id': message_id,
            'pair': pair,
            'direction': direction,
            'entry': entry,
            'tp_levels': signal_data.get('tp_levels', []),
            'sl': new_sl,
            'is_limit': signal_data.get('is_limit', False),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'updates': []
        }
        
        self.pair_to_message[key] = message_id
        self.save_state()
        
        logger.info(f"📋 Signal registered: {key} -> Msg {message_id}")
        return 'new', message_id
    
    def find_original_signal(self, msg_type, data):
        """
        Find the original signal that an update refers to
        Uses reply_to or pair matching
        """
        # First try reply_to
        reply_to = data.get('reply_to')
        if reply_to and str(reply_to) in self.message_registry:
            return self.message_registry[str(reply_to)]
        
        # Try pair matching
        pair = data.get('pair')
        if pair:
            # Try active signals for this pair
            for msg_id, signal in self.message_registry.items():
                if signal.get('pair') == pair and signal.get('status') == 'active':
                    return signal
        
        return None
    
    def save_signal_for_processing(self, message_text, message_id, msg_type, data):
        """Save signal to inbox file for AI processor"""
        signal_data = {
            'id': message_id,
            'type': msg_type,
            'text': message_text,
            'timestamp': datetime.now().isoformat(),
            'status': 'new',
            'processed': False,
            'extracted_data': data
        }
        
        # Save to inbox
        with open(SIGNAL_INBOX, 'w') as f:
            json.dump(signal_data, f, indent=2)
        
        # Also add to signal queue for AI processor
        self._add_to_signal_queue(signal_data)
        
        # Register in shared state
        if shared_state:
            shared_state.register_signal({
                'id': message_id,
                'pair': data.get('pair'),
                'direction': data.get('direction'),
                'entry': data.get('entry'),
                'sl': data.get('sl'),
                'tp_levels': data.get('tp_levels', []),
                'is_limit': data.get('is_limit', False)
            }, source='signal_hub')
        
        logger.info(f"📥 Signal saved to inbox: ID {message_id} ({msg_type})")
        return signal_data
    
    def _add_to_signal_queue(self, signal_data):
        """Add signal to queue for AI processor"""
        queue_file = BASE_DIR / 'state' / 'signal_queue.json'
        
        # Load existing queue
        queue = []
        if queue_file.exists():
            try:
                with open(queue_file) as f:
                    queue = json.load(f)
            except:
                queue = []
        
        # Check if signal already in queue
        for existing in queue:
            if existing.get('id') == signal_data['id']:
                return  # Already exists
        
        # Add to queue
        queue.append(signal_data)
        
        # Save queue
        with open(queue_file, 'w') as f:
            json.dump(queue, f)
        
        logger.info(f"📥 Signal added to queue: ID {signal_data['id']}")
    
    def save_update_for_processing(self, message_text, message_id, msg_type, data):
        """Save update to update inbox for TP Manager"""
        update_data = {
            'id': message_id,
            'type': msg_type,
            'text': message_text,
            'timestamp': datetime.now().isoformat(),
            'status': 'new',
            'processed': False,
            'extracted_data': data,
            'original_signal': self.find_original_signal(msg_type, data)
        }
        
        # Save to update inbox
        with open(UPDATE_INBOX, 'w') as f:
            json.dump(update_data, f, indent=2)
        
        logger.info(f"🔄 Update saved: ID {message_id} ({msg_type})")
        return update_data
    
    def trigger_ai_processor(self):
        """Trigger AI processor to handle the signal"""
        try:
            logger.info("🔔 Triggering AI Processor...")
            subprocess.Popen([
                'python3',
                str(BASE_DIR / 'felix_ai_processor.py'),
                '--process-queue'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            logger.error(f"Failed to trigger AI processor: {e}")
            return False
    
    def trigger_tp_manager_update(self):
        """Notify TP manager to refresh positions"""
        try:
            Path(TP_MANAGER_TRIGGER).touch()
            logger.info("📊 Notified TP Manager to update positions")
            return True
        except Exception as e:
            logger.error(f"Failed to notify TP manager: {e}")
            return False
    
    async def process_message(self, message):
        """Process any message from the channel"""
        text = message.text or ""
        message_id = message.id
        reply_to = message.reply_to_msg_id
        
        # Skip if already processed
        if message_id <= self.last_message_id:
            return
        
        self.last_message_id = message_id
        
        # Classify the message
        msg_type, data = self.classify_message(text, reply_to)
        
        logger.info(f"📩 Message {message_id}: {msg_type}")
        if reply_to:
            logger.info(f"   ↳ Reply to: {reply_to}")
        
        # Handle based on type
        if msg_type == MessageType.INITIAL_SIGNAL:
            await self._handle_initial_signal(message_id, text, data)
        
        elif msg_type == MessageType.TP_HIT:
            await self._handle_tp_hit(message_id, text, data)
        
        elif msg_type == MessageType.SL_HIT:
            await self._handle_sl_hit(message_id, text, data)
        
        elif msg_type == MessageType.ADJUSTED:
            await self._handle_adjusted(message_id, text, data)
        
        elif msg_type == MessageType.BREAKEVEN:
            await self._handle_breakeven(message_id, text, data)
        
        elif msg_type == MessageType.ACTIVATED:
            await self._handle_activated(message_id, text, data)
        
        elif msg_type == MessageType.CANCELLED:
            await self._handle_cancelled(message_id, text, data)
        
        elif msg_type == MessageType.CLOSE:
            await self._handle_close(message_id, text, data)
        
        else:
            logger.debug(f"   ⏭️ Unknown message type, skipping")
        
        self.save_state()
    
    async def _handle_initial_signal(self, message_id, text, data):
        """Handle new trading signal or detect as update if duplicate entry"""
        logger.info("=" * 60)
        logger.info(f"🎯 NEW SIGNAL: {data.get('pair')} {data.get('direction')}")
        logger.info(f"   Entry: {data.get('entry')}, TP: {data.get('tp_levels')}, SL: {data.get('sl')}")
        logger.info("=" * 60)
        
        # Register the signal (or detect as update/duplicate)
        result_type, result_id = self.register_signal(message_id, data)
        
        if result_type == 'duplicate':
            # This is a duplicate - ignore it completely
            logger.warning(f"🚫 DUPLICATE SIGNAL IGNORED: Same as Msg {result_id}")
            return  # Don't process further
        
        elif result_type == 'update':
            # This is an update to existing signal - save as update, not new signal
            logger.info(f"🔄 Signal is an UPDATE to Msg {result_id}")
            self.save_update_for_processing(text, message_id, MessageType.ADJUSTED, {
                'pair': data.get('pair'),
                'new_sl': data.get('sl'),
                'new_tp_levels': data.get('tp_levels'),
                'new_entry': data.get('entry'),
                'reply_to': result_id,
                'original_text': text
            })
            # Trigger TP Manager to update position tracking
            self.trigger_tp_manager_update()
        else:
            # New signal - normal flow
            self.save_signal_for_processing(text, message_id, MessageType.INITIAL_SIGNAL, data)
            self.trigger_ai_processor()
            self.trigger_tp_manager_update()
    
    async def _handle_tp_hit(self, message_id, text, data):
        """Handle TP hit message"""
        tp_level = data.get('tp_level', 1)
        pair = data.get('pair')
        pips = data.get('pips')
        
        logger.info(f"🎯 TP{tp_level} HIT: {pair or 'Unknown'} (+{pips or '?'} pips)")
        
        # Find original signal
        original = self.find_original_signal(MessageType.TP_HIT, data)
        if original:
            logger.info(f"   ↳ Linked to signal: {original.get('pair')} {original.get('direction')}")
            
            # Update signal status
            msg_key = str(original.get('message_id'))
            if msg_key in self.message_registry:
                self.message_registry[msg_key]['updates'].append({
                    'type': f'tp{tp_level}_hit',
                    'timestamp': datetime.now().isoformat(),
                    'pips': pips
                })
                
                # Mark TP as hit in status
                if tp_level == 3:
                    self.message_registry[msg_key]['status'] = 'completed'
        
        # Save update for TP Manager
        self.save_update_for_processing(text, message_id, MessageType.TP_HIT, data)
        self.trigger_tp_manager_update()
    
    async def _handle_sl_hit(self, message_id, text, data):
        """Handle SL hit message"""
        pair = data.get('pair')
        pips = data.get('pips')
        
        logger.info(f"🛑 SL HIT: {pair or 'Unknown'} ({pips or '?'} pips)")
        
        # Find and update original signal
        original = self.find_original_signal(MessageType.SL_HIT, data)
        if original:
            msg_key = str(original.get('message_id'))
            if msg_key in self.message_registry:
                self.message_registry[msg_key]['status'] = 'sl_hit'
                self.message_registry[msg_key]['updates'].append({
                    'type': 'sl_hit',
                    'timestamp': datetime.now().isoformat(),
                    'pips': pips
                })
        
        self.save_update_for_processing(text, message_id, MessageType.SL_HIT, data)
        self.trigger_tp_manager_update()
    
    async def _handle_adjusted(self, message_id, text, data):
        """Handle adjusted/update message"""
        pair = data.get('pair')
        new_tp = data.get('new_tp_levels')
        new_sl = data.get('new_sl')
        new_entry = data.get('new_entry')
        
        logger.info(f"🔧 ADJUSTED: {pair or 'Unknown'}")
        if new_tp:
            logger.info(f"   New TP: {new_tp}")
        if new_sl:
            logger.info(f"   New SL: {new_sl}")
        if new_entry:
            logger.info(f"   New Entry: {new_entry}")
        
        # Find original signal
        original = self.find_original_signal(MessageType.ADJUSTED, data)
        if original:
            msg_key = str(original.get('message_id'))
            if msg_key in self.message_registry:
                # Update the stored levels
                if new_tp:
                    self.message_registry[msg_key]['tp_levels'] = new_tp
                if new_sl:
                    self.message_registry[msg_key]['sl'] = new_sl
                if new_entry:
                    self.message_registry[msg_key]['entry'] = new_entry
                
                self.message_registry[msg_key]['updates'].append({
                    'type': 'adjusted',
                    'timestamp': datetime.now().isoformat(),
                    'changes': {
                        'tp': new_tp,
                        'sl': new_sl,
                        'entry': new_entry
                    }
                })
        
        self.save_update_for_processing(text, message_id, MessageType.ADJUSTED, data)
        self.trigger_tp_manager_update()
    
    async def _handle_breakeven(self, message_id, text, data):
        """Handle breakeven instruction"""
        pair = data.get('pair')
        logger.info(f"💚 BREAKEVEN: Move SL to entry for {pair or 'Unknown'}")
        
        self.save_update_for_processing(text, message_id, MessageType.BREAKEVEN, data)
        self.trigger_tp_manager_update()
    
    async def _handle_activated(self, message_id, text, data):
        """Handle limit order activation"""
        pair = data.get('pair')
        entry = data.get('entry')
        
        logger.info(f"⚡ ACTIVATED: Limit order {pair or 'Unknown'} @ {entry}")
        
        # Find original limit signal and update it
        original = self.find_original_signal(MessageType.ACTIVATED, data)
        if original:
            msg_key = str(original.get('message_id'))
            if msg_key in self.message_registry:
                self.message_registry[msg_key]['is_limit'] = False  # Now active
                self.message_registry[msg_key]['updates'].append({
                    'type': 'activated',
                    'timestamp': datetime.now().isoformat()
                })
        
        self.save_update_for_processing(text, message_id, MessageType.ACTIVATED, data)
        self.trigger_tp_manager_update()
    
    async def _handle_cancelled(self, message_id, text, data):
        """Handle cancelled message"""
        pair = data.get('pair')
        logger.info(f"❌ CANCELLED: {pair or 'All limit orders'}")
        
        # Find and mark as cancelled
        original = self.find_original_signal(MessageType.CANCELLED, data)
        if original:
            msg_key = str(original.get('message_id'))
            if msg_key in self.message_registry:
                self.message_registry[msg_key]['status'] = 'cancelled'
        
        self.save_update_for_processing(text, message_id, MessageType.CANCELLED, data)
        self.trigger_tp_manager_update()
    
    async def _handle_close(self, message_id, text, data):
        """Handle close/exit position message (NEW!)"""
        pair = data.get('pair')
        pips = data.get('pips')
        
        logger.info("=" * 60)
        logger.info(f"🔴 CLOSE POSITION: {pair or 'Unknown'} ({pips or '?'} pips)")
        logger.info("=" * 60)
        
        # Find original signal
        original = self.find_original_signal(MessageType.CLOSE, data)
        if original:
            msg_key = str(original.get('message_id'))
            if msg_key in self.message_registry:
                self.message_registry[msg_key]['status'] = 'closed'
                self.message_registry[msg_key]['updates'].append({
                    'type': 'close_signal',
                    'timestamp': datetime.now().isoformat(),
                    'pips': pips,
                    'source_msg': message_id
                })
                logger.info(f"   ↳ Linked to signal: {original.get('pair')} {original.get('direction')}")
        
        # Save update for TP Manager to close the position
        self.save_update_for_processing(text, message_id, MessageType.CLOSE, data)
        self.trigger_tp_manager_update()
        
        # Trigger immediate close via IG API
        if pair:
            logger.info(f"   ⚡ Triggering immediate close for {pair}")
            # This will be handled by TP Manager or AI processor
    
    async def check_new_messages(self):
        """Check for new messages in channel with connection recovery"""
        # Reconnect if needed
        if not self.client.is_connected():
            logger.warning("🔌 Reconnecting...")
            try:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    logger.error("❌ Not authorized")
                    return
            except Exception as e:
                logger.error(f"Reconnect failed: {e}")
                if "database is locked" in str(e).lower():
                    logger.warning("Database locked during reconnect - recreating client")
                    try:
                        await self.client.disconnect()
                    except:
                        pass
                    # Create fresh client instance
                    self.client = TelegramClient(str(SESSION_FILE), API_ID, API_HASH)
                    try:
                        await self.client.connect()
                    except Exception as conn_err:
                        logger.error(f"Fresh reconnection failed: {conn_err}")
                        return
                else:
                    return
        
        try:
            entity = await self.client.get_entity(CHANNEL_ID)
            
            # Get recent messages
            new_messages = []
            async for message in self.client.iter_messages(entity, limit=10):
                if message.id <= self.last_message_id:
                    continue
                
                new_messages.append(message)
            
            # Process in chronological order (oldest first)
            for message in reversed(new_messages):
                await self.process_message(message)
            
            if new_messages:
                logger.info(f"🚀 Processed {len(new_messages)} new message(s)")
            
        except Exception as e:
            logger.error(f"Error checking messages: {e}")
            if "database is locked" in str(e).lower():
                logger.warning("Database locked during message check - will retry next cycle")
    
    async def run(self):
        """Main hub loop with retry logic"""
        logger.info("=" * 60)
        logger.info("🤖 FELIX SIGNAL HUB - ENHANCED (v2.0)")
        logger.info("=" * 60)
        logger.info("Message types handled:")
        logger.info("  • Initial Signals (BUY/SELL)")
        logger.info("  • TP Hit notifications")
        logger.info("  • SL Hit notifications")
        logger.info("  • Adjusted/Updated signals")
        logger.info("  • Breakeven instructions")
        logger.info("  • Limit order activations")
        logger.info("  • Cancellation notices")
        logger.info("=" * 60)
        
        # Initialize client with SQLite session (file-based)
        self.client = TelegramClient(str(SESSION_FILE), API_ID, API_HASH)
        
        # Connect with retry and error handling
        connected = False
        for attempt in range(10):
            try:
                await self.client.connect()
                if await self.client.is_user_authorized():
                    connected = True
                    break
                else:
                    logger.error("❌ Session not authorized!")
                    return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt+1} failed: {e}")
                if "database is locked" in str(e).lower():
                    logger.warning("SQLite lock detected, waiting longer...")
                    await asyncio.sleep(5)
                await asyncio.sleep(2)
        
        if not connected:
            logger.error("❌ Could not connect after 10 attempts")
            return
        
        me = await self.client.get_me()
        logger.info(f"Logged in as: {me.first_name}")
        
        # Main loop with error recovery
        logger.info("👂 Listening for signals and updates...")
        consecutive_errors = 0
        while True:
            try:
                await self.check_new_messages()
                consecutive_errors = 0  # Reset on success
                await asyncio.sleep(30)
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Loop error ({consecutive_errors}): {e}")
                if "database is locked" in str(e).lower():
                    logger.warning("Database locked - will retry with fresh connection")
                    try:
                        await self.client.disconnect()
                    except:
                        pass
                    # Recreate client with same session
                    self.client = TelegramClient(str(SESSION_FILE), API_ID, API_HASH)
                    try:
                        await self.client.connect()
                    except Exception as conn_err:
                        logger.error(f"Reconnection failed: {conn_err}")
                if consecutive_errors > 5:
                    logger.error("Too many consecutive errors, waiting 60s...")
                    await asyncio.sleep(60)
                    consecutive_errors = 0
                else:
                    await asyncio.sleep(30)


def write_pid():
    """Write PID file"""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def remove_pid():
    """Remove PID file"""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def main():
    write_pid()
    try:
        hub = SignalHub()
        asyncio.run(hub.run())
    except KeyboardInterrupt:
        logger.info("🛑 Signal Hub stopped by user")
    finally:
        remove_pid()


if __name__ == "__main__":
    main()
