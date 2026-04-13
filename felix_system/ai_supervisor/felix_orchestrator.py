#!/usr/bin/env python3
"""
Felix AI Supervisor - Simplified Orchestrator Module
Handles trading signal processing via simple JSON file communication.
"""

import json
import os
import re
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Tuple

# Configuration
BASE_DIR = Path("~/.openclaw/ai_supervisor").expanduser()
SIGNAL_DIR = BASE_DIR / "signals"
ORDERS_DIR = BASE_DIR / "orders"
POSITIONS_DIR = BASE_DIR / "positions"
LOGS_DIR = BASE_DIR / "logs"
CONFIG_FILE = BASE_DIR / "config.json"

# Default epic codes mapping
DEFAULT_EPICS = {
    "EURUSD": "CS.D.EURUSD.CFD.IP",
    "GBPUSD": "CS.D.GBPUSD.CFD.IP",
    "USDJPY": "CS.D.USDJPY.CFD.IP",
    "AUDUSD": "CS.D.AUDUSD.CFD.IP",
    "USDCAD": "CS.D.USDCAD.CFD.IP",
    "USDCHF": "CS.D.USDCHF.CFD.IP",
    "NZDUSD": "CS.D.NZDUSD.CFD.IP",
    "EURGBP": "CS.D.EURGBP.CFD.IP",
    "EURJPY": "CS.D.EURJPY.CFD.IP",
    "GBPJPY": "CS.D.GBPJPY.CFD.IP",
    "AUDJPY": "CS.D.AUDJPY.CFD.IP",
    "CHFJPY": "CS.D.CHFJPY.CFD.IP",
    "EURAUD": "CS.D.EURAUD.CFD.IP",
    "EURCHF": "CS.D.EURCHF.CFD.IP",
    "GBPAUD": "CS.D.GBPAUD.CFD.IP",
    "GBPCHF": "CS.D.GBPCHF.CFD.IP",
    "XAUUSD": "CS.D.GOLD.CFD.IP",
    "GOLD": "CS.D.GOLD.CFD.IP",
}

