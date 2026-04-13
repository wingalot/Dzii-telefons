#!/usr/bin/env python3
"""
FELIX Trading System - Module Interfaces
=========================================

Šis fails satur kopīgās interfeisa definīcijas visiem FELIX moduļiem.
Visi moduļi importē no šī faila, lai nodrošinātu vienotu datu struktūru.

Usage:
    from felix_interfaces import Signal, Position, SignalParser, RiskManager

Author: FELIX Trading System
Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
import json


# =============================================================================
# ENUMERATIONS
# =============================================================================

class TradeDirection(Enum):
    """Tirdzniecības virziena tipi"""
    BUY = "BUY"
    SELL = "SELL"
    LONG = "LONG"  # Alias for BUY
    SHORT = "SHORT"  # Alias for SELL


class OrderType(Enum):
    """Ordera tipi"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class SignalStatus(Enum):
    """Signāla statusi"""
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class PositionStatus(Enum):
    """Pozīcijas statusi"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIAL = "PARTIAL"
    PENDING = "PENDING"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Signal:
    """
    Tirdzniecības signāla dataclass.
    
    Attributes:
        pair: Valūtu pāris (piem., EURUSD)
        direction: Virziens (BUY/SELL)
        entry: Ieejas cena (optional, ja None -> market price)
        tp: Take Profit cena vai procents
        sl: Stop Loss cena vai procents
        risk_percent: Riska procents no konta
        lot_size: Līguma lielums (optional)
        timestamp: Signāla laiks
        source: Signāla avots (telegram, manual, etc.)
        raw_data: Oriģinālais signāla datu JSON
        status: Signāla statuss
        epic: IG EPIC kods (aizpilda EPIC Resolver)
        validation_message: Validācijas ziņojums
    """
    pair: str
    direction: Union[TradeDirection, str]
    tp: Optional[float] = None
    sl: Optional[float] = None
    entry: Optional[float] = None
    risk_percent: Optional[float] = None
    lot_size: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    raw_data: Optional[Dict[str, Any]] = None
    status: SignalStatus = SignalStatus.PENDING
    epic: Optional[str] = None
    validation_message: Optional[str] = None
    
    def __post_init__(self):
        """Normalize direction to TradeDirection enum"""
        if isinstance(self.direction, str):
            dir_upper = self.direction.upper()
            if dir_upper in ["LONG", "BUY"]:
                self.direction = TradeDirection.BUY
            elif dir_upper in ["SHORT", "SELL"]:
                self.direction = TradeDirection.SELL
            else:
                raise ValueError(f"Invalid direction: {self.direction}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertē uz vārdnīcu"""
        return {
            "pair": self.pair,
            "direction": self.direction.value if isinstance(self.direction, TradeDirection) else self.direction,
            "tp": self.tp,
            "sl": self.sl,
            "entry": self.entry,
            "risk_percent": self.risk_percent,
            "lot_size": self.lot_size,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source": self.source,
            "status": self.status.value if isinstance(self.status, SignalStatus) else self.status,
            "epic": self.epic,
            "validation_message": self.validation_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Signal":
        """Izveido Signal no vārdnīcas"""
        return cls(
            pair=data.get("pair", ""),
            direction=data.get("direction", ""),
            tp=data.get("tp"),
            sl=data.get("sl"),
            entry=data.get("entry"),
            risk_percent=data.get("risk_percent"),
            lot_size=data.get("lot_size"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            source=data.get("source", "unknown"),
            raw_data=data.get("raw_data"),
            status=SignalStatus(data.get("status", "PENDING")),
            epic=data.get("epic"),
            validation_message=data.get("validation_message")
        )
    
    def to_json(self) -> str:
        """Konvertē uz JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    def is_valid(self) -> bool:
        """Pārbauda vai signāls ir derīgs"""
        return self.status != SignalStatus.REJECTED and self.epic is not None


@dataclass
class Position:
    """
    Tirdzniecības pozīcijas dataclass.
    
    Attributes:
        position_id: Pozīcijas ID (no IG)
        deal_id: Darījuma ID
        epic: IG EPIC kods
        pair: Valūtu pāris
        direction: Virziens (BUY/SELL)
        size: Pozīcijas lielums (līgumi)
        open_price: Atvēršanas cena
        current_price: Pašreizējā cena
        tp_price: Take Profit cena
        sl_price: Stop Loss cena
        margin: Izmantotā margin
        pnl: Pašreizējais P&L
        status: Pozīcijas statuss
        open_time: Atvēršanas laiks
        close_time: Aizvēršanas laiks (ja aizvērta)
        signal: Saistītais signāls (optional)
    """
    position_id: str
    epic: str
    pair: str
    direction: Union[TradeDirection, str]
    size: float
    open_price: float
    deal_id: Optional[str] = None
    current_price: Optional[float] = None
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None
    margin: Optional[float] = None
    pnl: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    open_time: datetime = field(default_factory=datetime.now)
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    signal: Optional[Signal] = None
    
    def __post_init__(self):
        """Normalize direction"""
        if isinstance(self.direction, str):
            dir_upper = self.direction.upper()
            if dir_upper in ["LONG", "BUY"]:
                self.direction = TradeDirection.BUY
            elif dir_upper in ["SHORT", "SELL"]:
                self.direction = TradeDirection.SELL
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertē uz vārdnīcu"""
        return {
            "position_id": self.position_id,
            "deal_id": self.deal_id,
            "epic": self.epic,
            "pair": self.pair,
            "direction": self.direction.value if isinstance(self.direction, TradeDirection) else self.direction,
            "size": self.size,
            "open_price": self.open_price,
            "current_price": self.current_price,
            "tp_price": self.tp_price,
            "sl_price": self.sl_price,
            "margin": self.margin,
            "pnl": self.pnl,
            "status": self.status.value if isinstance(self.status, PositionStatus) else self.status,
            "open_time": self.open_time.isoformat() if self.open_time else None,
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "close_price": self.close_price
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        """Izveido Position no vārdnīcas"""
        return cls(
            position_id=data.get("position_id", ""),
            epic=data.get("epic", ""),
            pair=data.get("pair", ""),
            direction=data.get("direction", ""),
            size=data.get("size", 0.0),
            open_price=data.get("open_price", 0.0),
            deal_id=data.get("deal_id"),
            current_price=data.get("current_price"),
            tp_price=data.get("tp_price"),
            sl_price=data.get("sl_price"),
            margin=data.get("margin"),
            pnl=data.get("pnl", 0.0),
            status=PositionStatus(data.get("status", "OPEN")),
            open_time=datetime.fromisoformat(data["open_time"]) if data.get("open_time") else datetime.now(),
            close_time=datetime.fromisoformat(data["close_time"]) if data.get("close_time") else None,
            close_price=data.get("close_price")
        )
    
    def update_pnl(self, current_price: float) -> float:
        """Atjaunina P&L ar pašreizējo cenu"""
        self.current_price = current_price
        if self.direction == TradeDirection.BUY:
            self.pnl = (current_price - self.open_price) * self.size
        else:
            self.pnl = (self.open_price - current_price) * self.size
        return self.pnl
    
    def is_profit(self) -> bool:
        """Vai pozīcija ir peļņā"""
        return self.pnl > 0


@dataclass
class TradeResult:
    """
    Darījuma izpildes rezultāts.
    
    Attributes:
        success: Vai darījums veiksmīgs
        position: Pozīcijas dati (ja veiksmīgs)
        error_message: Kļūdas ziņojums (ja neveiksmīgs)
        order_id: Ordera ID
        deal_reference: IG deal reference
    """
    success: bool
    position: Optional[Position] = None
    error_message: Optional[str] = None
    order_id: Optional[str] = None
    deal_reference: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertē uz vārdnīcu"""
        return {
            "success": self.success,
            "position": self.position.to_dict() if self.position else None,
            "error_message": self.error_message,
            "order_id": self.order_id,
            "deal_reference": self.deal_reference,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class RiskCheck:
    """
    Riska pārbaudes rezultāts.
    
    Attributes:
        allowed: Vai darījums atļauts
        reason: Iemesls (ja atteikts)
        daily_pnl: Dienas P&L
        open_positions: Atvērto pozīciju skaits
        daily_trades: Dienas darījumu skaits
    """
    allowed: bool
    reason: Optional[str] = None
    daily_pnl: float = 0.0
    open_positions: int = 0
    daily_trades: int = 0
    risk_percent: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "daily_pnl": self.daily_pnl,
            "open_positions": self.open_positions,
            "daily_trades": self.daily_trades,
            "risk_percent": self.risk_percent
        }


# =============================================================================
# ABSTRACT BASE CLASSES
# =============================================================================

class SignalParser(ABC):
    """
    Abstract base class for signal parsers.
    
    Visi signālu parsētāji implementē šo interfeisu.
    """
    
    @abstractmethod
    def parse(self, raw_data: Union[str, Dict[str, Any]]) -> Signal:
        """
        Parsē izejas datus uz Signal objektu.
        
        Args:
            raw_data: Signāla dati (JSON string vai dict)
            
        Returns:
            Signal: Parsēts signāls
            
        Raises:
            ValueError: Ja dati ir nepareizi
        """
        pass
    
    @abstractmethod
    def validate(self, signal: Signal) -> bool:
        """
        Validē signāla struktūru.
        
        Args:
            signal: Signāls ko validēt
            
        Returns:
            bool: True ja derīgs, False ja nederīgs
        """
        pass


class RiskManager(ABC):
    """
    Abstract base class for risk management.
    
    Riska pārvaldības moduļi implementē šo interfeisu.
    """
    
    @abstractmethod
    def check_signal(self, signal: Signal) -> RiskCheck:
        """
        Pārbauda signālu pret riska noteikumiem.
        
        Args:
            signal: Signāls ko pārbaudīt
            
        Returns:
            RiskCheck: Pārbaudes rezultāts
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: Signal, account_balance: float) -> float:
        """
        Aprēķina pozīcijas lielumu.
        
        Args:
            signal: Tirdzniecības signāls
            account_balance: Konta bilance
            
        Returns:
            float: Ieteicamais līgumu skaits
        """
        pass
    
    @abstractmethod
    def get_daily_stats(self) -> Dict[str, Any]:
        """
        Atgriež dienas statistiku.
        
        Returns:
            Dict ar daily_pnl, trades_count, positions_count
        """
        pass


class EpicResolver(ABC):
    """
    Abstract base class for EPIC code resolution.
    
    Valūtu pāru → EPIC kodu kartēšana.
    """
    
    @abstractmethod
    def resolve(self, pair: str) -> Optional[str]:
        """
        Konvertē valūtu pāri uz IG EPIC kodu.
        
        Args:
            pair: Valūtu pāris (EURUSD, EU, etc.)
            
        Returns:
            Optional[str]: EPIC kods vai None
        """
        pass
    
    @abstractmethod
    def normalize_pair(self, pair: str) -> str:
        """
        Normalizē valūtu pāri uz standarta formātu.
        
        Args:
            pair: Ievades pāris
            
        Returns:
            str: Normalizēts pāris
        """
        pass


class PositionManager(ABC):
    """
    Abstract base class for position management.
    
    Pozīciju atvēršana/aizvēršana/pārvaldība.
    """
    
    @abstractmethod
    def open_position(self, signal: Signal) -> TradeResult:
        """
        Atver pozīciju pēc signāla.
        
        Args:
            signal: Tirdzniecības signāls
            
        Returns:
            TradeResult: Darījuma rezultāts
        """
        pass
    
    @abstractmethod
    def close_position(self, position_id: str) -> TradeResult:
        """
        Aizver pozīciju pēc ID.
        
        Args:
            position_id: Pozīcijas ID
            
        Returns:
            TradeResult: Darījuma rezultāts
        """
        pass
    
    @abstractmethod
    def get_open_positions(self) -> List[Position]:
        """
        Atgriež visus atvērtos pozīcijas.
        
        Returns:
            List[Position]: Atvērto pozīciju saraksts
        """
        pass
    
    @abstractmethod
    def modify_position(self, position_id: str, 
                       tp: Optional[float] = None,
                       sl: Optional[float] = None) -> bool:
        """
        Modificē pozīcijas TP/SL.
        
        Args:
            position_id: Pozīcijas ID
            tp: Jauns TP līmenis
            sl: Jauns SL līmenis
            
        Returns:
            bool: True ja veiksmīgi
        """
        pass


class IGExecutor(ABC):
    """
    Abstract base class for IG API execution.
    
    IG API komunikācija.
    """
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Autentificējas ar IG API.
        
        Returns:
            bool: True ja veiksmīgi
        """
        pass
    
    @abstractmethod
    def place_order(self, signal: Signal, size: float) -> TradeResult:
        """
        Iesniedz orderi IG.
        
        Args:
            signal: Tirdzniecības signāls
            size: Pozīcijas lielums
            
        Returns:
            TradeResult: Ordera rezultāts
        """
        pass
    
    @abstractmethod
    def close_order(self, deal_id: str) -> TradeResult:
        """
        Aizver orderi/deal.
        
        Args:
            deal_id: Darījuma ID
            
        Returns:
            TradeResult: Aizvēršanas rezultāts
        """
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """
        Atgriež konta informāciju.
        
        Returns:
            Dict ar balance, equity, margin, pnl
        """
        pass


class NotificationService(ABC):
    """
    Abstract base class for notifications.
    
    Paziņojumu sūtīšana.
    """
    
    @abstractmethod
    def send_trade_notification(self, result: TradeResult) -> bool:
        """
        Sūta paziņojumu par darījumu.
        
        Args:
            result: Darījuma rezultāts
            
        Returns:
            bool: True ja veiksmīgi
        """
        pass
    
    @abstractmethod
    def send_alert(self, message: str, level: str = "INFO") -> bool:
        """
        Sūta alerta ziņojumu.
        
        Args:
            message: Ziņojums
            level: Līmenis (INFO, WARNING, ERROR)
            
        Returns:
            bool: True ja veiksmīgi
        """
        pass
    
    @abstractmethod
    def send_daily_summary(self, stats: Dict[str, Any]) -> bool:
        """
        Sūta dienas kopsavilkumu.
        
        Args:
            stats: Dienas statistika
            
        Returns:
            bool: True ja veiksmīgi
        """
        pass


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_price(price: float, decimals: int = 5) -> str:
    """
    Formatē cenu ar norādīto decimāldaļu skaitu.
    
    Args:
        price: Cena
        decimals: Decimālzīmju skaits
        
    Returns:
        str: Formatēta cena
    """
    return f"{price:.{decimals}f}"


def format_pnl(pnl: float, currency: str = "€") -> str:
    """
    Formatē P&L ar valūtas simbolu un krāsu indikatoru.
    
    Args:
        pnl: P&L vērtība
        currency: Valūtas simbols
        
    Returns:
        str: Formatēts P&L
    """
    sign = "+" if pnl >= 0 else ""
    return f"{sign}{pnl:.2f}{currency}"


def calculate_tp_sl(entry: float, direction: Union[TradeDirection, str],
                   tp_percent: Optional[float] = None,
                   sl_percent: Optional[float] = None) -> tuple:
    """
    Aprēķina TP un SL cenas no procentiem.
    
    Args:
        entry: Ieejas cena
        direction: Virziens (BUY/SELL)
        tp_percent: TP procents
        sl_percent: SL procents
        
    Returns:
        tuple: (tp_price, sl_price)
    """
    if isinstance(direction, str):
        direction = TradeDirection.BUY if direction.upper() in ["BUY", "LONG"] else TradeDirection.SELL
    
    tp_price = None
    sl_price = None
    
    if tp_percent:
        if direction == TradeDirection.BUY:
            tp_price = entry * (1 + tp_percent / 100)
        else:
            tp_price = entry * (1 - tp_percent / 100)
    
    if sl_percent:
        if direction == TradeDirection.BUY:
            sl_price = entry * (1 - sl_percent / 100)
        else:
            sl_price = entry * (1 + sl_percent / 100)
    
    return tp_price, sl_price


def risk_reward_ratio(entry: float, tp: float, sl: float, 
                     direction: Union[TradeDirection, str]) -> float:
    """
    Aprēķina risk/reward attiecību.
    
    Args:
        entry: Ieejas cena
        tp: TP cena
        sl: SL cena
        direction: Virziens
        
    Returns:
        float: Risk/Reward ratio
    """
    if isinstance(direction, str):
        direction = TradeDirection.BUY if direction.upper() in ["BUY", "LONG"] else TradeDirection.SELL
    
    if direction == TradeDirection.BUY:
        reward = tp - entry
        risk = entry - sl
    else:
        reward = entry - tp
        risk = sl - entry
    
    if risk == 0:
        return 0.0
    return reward / risk


def validate_signal_json(data: Dict[str, Any]) -> tuple:
    """
    Validē signāla JSON struktūru.
    
    Args:
        data: Signāla datu vārdnīca
        
    Returns:
        tuple: (is_valid: bool, error_message: Optional[str])
    """
    required_fields = ["pair", "direction"]
    
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    direction = data.get("direction", "").upper()
    if direction not in ["BUY", "SELL", "LONG", "SHORT"]:
        return False, f"Invalid direction: {direction}"
    
    return True, None


def load_config(config_path: str = "~/.trading/felix_config.json") -> Dict[str, Any]:
    """
    Ielādē konfigurācijas failu.
    
    Args:
        config_path: Ceļš uz config failu
        
    Returns:
        Dict: Konfigurācijas dati
    """
    import os
    path = os.path.expanduser(config_path)
    
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")


def save_position(position: Position, filepath: str = "~/.trading/felix_positions.json"):
    """
    Saglabā pozīciju failā.
    
    Args:
        position: Pozīcija ko saglabāt
        filepath: Ceļš uz failu
    """
    import os
    path = os.path.expanduser(filepath)
    
    # Ielādē esošās pozīcijas
    positions = []
    if os.path.exists(path):
        with open(path, 'r') as f:
            try:
                data = json.load(f)
                positions = data.get("positions", [])
            except json.JSONDecodeError:
                positions = []
    
    # Pievieno jauno pozīciju
    positions.append(position.to_dict())
    
    # Saglabā
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump({"positions": positions}, f, indent=2)


def get_timestamp() -> str:
    """
    Atgriež pašreizējo timestamp ISO formātā.
    
    Returns:
        str: ISO format timestamp
    """
    return datetime.now().isoformat()


def log_message(message: str, level: str = "INFO", 
               log_file: str = "~/.trading/logs/felix.log"):
    """
    Ieraksta ziņojumu log failā.
    
    Args:
        message: Ziņojums
        level: Līmenis (DEBUG, INFO, WARNING, ERROR)
        log_file: Log faila ceļš
    """
    import os
    path = os.path.expanduser(log_file)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    with open(path, 'a') as f:
        f.write(log_entry)


# =============================================================================
# CONSTANTS
# =============================================================================

# IG API endpoints
IG_DEMO_URL = "https://demo-api.ig.com/gateway/deal"
IG_LIVE_URL = "https://api.ig.com/gateway/deal"

# Default configuration paths
DEFAULT_CONFIG_PATH = "~/.trading/felix_config.json"
DEFAULT_POSITIONS_PATH = "~/.trading/felix_positions.json"
DEFAULT_HISTORY_PATH = "~/.trading/felix_history.json"
DEFAULT_LOG_PATH = "~/.trading/logs"

# Session hours (UTC)
SESSION_LONDON = ("08:00", "17:00")
SESSION_NEW_YORK = ("13:00", "22:00")
SESSION_TOKYO = ("00:00", "09:00")
SESSION_SYDNEY = ("22:00", "07:00")

# Version
FELIX_VERSION = "1.0.0"


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "TradeDirection",
    "OrderType",
    "SignalStatus",
    "PositionStatus",
    
    # Data Classes
    "Signal",
    "Position",
    "TradeResult",
    "RiskCheck",
    
    # Abstract Classes
    "SignalParser",
    "RiskManager",
    "EpicResolver",
    "PositionManager",
    "IGExecutor",
    "NotificationService",
    
    # Utility Functions
    "format_price",
    "format_pnl",
    "calculate_tp_sl",
    "risk_reward_ratio",
    "validate_signal_json",
    "load_config",
    "save_position",
    "get_timestamp",
    "log_message",
    
    # Constants
    "IG_DEMO_URL",
    "IG_LIVE_URL",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_POSITIONS_PATH",
    "FELIX_VERSION",
]


if __name__ == "__main__":
    # Test/example usage
    print("FELIX Trading System - Module Interfaces")
    print(f"Version: {FELIX_VERSION}")
    
    # Create example signal
    signal = Signal(
        pair="EURUSD",
        direction="BUY",
        entry=1.0850,
        tp=1.0950,
        sl=1.0800,
        risk_percent=2.0,
        source="telegram"
    )
    
    print(f"\nExample Signal:")
    print(signal.to_json())
    
    # Calculate TP/SL
    tp, sl = calculate_tp_sl(1.0850, "BUY", 2.0, 1.0)
    print(f"\nCalculated TP: {format_price(tp)}")
    print(f"Calculated SL: {format_price(sl)}")
    
    # Risk/Reward ratio
    rr = risk_reward_ratio(1.0850, tp, sl, "BUY")
    print(f"Risk/Reward Ratio: 1:{rr:.2f}")
