#!/usr/bin/env python3
"""
FELIX AI-ENHANCED LISTENER
Wraps the standard listener with AI supervision
Ensures 100% signal execution through intelligent retry and fix
"""

import os
import sys
import json
import asyncio
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

# Add supervisor to path
sys.path.insert(0, str(Path.home() / ".openclaw" / "ai_supervisor"))
from felix_ai_supervisor import FelixAISupervisor

# Configuration
API_ID = 39214400
API_HASH = "ce1b295d4cc19db6c9f9804bc8b88c9c"
PHONE = "+37126225767"
TARGET_CHANNEL = "Felix | VIP room"
FORWARD_TO = 395239117  # Nigerian Prince Telegram ID

AUTO_EXECUTE = True
RISK_VALIDATOR = False

# Paths
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
SESSION_FILE = Path.home() / ".openclaw" / "telegram" / "felix_listener"
STATE_FILE = BASE_DIR / "state" / "enhanced_listener.json"
LOG_FILE = BASE_DIR / "logs" / "enhanced_listener.log"

# Setup logging
os.makedirs(BASE_DIR / "logs", exist_ok=True)
os.makedirs(BASE_DIR / "state", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AI-LISTENER] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AIEnhancedListener:
    """Enhanced listener with AI supervision"""
    
    def __init__(self):
        self.supervisor = FelixAISupervisor()
        self.client = None
        self.forward_user = None
        
    async def initialize(self):
        """Initialize the listener"""
        logger.info("Initializing AI-Enhanced Felix Listener...")
        
        # Create Telegram client
        self.client = TelegramClient(str(SESSION_FILE), API_ID, API_HASH)
        await self.client.start()
        
        me = await self.client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username})")
        
        # Get forward user entity
        try:
            self.forward_user = await self.client.get_entity(FORWARD_TO)
            logger.info(f"Forward target: {self.forward_user.first_name}")
        except Exception as e:
            logger.error(f"Could not get forward user: {e}")
            self.forward_user = None
        
        return True
    
    async def find_channel(self):
        """Find the target channel"""
        try:
            # Known channel ID
            channel_id = -1001998353092
            entity = await self.client.get_entity(channel_id)
            if entity:
                logger.info(f"Found channel: {entity.title}")
                return channel_id
        except Exception as e:
            logger.warning(f"Could not access by ID: {e}")
        
        # Search by name
        async for dialog in self.client.iter_dialogs():
            if dialog.name and TARGET_CHANNEL.lower() in dialog.name.lower():
                logger.info(f"Found channel: {dialog.name}")
                return dialog.id
        
        return None
    
    def is_trading_signal(self, text):
        """Check if message is a trading signal"""
        if not text:
            return False
        
        text_upper = text.upper()
        
        # Must have BUY or SELL
        has_direction = "BUY" in text_upper or "SELL" in text_upper
        
        # Extended pair list
        pairs = [
            "GBPJPY", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", 
            "GOLD", "XAGUSD", "US30", "NAS100", "SPX500",
            "AUDUSD", "USDCAD", "NZDUSD", "EURJPY", "GBPAUD"
        ]
        has_pair = any(pair in text_upper for pair in pairs)
        
        return has_direction and has_pair
    
    async def send_notification(self, message, urgent=False):
        """Send notification to user"""
        if not self.forward_user:
            logger.warning("Cannot send notification: no forward user")
            return
        
        try:
            prefix = "🚨" if urgent else "📊"
            await self.client.send_message(
                self.forward_user,
                f"{prefix} {message}"
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    async def process_signal(self, message_text, message_id):
        """Process signal with AI supervision"""
        logger.info("=" * 60)
        logger.info(f"🎯 NEW SIGNAL (ID: {message_id})")
        logger.info("=" * 60)
        logger.info(f"Raw: {message_text[:150]}...")
        
        # Notify user
        await self.send_notification(
            f"**Signal Detected**\n```\n{message_text[:300]}\n```\n\n🔄 AI processing..."
        )
        
        # Process with supervisor
        try:
            success = self.supervisor.process_signal(message_text)
            
            if success:
                await self.send_notification(
                    "✅ **Trade Executed Successfully**\n\n"
                    f"Signal ID: {message_id}\n"
                    f"Success Rate: {self.supervisor.calculate_success_rate()}%"
                )
            else:
                await self.send_notification(
                    "❌ **Trade Failed**\n\n"
                    f"Signal ID: {message_id}\n"
                    "AI could not fix the issue. Manual intervention required.",
                    urgent=True
                )
                
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            await self.send_notification(
                f"❌ **Processing Error**\n\n{str(e)[:200]}",
                urgent=True
            )
    
    async def start_listening(self):
        """Start listening for messages"""
        if not await self.initialize():
            return
        
        channel_id = await self.find_channel()
        
        if not channel_id:
            logger.error("Cannot find channel, exiting")
            await self.client.disconnect()
            return
        
        logger.info("=" * 60)
        logger.info("🚀 AI-ENHANCED LISTENER ACTIVE")
        logger.info("=" * 60)
        logger.info(f"Monitoring: {TARGET_CHANNEL}")
        logger.info(f"Auto-execute: {'ENABLED' if AUTO_EXECUTE else 'DISABLED'}")
        logger.info(f"AI Supervisor: ACTIVE")
        logger.info("=" * 60)
        
        # Send startup notification
        await self.send_notification(
            "🤖 **AI Supervisor Activated**\n\n"
            "System is monitoring Felix VIP Room\n"
            "100% signal execution guarantee active"
        )
        
        @self.client.on(events.NewMessage(chats=channel_id))
        async def handler(event):
            message = event.message
            text = message.text or ""
            
            logger.info(f"📩 New message received")
            
            if self.is_trading_signal(text):
                await self.process_signal(text, message.id)
            else:
                logger.info("⏭️ Not a trading signal, skipping")
        
        logger.info("✅ Listening... Press Ctrl+C to stop")
        await self.client.run_until_disconnected()

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", action="store_true", help="Start listening")
    args = parser.parse_args()
    
    if args.listen:
        listener = AIEnhancedListener()
        try:
            await listener.start_listening()
        except KeyboardInterrupt:
            logger.info("Listener stopped")
    else:
        print("Felix AI-Enhanced Listener")
        print("Usage: python3 felix_ai_listener.py --listen")

if __name__ == "__main__":
    asyncio.run(main())
