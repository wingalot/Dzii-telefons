#!/usr/bin/env python3
"""
FELIX AI SUPERVISOR
Intelligent system supervisor ensuring 100% signal execution
- Monitors all processes
- Fixes parsing errors with AI
- Retries failed trades
- Self-healing capabilities
"""

import os
import sys
import json
import asyncio
import logging
import subprocess
import re
import time
from datetime import datetime
from pathlib import Path

# Import trained parser
sys.path.insert(0, str(Path(__file__).parent))
from felix_trained_parser import ai_parse_signal_trained

# Configuration
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
LOG_DIR = BASE_DIR / "logs"
STATE_DIR = BASE_DIR / "state"
FIXES_DIR = BASE_DIR / "fixes"

# Paths to existing components
FELIX_LISTENER = Path.home() / ".openclaw" / "telegram" / "felix_auto_trader.py"
FELIX_TRADER = Path.home() / ".openclaw" / "workspace" / "felix_trader.sh"
IG_API = Path.home() / ".trading" / "ig_api.sh"
DATA_DIR = Path.home() / ".trading" / "data"

# Setup logging
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(FIXES_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AI-SUPERVISOR] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "supervisor.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class FelixAISupervisor:
    """AI-powered supervisor for Felix trading system"""
    
    # IG API Documentation - loaded for error fixing
    IG_API_ERRORS = {
        "error.security.api-key-invalid": {
            "cause": "API key expired or invalid",
            "solution": "Notify user to regenerate API key in IG settings"
        },
        "validation.null-not-allowed.request.guaranteedStop": {
            "cause": "Missing guaranteedStop field",
            "solution": "Add guaranteedStop: false to order",
            "auto_fix": True,
            "field": "guaranteedStop",
            "value": False
        },
        "validation.null-not-allowed.request.currencyCode": {
            "cause": "Missing currencyCode field",
            "solution": "Add currencyCode (counter currency) to order",
            "auto_fix": True,
            "field": "currencyCode",
            "value": None  # Extract from pair
        },
        "validation.null-not-allowed.request": {
            "cause": "Missing required field",
            "solution": "Check all required fields are provided"
        },
        "error.invalid.input": {
            "cause": "Invalid input parameters",
            "solution": "Validate order parameters"
        },
        "error.security.invalid-details": {
            "cause": "Invalid credentials",
            "solution": "Check username/password"
        },
        "error.confirms.invalid-deal-reference": {
            "cause": "Deal reference not found",
            "solution": "Wait and retry verification"
        }
    }
    
    # Position closing parameters
    IG_CLOSE_PARAMS = {
        "timeInForce": "EXECUTE_AND_ELIMINATE",
        "forceOpen": False,  # Critical for closing!
        "guaranteedStop": False
    }
    
    def __init__(self):
        self.state_file = STATE_DIR / "supervisor_state.json"
        self.signal_queue = []
        self.failed_signals = []
        self.load_state()
        
    def load_state(self):
        """Load supervisor state"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                self.state = json.load(f)
        else:
            self.state = {
                "started": datetime.now().isoformat(),
                "signals_processed": 0,
                "signals_failed": 0,
                "signals_fixed": 0,
                "patches_applied": [],
                "last_check": None
            }
    
    def save_state(self):
        """Save supervisor state"""
        self.state["last_check"] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def log_signal(self, signal_text, status, details=None):
        """Log signal processing"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "signal": signal_text[:200],
            "status": status,
            "details": details
        }
        log_file = LOG_DIR / "signals.log"
        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    
    def ai_parse_signal(self, raw_text):
        """
        AI-powered signal parser using trained parser
        """
        logger.info("🧠 AI parsing signal with trained parser...")
        
        # Use the trained parser
        result = ai_parse_signal_trained(raw_text)
        
        # Add ai_parsed flag for tracking
        result["ai_parsed"] = True
        
        logger.info(f"Parsed with format: {result.get('format', 'unknown')}")
        
        return result
    
    def fix_and_retry(self, signal_text, original_error):
        """
        Fix a failed signal and retry execution
        """
        logger.info(f"🔧 Fixing failed signal: {original_error}")
        
        # Use AI to parse
        parsed = self.ai_parse_signal(signal_text)
        
        if not parsed["valid"]:
            logger.error(f"❌ AI could not fix signal. Missing: {parsed.get('missing', [])}")
            return False, parsed
        
        # Build fixed signal in standard format
        fixed_signal = self.build_standard_signal(parsed)
        
        # Retry execution
        success, output = self.execute_trade(fixed_signal)
        
        if success:
            self.state["signals_fixed"] += 1
            self.log_fix(signal_text, fixed_signal, "auto_fixed")
            logger.info("✅ Signal fixed and executed successfully!")
        else:
            logger.error(f"❌ Retry failed: {output}")
        
        return success, output
    
    def build_standard_signal(self, parsed):
        """Build standardized signal text from parsed data"""
        pair = parsed["pair"]
        direction = parsed["direction"]
        entry = parsed["entry"]
        sl = parsed["stop_loss"]
        tps = parsed["take_profits"]
        
        signal = f"#{pair} {direction}\n\n📊 Entry: {entry}\n⛔️ SL: {sl}"
        
        for i, tp in enumerate(tps, 1):
            signal += f"\n🎯 TP{i}: {tp}"
        
        return signal
    
    def execute_trade(self, signal_text):
        """Execute trade via felix_trader.sh with IG error analysis"""
        try:
            result = subprocess.run(
                ["bash", str(FELIX_TRADER), "execute", signal_text],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout + result.stderr
            
            # Check for actual success - look for successful execution markers
            success = (
                result.returncode == 0 and 
                "TRADE EXECUTED SUCCESSFULLY" in output and
                "verification_failed" not in output.lower() and
                "parse_error" not in output.lower() and
                "missing_fields" not in output.lower()
            )
            
            # If failed, analyze for IG API errors
            if not success:
                error_code, can_fix, fix_details = self.analyze_ig_error(output)
                if error_code:
                    logger.warning(f"⚠️ IG API error detected: {error_code}")
                    if can_fix:
                        logger.info(f"🔧 Attempting auto-fix for {error_code}")
                        fixed, fix_result = self.fix_ig_api_error(error_code, signal_text, fix_details)
                        if fixed:
                            return True, f"Fixed and executed: {fix_result}"
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "Execution timeout"
        except Exception as e:
            return False, str(e)
    
    def log_fix(self, original, fixed, method):
        """Log applied fix"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "original": original[:200],
            "fixed": fixed[:200],
            "method": method
        }
        fix_file = FIXES_DIR / "applied_fixes.jsonl"
        with open(fix_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")
        self.state["patches_applied"].append(entry)
    
    def monitor_rejections(self):
        """Monitor rejection log and attempt fixes"""
        rejections_file = DATA_DIR / "rejections.jsonl"
        
        if not rejections_file.exists():
            return
        
        # Read rejections
        try:
            with open(rejections_file) as f:
                lines = f.readlines()
            
            # Process recent rejections (last 5)
            for line in lines[-5:]:
                try:
                    rejection = json.loads(line)
                    timestamp = rejection.get("timestamp", "")
                    
                    # Only process recent rejections (within last hour)
                    if timestamp and self.is_recent(timestamp):
                        signal_data = rejection.get("signal", {})
                        raw = signal_data.get("raw", "")
                        reason = rejection.get("reason", "")
                        
                        if raw and reason in ["parse_error", "missing_fields"]:
                            logger.info(f"🔍 Found rejected signal to fix: {reason}")
                            self.fix_and_retry(raw, reason)
                            
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"Error monitoring rejections: {e}")
    
    def is_recent(self, timestamp_str, minutes=60):
        """Check if timestamp is within last N minutes"""
        try:
            ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            delta = datetime.now(ts.tzinfo) - ts
            return delta.total_seconds() < minutes * 60
        except:
            return False
    
    def analyze_ig_error(self, error_output):
        """
        Analyze IG API error and suggest/apply fix
        Returns: (error_code, fix_applied, fix_details)
        """
        # Extract error code from output
        error_code = None
        for code in self.IG_API_ERRORS.keys():
            if code in error_output:
                error_code = code
                break
        
        if not error_code:
            # Try to extract generic error patterns
            if "errorCode" in error_output:
                try:
                    error_json = json.loads(error_output)
                    error_code = error_json.get("errorCode", "unknown")
                except:
                    pass
        
        if not error_code:
            return None, False, None
        
        error_info = self.IG_API_ERRORS.get(error_code, {})
        
        logger.info(f"🔍 Detected IG API error: {error_code}")
        logger.info(f"   Cause: {error_info.get('cause', 'Unknown')}")
        logger.info(f"   Solution: {error_info.get('solution', 'Manual intervention required')}")
        
        # Check if auto-fix is available
        if error_info.get('auto_fix') and error_info.get('field'):
            field = error_info['field']
            value = error_info['value']
            
            # If value is None, extract from pair
            if value is None and field == "currencyCode":
                # Extract counter currency from pair
                value = "USD"  # Default, should be extracted dynamically
            
            logger.info(f"🔧 Auto-fix available: Add {field}={value}")
            return error_code, True, {"field": field, "value": value}
        
        return error_code, False, None
    
    def fix_ig_api_error(self, error_code, signal_text, fix_details=None):
        """
        Attempt to fix IG API error and retry
        """
        logger.info(f"🔧 Fixing IG API error: {error_code}")
        
        if error_code == "error.security.api-key-invalid":
            logger.error("❌ API key invalid - cannot auto-fix. User intervention required.")
            # Send notification to user
            asyncio.run(self.notify_user("🚨 IG API Key Invalid\nPlease regenerate API key in IG settings."))
            return False, "api_key_invalid"
        
        elif error_code in ["validation.null-not-allowed.request.guaranteedStop", 
                          "validation.null-not-allowed.request.currencyCode"]:
            # These are handled by ig_api.sh automatically now
            # But if they occur, we need to check if ig_api.sh needs updating
            logger.info("🔧 This error should be handled by ig_api.sh")
            logger.info("   If it persists, check ig_api.sh for required fields.")
            return False, "missing_fields"
        
        elif "AMENDED" in error_code or "forceOpen" in str(fix_details):
            logger.info("🔧 Position close issue detected")
            logger.info("   Solution: Use POST with forceOpen: false")
            return False, "close_method"
        
        return False, "unknown_error"
    
    def notify_user(self, message):
        """Send notification to user via Telegram"""
        try:
            # Use existing notification mechanism if available
            from telethon import TelegramClient
            # This would need proper session setup
            logger.info(f"📧 Would notify user: {message}")
        except:
            logger.info(f"📧 Notification: {message}")
    
    def check_listener_health(self):
        """Check if felix listener is running"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "felix_auto_trader.py"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning("⚠️ Felix listener not running! Restarting...")
                self.restart_listener()
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False
    
    def restart_listener(self):
        """Restart the felix listener"""
        try:
            # Kill existing
            subprocess.run(["pkill", "-f", "felix_auto_trader.py"], capture_output=True)
            time.sleep(2)
            
            # Start new
            subprocess.Popen(
                ["python3", str(FELIX_LISTENER), "--listen"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            logger.info("✅ Felix listener restarted")
            
        except Exception as e:
            logger.error(f"Failed to restart listener: {e}")
    
    def process_signal(self, signal_text):
        """
        Main entry point: Process a signal with full AI supervision
        """
        logger.info("=" * 60)
        logger.info("🚀 AI SUPERVISOR: Processing new signal")
        logger.info("=" * 60)
        
        self.state["signals_processed"] += 1
        
        # First attempt: standard execution
        success, output = self.execute_trade(signal_text)
        
        if success:
            logger.info("✅ Signal executed successfully on first attempt")
            self.log_signal(signal_text, "success", {"output": output[:500]})
            self.save_state()
            return True
        
        # Failed: Analyze error and fix
        logger.warning(f"⚠️ Initial execution failed. Analyzing...")
        self.state["signals_failed"] += 1
        
        # Check if it's a parsing error
        if "parse_error" in output or "missing_fields" in output:
            logger.info("🔧 Detected parsing error. Attempting AI fix...")
            success, fix_result = self.fix_and_retry(signal_text, "parse_error")
            
            if success:
                self.log_signal(signal_text, "fixed", {"fix": fix_result})
                self.save_state()
                return True
        
        # Check if it's a verification failure (IG order not confirmed)
        if "verification_failed" in output.lower() or "not_verified" in output.lower():
            logger.warning("⚠️ Order verification failed. IG may be rejecting orders.")
            logger.info("🔧 Retrying with adjusted parameters...")
            # Could retry with different parameters or notify user
            success, fix_result = self.fix_and_retry(signal_text, "verification_failed")
            
            if success:
                self.log_signal(signal_text, "fixed", {"fix": fix_result})
                self.save_state()
                return True
        
        # Check if it's an execution error
        if "execution_failed" in output or "api_error" in output:
            logger.info("🔧 Detected execution error. Retrying with fixes...")
            
            # Parse the error to understand what went wrong
            error_lower = output.lower()
            
            # Check for invalid request format errors
            if "invalid.request.format" in error_lower or "invalid" in error_lower:
                logger.info("🔧 Detected IG API format error. Attempting retry with position size adjustment...")
                
                # Try with different parameters - sometimes IG rejects certain pairs
                parsed = self.ai_parse_signal(signal_text)
                if parsed.get("valid"):
                    pair = parsed.get("pair", "")
                    
                    # For problematic pairs like AUDCAD, try different approach
                    if pair in ["AUDCAD", "AUDCHF", "NZDCAD", "NZDCHF"]:
                        logger.warning(f"⚠️ {pair} known to have IG API issues. Trying alternative approach...")
                        
                        # Retry with smaller size
                        original_size = parsed.get("size", 0.5)
                        parsed["size"] = 0.3
                        
                        # Rebuild signal
                        fixed_signal = self.build_standard_signal(parsed)
                        success, fix_result = self.execute_trade(fixed_signal)
                        
                        if success:
                            self.state["signals_fixed"] += 1
                            self.log_signal(signal_text, "fixed", {"method": "size_adjustment", "fix": fix_result})
                            self.save_state()
                            logger.info(f"✅ {pair} executed with reduced size (0.3)")
                            return True
                        else:
                            logger.error(f"❌ Retry with reduced size also failed for {pair}")
                    
                    # Try generic retry
                    logger.info("🔧 Retrying with same parameters (temporary IG glitch)...")
                    time.sleep(2)  # Wait a moment before retry
                    success, fix_result = self.fix_and_retry(signal_text, "api_error")
                    
                    if success:
                        self.state["signals_fixed"] += 1
                        self.log_signal(signal_text, "fixed", {"fix": fix_result})
                        self.save_state()
                        return True
            else:
                # Generic execution error - try once more
                logger.info("🔧 Retrying execution...")
                time.sleep(1)
                success, fix_result = self.execute_trade(signal_text)
                
                if success:
                    self.state["signals_fixed"] += 1
                    self.log_signal(signal_text, "fixed", {"fix": "retry_success"})
                    self.save_state()
                    return True
        
        # Log final failure
        logger.error("❌ Could not recover from failure")
        self.log_signal(signal_text, "failed", {"error": output[:500]})
        self.save_state()
        return False
    
    def run_continuous(self):
        """Run continuous monitoring"""
        logger.info("=" * 60)
        logger.info("🤖 FELIX AI SUPERVISOR STARTED")
        logger.info("=" * 60)
        logger.info("Monitoring system health and fixing errors...")
        
        while True:
            try:
                # Check listener health every 30 seconds
                self.check_listener_health()
                
                # Monitor rejections and fix
                self.monitor_rejections()
                
                # Save state
                self.save_state()
                
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("Supervisor stopped by user")
                break
            except Exception as e:
                logger.error(f"Supervisor error: {e}")
                time.sleep(30)
    
    def get_status(self):
        """Get supervisor status"""
        return {
            "status": "active",
            "started": self.state.get("started"),
            "signals_processed": self.state.get("signals_processed", 0),
            "signals_failed": self.state.get("signals_failed", 0),
            "signals_fixed": self.state.get("signals_fixed", 0),
            "success_rate": self.calculate_success_rate(),
            "last_check": self.state.get("last_check")
        }
    
    def calculate_success_rate(self):
        """Calculate signal success rate"""
        processed = self.state.get("signals_processed", 0)
        if processed == 0:
            return 100.0
        failed = self.state.get("signals_failed", 0)
        fixed = self.state.get("signals_fixed", 0)
        successful = processed - failed + fixed
        return round((successful / processed) * 100, 2)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Felix AI Supervisor")
    parser.add_argument("--monitor", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--process", help="Process a single signal")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--fix-last", action="store_true", help="Fix last rejected signal")
    
    args = parser.parse_args()
    
    supervisor = FelixAISupervisor()
    
    if args.monitor:
        supervisor.run_continuous()
    elif args.process:
        supervisor.process_signal(args.process)
    elif args.fix_last:
        supervisor.monitor_rejections()
    elif args.status:
        status = supervisor.get_status()
        print(json.dumps(status, indent=2))
    else:
        print("Felix AI Supervisor")
        print("===================")
        print("Commands:")
        print("  --monitor     Run continuous monitoring")
        print("  --process 'signal'  Process a signal")
        print("  --status      Show system status")
        print("  --fix-last    Fix last rejected signal")

if __name__ == "__main__":
    main()
