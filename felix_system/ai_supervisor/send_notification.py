#!/usr/bin/env python3
"""
Telegram Notification Sender
Sends notifications to Saved Messages
"""

import os
import sys
import asyncio
from pathlib import Path

# Add path for telethon
sys.path.insert(0, str(Path.home() / ".local" / "lib" / "python3.11" / "site-packages"))
sys.path.insert(0, str(Path.home() / ".local" / "lib" / "python3.10" / "site-packages"))

try:
    from telethon import TelegramClient
    from telethon.tl.functions.messages import GetDialogsRequest
except ImportError:
    print("Telethon not available")
    sys.exit(1)

# Telegram config
API_ID = YOUR_API_ID_HERE
API_HASH = 'YOUR_API_HASH_HERE'
PHONE = 'YOUR_PHONE_HERE'
SESSION_FILE = str(Path.home() / ".openclaw" / "telegram" / "felix_listener")

async def send_notification(message):
    """Send message to Saved Messages"""
    try:
        client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("Not authorized")
            return False
        
        # Send to "Saved Messages" (me/self)
        await client.send_message('me', message)
        await client.disconnect()
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: send_notification.py 'message'")
        sys.exit(1)
    
    message = sys.argv[1]
    result = asyncio.run(send_notification(message))
    sys.exit(0 if result else 1)

if __name__ == "__main__":
    main()
