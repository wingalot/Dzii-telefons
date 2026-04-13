#!/usr/bin/env python3
"""
FELIX SMART PARSER - Enhanced with contextual understanding
Combines regex patterns with smart fallback logic
"""

import re
import json
from typing import Dict, List, Optional

class SmartSignalParser:
    """
    Smart parser that uses multiple strategies:
    1. Pattern matching for known formats
    2. Contextual analysis for unknown formats
    3. Historical signal matching as fallback
    """
    
    def __init__(self):
        self.pair_keywords = {
            'EURUSD': ['eurusd', 'eur/usd', '#eurusd'],
            'GBPUSD': ['gbpusd', 'gbp/usd', '#gbpusd'],
            'USDJPY': ['usdjpy', 'usd/jpy', '#usdjpy'],
            'XAUUSD': ['xauusd', 'gold', 'xau/usd', '#xauusd', '#gold'],
            'BTCUSD': ['btcusd', 'bitcoin', 'btc/usd', '#btcusd'],
            'AUDUSD': ['audusd', 'aud/usd', '#audusd'],
            'USDCAD': ['usdcad', 'usd/cad', '#usdcad'],
            'EURJPY': ['eurjpy', 'eur/jpy', '#eurjpy'],
            'GBPJPY': ['gbpjpy', 'gbp/jpy', '#gbpjpy'],
            'CADJPY': ['cadjpy', 'cad/jpy', '#cadjpy'],
            'NZDJPY': ['nzdjpy', 'nzd/jpy', '#nzdjpy'],
            'AUDJPY': ['audjpy', 'aud/jpy', '#audjpy'],
            'EURAUD': ['euraud', 'eur/aud', '#euraud'],
            'EURCAD': ['eurcad', 'eur/cad', '#eurcad'],
            'GBPCAD': ['gbpcad', 'gbp/cad', '#gbpcad'],
            'GBPAUD': ['gbpaud', 'gbp/aud', '#gbpaud'],
            'AUDNZD': ['audnzd', 'aud/nzd', '#audnzd'],
            'NZDCAD': ['nzdcad', 'nzd/cad', '#nzdcad'],
            'EURGBP': ['eurgbp', 'eur/gbp', '#eurgbp'],
            'USDCHF': ['usdchf', 'usd/chf', '#usdchf'],
            'NZDUSD': ['nzdusd', 'nzd/usd', '#nzdusd'],
            'CHFJPY': ['chfjpy', 'chf/jpy', '#chfjpy'],
            'US30': ['us30', 'us 30', '#us30', 'dow'],
            'NAS100': ['nas100', 'nas 100', '#nas100', 'nasdaq'],
        }
    
    def parse(self, text: str) -> Dict:
        """Main parsing method with multiple strategies"""
        if not text or not text.strip():
            return {"valid": False, "error": "empty_text"}
        
        text_clean = self._clean_text(text)
        text_upper = text_clean.upper()
        
        # Strategy 1: Pattern matching for known formats
        result = self._parse_known_formats(text_clean, text_upper)
        if result.get('valid') and result.get('sl'):
            return result
        
        # Strategy 2: Contextual extraction for unknown formats
        result = self._parse_contextual(text_clean, text_upper)
        if result.get('valid') and result.get('sl'):
            return result
        
        # Strategy 3: Best effort extraction
        return self._parse_best_effort(text_clean, text_upper)
    
    def _clean_text(self, text: str) -> str:
        """Clean text for parsing"""
        # Remove markdown bold markers
        text = text.replace('**', ' ').replace('__', ' ')
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def _parse_known_formats(self, text: str, text_upper: str) -> Dict:
        """Parse known signal formats"""
        pair = self._extract_pair(text_upper)
        direction = self._extract_direction(text_upper)
        
        if not pair or not direction:
            return {"valid": False}
        
        # Try emoji format first
        entry = self._extract_emoji_entry(text, text_upper)
        sl = self._extract_emoji_sl(text, text_upper, entry)
        tps = self._extract_emoji_tp(text, text_upper, entry)
        
        if entry and sl:
            return {
                "valid": True,
                "pair": pair,
                "direction": direction,
                "entry": entry,
                "sl": sl,
                "tp_levels": tps,
                "format": "emoji"
            }
        
        # Try standard format
        entry = self._extract_standard_entry(text, text_upper, pair)
        sl = self._extract_standard_sl(text, text_upper)
        tps = self._extract_standard_tp(text, text_upper)
        
        # Handle BUY NOW/SELL NOW with relative TP
        if not sl and entry and 'NOW' in text_upper:
            sl, tps = self._handle_buy_now_format(text, text_upper, pair, direction, entry)
        
        return {
            "valid": all([pair, direction, entry]),
            "pair": pair,
            "direction": direction,
            "entry": entry,
            "sl": sl,
            "tp_levels": tps,
            "format": "standard"
        }
    
    def _parse_contextual(self, text: str, text_upper: str) -> Dict:
        """Parse using contextual understanding"""
        pair = self._extract_pair(text_upper)
        direction = self._extract_direction(text_upper)
        
        if not pair or not direction:
            return {"valid": False}
        
        # Find all numbers in text
        numbers = self._extract_all_numbers(text)
        if len(numbers) < 2:
            return {"valid": False}
        
        # Sort numbers
        sorted_nums = sorted(numbers)
        
        # Based on direction, infer which numbers are what
        if direction == "BUY":
            # For BUY: lowest is likely SL, middle is entry, highest is TP
            sl = sorted_nums[0]
            entry = sorted_nums[len(sorted_nums)//2]
            tps = sorted_nums[len(sorted_nums)//2 + 1:len(sorted_nums)//2 + 4]
        else:  # SELL
            # For SELL: highest is likely SL, middle is entry, lowest is TP
            sl = sorted_nums[-1]
            entry = sorted_nums[len(sorted_nums)//2]
            tps = sorted_nums[:3]
        
        # Validate distances make sense
        if self._validate_signal_logic(entry, sl, tps, direction):
            return {
                "valid": True,
                "pair": pair,
                "direction": direction,
                "entry": entry,
                "sl": sl,
                "tp_levels": tps,
                "format": "contextual",
                "note": "inferred_from_context"
            }
        
        return {"valid": False}
    
    def _parse_best_effort(self, text: str, text_upper: str) -> Dict:
        """Best effort extraction - return whatever we can find"""
        pair = self._extract_pair(text_upper)
        direction = self._extract_direction(text_upper)
        numbers = self._extract_all_numbers(text)
        
        return {
            "valid": all([pair, direction]),
            "pair": pair,
            "direction": direction,
            "entry": numbers[0] if numbers else None,
            "sl": numbers[1] if len(numbers) > 1 else None,
            "tp_levels": numbers[2:5] if len(numbers) > 2 else [],
            "format": "best_effort",
            "all_numbers": numbers,
            "note": "partial_extraction"
        }
    
    def _extract_pair(self, text_upper: str) -> Optional[str]:
        """Extract currency pair"""
        for pair, keywords in self.pair_keywords.items():
            for kw in keywords:
                if kw.upper() in text_upper:
                    return pair
        return None
    
    def _extract_direction(self, text_upper: str) -> Optional[str]:
        """Extract BUY/SELL direction"""
        if re.search(r'\bBUY\b|\bLONG\b', text_upper):
            return "BUY"
        if re.search(r'\bSELL\b|\bSHORT\b', text_upper):
            return "SELL"
        return None
    
    def _extract_emoji_entry(self, text: str, text_upper: str) -> Optional[float]:
        """Extract entry from emoji format"""
        patterns = [
            r'⚪[\s\w]*ENTRY[\s\w]*POINT[\s\w]*[:\s]+(\d+\.?\d*)',
            r'⚪[\s\w]*POINT[\s\w]*[:\s]+(\d+\.?\d*)',
            r'ENTRY[\s\w]*POINT[\s\w]*[:\s]+(\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text_upper)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        return None
    
    def _extract_emoji_sl(self, text: str, text_upper: str, entry: float = None) -> Optional[float]:
        """Extract SL from emoji format"""
        # Match 🔴 followed by any text and then a number
        match = re.search(r'🔴[^\n]*?[:\s]+(\d+\.?\d*)', text)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
        return None
    
    def _extract_emoji_tp(self, text: str, text_upper: str, entry: float = None) -> List[float]:
        """Extract TP levels from emoji format"""
        tps = []
        # Match 🟢 followed by any text and then a decimal number
        matches = re.findall(r'🟢[^\n]*?[:\s]+(\d{1,3}\.\d{2,})', text)
        for m in matches:
            try:
                tps.append(float(m))
            except:
                pass
        
        # Also try plain text TP format: TP #1: 4552
        if not tps:
            for i in range(1, 4):
                match = re.search(rf'TP\s*#?\s*{i}[\s:]*(__)?(\d+\.?\d*)', text_upper)
                if match:
                    try:
                        tps.append(float(match.group(2)))
                    except:
                        pass
        
        return tps[:3]  # Max 3 TPs
    
    def _extract_standard_entry(self, text: str, text_upper: str, pair: str) -> Optional[float]:
        """Extract entry from standard format"""
        # Pattern: BUY XAUUSD 4533.8
        match = re.search(rf'{pair}[\s:]+(\d+\.?\d*)', text_upper)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
        
        # Pattern: BUY NOW 4533
        match = re.search(r'(?:BUY|SELL)\s+NOW\s+(\d+\.?\d*)', text_upper)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
        
        return None
    
    def _extract_standard_sl(self, text: str, text_upper: str) -> Optional[float]:
        """Extract SL from standard format"""
        patterns = [
            r'SL[\s:]*(?:\(SL\))?[\s:]*(\d+\.?\d*)',
            r'STOP[\s\w]*LOSS[\s:]*(\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text_upper)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        return None
    
    def _extract_standard_tp(self, text: str, text_upper: str) -> List[float]:
        """Extract TP from standard format"""
        tps = []
        # Match TP1, TP2, TP3
        for i in range(1, 4):
            match = re.search(rf'TP\s*#?\s*{i}[\s:]*(\d+\.?\d*)', text_upper)
            if match:
                try:
                    tps.append(float(match.group(1)))
                except:
                    pass
        return tps
    
    def _handle_buy_now_format(self, text: str, text_upper: str, pair: str, direction: str, entry: float):
        """Handle BUY NOW/SELL NOW format with relative TP (+15 pips)"""
        # Check for relative TP (+15 Pips, +30 Pips, etc.)
        tp_match = re.search(r'(?:SET\s+)?TP\d*\s*\+(\d+)\s*PIPS?', text_upper)
        if not tp_match:
            return None, []
        
        tp_pips = int(tp_match.group(1))
        
        # Determine pip size based on pair and entry price
        if 'JPY' in pair or entry > 50:
            pip_size = 0.01  # JPY pairs, Gold, indices
        else:
            pip_size = 0.0001  # Standard forex pairs
        
        # Calculate TP
        if direction == "BUY":
            tp = entry + (tp_pips * pip_size)
            # Default SL: 20 pips below entry
            sl = entry - (20 * pip_size)
        else:  # SELL
            tp = entry - (tp_pips * pip_size)
            # Default SL: 20 pips above entry
            sl = entry + (20 * pip_size)
        
        return sl, [tp]
    
    def _extract_all_numbers(self, text: str) -> List[float]:
        """Extract all numbers from text"""
        numbers = []
        # Find decimal numbers
        matches = re.findall(r'\d+\.\d+', text)
        for m in matches:
            try:
                n = float(m)
                if n > 1:  # Filter out small numbers
                    numbers.append(n)
            except:
                pass
        return sorted(list(set(numbers)))  # Remove duplicates
    
    def _validate_signal_logic(self, entry: float, sl: float, tps: List[float], direction: str) -> bool:
        """Validate that signal makes logical sense"""
        if not entry or not sl:
            return False
        
        # Check SL is on correct side of entry
        if direction == "BUY":
            if sl >= entry:
                return False
            for tp in tps:
                if tp <= entry:
                    return False
        else:  # SELL
            if sl <= entry:
                return False
            for tp in tps:
                if tp >= entry:
                    return False
        
        # Check distances are reasonable (not too far, not too close)
        sl_distance = abs(entry - sl) / entry
        if sl_distance < 0.001 or sl_distance > 0.05:  # 0.1% to 5%
            return False
        
        return True


# Convenience function
def smart_parse_signal(raw_text: str) -> Dict:
    """Parse signal using smart parser"""
    parser = SmartSignalParser()
    return parser.parse(raw_text)


# Test
if __name__ == "__main__":
    parser = SmartSignalParser()
    
    test_cases = [
        "**🚨 SIGNAL ALERT 🚨**\n\n**🌐 #EURUSD**\n\n**📊 Trade Details:**📈**#BUY**\n\n**⚪️ Entry Point:** **1.15580**\n**🔴 Stop Loss (SL): **1.15230\n\n**🟢 Take Profit 1 (TP1):** 1.15730\n**🟢 Take Profit 2 (TP2):** 1.16190\n**🟢 Take Profit 3 (TP3): **1.16720",
        "XAUUSD BUY NOW 4450\nSet TP1 +30 Pips",
        "Quick setup: Buy GBPUSD at 1.3200, stop 1.3150, target 1.3300",
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n=== Test {i} ===")
        result = parser.parse(text)
        print(f"Valid: {result.get('valid')}")
        print(f"Format: {result.get('format')}")
        print(f"Pair: {result.get('pair')} {result.get('direction')}")
        print(f"Entry: {result.get('entry')}, SL: {result.get('sl')}")
        print(f"TPs: {result.get('tp_levels')}")
        if result.get('note'):
            print(f"Note: {result.get('note')}")
