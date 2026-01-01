"""
Relative Strength Index (RSI) strategy implementation.
"""

from typing import Dict, List, Any, Tuple
import logging

from strategies.base_strategy import BaseStrategy
from utils.indicators import indicators
from utils.logger import get_logger

logger = get_logger(__name__)

class RSIStrategy(BaseStrategy):
    """
    RSI-based trading strategy.
    
    Strategy Rules:
    - Buy when RSI is below oversold threshold (default 30)
    - Sell when RSI is above overbought threshold (default 70)
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        """
        Initialize RSI strategy.
        
        Args:
            parameters: Strategy parameters from database configuration
        """
        # Default parameters (will be overridden by database config)
        default_params = {
            'rsi_period': 14,
            'overbought_threshold': 70,
            'oversold_threshold': 30,
            'min_data_points': 24  # rsi_period + 10
        }
        
        if parameters:
            default_params.update(parameters)
            # Recalculate min_data_points based on rsi_period
            default_params['min_data_points'] = default_params['rsi_period'] + 10
        
        super().__init__("RSI", default_params)
        
        # Strategy state
        self.rsi_history = []
        self.last_signal_type = None  # 'overbought' or 'oversold'
        self.signal_cooldown = 0  # Prevent rapid signals
    
    def calculate_signals(self, market_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate RSI indicator.
        
        Args:
            market_data: List of OHLCV data
            
        Returns:
            Dictionary with RSI values
        """
        if not self.validate_market_data(market_data):
            return {'rsi': None, 'current_price': None, 'rsi_level': None, 'rsi_momentum': None}
        
        # Check if we have enough data points for RSI calculation
        min_required = self.parameters.get('min_data_points', self.parameters['rsi_period'] + 10)
        if len(market_data) < min_required:
            logger.debug(f"RSI: Insufficient data points. Have {len(market_data)}, need {min_required}")
            return {'rsi': None, 'current_price': None, 'rsi_level': None, 'rsi_momentum': None}
        
        # Extract close prices
        close_prices = [candle['close'] for candle in market_data]
        
        # Calculate RSI
        rsi_value = indicators.rsi(close_prices, self.parameters['rsi_period'])
        
        # Update RSI history
        if rsi_value is not None:
            self.rsi_history.append(rsi_value)
            if len(self.rsi_history) > 100:  # Keep last 100 values
                self.rsi_history = self.rsi_history[-100:]
        
        # Decrease cooldown
        if self.signal_cooldown > 0:
            self.signal_cooldown -= 1
        
        return {
            'rsi': rsi_value,
            'current_price': close_prices[-1] if close_prices else None,
            'rsi_level': self._get_rsi_level(rsi_value) if rsi_value is not None else None,
            'rsi_momentum': self._get_rsi_momentum() if len(self.rsi_history) >= 3 else None
        }
    
    def should_buy(self, market_data: List[Dict[str, Any]], indicators: Dict[str, float]) -> Tuple[bool, str]:
        """
        Check for buy signal (RSI oversold).
        
        Args:
            market_data: Market data
            indicators: Calculated indicators
            
        Returns:
            Tuple of (should_buy, reason)
        """
        rsi_value = indicators.get('rsi')
        
        if rsi_value is None:
            return False, "RSI value not available"
        
        # Check cooldown to prevent rapid signals
        if self.signal_cooldown > 0:
            return False, f"Signal cooldown active ({self.signal_cooldown} periods remaining)"
        
        # Ensure rsi_value is a valid number before comparison
        try:
            rsi_float = float(rsi_value)
        except (TypeError, ValueError):
            return False, f"Invalid RSI value: {rsi_value}"
        
        # Buy when RSI is oversold
        if rsi_float <= self.parameters['oversold_threshold']:
            # Additional confirmation: RSI should be turning up
            rsi_momentum = indicators.get('rsi_momentum', 0)
            
            if rsi_momentum is not None and rsi_momentum > 0:  # RSI is increasing
                self.last_signal_type = 'oversold'
                self.signal_cooldown = 5  # 5-period cooldown
                return True, f"RSI oversold signal (RSI: {rsi_float:.1f}, momentum: positive)"
            else:
                return False, f"RSI oversold but momentum negative (RSI: {rsi_float:.1f})"
        
        return False, f"RSI not oversold (RSI: {rsi_float:.1f})"
    
    def should_sell(self, market_data: List[Dict[str, Any]], indicators: Dict[str, float]) -> Tuple[bool, str]:
        """
        Check for sell signal (RSI overbought).
        
        Args:
            market_data: Market data
            indicators: Calculated indicators
            
        Returns:
            Tuple of (should_sell, reason)
        """
        rsi_value = indicators.get('rsi')
        
        if rsi_value is None:
            return False, "RSI value not available"
        
        # Check cooldown to prevent rapid signals
        if self.signal_cooldown > 0:
            return False, f"Signal cooldown active ({self.signal_cooldown} periods remaining)"
        
        # Ensure rsi_value is a valid number before comparison
        try:
            rsi_float = float(rsi_value)
        except (TypeError, ValueError):
            return False, f"Invalid RSI value: {rsi_value}"
        
        # Sell when RSI is overbought
        if rsi_float >= self.parameters['overbought_threshold']:
            # Additional confirmation: RSI should be turning down
            rsi_momentum = indicators.get('rsi_momentum', 0)
            
            if rsi_momentum is not None and rsi_momentum < 0:  # RSI is decreasing
                self.last_signal_type = 'overbought'
                self.signal_cooldown = 5  # 5-period cooldown
                return True, f"RSI overbought signal (RSI: {rsi_float:.1f}, momentum: negative)"
            else:
                return False, f"RSI overbought but momentum positive (RSI: {rsi_float:.1f})"
        
        return False, f"RSI not overbought (RSI: {rsi_float:.1f})"
    
    def calculate_confidence(self, market_data: List[Dict[str, Any]], 
                           indicators: Dict[str, float], action: str) -> float:
        """
        Calculate confidence level for RSI signals.
        
        Args:
            market_data: Market data
            indicators: Calculated indicators
            action: Signal action
            
        Returns:
            Confidence level (0.0 to 1.0)
        """
        base_confidence = 0.5
        
        rsi_value = indicators.get('rsi')
        rsi_momentum = indicators.get('rsi_momentum', 0)
        
        if rsi_value is None:
            return 0.0
        
        # Increase confidence based on RSI extremes
        if action == 'BUY':
            # More extreme oversold = higher confidence
            if rsi_value <= 20:  # Very oversold
                base_confidence += 0.3
            elif rsi_value <= 25:  # Moderately oversold
                base_confidence += 0.2
            elif rsi_value <= 30:  # Oversold
                base_confidence += 0.1
        
        elif action == 'SELL':
            # More extreme overbought = higher confidence
            if rsi_value >= 80:  # Very overbought
                base_confidence += 0.3
            elif rsi_value >= 75:  # Moderately overbought
                base_confidence += 0.2
            elif rsi_value >= 70:  # Overbought
                base_confidence += 0.1
        
        # Increase confidence if momentum supports the signal
        if (action == 'BUY' and rsi_momentum > 2) or (action == 'SELL' and rsi_momentum < -2):
            base_confidence += 0.1
        
        # Check for RSI divergence (advanced feature)
        divergence_strength = self._check_rsi_divergence(market_data)
        if divergence_strength > 0:
            base_confidence += min(divergence_strength * 0.2, 0.2)
        
        return min(base_confidence, 1.0)
    
    def _get_rsi_level(self, rsi_value: float) -> str:
        """
        Get RSI level description.
        
        Args:
            rsi_value: RSI value
            
        Returns:
            RSI level string
        """
        if rsi_value >= 80:
            return "EXTREMELY_OVERBOUGHT"
        elif rsi_value >= 70:
            return "OVERBOUGHT"
        elif rsi_value >= 60:
            return "BULLISH"
        elif rsi_value >= 40:
            return "NEUTRAL"
        elif rsi_value >= 30:
            return "BEARISH"
        elif rsi_value >= 20:
            return "OVERSOLD"
        else:
            return "EXTREMELY_OVERSOLD"
    
    def _get_rsi_momentum(self) -> float:
        """
        Calculate RSI momentum (rate of change).
        
        Returns:
            RSI momentum value
        """
        if len(self.rsi_history) < 3:
            return 0.0
        
        # Calculate 3-period RSI momentum
        current_rsi = self.rsi_history[-1]
        previous_rsi = self.rsi_history[-3]
        
        return current_rsi - previous_rsi
    
    def _check_rsi_divergence(self, market_data: List[Dict[str, Any]]) -> float:
        """
        Check for RSI divergence with price.
        
        Args:
            market_data: Market data
            
        Returns:
            Divergence strength (0.0 to 1.0)
        """
        if len(self.rsi_history) < 10 or len(market_data) < 10:
            return 0.0
        
        try:
            # Get recent price and RSI data
            recent_prices = [candle['close'] for candle in market_data[-10:]]
            recent_rsi = self.rsi_history[-10:]
            
            # Simple divergence check: compare trends
            price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            rsi_trend = (recent_rsi[-1] - recent_rsi[0]) / recent_rsi[0]
            
            # Bullish divergence: price down, RSI up
            if price_trend < -0.02 and rsi_trend > 0.05:
                return min(abs(price_trend) + rsi_trend, 1.0)
            
            # Bearish divergence: price up, RSI down
            if price_trend > 0.02 and rsi_trend < -0.05:
                return min(price_trend + abs(rsi_trend), 1.0)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error checking RSI divergence: {e}")
            return 0.0
    
    def get_rsi_trend(self, periods: int = 5) -> str:
        """
        Get RSI trend over specified periods.
        
        Args:
            periods: Number of periods to analyze
            
        Returns:
            'RISING', 'FALLING', or 'SIDEWAYS'
        """
        if len(self.rsi_history) < periods:
            return 'SIDEWAYS'
        
        recent_rsi = self.rsi_history[-periods:]
        
        # Calculate trend
        rising_count = 0
        falling_count = 0
        
        for i in range(1, len(recent_rsi)):
            if recent_rsi[i] > recent_rsi[i-1]:
                rising_count += 1
            elif recent_rsi[i] < recent_rsi[i-1]:
                falling_count += 1
        
        if rising_count > falling_count * 1.5:
            return 'RISING'
        elif falling_count > rising_count * 1.5:
            return 'FALLING'
        else:
            return 'SIDEWAYS'
    
    def is_rsi_extreme(self) -> Tuple[bool, str]:
        """
        Check if RSI is at extreme levels.
        
        Returns:
            Tuple of (is_extreme, level_description)
        """
        if not self.rsi_history:
            return False, "No RSI data"
        
        current_rsi = self.rsi_history[-1]
        
        if current_rsi >= 80:
            return True, "Extremely Overbought"
        elif current_rsi <= 20:
            return True, "Extremely Oversold"
        elif current_rsi >= 70:
            return True, "Overbought"
        elif current_rsi <= 30:
            return True, "Oversold"
        else:
            return False, "Normal Range"
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """
        Get comprehensive strategy status.
        
        Returns:
            Strategy status dictionary
        """
        current_rsi = self.rsi_history[-1] if self.rsi_history else None
        
        # Handle None RSI values safely
        if current_rsi is not None:
            is_extreme, extreme_level = self.is_rsi_extreme()
            rsi_level = self._get_rsi_level(current_rsi)
            trend_direction = rsi_level
        else:
            is_extreme, extreme_level = False, "No RSI data"
            rsi_level = "N/A"
            trend_direction = "N/A"
        
        return {
            'strategy_name': self.name,
            'position': self.position,
            'trend_direction': trend_direction,
            'rsi_current': current_rsi,
            'rsi_level': rsi_level,
            'rsi_trend': self.get_rsi_trend(),
            'rsi_momentum': self._get_rsi_momentum(),
            'is_extreme': is_extreme,
            'extreme_level': extreme_level,
            'last_signal_type': self.last_signal_type,
            'signal_cooldown': self.signal_cooldown,
            'data_points_available': len(self.rsi_history),
            'parameters': self.parameters
        }