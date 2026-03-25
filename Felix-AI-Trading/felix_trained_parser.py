#!/usr/bin/env python3
"""
FELIX AI SIGNAL PARSER - TRAINED VERSION
Handles ALL historical Felix VIP Room signal formats
"""

import re
import json
from typing import Optional, Dict, List, Tuple

class FelixAITrainedParser:
    """
    AI-trained parser for Felix VIP Room signals.
    Handles multiple formats found in historical data.
    """
    
    # Comprehensive asset list
    ASSETS = [
        # Forex majors
        'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD',
        # Forex crosses
        'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY', 'EURCAD', 'EURAUD',
        'GBPCAD', 'GBPAUD', 'NZDJPY', 'EURNZD', 'GBPNZD', 'AUDCAD', 'AUDNZD',
        'CADCHF', 'EURCHF', 'GBPCHF', 'NZDCAD', 'NZDCHF',
        # Crypto/Metals
        'BTCUSD', 'ETHUSD', 'XRPUSD', 'XAUUSD', 'XAGUSD', 'GOLD', 'SILVER',
        # Indices
        'US30', 'NAS100', 'SPX500', 'UK100', 'GER40', 'JPN225'
    ]
    
    def __init__(self):
        self.training_examples = self._load_training_examples()
    
    def _load_training_examples(self) -> List[Dict]:
        """Load training examples from historical data"""
        return [
            # Format 1: Simple with price after pair
            {
                "text": "BUY XAUUSD 4653.0\n🤑TP1: 4655.0\n🤑TP2: 4657.0\n🔴SL: 4635.0",
                "expected": {"pair": "XAUUSD", "direction": "BUY", "entry": "4653.0", "sl": "4635.0"}
            },
            # Format 2: Limit order with @
            {
                "text": "🔴** Sell Limit XAUUSD @ 4721 **(__4720.75__)**\nTP #1: 4718\nTP #2: 4660\nSL: 4731",
                "expected": {"pair": "XAUUSD", "direction": "SELL", "entry": "4721", "sl": "4731"}
            },
            # Format 3: BTC format
            {
                "text": "🔴 Sell BTCUSD @ 68000\nTP #1: 67700\nTP #2: 63000\nSL: 68700",
                "expected": {"pair": "BTCUSD", "direction": "SELL", "entry": "68000", "sl": "68700"}
            },
            # Format 4: Detailed emoji format
            {
                "text": "🚨 SIGNAL ALERT 🚨\n🌐 #EURCAD\n📈 #BUY\n⚪️ Entry Point: 1.57680\n🔴 Stop Loss: 1.57330\n🟢 Take Profit 1: 1.57830",
                "expected": {"pair": "EURCAD", "direction": "BUY", "entry": "1.57680", "sl": "1.57330"}
            },
            # Format 5: GBPJPY with entry zone
            {
                "text": "🇬🇧🇯🇵 GBPJPY 🔵 BUY\n📊 Entry Zone: 192.500 - 192.800\n🎯 TP1: 193.200\n⛔️ SL: 191.800",
                "expected": {"pair": "GBPJPY", "direction": "BUY", "entry": "192.500", "sl": "191.800"}
            },
            # Format 6: Signal alert with hashtag
            {
                "text": "🚨 SIGNAL ALERT\n#GBPUSD #SELL\nEntry: 1.27500\nTP1: 1.27300\nSL: 1.27700",
                "expected": {"pair": "GBPUSD", "direction": "SELL", "entry": "1.27500", "sl": "1.27700"}
            },
        ]
    
    def parse(self, raw_text: str) -> Dict:
        """
        Main parsing method - tries all format parsers
        """
        if not raw_text:
            return {"valid": False, "error": "empty_text"}
        
        # Normalize text
        text = raw_text.strip()
        text_upper = text.upper()
        
        # Try each parser in order
        parsers = [
            self._parse_buy_now_format,             # BUY NOW 1.33770
            self._parse_simple_price_after_pair,   # BUY XAUUSD 4653.0
            self._parse_limit_order_with_at,        # Sell @ 4721
            self._parse_detailed_emoji_format,      # 🚨 SIGNAL ALERT with emojis
            self._parse_gbpjpy_format,              # 🇬🇧🇯🇵 format
            self._parse_signal_alert_hashtag,       # #GBPUSD #SELL
            self._parse_generic,                    # Fallback
        ]
        
        for parser in parsers:
            result = parser(text, text_upper)
            if result and result.get("valid"):
                return result
        
        # If all fail, return best effort
        return self._parse_generic(text, text_upper)
    
    def _extract_pair(self, text: str) -> Optional[str]:
        """Extract currency pair from text"""
        text_upper = text.upper()
        
        # Check each asset
        for asset in self.ASSETS:
            # Look for exact match or with # prefix
            patterns = [
                rf'\b{asset}\b',
                rf'#{asset}\b',
            ]
            for pattern in patterns:
                if re.search(pattern, text_upper):
                    return asset
        
        # Special case: GOLD -> XAUUSD
        if 'GOLD' in text_upper:
            return 'XAUUSD'
        
        return None
    
    def _extract_direction(self, text: str) -> Optional[str]:
        """Extract BUY/SELL direction"""
        text_upper = text.upper()
        
        # Look for direction keywords
        if re.search(r'\bSELL\b', text_upper) or 'SHORT' in text_upper:
            return 'SELL'
        if re.search(r'\bBUY\b', text_upper) or 'LONG' in text_upper:
            return 'BUY'
        
        return None
    
    def _extract_numbers(self, text: str) -> List[float]:
        """Extract all numbers from text"""
        # Match decimal numbers
        numbers = re.findall(r'\d+\.?\d*', text)
        return [float(n) for n in numbers if float(n) > 1]
    
    def _parse_simple_price_after_pair(self, text: str, text_upper: str) -> Optional[Dict]:
        """
        Format: BUY XAUUSD 4653.0
                SELL GBPUSD 1.27500
        """
        pair = self._extract_pair(text)
        direction = self._extract_direction(text)
        
        if not pair or not direction:
            return None
        
        # Look for number immediately after pair
        pattern = rf'{pair}\s+(\d+\.?\d*)'
        match = re.search(pattern, text_upper)
        
        if match:
            entry = match.group(1)
            
            # Extract SL - look for SL: pattern
            sl_match = re.search(r'SL[\s:]*(\d+\.?\d*)', text_upper)
            sl = sl_match.group(1) if sl_match else None
            
            # Extract TPs
            tps = self._extract_tps(text_upper)
            
            return {
                "valid": all([pair, direction, entry, sl]),
                "pair": pair,
                "direction": direction,
                "entry": entry,
                "stop_loss": sl,
                "take_profits": tps,
                "format": "simple_price_after_pair",
                "raw": text[:200]
            }
        
        return None
    
    def _parse_limit_order_with_at(self, text: str, text_upper: str) -> Optional[Dict]:
        """
        Format: 🔴** Sell Limit XAUUSD @ 4721
                🔴 Sell BTCUSD @ 68000
        """
        pair = self._extract_pair(text)
        direction = self._extract_direction(text)
        
        if not pair or not direction:
            return None
        
        # Look for @ price pattern
        at_match = re.search(r'@\s*(\d+\.?\d*)', text_upper)
        if at_match:
            entry = at_match.group(1)
            
            # Also check for price in parentheses like (__4720.75__)
            paren_match = None  # Disabled - use @ price instead
            # paren_match = re.search(r'\(\s*_*(\d+\.?\d*)_*\s*\)', text)
            # Using @ price as entry (limit order price)
            
            # Extract SL
            sl = self._extract_sl(text_upper)
            tps = self._extract_tps(text_upper)
            
            return {
                "valid": all([pair, direction, entry, sl]),
                "pair": pair,
                "direction": direction,
                "entry": entry,
                "stop_loss": sl,
                "take_profits": tps,
                "format": "limit_order_with_at",
                "raw": text[:200]
            }
        
        return None
    
    def _parse_detailed_emoji_format(self, text: str, text_upper: str) -> Optional[Dict]:
        """
        Format: 🚨 SIGNAL ALERT 🚨
                🌐 #EURCAD
                📈 #BUY
                ⚪️ Entry Point: 1.57680
        """
        if 'SIGNAL ALERT' not in text_upper:
            return None
        
        pair = self._extract_pair(text)
        direction = self._extract_direction(text)
        
        if not pair:
            return None
        
        # Look for Entry Point pattern
        entry_match = re.search(r'ENTRY[\s\w]*[:\s]+(\d+\.?\d*)', text_upper)
        if not entry_match:
            # Try alternative patterns
            entry_match = re.search(r'⚪[\s\w]*[:\s]+(\d+\.?\d*)', text)
        
        if entry_match:
            entry = entry_match.group(1)
            sl = self._extract_sl(text_upper)
            tps = self._extract_tps(text_upper)
            
            return {
                "valid": all([pair, direction, entry, sl]),
                "pair": pair,
                "direction": direction or "BUY",  # Default to BUY if not found
                "entry": entry,
                "stop_loss": sl,
                "take_profits": tps,
                "format": "detailed_emoji",
                "raw": text[:200]
            }
        
        return None
    
    def _parse_gbpjpy_format(self, text: str, text_upper: str) -> Optional[Dict]:
        """
        Format: 🇬🇧🇯🇵 GBPJPY 🔵 BUY
                📊 Entry Zone: 192.500 - 192.800
        """
        # Check for flag emojis pattern
        if not re.search(r'🇬🇧|🇯🇵|🇪🇺|🇺🇸', text):
            return None
        
        pair = self._extract_pair(text)
        direction = self._extract_direction(text)
        
        if not pair:
            return None
        
        # Look for Entry Zone
        zone_match = re.search(r'ENTRY[\s\w]*[:\s]+(\d+\.?\d*)', text_upper)
        if zone_match:
            entry = zone_match.group(1)
            sl = self._extract_sl(text_upper)
            tps = self._extract_tps(text_upper)
            
            return {
                "valid": all([pair, direction, entry, sl]),
                "pair": pair,
                "direction": direction,
                "entry": entry,
                "stop_loss": sl,
                "take_profits": tps,
                "format": "gbpjpy_emoji",
                "raw": text[:200]
            }
        
        return None
    
    def _parse_signal_alert_hashtag(self, text: str, text_upper: str) -> Optional[Dict]:
        """
        Format: 🚨 SIGNAL ALERT
                #GBPUSD #SELL
                Entry: 1.27500
        """
        if 'SIGNAL ALERT' not in text_upper:
            return None
        
        pair = self._extract_pair(text)
        direction = self._extract_direction(text)
        
        if not pair or not direction:
            return None
        
        # Look for Entry: pattern
        entry_match = re.search(r'ENTRY[\s:]*(\d+\.?\d*)', text_upper)
        if entry_match:
            entry = entry_match.group(1)
            sl = self._extract_sl(text_upper)
            tps = self._extract_tps(text_upper)
            
            return {
                "valid": all([pair, direction, entry, sl]),
                "pair": pair,
                "direction": direction,
                "entry": entry,
                "stop_loss": sl,
                "take_profits": tps,
                "format": "signal_alert_hashtag",
                "raw": text[:200]
            }
        
        return None
    
    def _parse_buy_now_format(self, text: str, text_upper: str) -> Optional[Dict]:
        """
        Format: BUY NOW 1.33770
                Set TP1 +15 Pips
                (No SL provided - need to calculate)
        """
        if 'BUY NOW' not in text_upper and 'SELL NOW' not in text_upper:
            return None
        
        pair = self._extract_pair(text)
        direction = self._extract_direction(text)
        
        if not pair or not direction:
            return None
        
        # Extract entry price (number after BUY NOW / SELL NOW)
        entry_match = re.search(r'(?:BUY|SELL)\s+NOW\s+(\d+\.?\d*)', text_upper)
        if not entry_match:
            return None
        
        entry = entry_match.group(1)
        entry_float = float(entry)
        
        # Extract relative TP (+15 pips, +30 pips, etc.)
        tp_relative_match = re.search(r'(?:TP|TAKE PROFIT)\s*#?\s*1?\s*\+?\s*(\d+)\s*PIPS?', text_upper)
        tp_pips = int(tp_relative_match.group(1)) if tp_relative_match else 15  # default 15
        
        # Calculate TP based on direction
        pip_size = 0.0001  # Default for most pairs
        if 'JPY' in pair or 'XAU' in pair or 'GOLD' in pair:
            pip_size = 0.01
        
        if direction == 'BUY':
            tp1 = f"{entry_float + (tp_pips * pip_size):.5f}"
            # Default SL: 20 pips below entry if not specified
            sl = f"{entry_float - (20 * pip_size):.5f}"
        else:  # SELL
            tp1 = f"{entry_float - (tp_pips * pip_size):.5f}"
            # Default SL: 20 pips above entry if not specified
            sl = f"{entry_float + (20 * pip_size):.5f}"
        
        return {
            "valid": True,
            "pair": pair,
            "direction": direction,
            "entry": entry,
            "stop_loss": sl,
            "take_profits": [tp1],
            "format": "buy_now_relative_tp",
            "raw": text[:200],
            "notes": f"Relative TP (+{tp_pips} pips), SL auto-calculated (-20 pips)"
        }
    
    def _parse_generic(self, text: str, text_upper: str) -> Dict:
        """Fallback parser - extracts whatever it can find"""
        pair = self._extract_pair(text)
        direction = self._extract_direction(text)
        numbers = self._extract_numbers(text)
        
        # Filter out small numbers (< 10) which are likely pip counts, not prices
        price_numbers = [n for n in numbers if n > 10]
        
        # Smart assignment based on direction
        entry = None
        sl = None
        tps = []
        
        if len(price_numbers) >= 2 and direction:
            sorted_nums = sorted(price_numbers)
            
            if direction == "BUY":
                # For BUY: lowest is SL, entry is middle or first, highest is TP
                sl = str(sorted_nums[0])
                entry = str(sorted_nums[len(sorted_nums)//2])
                if len(sorted_nums) > 2:
                    tps = [str(n) for n in sorted_nums[2:5]]
            else:  # SELL
                # For SELL: highest is SL, entry is middle or first, lowest is TP
                sl = str(sorted_nums[-1])
                entry = str(sorted_nums[len(sorted_nums)//2])
                if len(sorted_nums) > 2:
                    tps = [str(n) for n in sorted_nums[:2]]
        
        return {
            "valid": all([pair, direction, entry, sl]),
            "pair": pair,
            "direction": direction,
            "entry": entry,
            "stop_loss": sl,
            "take_profits": tps[:3],
            "format": "generic_fallback",
            "raw": text[:200],
            "notes": "Used generic parser - results may be approximate"
        }
    
    def _extract_sl(self, text_upper: str) -> Optional[str]:
        """Extract stop loss from text"""
        patterns = [
            r'SL[\s:]*(\d+\.?\d*)',
            r'STOP[\s\w]*[:\s]+(\d+\.?\d*)',
            r'🔴[\s\w]*[:\s]+(\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text_upper)
            if match:
                return match.group(1)
        return None
    
    def _extract_tps(self, text_upper: str) -> List[str]:
        """Extract take profits from text"""
        tps = []
        
        # Pattern 1: TP1, TP #1, etc.
        for i in range(1, 4):
            patterns = [
                rf'TP\s*#?\s*{i}[\s:]*(\d+\.?\d*)',
                rf'TP{i}[\s:]*(\d+\.?\d*)',
                rf'TAKE[\s\w]*{i}[\s:]*(\d+\.?\d*)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text_upper)
                if match:
                    tps.append(match.group(1))
                    break
        
        # Pattern 2: 🤑 or 🎯 emoji patterns
        if not tps:
            emoji_matches = re.findall(r'[🤑🎯][\s\w]*[:\s]+(\d+\.?\d*)', text_upper)
            tps = emoji_matches[:3]
        
        return tps
    
    def test(self):
        """Run tests on training examples"""
        print("=" * 60)
        print("FELIX AI PARSER - TRAINING TESTS")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for i, example in enumerate(self.training_examples, 1):
            result = self.parse(example["text"])
            expected = example["expected"]
            
            success = (
                result.get("pair") == expected["pair"] and
                result.get("direction") == expected["direction"] and
                result.get("entry") == expected["entry"] and
                result.get("stop_loss") == expected["sl"]
            )
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"\nTest {i}: {status}")
            print(f"  Format: {result.get('format', 'unknown')}")
            print(f"  Pair: {result.get('pair')} (expected: {expected['pair']})")
            print(f"  Direction: {result.get('direction')} (expected: {expected['direction']})")
            print(f"  Entry: {result.get('entry')} (expected: {expected['entry']})")
            print(f"  SL: {result.get('stop_loss')} (expected: {expected['sl']})")
            
            if success:
                passed += 1
            else:
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"Results: {passed}/{len(self.training_examples)} passed")
        print("=" * 60)
        
        return passed == len(self.training_examples)


# Standalone function for use in supervisor
def ai_parse_signal_trained(raw_text: str) -> Dict:
    """Standalone function for the supervisor"""
    parser = FelixAITrainedParser()
    return parser.parse(raw_text)


if __name__ == "__main__":
    parser = FelixAITrainedParser()
    parser.test()
