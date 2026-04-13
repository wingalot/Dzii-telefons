#!/usr/bin/env python3
"""
FELIX LLM PARSER - Fallback for complex signal formats
Uses LLM to extract trading signal data when regex fails
"""

import json
import os
from typing import Dict, Optional

def parse_signal_with_llm(raw_text: str) -> Dict:
    """
    Use LLM to parse trading signal from text.
    Returns structured data or empty dict if parsing fails.
    """
    
    # System prompt for signal extraction
    system_prompt = """You are a trading signal parser. Extract the following from the message:
- pair: Currency pair (EURUSD, GBPUSD, XAUUSD, etc.)
- direction: BUY or SELL
- entry: Entry price (number)
- stop_loss: Stop loss price (number)  
- take_profits: List of take profit levels [tp1, tp2, tp3]

Return ONLY a JSON object in this exact format:
{
  "pair": "EURUSD",
  "direction": "BUY", 
  "entry": 1.1558,
  "stop_loss": 1.1523,
  "take_profits": [1.1573, 1.1619, 1.1672],
  "valid": true
}

If any field is missing, use null. If the message is not a trading signal, return {"valid": false}.
Be precise with numbers - extract exact values from the text."""

    user_prompt = f"Parse this trading signal:\n\n{raw_text}"
    
    try:
        # Call LLM via OpenClaw's model
        result = call_llm(system_prompt, user_prompt)
        
        # Parse JSON response
        parsed = json.loads(result)
        
        # Validate required fields
        if not parsed.get('valid'):
            return {"valid": False, "error": "not_a_signal"}
            
        # Ensure all fields exist
        return {
            "valid": True,
            "pair": parsed.get('pair'),
            "direction": parsed.get('direction'),
            "entry": parsed.get('entry'),
            "stop_loss": parsed.get('stop_loss'),
            "take_profits": parsed.get('take_profits', []),
            "format": "llm_parsed",
            "raw": raw_text[:200]
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Call LLM using available method.
    Tries multiple approaches in order of preference.
    """
    
    # Method 1: Try using sessions_spawn with subagent (if available)
    try:
        return call_via_subagent(system_prompt, user_prompt)
    except:
        pass
    
    # Method 2: Try using local model via ollama/llm CLI
    try:
        return call_via_cli(system_prompt, user_prompt)
    except:
        pass
    
    # Method 3: Return empty (will fall back to regex)
    raise Exception("No LLM available")


def call_via_subagent(system_prompt: str, user_prompt: str) -> str:
    """Call LLM via OpenClaw subagent"""
    import subprocess
    import tempfile
    
    # Create prompt file
    full_prompt = f"{system_prompt}\n\n{user_prompt}\n\nReturn ONLY the JSON object, nothing else."
    
    # Use a simple approach - write to temp file and read result
    # This is a placeholder - actual implementation depends on OpenClaw setup
    raise Exception("Subagent not configured")


def call_via_cli(system_prompt: str, user_prompt: str) -> str:
    """Call LLM via command line tool"""
    import subprocess
    import tempfile
    import os
    
    # Create temp files for input/output
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(f"{system_prompt}\n\n{user_prompt}\n\nReturn ONLY the JSON object.")
        prompt_file = f.name
    
    try:
        # Try different LLM CLI tools
        
        # Option 1: ollama
        try:
            result = subprocess.run(
                ['ollama', 'run', 'llama3.2', f'@{prompt_file}'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # Option 2: llm (Simon Willison's tool)
        try:
            result = subprocess.run(
                ['llm', 'prompt', '-s', system_prompt, user_prompt],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
            
        raise Exception("No LLM CLI tool available")
        
    finally:
        os.unlink(prompt_file)


# Integration with SignalHub
def llm_parse_fallback(raw_text: str, regex_result: Dict) -> Dict:
    """
    Use as fallback when regex parsing fails or returns incomplete data.
    """
    # Check if regex result is valid and complete
    if regex_result.get('valid') and regex_result.get('pair') and regex_result.get('stop_loss'):
        return regex_result  # Regex worked, use it
    
    # Try LLM parsing
    llm_result = parse_signal_with_llm(raw_text)
    
    if llm_result.get('valid'):
        return llm_result
    
    # Both failed, return regex result (might be partial)
    return regex_result


# Test function
def test_llm_parser():
    """Test the LLM parser with sample signals"""
    test_signals = [
        # Complex emoji format
        "🚨 SIGNAL ALERT 🚨\n\n🌐 #EURUSD\n\n📊 Trade Details:📈#BUY\n\n⚪️ Entry Point: 1.15580\n🔴 Stop Loss (SL): 1.15230\n\n🟢 Take Profit 1 (TP1): 1.15730\n🟢 Take Profit 2 (TP2): 1.16190\n🟢 Take Profit 3 (TP3): 1.16720",
        
        # Non-standard format
        "Quick trade setup:\nPair: GBPUSD\nSide: Long\nEntry around 1.3200\nStop: 1.3150\nTarget: 1.3300",
        
        # Voice transcription style
        "Buy gold at 1950, stop loss 1940, take profit 1960 and 1970"
    ]
    
    print("=" * 60)
    print("LLM PARSER TEST")
    print("=" * 60)
    
    for i, text in enumerate(test_signals, 1):
        print(f"\nTest {i}:")
        print(f"Input: {text[:80]}...")
        
        result = parse_signal_with_llm(text)
        
        if result.get('valid'):
            print(f"✅ Parsed: {result['pair']} {result['direction']}")
            print(f"   Entry: {result['entry']}, SL: {result['stop_loss']}")
            print(f"   TPs: {result['take_profits']}")
        else:
            print(f"❌ Failed: {result.get('error', 'unknown')}")


if __name__ == "__main__":
    test_llm_parser()
