#!/usr/bin/env python3
"""
FELIX WAKE-ON-SIGNAL DAEMON
Lightweight monitor that wakes full AI supervisor when signals arrive
- Runs in background with minimal resources
- Detects new messages in Felix channel
- Triggers full AI processing when signal detected
- Self-healing: restarts if crashed
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
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel

# Configuration
API_ID = 39214400
API_HASH = "ce1b295d4cc19db6c9f9804bc8b88c9c"
PHONE = "+37126225767"
TARGET_CHANNEL = "Felix | VIP room"
CHANNEL_ID = -1001998353092  # Known Felix channel ID

# Paths
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
# Use same session as existing listener
SESSION_FILE = Path.home() / ".openclaw" / "telegram" / "felix_listener"
STATE_FILE = BASE_DIR / "state" / "wake_daemon.json"
LOG_FILE = BASE_DIR / "logs" / "wake_daemon.log"
PID_FILE = BASE_DIR / "wake_daemon.pid"
SIGNAL_QUEUE_FILE = BASE_DIR / "state" / "signal_queue.json"

# Setup logging
os.makedirs(BASE_DIR / "logs", exist_ok=True)
os.makedirs(BASE_DIR / "state", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [WAKE-DAEMON] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class FelixWakeDaemon:
    """Lightweight daemon that wakes AI supervisor on signals"""
    
    def __init__(self):
        self.client = None
        self.last_message_id = 0
        self.processing = False
        self.load_state()
        
    def load_state(self):
        """Load daemon state"""
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                state = json.load(f)
                self.last_message_id = state.get('last_message_id', 0)
        else:
            self.last_message_id = 0
    
    def save_state(self):
        """Save daemon state"""
        with open(STATE_FILE, 'w') as f:
            json.dump({
                'last_message_id': self.last_message_id,
                'last_check': datetime.now().isoformat()
            }, f)
    
    def is_trading_signal(self, text):
        """Quick check if message is a trading signal"""
        if not text:
            return False
        
        text_upper = text.upper()
        
        # Must have BUY or SELL
        has_direction = "BUY" in text_upper or "SELL" in text_upper
        
        # Quick pair check - extended list
        pairs = ["GBPJPY", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", 
                 "GOLD", "XAGUSD", "US30", "NAS100", "SPX500",
                 "AUDUSD", "USDCAD", "NZDUSD", "EURJPY", "GBPAUD"]
        has_pair = any(pair in text_upper for pair in pairs)
        
        return has_direction and has_pair
    
    def queue_signal(self, message_text, message_id):
        """Add signal to processing queue"""
        queue = []
        if SIGNAL_QUEUE_FILE.exists():
            with open(SIGNAL_QUEUE_FILE) as f:
                queue = json.load(f)
        
        queue.append({
            'id': message_id,
            'text': message_text,
            'timestamp': datetime.now().isoformat(),
            'processed': False
        })
        
        with open(SIGNAL_QUEUE_FILE, 'w') as f:
            json.dump(queue, f)
        
        logger.info(f"📥 Signal queued: ID {message_id}")
    
    def wake_supervisor(self):
        """Wake up the full AI supervisor to process queued signals"""
        if self.processing:
            logger.info("⏳ Supervisor already running, skipping wake")
            return
        
        self.processing = True
        logger.info("🔔 WAKING AI SUPERVISOR!")
        
        try:
            # Start the full AI listener in background
            subprocess.Popen([
                'python3',
                str(BASE_DIR / 'felix_ai_processor.py'),
                '--process-queue'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info("✅ AI supervisor triggered")
            
            # Reset processing flag after delay
            time.sleep(5)
            self.processing = False
            
        except Exception as e:
            logger.error(f"❌ Failed to wake supervisor: {e}")
            self.processing = False
    
    async def check_new_messages(self):
        """Check for new messages in channel"""
        # Reconnect if disconnected
        if not self.client.is_connected():
            logger.warning("🔌 Disconnected - reconnecting...")
            try:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    logger.error("❌ Reconnect failed - not authorized")
                    return
                logger.info("✅ Reconnected successfully")
            except Exception as e:
                logger.error(f"❌ Reconnect failed: {e}")
                return
        
        try:
            entity = await self.client.get_entity(CHANNEL_ID)
            
            # Get recent messages
            new_signals = []
            async for message in self.client.iter_messages(entity, limit=5):
                if message.id <= self.last_message_id:
                    continue
                
                # Update last seen
                if message.id > self.last_message_id:
                    self.last_message_id = message.id
                
                # Check if signal
                text = message.text or ""
                if self.is_trading_signal(text):
                    logger.info(f"🎯 SIGNAL DETECTED: ID {message.id}")
                    self.queue_signal(text, message.id)
                    new_signals.append(message.id)
            
            # Save state
            self.save_state()
            
            # Wake supervisor if new signals found
            if new_signals:
                logger.info(f"🚀 {len(new_signals)} new signals - waking supervisor!")
                self.wake_supervisor()
            
        except Exception as e:
            logger.error(f"Error checking messages: {e}")
    
    async def run(self):
        """Main daemon loop"""
        logger.info("=" * 60)
        logger.info("🤖 FELIX WAKE-ON-SIGNAL DAEMON")
        logger.info("=" * 60)
        logger.info("Lightweight monitor - wakes AI on signals")
        
        # Initialize client with retry and timeout
        for attempt in range(10):
            try:
                # Set SQLite timeout to avoid "database is locked" errors
                import sqlite3
                sqlite3.connect(str(SESSION_FILE) + ".session", timeout=30)
                
                self.client = TelegramClient(str(SESSION_FILE), API_ID, API_HASH)
                await self.client.connect()
                break
            except Exception as e:
                logger.warning(f"Connection attempt {attempt+1} failed: {e}")
                if "database is locked" in str(e):
                    logger.info("Waiting for database to unlock...")
                    await asyncio.sleep(3)
                else:
                    await asyncio.sleep(2)
        else:
            logger.error("❌ Could not connect after 10 attempts")
            return
        
        if not await self.client.is_user_authorized():
            logger.error("❌ Session not authorized! Run felix_ai_listener.py first to authenticate.")
            return
        
        me = await self.client.get_me()
        logger.info(f"Logged in as: {me.first_name}")
        
        # Main loop - check every 30 seconds
        logger.info("👂 Listening for signals...")
        while True:
            try:
                await self.check_new_messages()
                await asyncio.sleep(30)  # Check every 30 seconds
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
        daemon = FelixWakeDaemon()
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        logger.info("🛑 Daemon stopped by user")
    finally:
        remove_pid()

if __name__ == "__main__":
    main()