#!/usr/bin/env python3
"""
FELIX SYSTEM SUPERVISOR - v3.0
==============================
Validates system accuracy by cross-checking:
- Felix signals vs IG positions
- TP/SL completeness
- Duplicate detection
- Local state vs IG state consistency

Runs continuously and reports discrepancies.
"""

import os
import sys
import json
import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add supervisor directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from felix_interfaces import Position, Signal
except ImportError:
    pass  # Will work without it

# Configuration
BASE_DIR = Path.home() / ".openclaw" / "ai_supervisor"
TRADING_DIR = Path.home() / ".trading"
STATE_FILE = BASE_DIR / "state" / "supervisor_state.json"
LOG_FILE = BASE_DIR / "logs" / "supervisor.log"
IG_API = TRADING_DIR / "ig_api.sh"

# Check intervals
CHECK_INTERVAL = 60  # seconds
ALERT_COOLDOWN = 300  # 5 minutes between same alerts

# Setup logging
os.makedirs(BASE_DIR / "logs", exist_ok=True)
os.makedirs(BASE_DIR / "state", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [SUPERVISOR] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Represents a validation problem"""
    severity: str  # ERROR, WARNING, INFO
    category: str  # duplicate, missing_tp, missing_sl, sync_mismatch, etc.
    message: str
    position_id: Optional[str] = None
    pair: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class SystemSupervisor:
    """Main supervisor class for system validation"""
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.alert_history: Dict[str, datetime] = {}  # Prevent spam
        self.ig_positions: List[Dict] = []
        self.local_positions: Dict = {}
        self.signal_history: List[Dict] = []
        self.running = True
        self.auto_fix_enabled = False  # Set to True to enable auto-fix
        self.auto_fix_counter = 0  # Only auto-fix every N cycles
        
    def run_auto_fix(self):
        """Run auto-fix for duplicate positions"""
        if not self.auto_fix_enabled:
            return
        
        try:
            # Import autofix module
            from felix_autofix import SystemAutoFix
            
            fixer = SystemAutoFix(dry_run=False)  # Live mode
            
            # Only fix duplicates (safer than adding SL/TP)
            duplicates = fixer.find_duplicates(self.ig_positions)
            
            if duplicates:
                logger.info(f"🔧 Auto-fixing {len(duplicates)} duplicate groups...")
                for key, dup_list in duplicates.items():
                    # Close all but the most recent
                    sorted_positions = sorted(
                        dup_list,
                        key=lambda x: x.get('created_date', ''),
                        reverse=True
                    )
                    
                    # Keep first, close rest
                    for pos in sorted_positions[1:]:
                        logger.info(f"   Auto-closing duplicate: {pos['pair']} {pos['deal_id']}")
                        fixer.close_position(pos['deal_id'], pos['pair'])
                        
        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")
        
    def send_alert(self, issue: ValidationIssue):
        """Send alert if not in cooldown"""
        alert_key = f"{issue.category}:{issue.position_id or issue.pair}"
        now = datetime.now()
        
        # Check cooldown
        if alert_key in self.alert_history:
            last_alert = self.alert_history[alert_key]
            if (now - last_alert).seconds < ALERT_COOLDOWN:
                return  # Skip - in cooldown
        
        self.alert_history[alert_key] = now
        
        # Log the issue
        if issue.severity == "ERROR":
            logger.error(f"🚨 {issue.message}")
        elif issue.severity == "WARNING":
            logger.warning(f"⚠️  {issue.message}")
        else:
            logger.info(f"ℹ️  {issue.message}")
        
        # Send Telegram notification for errors
        if issue.severity in ["ERROR", "WARNING"]:
            self._notify_telegram(issue)
    
    def _notify_telegram(self, issue: ValidationIssue):
        """Send notification to Telegram"""
        try:
            emoji = "🚨" if issue.severity == "ERROR" else "⚠️"
            message = f"{emoji} Supervisor Alert\n\n"
            message += f"Type: {issue.category}\n"
            message += f"Severity: {issue.severity}\n"
            if issue.pair:
                message += f"Pair: {issue.pair}\n"
            message += f"\n{issue.message}"
            
            script_path = BASE_DIR / "send_notification.py"
            subprocess.Popen(
                ['python3', str(script_path), message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def get_ig_positions(self) -> List[Dict]:
        """Fetch positions from IG API"""
        try:
            result = subprocess.run(
                ['bash', str(IG_API), 'positions'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get('positions', [])
        except Exception as e:
            logger.error(f"Failed to fetch IG positions: {e}")
        return []
    
    def get_local_positions(self) -> Dict:
        """Get positions from TP Manager state"""
        try:
            tp_state_file = BASE_DIR / "state" / "tp_manager_state.json"
            if tp_state_file.exists():
                with open(tp_state_file) as f:
                    data = json.load(f)
                    return data.get('positions', {})
        except Exception as e:
            logger.error(f"Failed to load local positions: {e}")
        return {}
    
    def get_signal_history(self) -> List[Dict]:
        """Get recent signals from Signal Hub state"""
        try:
            hub_state_file = BASE_DIR / "state" / "signal_hub.json"
            if hub_state_file.exists():
                with open(hub_state_file) as f:
                    data = json.load(f)
                    registry = data.get('message_registry', {})
                    # Convert to list and filter recent
                    signals = []
                    for msg_id, info in registry.items():
                        if info.get('type') == 'initial_signal':
                            signals.append({
                                'message_id': msg_id,
                                'pair': info.get('pair'),
                                'direction': info.get('direction'),
                                'entry': info.get('entry'),
                                'tp1': info.get('tp1'),
                                'tp2': info.get('tp2'),
                                'tp3': info.get('tp3'),
                                'sl': info.get('sl'),
                                'timestamp': info.get('timestamp')
                            })
                    return signals
        except Exception as e:
            logger.error(f"Failed to load signal history: {e}")
        return []
    
    def check_duplicates(self) -> List[ValidationIssue]:
        """Check for duplicate positions (same pair+direction within 5 min)"""
        issues = []
        seen = {}
        
        for pos in self.ig_positions:
            pair = pos.get('market', {}).get('epic', '').replace('CS.D.', '').replace('.CFD.IP', '')
            direction = pos.get('position', {}).get('direction', '')
            deal_id = pos.get('position', {}).get('dealId', '')
            
            key = f"{pair}:{direction}"
            if key in seen:
                # Check time difference
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="duplicate",
                    message=f"Duplicate position detected: {pair} {direction}",
                    pair=pair,
                    position_id=deal_id
                ))
            else:
                seen[key] = pos
        
        return issues
    
    def check_missing_tp_sl(self) -> List[ValidationIssue]:
        """Check if positions have TP and SL defined"""
        issues = []
        
        for pos in self.ig_positions:
            pair = pos.get('market', {}).get('epic', '').replace('CS.D.', '').replace('.CFD.IP', '')
            deal_id = pos.get('position', {}).get('dealId', '')
            
            # Check local state for TP/SL
            local_pos = self.local_positions.get(deal_id, {})
            
            if not local_pos.get('tp1') and not local_pos.get('tp2') and not local_pos.get('tp3'):
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="missing_tp",
                    message=f"Position {pair} has no Take Profit levels defined",
                    pair=pair,
                    position_id=deal_id
                ))
            
            if not local_pos.get('sl'):
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="missing_sl",
                    message=f"Position {pair} has NO STOP LOSS!",
                    pair=pair,
                    position_id=deal_id
                ))
        
        return issues
    
    def check_sync_mismatch(self) -> List[ValidationIssue]:
        """Check if IG and local state match"""
        issues = []
        
        # Get IG position IDs
        ig_ids = set()
        ig_pairs = {}
        for pos in self.ig_positions:
            deal_id = pos.get('position', {}).get('dealId', '')
            pair = pos.get('market', {}).get('epic', '').replace('CS.D.', '').replace('.CFD.IP', '')
            ig_ids.add(deal_id)
            ig_pairs[deal_id] = pair
        
        # Get local position IDs
        local_ids = set(self.local_positions.keys())
        
        # Check for IG positions not tracked locally
        for deal_id in ig_ids:
            if deal_id not in local_ids:
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="sync_mismatch",
                    message=f"IG position {deal_id} ({ig_pairs.get(deal_id)}) not tracked by TP Manager",
                    pair=ig_pairs.get(deal_id),
                    position_id=deal_id
                ))
        
        # Check for local positions that don't exist in IG
        for deal_id in local_ids:
            if deal_id not in ig_ids:
                pos_info = self.local_positions[deal_id]
                issues.append(ValidationIssue(
                    severity="INFO",
                    category="sync_mismatch",
                    message=f"Local position {deal_id} ({pos_info.get('pair')}) not found in IG (may be closed)",
                    pair=pos_info.get('pair'),
                    position_id=deal_id
                ))
        
        return issues
    
    def check_signal_position_match(self) -> List[ValidationIssue]:
        """Check if Felix signals match opened positions"""
        issues = []
        
        # Get recent signals (last 10 minutes)
        recent_signals = [
            s for s in self.signal_history
            if s.get('timestamp') and 
            (datetime.now() - datetime.fromisoformat(s['timestamp'].replace('Z', '+00:00'))).seconds < 600
        ]
        
        for signal in recent_signals:
            pair = signal.get('pair', '')
            direction = signal.get('direction', '')
            
            # Check if corresponding position exists in IG
            found = False
            for pos in self.ig_positions:
                pos_pair = pos.get('market', {}).get('epic', '').replace('CS.D.', '').replace('.CFD.IP', '')
                pos_dir = pos.get('position', {}).get('direction', '')
                
                if pair in pos_pair and direction.upper() == pos_dir.upper():
                    found = True
                    break
            
            if not found:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="signal_not_executed",
                    message=f"Signal {pair} {direction} not found as IG position - execution failed?",
                    pair=pair
                ))
        
        return issues
    
    def generate_report(self) -> Dict:
        """Generate validation report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'ig_positions_count': len(self.ig_positions),
            'local_positions_count': len(self.local_positions),
            'signals_count': len(self.signal_history),
            'issues_count': len(self.issues),
            'issues_by_severity': {
                'ERROR': len([i for i in self.issues if i.severity == 'ERROR']),
                'WARNING': len([i for i in self.issues if i.severity == 'WARNING']),
                'INFO': len([i for i in self.issues if i.severity == 'INFO'])
            }
        }
    
    async def run_validation_cycle(self):
        """Run one complete validation cycle"""
        logger.info("🔍 Starting validation cycle...")
        
        # Fetch data
        self.ig_positions = self.get_ig_positions()
        self.local_positions = self.get_local_positions()
        self.signal_history = self.get_signal_history()
        
        logger.info(f"📊 IG positions: {len(self.ig_positions)}")
        logger.info(f"📊 Local positions: {len(self.local_positions)}")
        logger.info(f"📊 Recent signals: {len(self.signal_history)}")
        
        # Run checks
        all_issues = []
        all_issues.extend(self.check_duplicates())
        all_issues.extend(self.check_missing_tp_sl())
        all_issues.extend(self.check_sync_mismatch())
        all_issues.extend(self.check_signal_position_match())
        
        self.issues = all_issues
        
        # Send alerts
        for issue in all_issues:
            self.send_alert(issue)
        
        # Auto-fix duplicates every 5 cycles (if enabled)
        self.auto_fix_counter += 1
        if self.auto_fix_counter >= 5:
            self.auto_fix_counter = 0
            duplicate_count = len([i for i in all_issues if i.category == 'duplicate'])
            if duplicate_count > 0:
                logger.info(f"🔧 Auto-fix triggered for {duplicate_count} duplicates")
                self.run_auto_fix()
        
        # Generate report
        report = self.generate_report()
        logger.info(f"✅ Validation complete: {report['issues_count']} issues found")
        
        # Save state
        self.save_state(report)
        
        return report
    
    def save_state(self, report: Dict):
        """Save supervisor state"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump({
                    'last_check': datetime.now().isoformat(),
                    'report': report,
                    'recent_issues': [
                        {
                            'severity': i.severity,
                            'category': i.category,
                            'message': i.message,
                            'pair': i.pair,
                            'timestamp': i.timestamp.isoformat()
                        }
                        for i in self.issues[-10:]  # Last 10 issues
                    ]
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    async def run(self):
        """Main supervisor loop"""
        logger.info("=" * 60)
        logger.info("🛡️  FELIX SYSTEM SUPERVISOR v3.0")
        logger.info("=" * 60)
        logger.info("Validation checks:")
        logger.info("  • Duplicate position detection")
        logger.info("  • TP/SL completeness")
        logger.info("  • IG/Local sync validation")
        logger.info("  • Signal execution verification")
        logger.info("=" * 60)
        
        while self.running:
            try:
                await self.run_validation_cycle()
                logger.info(f"💤 Sleeping for {CHECK_INTERVAL}s...")
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Validation cycle error: {e}", exc_info=True)
                await asyncio.sleep(CHECK_INTERVAL)
    
    def stop(self):
        """Stop supervisor"""
        self.running = False
        logger.info("🛑 Supervisor stopping...")


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Felix System Supervisor')
    parser.add_argument('--once', action='store_true', help='Run one check and exit')
    args = parser.parse_args()
    
    supervisor = SystemSupervisor()
    
    if args.once:
        # Run single check
        asyncio.run(supervisor.run_validation_cycle())
    else:
        # Run continuous
        try:
            asyncio.run(supervisor.run())
        except KeyboardInterrupt:
            supervisor.stop()


if __name__ == "__main__":
    main()
