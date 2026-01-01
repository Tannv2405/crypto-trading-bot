"""
Abstract base class for trading strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from utils.logger import get_logger

logger = get_logger(__name__)

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name
            parameters: Strategy parameters dictionary
        """
        self.name = name
        self.parameters = parameters or {}
        self.position = None  # 'long', 'short', or None
        self.signals_history = []
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0
        }
    
    @abstractmethod
    def calculate_signals(self, market_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate trading signals based on market data.
        
        Args:
            market_data: List of market data dictionaries (OHLCV)
            
        Returns:
            Dictionary containing signal information
        """
        pass
    
    @abstractmethod
    def should_buy(self, market_data: List[Dict[str, Any]], indicators: Dict[str, float]) -> Tuple[bool, str]:
        """
        Determine if a buy signal should be generated.
        
        Args:
            market_data: List of market data dictionaries
            indicators: Dictionary of calculated indicators
            
        Returns:
            Tuple of (should_buy, reason)
        """
        pass
    
    @abstractmethod
    def should_sell(self, market_data: List[Dict[str, Any]], indicators: Dict[str, float]) -> Tuple[bool, str]:
        """
        Determine if a sell signal should be generated.
        
        Args:
            market_data: List of market data dictionaries
            indicators: Dictionary of calculated indicators
            
        Returns:
            Tuple of (should_sell, reason)
        """
        pass
    
    def get_signal(self, market_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get trading signal based on current market data.
        
        Args:
            market_data: List of market data dictionaries
            
        Returns:
            Signal dictionary with action, confidence, and indicators
        """
        try:
            # Calculate indicators
            indicators = self.calculate_signals(market_data)
            
            # Determine action
            action = 'HOLD'
            reason = 'No clear signal'
            confidence = 0.0
            
            # Check for buy signal
            should_buy, buy_reason = self.should_buy(market_data, indicators)
            if should_buy and self.position != 'long':
                action = 'BUY'
                reason = buy_reason
                confidence = self.calculate_confidence(market_data, indicators, 'BUY')
            
            # Check for sell signal
            should_sell, sell_reason = self.should_sell(market_data, indicators)
            if should_sell and self.position == 'long':
                action = 'SELL'
                reason = sell_reason
                confidence = self.calculate_confidence(market_data, indicators, 'SELL')
            
            signal = {
                'strategy': self.name,
                'action': action,
                'reason': reason,
                'confidence': confidence,
                'indicators': indicators,
                'timestamp': datetime.now()
            }
            
            # Store signal in history
            self.signals_history.append(signal)
            
            # Keep only recent signals (last 100)
            if len(self.signals_history) > 100:
                self.signals_history = self.signals_history[-100:]
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {self.name}: {e}")
            return {
                'strategy': self.name,
                'action': 'HOLD',
                'reason': f'Error: {str(e)}',
                'confidence': 0.0,
                'indicators': {},
                'timestamp': datetime.now()
            }
    
    def calculate_confidence(self, market_data: List[Dict[str, Any]], 
                           indicators: Dict[str, float], action: str) -> float:
        """
        Calculate confidence level for the signal (0.0 to 1.0).
        
        Args:
            market_data: Market data
            indicators: Calculated indicators
            action: Signal action ('BUY' or 'SELL')
            
        Returns:
            Confidence level (0.0 to 1.0)
        """
        # Default implementation - can be overridden by specific strategies
        return 0.7  # Medium confidence
    
    def update_position(self, new_position: str):
        """
        Update current position.
        
        Args:
            new_position: New position ('long', 'short', or None)
        """
        self.position = new_position
        logger.debug(f"{self.name} position updated to: {new_position}")
    
    def update_performance(self, trade_result: Dict[str, Any]):
        """
        Update strategy performance metrics.
        
        Args:
            trade_result: Trade result dictionary
        """
        self.performance_metrics['total_trades'] += 1
        
        pnl = trade_result.get('pnl', 0)
        self.performance_metrics['total_pnl'] += pnl
        
        if pnl > 0:
            self.performance_metrics['winning_trades'] += 1
        
        # Calculate win rate
        if self.performance_metrics['total_trades'] > 0:
            self.performance_metrics['win_rate'] = (
                self.performance_metrics['winning_trades'] / 
                self.performance_metrics['total_trades']
            ) * 100
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get strategy performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        return self.performance_metrics.copy()
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get strategy parameters.
        
        Returns:
            Parameters dictionary
        """
        return self.parameters.copy()
    
    def set_parameter(self, key: str, value: Any):
        """
        Set a strategy parameter.
        
        Args:
            key: Parameter key
            value: Parameter value
        """
        self.parameters[key] = value
        logger.debug(f"{self.name} parameter {key} set to {value}")
    
    def validate_market_data(self, market_data: List[Dict[str, Any]]) -> bool:
        """
        Validate market data before processing.
        
        Args:
            market_data: Market data to validate
            
        Returns:
            True if data is valid
        """
        if not market_data:
            return False
        
        required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        for candle in market_data[-5:]:  # Check last 5 candles
            for field in required_fields:
                if field not in candle:
                    logger.warning(f"Missing field {field} in market data")
                    return False
                
                if field != 'timestamp' and (candle[field] is None or candle[field] <= 0):
                    logger.warning(f"Invalid value for {field}: {candle[field]}")
                    return False
        
        return True
    
    def get_recent_signals(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent signals.
        
        Args:
            count: Number of recent signals to return
            
        Returns:
            List of recent signals
        """
        return self.signals_history[-count:] if self.signals_history else []
    
    def __str__(self) -> str:
        """String representation of the strategy."""
        return f"{self.name} Strategy (Position: {self.position})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the strategy."""
        return f"{self.name}(parameters={self.parameters}, position={self.position})"