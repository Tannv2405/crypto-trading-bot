"""
Simple Moving Average (SMA) crossover strategy implementation.
"""

from typing import Dict, List, Any, Tuple
import logging

from strategies.base_strategy import BaseStrategy
from utils.indicators import indicators
from utils.logger import get_logger

logger = get_logger(__name__)

class MovingAverageStrategy(BaseStrategy):
    """
    Simple Moving Average crossover strategy.
    
    Strategy Rules:
    - Buy when short SMA crosses above long SMA (Golden Cross)
    - Sell when short SMA crosses below long SMA (Death Cross)
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        """
        Initialize SMA strategy.
        
        Args:
            parameters: Strategy parameters from database configuration
        """
        # Default parameters (will be overridden by database config)
        default_params = {
            'short_period': 10,
            'long_period': 30,
            'min_data_points': 35  # long_period + 5
        }
        
        if parameters:
            default_params.update(parameters)
            # Recalculate min_data_points based on long_period
            default_params['min_data_points'] = default_params['long_period'] + 5
        
        super().__init__("SMA_Crossover", default_params)
        
        # Strategy state
        self.short_sma_history = []
        self.long_sma_history = []
        self.last_crossover_type = None  # 'golden' or 'death'
    
    def calculate_signals(self, market_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate SMA indicators.
        
        Args:
            market_data: List of OHLCV data
            
        Returns:
            Dictionary with SMA values
        """
        if not self.validate_market_data(market_data):
            return {}
        
        # Extract close prices
        close_prices = [candle['close'] for candle in market_data]
        
        # Calculate SMAs
        short_sma = indicators.sma(close_prices, self.parameters['short_period'])
        long_sma = indicators.sma(close_prices, self.parameters['long_period'])
        
        # Update SMA history
        if short_sma is not None:
            self.short_sma_history.append(short_sma)
            if len(self.short_sma_history) > 50:  # Keep last 50 values
                self.short_sma_history = self.short_sma_history[-50:]
        
        if long_sma is not None:
            self.long_sma_history.append(long_sma)
            if len(self.long_sma_history) > 50:  # Keep last 50 values
                self.long_sma_history = self.long_sma_history[-50:]
        
        return {
            'short_sma': short_sma,
            'long_sma': long_sma,
            'current_price': close_prices[-1] if close_prices else None,
            'sma_spread': (short_sma - long_sma) if (short_sma and long_sma) else None,
            'sma_spread_percent': ((short_sma - long_sma) / long_sma * 100) if (short_sma and long_sma) else None
        }
    
    def should_buy(self, market_data: List[Dict[str, Any]], indicators: Dict[str, float]) -> Tuple[bool, str]:
        """
        Check for buy signal (Golden Cross).
        
        Args:
            market_data: Market data
            indicators: Calculated indicators
            
        Returns:
            Tuple of (should_buy, reason)
        """
        short_sma = indicators.get('short_sma')
        long_sma = indicators.get('long_sma')
        
        if not short_sma or not long_sma:
            return False, "Insufficient data for SMA calculation"
        
        # Need at least 2 data points to detect crossover
        if len(self.short_sma_history) < 2 or len(self.long_sma_history) < 2:
            return False, "Insufficient SMA history for crossover detection"
        
        # Current values
        short_current = self.short_sma_history[-1]
        long_current = self.long_sma_history[-1]
        
        # Previous values
        short_previous = self.short_sma_history[-2]
        long_previous = self.long_sma_history[-2]
        
        # Golden Cross: Short SMA crosses above Long SMA
        if short_previous <= long_previous and short_current > long_current:
            spread_percent = ((short_current - long_current) / long_current) * 100
            self.last_crossover_type = 'golden'
            return True, f"Golden Cross detected (SMA spread: {spread_percent:.2f}%)"
        
        return False, "No golden cross detected"
    
    def should_sell(self, market_data: List[Dict[str, Any]], indicators: Dict[str, float]) -> Tuple[bool, str]:
        """
        Check for sell signal (Death Cross).
        
        Args:
            market_data: Market data
            indicators: Calculated indicators
            
        Returns:
            Tuple of (should_sell, reason)
        """
        short_sma = indicators.get('short_sma')
        long_sma = indicators.get('long_sma')
        
        if not short_sma or not long_sma:
            return False, "Insufficient data for SMA calculation"
        
        # Need at least 2 data points to detect crossover
        if len(self.short_sma_history) < 2 or len(self.long_sma_history) < 2:
            return False, "Insufficient SMA history for crossover detection"
        
        # Current values
        short_current = self.short_sma_history[-1]
        long_current = self.long_sma_history[-1]
        
        # Previous values
        short_previous = self.short_sma_history[-2]
        long_previous = self.long_sma_history[-2]
        
        # Death Cross: Short SMA crosses below Long SMA
        if short_previous >= long_previous and short_current < long_current:
            spread_percent = ((long_current - short_current) / long_current) * 100
            self.last_crossover_type = 'death'
            return True, f"Death Cross detected (SMA spread: {spread_percent:.2f}%)"
        
        return False, "No death cross detected"
    
    def calculate_confidence(self, market_data: List[Dict[str, Any]], 
                           indicators: Dict[str, float], action: str) -> float:
        """
        Calculate confidence level for SMA signals.
        
        Args:
            market_data: Market data
            indicators: Calculated indicators
            action: Signal action
            
        Returns:
            Confidence level (0.0 to 1.0)
        """
        base_confidence = 0.6
        
        short_sma = indicators.get('short_sma')
        long_sma = indicators.get('long_sma')
        current_price = indicators.get('current_price')
        
        if not all([short_sma, long_sma, current_price]):
            return 0.0
        
        # Increase confidence based on SMA spread
        sma_spread_percent = abs(((short_sma - long_sma) / long_sma) * 100)
        
        if sma_spread_percent > 2.0:  # Strong signal
            base_confidence += 0.2
        elif sma_spread_percent > 1.0:  # Medium signal
            base_confidence += 0.1
        
        # Increase confidence if price is aligned with signal
        if action == 'BUY' and current_price > short_sma > long_sma:
            base_confidence += 0.1
        elif action == 'SELL' and current_price < short_sma < long_sma:
            base_confidence += 0.1
        
        # Check volume confirmation if available
        if len(market_data) >= 2:
            current_volume = market_data[-1].get('volume', 0)
            previous_volume = market_data[-2].get('volume', 0)
            
            if current_volume > previous_volume * 1.2:  # 20% volume increase
                base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def get_trend_direction(self) -> str:
        """
        Get current trend direction based on SMA relationship.
        
        Returns:
            'BULLISH', 'BEARISH', or 'NEUTRAL'
        """
        if len(self.short_sma_history) == 0 or len(self.long_sma_history) == 0:
            return 'NEUTRAL'
        
        short_sma = self.short_sma_history[-1]
        long_sma = self.long_sma_history[-1]
        
        if short_sma > long_sma:
            return 'BULLISH'
        elif short_sma < long_sma:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
    
    def get_sma_divergence(self) -> float:
        """
        Get SMA divergence percentage.
        
        Returns:
            Divergence percentage (positive for bullish, negative for bearish)
        """
        if len(self.short_sma_history) == 0 or len(self.long_sma_history) == 0:
            return 0.0
        
        short_sma = self.short_sma_history[-1]
        long_sma = self.long_sma_history[-1]
        
        return ((short_sma - long_sma) / long_sma) * 100
    
    def is_in_consolidation(self, lookback_periods: int = 10) -> bool:
        """
        Check if SMAs are in consolidation (moving sideways).
        
        Args:
            lookback_periods: Number of periods to look back
            
        Returns:
            True if in consolidation
        """
        if len(self.short_sma_history) < lookback_periods or len(self.long_sma_history) < lookback_periods:
            return False
        
        # Calculate SMA volatility over lookback period
        short_sma_values = self.short_sma_history[-lookback_periods:]
        long_sma_values = self.long_sma_history[-lookback_periods:]
        
        short_volatility = (max(short_sma_values) - min(short_sma_values)) / min(short_sma_values)
        long_volatility = (max(long_sma_values) - min(long_sma_values)) / min(long_sma_values)
        
        # Consider consolidation if volatility is low (< 2%)
        return short_volatility < 0.02 and long_volatility < 0.02
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """
        Get comprehensive strategy status.
        
        Returns:
            Strategy status dictionary
        """
        return {
            'strategy_name': self.name,
            'position': self.position,
            'trend_direction': self.get_trend_direction(),
            'sma_divergence_percent': self.get_sma_divergence(),
            'last_crossover_type': self.last_crossover_type,
            'is_consolidating': self.is_in_consolidation(),
            'short_sma_current': self.short_sma_history[-1] if self.short_sma_history else None,
            'long_sma_current': self.long_sma_history[-1] if self.long_sma_history else None,
            'data_points_available': len(self.short_sma_history),
            'parameters': self.parameters
        }