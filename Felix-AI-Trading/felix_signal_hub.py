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

# Configuration
API_ID = 39214400
API_HASH = "ce1b295d4cc19db6c9f9804bc8b88c9c"
PHONE = "+37126225767"
TARGET_CHANNEL = "Felix | VIP room"
CHANNEL_ID = -1001998353092

# Paths
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
TRADING_DIR = Path.home() / ".trading"
SESSION_FILE = Path.home() / ".openclaw" / "telegram" / "felix_listener"
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
                new_tp = self._extract_tp_levels(text)
                new_sl = self._extract_sl(text)
                new_entry = self._extract_entry(text)
                
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
        
        # Check for Initial Signal (BUY/SELL with pair)
        if self._is_trading_signal(text):
            pair = self._extract_pair(text)
            direction = 'BUY' if 'BUY' in text_upper else 'SELL'
            entry = self._extract_entry(text)
            tp_levels = self._extract_tp_levels(text)
            sl = self._extract_sl(text)
            is_limit = 'LIMIT' in text_upper
            
            return MessageType.INITIAL_SIGNAL, {
                'pair': pair,
                'direction': direction,
                'entry': entry,
                'tp_levels': tp_levels,
                'sl': sl,
                'is_limit': is_limit,
                'original_text': text
            }
        
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
        """Extract entry price from text"""
        if not text:
            return None
        
        patterns = [
            r'(?:BUY|SELL)(?:\s+NOW)?\s+([\d.]+)',
            r'@\s*([\d.]+)',
            r'ENTRY[:\s]+([\d.]+)',
            r'ENTRY POINT[:\s]+([\d.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        return None
    
    def _extract_tp_levels(self, text):
        """Extract TP levels from text"""
        if not text:
            return []
        
        tps = []
        
        # Pattern: TP1: 1.2345, TP2: 1.2350, etc.
        tp_matches = re.findall(r'TP\s*#?\s*\d*[\s:]*([\d.]+)', text.upper())
        if tp_matches:
            tps = [float(tp) for tp in tp_matches if self._is_valid_price(tp)]
        
        # Pattern: 🤑TP1: 1.2345
        if not tps:
            tp_matches = re.findall(r'🤑TP\d*[\s:]*([\d.]+)', text.upper())
            tps = [float(tp) for tp in tp_matches if self._is_valid_price(tp)]
        
        # Check for relative TP (+15 Pips)
        if not tps:
            relative_match = re.search(r'SET\s+TP\d*\s*\+(\d+)\s*PIPS', text.upper())
            if relative_match:
                tps = [int(relative_match.group(1))]  # Store as int to indicate relative
        
        return tps
    
    def _extract_sl(self, text):
        """Extract SL level from text"""
        if not text:
            return None
        
        patterns = [
            r'SL[:\s]+([\d.]+)',
            r'SL[:\s]+([\d.]+)\s*\(',
            r'🔴SL[:\s]+([\d.]+)',
            r'STOP LOSS[:\s]+([\d.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                try:
                    price = match.group(1)
                    if self._is_valid_price(price):
                        return float(price)
                except:
                    pass
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
        """Register a new signal in the registry"""
        key = f"{signal_data.get('pair')}_{signal_data.get('direction')}"
        
        self.message_registry[str(message_id)] = {
            'message_id': message_id,
            'pair': signal_data.get('pair'),
            'direction': signal_data.get('direction'),
            'entry': signal_data.get('entry'),
            'tp_levels': signal_data.get('tp_levels', []),
            'sl': signal_data.get('sl'),
            'is_limit': signal_data.get('is_limit', False),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'updates': []
        }
        
        self.pair_to_message[key] = message_id
        self.save_state()
        
        logger.info(f"📋 Signal registered: {key} -> Msg {message_id}")
    
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
        
        else:
            logger.debug(f"   ⏭️ Unknown message type, skipping")
        
        self.save_state()
    
    async def _handle_initial_signal(self, message_id, text, data):
        """Handle new trading signal"""
        logger.info("=" * 60)
        logger.info(f"🎯 NEW SIGNAL: {data.get('pair')} {data.get('direction')}")
        logger.info(f"   Entry: {data.get('entry')}, TP: {data.get('tp_levels')}, SL: {data.get('sl')}")
        logger.info("=" * 60)
        
        # Register the signal
        self.register_signal(message_id, data)
        
        # Save for processing
        self.save_signal_for_processing(text, message_id, MessageType.INITIAL_SIGNAL, data)
        
        # Trigger AI processor
        self.trigger_ai_processor()
        
        # Notify TP Manager
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
    
    async def check_new_messages(self):
        """Check for new messages in channel"""
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
    
    async def run(self):
        """Main hub loop"""
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
        
        # Initialize client
        self.client = TelegramClient(str(SESSION_FILE), API_ID, API_HASH)
        
        # Connect with retry
        for attempt in range(10):
            try:
                await self.client.connect()
                break
            except Exception as e:
                logger.warning(f"Connection attempt {attempt+1} failed: {e}")
                await asyncio.sleep(2)
        else:
            logger.error("❌ Could not connect after 10 attempts")
            return
        
        if not await self.client.is_user_authorized():
            logger.error("❌ Session not authorized!")
            return
        
        me = await self.client.get_me()
        logger.info(f"Logged in as: {me.first_name}")
        
        # Main loop
        logger.info("👂 Listening for signals and updates...")
        while True:
            try:
                await self.check_new_messages()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Loop error: {e}")
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