class FelixOrchestrator:
    """Main orchestrator for processing trading signals."""
    
    def __init__(self):
        self._setup_directories()
        self._setup_logging()
        self.config = self._load_config()
        self.epics = self.config.get("epics", DEFAULT_EPICS)
        
    def _setup_directories(self):
        """Create necessary directories if they don't exist."""
        for dir_path in [SIGNAL_DIR, ORDERS_DIR, POSITIONS_DIR, LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
    def _setup_logging(self):
        """Setup logging to file."""
        log_file = LOGS_DIR / f"orchestrator_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self) -> Dict:
        """Load configuration from config file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid config JSON: {e}")
                return {}
        return {}
    
    def parse_signal(self, signal_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse trading signal text to extract trade parameters.
        
        Args:
            signal_text: Raw signal text from Telegram or other source
            
        Returns:
            Dictionary with parsed trade parameters or None if invalid
        """
        result = {
            "pair": None,
            "direction": None,
            "entry": None,
            "sl": None,
            "tp1": None,
            "tp2": None,
            "tp3": None,
            "raw_text": signal_text
        }
        
        text_upper = signal_text.upper()
        text_clean = signal_text
        
        # Extract currency pair (e.g., EURUSD, GBPUSD, USDJPY)
        pair_pattern = r'\b(EUR|GBP|USD|AUD|NZD|CAD|CHF|JPY){2,6}\b'
        pair_match = re.search(pair_pattern, text_upper)
        if pair_match:
            result["pair"] = pair_match.group(0)
        else:
            # Try alternative: XAUUSD / GOLD
            gold_pattern = r'\b(XAUUSD|GOLD)\b'
            gold_match = re.search(gold_pattern, text_upper)
            if gold_match:
                result["pair"] = "XAUUSD" if gold_match.group(0) == "XAUUSD" else "GOLD"
        
        # Extract direction (BUY or SELL)
        direction_pattern = r'\b(BUY|SELL)\b'
        direction_match = re.search(direction_pattern, text_upper)
        if direction_match:
            result["direction"] = direction_match.group(0)
        
        # Extract entry price - try __price__ format first
        entry_patterns = [
            r'@\s*([\d.]+)',  # @ price
            r'__?([\d.]+)__?',  # __price__ format
            r'ENTRY[:\s]+([\d.]+)',  # Entry: price
            r'PRICE[:\s]+([\d.]+)',  # Price: price
        ]
        for pattern in entry_patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                try:
                    result["entry"] = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        # Extract Stop Loss
        sl_patterns = [
            r'(?:SL|STOP\s*LOSS)[:\s]+([\d.]+)',  # SL: price or Stop Loss: price
            r'(?:SL|STOP)\s*[:\s]+([\d.]+)',  # SL: price
        ]
        for pattern in sl_patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                try:
                    result["sl"] = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        # Extract Take Profits (TP1, TP2, TP3)
        tp_patterns = [
            (r'TP1[:\s]+([\d.]+)', "tp1"),
            (r'TP2[:\s]+([\d.]+)', "tp2"),
            (r'TP3[:\s]+([\d.]+)', "tp3"),
            (r'TAKE\s*PROFIT\s*1[:\s]+([\d.]+)', "tp1"),
            (r'TAKE\s*PROFIT\s*2[:\s]+([\d.]+)', "tp2"),
            (r'TAKE\s*PROFIT\s*3[:\s]+([\d.]+)', "tp3"),
            (r'TP\s*1[:\s]+([\d.]+)', "tp1"),
            (r'TP\s*2[:\s]+([\d.]+)', "tp2"),
            (r'TP\s*3[:\s]+([\d.]+)', "tp3"),
        ]
        for pattern, key in tp_patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                try:
                    result[key] = float(match.group(1))
                except ValueError:
                    continue
        
        # Alternative: find all prices and assign by position
        all_prices = re.findall(r'[\d.]+', signal_text)
        numeric_prices = []
        for p in all_prices:
            try:
                price = float(p)
                if price > 0:  # Valid price
                    numeric_prices.append(price)
            except ValueError:
                continue
        
        # If we have prices but missing some fields, try to infer
        if len(numeric_prices) >= 2 and result["entry"] and not result["sl"]:
            # SL is usually closest to entry in opposite direction
            entry = result["entry"]
            direction = result["direction"]
            
            # Find price closest to entry (excluding entry itself)
            closest = None
            min_diff = float('inf')
            for p in numeric_prices:
                if abs(p - entry) > 0.001:  # Not the entry itself
                    diff = abs(p - entry)
                    if diff < min_diff:
                        min_diff = diff
                        closest = p
            
            if closest:
                result["sl"] = closest
        
        # Validate minimum required fields
        if not result["pair"] or not result["direction"]:
            self.logger.error("Missing required fields: pair or direction")
            return None
            
        return result
    
    def get_epic_code(self, pair: str) -> Optional[str]:
        """Get IG epic code for currency pair."""
        pair_upper = pair.upper()
        return self.epics.get(pair_upper)
    
    def get_currency_code(self, pair: str) -> str:
        """Get currency code for position sizing (last 3 letters or JPY)."""
        pair_upper = pair.upper()
        if pair_upper.endswith("JPY"):
            return "JPY"
        elif len(pair_upper) >= 6:
            return pair_upper[3:6]
        return "USD"  # Default fallback
    
    def create_order_request(self, parsed_signal: Dict) -> Dict:
        """
        Create order request for IG API.
        
        Args:
            parsed_signal: Parsed signal dictionary
            
        Returns:
            Order request dictionary
        """
        pair = parsed_signal["pair"]
        epic = self.get_epic_code(pair)
        
        if not epic:
            raise ValueError(f"Unknown pair: {pair}")
        
        order = {
            "epic": epic,
            "direction": parsed_signal["direction"],
            "size": 1.0,  # Default size, can be adjusted
            "order_type": "MARKET",  # or LIMIT if entry is specified
            "currency_code": self.get_currency_code(pair),
            "stop_level": parsed_signal.get("sl"),
            "limit_level": parsed_signal.get("tp1"),  # Primary TP
            "tp2": parsed_signal.get("tp2"),
            "tp3": parsed_signal.get("tp3"),
            "timestamp": datetime.now().isoformat(),
            "signal_id": f"SIG_{int(time.time())}"
        }
        
        # If entry price is specified and different from current, use LIMIT order
        if parsed_signal.get("entry"):
            order["order_type"] = "LIMIT"
            order["level"] = parsed_signal["entry"]
        
        return order
    
    def process_signal_file(self, input_file: Path) -> Dict:
        """
        Process a signal file and return result.
        
        Args:
            input_file: Path to input JSON file
            
        Returns:
            Result dictionary
        """
        result = {
            "success": False,
            "signal_id": None,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Read input signal
            with open(input_file, 'r') as f:
                signal_data = json.load(f)
            
            signal_text = signal_data.get("text", "")
            signal_id = signal_data.get("id", f"SIG_{int(time.time())}")
            result["signal_id"] = signal_id
            
            self.logger.info(f"Processing signal {signal_id}")
            
            # Parse signal
            parsed = self.parse_signal(signal_text)
            if not parsed:
                result["error"] = "Failed to parse signal"
                self.logger.error(f"Failed to parse signal: {signal_text[:100]}...")
                return result
            
            self.logger.info(f"Parsed: {parsed['pair']} {parsed['direction']} @ {parsed.get('entry', 'MARKET')}")
            
            # Create order request
            order = self.create_order_request(parsed)
            order["signal_id"] = signal_id
            
            # Save order request for IG API module
            order_file = ORDERS_DIR / f"{signal_id}_order.json"
            with open(order_file, 'w') as f:
                json.dump(order, f, indent=2)
            
            self.logger.info(f"Order request saved: {order_file}")
            
            # Register position for TP Manager
            position = {
                "signal_id": signal_id,
                "epic": order["epic"],
                "pair": parsed["pair"],
                "direction": order["direction"],
                "size": order["size"],
                "entry_price": parsed.get("entry"),
                "sl": order["stop_level"],
                "tp1": order["limit_level"],
                "tp2": order.get("tp2"),
                "tp3": order.get("tp3"),
                "status": "PENDING",
                "created_at": datetime.now().isoformat()
            }
            
            position_file = POSITIONS_DIR / f"{signal_id}_position.json"
            with open(position_file, 'w') as f:
                json.dump(position, f, indent=2)
            
            self.logger.info(f"Position registered: {position_file}")
            
            result["success"] = True
            result["order_file"] = str(order_file)
            result["position_file"] = str(position_file)
            result["parsed"] = parsed
            
        except json.JSONDecodeError as e:
            result["error"] = f"Invalid JSON: {e}"
            self.logger.error(f"JSON decode error: {e}")
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"Error processing signal: {e}")
        
        return result
    
    def run(self):
        """Main loop - process signal files from signal directory."""
        self.logger.info("Felix Orchestrator started")
        
        while True:
            try:
                # Look for new signal files
                signal_files = list(SIGNAL_DIR.glob("*_signal.json"))
                
                for signal_file in signal_files:
                    self.logger.info(f"Found signal file: {signal_file}")
                    
                    # Process signal
                    result = self.process_signal_file(signal_file)
                    
                    # Write result
                    result_file = SIGNAL_DIR / f"{signal_file.stem}_result.json"
                    with open(result_file, 'w') as f:
                        json.dump(result, f, indent=2)
                    
                    # Delete input file
                    signal_file.unlink()
                    self.logger.info(f"Processed and removed: {signal_file}")
                
                # Sleep before next check
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("Orchestrator stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                time.sleep(5)


def process_single_signal(signal_text: str, signal_id: Optional[str] = None) -> Dict:
    """
    Process a single signal text directly (for testing or manual use).
    
    Args:
        signal_text: Raw signal text
        signal_id: Optional signal ID
        
    Returns:
        Result dictionary
    """
    orchestrator = FelixOrchestrator()
    
    if not signal_id:
        signal_id = f"SIG_{int(time.time())}"
    
    # Create input file
    signal_data = {
        "id": signal_id,
        "text": signal_text,
        "timestamp": datetime.now().isoformat()
    }
    
    input_file = SIGNAL_DIR / f"{signal_id}_signal.json"
    with open(input_file, 'w') as f:
        json.dump(signal_data, f, indent=2)
    
    # Process
    result = orchestrator.process_signal_file(input_file)
    
    # Cleanup
    if input_file.exists():
        input_file.unlink()
    
    return result


def main():
    """Entry point."""
    if len(sys.argv) > 1:
        # Process single signal from command line
        signal_text = " ".join(sys.argv[1:])
        result = process_single_signal(signal_text)
        print(json.dumps(result, indent=2))
    else:
        # Run continuous mode
        orchestrator = FelixOrchestrator()
        orchestrator.run()


if __name__ == "__main__":
    main()
