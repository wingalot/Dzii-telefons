#!/usr/bin/env python3
"""
FELIX MASTER COORDINATOR - Unified Trading System
Combines SignalHub, SmartParser, TP Manager, and IG Trader into one system
"""

import os
import sys
import json
import asyncio
import logging
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Add supervisor directory to path
sys.path.insert(0, str(Path(__file__).parent / 'ai_supervisor'))

# Import components
try:
    from felix_signal_hub import SignalHub, MessageType
    from felix_smart_parser import smart_parse_signal
    from felix_tp_manager import TPManager
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

# Configuration
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
STATE_DIR = BASE_DIR / "state"
LOG_DIR = BASE_DIR / "logs"
PID_DIR = STATE_DIR

class FelixMasterCoordinator:
    """
    Unified trading system coordinator.
    
    Architecture:
    ┌─────────────────────────────────────────┐
    │         FELIX MASTER COORDINATOR         │
    │  ┌──────────┐  ┌──────────┐  ┌────────┐ │
    │  │  Signal  │→ │  Smart   │→ │   TP   │ │
    │  │   Hub    │  │  Parser  │  │Manager │ │
    │  └──────────┘  └──────────┘  └────────┘ │
    │       ↓              ↓           ↓      │
    │  ┌────────────────────────────────────┐ │
    │  │         Unified State              │ │
    │  └────────────────────────────────────┘ │
    └─────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.running = False
        self.state = {
            'positions': {},
            'pending_limits': {},
            'signal_history': [],
            'last_update': None
        }
        self.components = {}
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup unified logging"""
        os.makedirs(LOG_DIR, exist_ok=True)
        
        logger = logging.getLogger('FELIX-MASTER')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(LOG_DIR / 'felix_master.log')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - [MASTER] - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(console)
        
        return logger
    
    async def initialize(self):
        """Initialize all components"""
        self.logger.info("🚀 Initializing Felix Master Coordinator...")
        
        # Initialize SignalHub
        self.components['signal_hub'] = SignalHub()
        self.logger.info("✅ SignalHub initialized")
        
        # Initialize TP Manager
        self.components['tp_manager'] = TPManager()
        self.logger.info("✅ TP Manager initialized")
        
        # Sync with IG positions
        await self.sync_ig_positions()
        
        self.running = True
        self.logger.info("🎉 Felix Master Coordinator ready!")
    
    async def sync_ig_positions(self):
        """Sync positions from IG"""
        self.logger.info("🔄 Syncing IG positions...")
        # This would call ig_api.sh positions
        # For now, placeholder
        pass
    
    async def process_signal(self, raw_text: str) -> Dict:
        """
        Process trading signal through unified pipeline:
        Text → Smart Parser → Validation → TP Manager
        """
        self.logger.info(f"📩 Processing signal: {raw_text[:80]}...")
        
        # Step 1: Parse with Smart Parser
        parsed = smart_parse_signal(raw_text)
        
        if not parsed.get('valid'):
            self.logger.warning("❌ Signal parsing failed")
            return {'success': False, 'error': 'parsing_failed'}
        
        self.logger.info(f"✅ Parsed: {parsed['pair']} {parsed['direction']} @ {parsed['entry']}")
        
        # Step 2: Validate signal logic
        if not self._validate_signal(parsed):
            return {'success': False, 'error': 'validation_failed'}
        
        # Step 3: Execute or queue
        if parsed.get('is_limit'):
            result = await self._handle_limit_order(parsed)
        else:
            result = await self._handle_market_order(parsed)
        
        # Step 4: Record in history
        self._record_signal(raw_text, parsed, result)
        
        return result
    
    def _validate_signal(self, signal: Dict) -> bool:
        """Validate signal logic"""
        entry = signal.get('entry')
        sl = signal.get('sl')
        direction = signal.get('direction')
        
        if not all([entry, sl, direction]):
            return False
        
        # SL must be on correct side
        if direction == 'BUY' and sl >= entry:
            self.logger.error(f"❌ Invalid SL for BUY: SL {sl} >= Entry {entry}")
            return False
        if direction == 'SELL' and sl <= entry:
            self.logger.error(f"❌ Invalid SL for SELL: SL {sl} <= Entry {entry}")
            return False
        
        return True
    
    async def _handle_market_order(self, signal: Dict) -> Dict:
        """Execute market order"""
        self.logger.info(f"📈 Executing MARKET {signal['direction']} {signal['pair']}")
        
        # Call IG API
        # Placeholder for actual implementation
        result = {
            'success': True,
            'order_type': 'MARKET',
            'deal_id': f"SIM_{datetime.now().strftime('%H%M%S')}",
            'signal': signal
        }
        
        # Register with TP Manager
        tp_manager = self.components['tp_manager']
        # tp_manager.register_position(result['deal_id'], signal)
        
        return result
    
    async def _handle_limit_order(self, signal: Dict) -> Dict:
        """Place limit order"""
        self.logger.info(f"⏳ Placing LIMIT {signal['direction']} {signal['pair']} @ {signal['entry']}")
        
        # Placeholder
        return {
            'success': True,
            'order_type': 'LIMIT',
            'status': 'pending'
        }
    
    def _record_signal(self, raw_text: str, parsed: Dict, result: Dict):
        """Record signal in history"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'raw': raw_text[:200],
            'parsed': parsed,
            'result': result
        }
        self.state['signal_history'].append(record)
        self.state['last_update'] = datetime.now().isoformat()
    
    async def run(self):
        """Main run loop"""
        await self.initialize()
        
        self.logger.info("🟢 Felix Master running...")
        
        while self.running:
            try:
                # Check for new signals (via file trigger or API)
                await self._check_new_signals()
                
                # Monitor positions
                await self._monitor_positions()
                
                # Sleep briefly
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(5)
    
    async def _check_new_signals(self):
        """Check for new signals"""
        # Check signal inbox file
        inbox = STATE_DIR / 'new_signal.json'
        if inbox.exists():
            try:
                with open(inbox) as f:
                    signal_data = json.load(f)
                
                await self.process_signal(signal_data['text'])
                
                # Remove processed signal
                inbox.unlink()
            except Exception as e:
                self.logger.error(f"Failed to process signal: {e}")
    
    async def _monitor_positions(self):
        """Monitor and manage positions"""
        # This would check TP/SL hits
        pass
    
    def stop(self):
        """Stop coordinator"""
        self.logger.info("🛑 Stopping Felix Master Coordinator...")
        self.running = False
        
        # Cleanup
        for name, component in self.components.items():
            self.logger.info(f"  Stopping {name}...")
        
        self.logger.info("✅ Coordinator stopped")


# CLI Interface
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Felix Master Coordinator')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'test'])
    args = parser.parse_args()
    
    if args.action == 'start':
        coordinator = FelixMasterCoordinator()
        
        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            coordinator.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Run
        asyncio.run(coordinator.run())
    
    elif args.action == 'test':
        # Test mode
        coordinator = FelixMasterCoordinator()
        
        test_signals = [
            "BUY XAUUSD 4500 SL: 4480 TP1: 4520",
            "🚨 SIGNAL ALERT 🚨\n\n⚪️ Entry Point: 1.15580\n🔴 Stop Loss (SL): 1.15230",
        ]
        
        async def test():
            await coordinator.initialize()
            for sig in test_signals:
                result = await coordinator.process_signal(sig)
                print(f"\nResult: {result}")
        
        asyncio.run(test())
    
    elif args.action == 'status':
        print("Status check placeholder")
    
    elif args.action == 'stop':
        print("Stop signal sent")


if __name__ == "__main__":
    main()
