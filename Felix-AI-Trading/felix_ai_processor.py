#!/usr/bin/env python3
"""
FELIX AI PROCESSOR
Triggered by wake daemon when signals arrive
Processes queued signals with full AI capabilities
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from telethon import TelegramClient

# Configuration
API_ID = 39214400
API_HASH = "ce1b295d4cc19db6c9f9804bc8b88c9c"
FORWARD_TO = 395239117  # Nigerian Prince Telegram ID

# Paths
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
SESSION_FILE = Path.home() / ".openclaw" / "telegram" / "felix_listener"
SIGNAL_QUEUE_FILE = BASE_DIR / "state" / "signal_queue.json"

sys.path.insert(0, str(BASE_DIR))
from felix_ai_supervisor import FelixAISupervisor

class SignalProcessor:
    """Processes queued signals with full AI"""
    
    def __init__(self):
        self.supervisor = FelixAISupervisor()
        self.client = None
        self.forward_user = None
    
    async def initialize(self):
        """Initialize Telegram client for notifications (optional)"""
        try:
            self.client = TelegramClient(str(SESSION_FILE), API_ID, API_HASH)
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                print("⚠️ Telegram not authorized - notifications disabled")
                await self.client.disconnect()
                self.client = None
                return
            
            try:
                self.forward_user = await self.client.get_entity(FORWARD_TO)
            except Exception as e:
                print(f"⚠️ Could not get forward user: {e}")
                self.forward_user = None
        except Exception as e:
            print(f"⚠️ Telegram init failed: {e}")
            self.client = None
            self.forward_user = None
    
    def load_queue(self):
        """Load signal queue"""
        if not SIGNAL_QUEUE_FILE.exists():
            return []
        
        with open(SIGNAL_QUEUE_FILE) as f:
            return json.load(f)
    
    def save_queue(self, queue):
        """Save signal queue"""
        with open(SIGNAL_QUEUE_FILE, 'w') as f:
            json.dump(queue, f)
    
    async def send_notification(self, message, urgent=False):
        """Send notification to user"""
        if not self.client or not self.forward_user:
            return
        
        try:
            prefix = "🚨" if urgent else "📊"
            await self.client.send_message(
                self.forward_user,
                f"{prefix} {message}"
            )
        except Exception as e:
            print(f"Failed to send notification: {e}")
    
    def process_signal(self, signal_data):
        """Process a single signal with AI"""
        signal_text = signal_data['text']
        signal_id = signal_data['id']
        
        print(f"\n{'='*60}")
        print(f"🎯 Processing Signal {signal_id}")
        print(f"{'='*60}")
        print(f"Raw: {signal_text[:200]}...")
        
        # Process with AI supervisor - returns bool
        success = self.supervisor.process_signal(signal_text)
        
        if success:
            print("✅ Signal executed successfully!")
            return True, "executed"
        else:
            print("❌ Failed to execute signal")
            return False, "execution_failed"
    
    async def process_queue(self):
        """Process all unprocessed signals in queue"""
        queue = self.load_queue()
        
        if not queue:
            print("📭 No signals in queue")
            return
        
        # Filter unprocessed
        pending = [s for s in queue if not s.get('processed')]
        
        if not pending:
            print("📭 No pending signals")
            return
        
        print(f"\n{'='*60}")
        print(f"🤖 FELIX AI PROCESSOR")
        print(f"{'='*60}")
        print(f"Processing {len(pending)} pending signals...")
        
        # Notify user
        await self.send_notification(
            f"🤖 AI Processor Activated\n📥 Processing {len(pending)} signal(s)..."
        )
        
        # Initialize for notifications
        await self.initialize()
        
        # Process each signal
        results = []
        for signal in pending:
            success, details = self.process_signal(signal)
            signal['processed'] = True
            signal['processed_at'] = datetime.now().isoformat()
            signal['success'] = success
            signal['details'] = str(details)
            results.append((signal['id'], success))
        
        # Save updated queue
        self.save_queue(queue)
        
        # Summary
        successful = sum(1 for _, s in results if s)
        print(f"\n{'='*60}")
        print(f"📊 SUMMARY: {successful}/{len(results)} signals successful")
        print(f"{'='*60}")
        
        # Notify user
        await self.send_notification(
            f"✅ Processing Complete\n"
            f"📊 {successful}/{len(results)} signals executed\n"
            f"🔄 AI supervisor returning to sleep..."
        )
        
        # Disconnect if connected
        if self.client:
            await self.client.disconnect()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--process-queue', action='store_true', 
                       help='Process all queued signals')
    parser.add_argument('--process', type=str,
                       help='Process a specific signal text')
    
    args = parser.parse_args()
    
    processor = SignalProcessor()
    
    if args.process_queue:
        asyncio.run(processor.process_queue())
    elif args.process:
        # Quick single signal process
        result = processor.supervisor.process_signal(args.process)
        print(json.dumps(result, indent=2))
    else:
        print("Use --process-queue to process pending signals")

if __name__ == "__main__":
    main()