"""
Technical indicator calculations for trading strategies.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Technical indicator calculations."""
    
    @staticmethod
    def sma(prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Simple Moving Average.
        
        Args:
            prices: List of prices
            period: SMA period
            
        Returns:
            SMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    @staticmethod
    def ema(prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Exponential Moving Average.
        
        Args:
            prices: List of prices
            period: EMA period
            
        Returns:
            EMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        df = pd.DataFrame({'price': prices})
        ema_value = df['price'].ewm(span=period).mean().iloc[-1]
        return float(ema_value)
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            prices: List of prices
            period: RSI period (default 14)
            
        Returns:
            RSI value (0-100) or None if insufficient data
        """
        if len(prices) < period + 1:
            return None
        
        try:
            df = pd.DataFrame({'price': prices})
            delta = df['price'].diff()
            
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1])
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None
    
    @staticmethod
    def macd(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: List of prices
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line EMA period
            
        Returns:
            Tuple of (MACD line, Signal line, Histogram) or (None, None, None)
        """
        if len(prices) < slow_period + signal_period:
            return None, None, None
        
        try:
            df = pd.DataFrame({'price': prices})
            
            # Calculate EMAs
            ema_fast = df['price'].ewm(span=fast_period).mean()
            ema_slow = df['price'].ewm(span=slow_period).mean()
            
            # MACD line
            macd_line = ema_fast - ema_slow
            
            # Signal line
            signal_line = macd_line.ewm(span=signal_period).mean()
            
            # Histogram
            histogram = macd_line - signal_line
            
            return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return None, None, None
    
    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate Bollinger Bands.
        
        Args:
            prices: List of prices
            period: Moving average period
            std_dev: Standard deviation multiplier
            
        Returns:
            Tuple of (Upper band, Middle band, Lower band) or (None, None, None)
        """
        if len(prices) < period:
            return None, None, None
        
        try:
            df = pd.DataFrame({'price': prices})
            
            # Middle band (SMA)
            middle_band = df['price'].rolling(window=period).mean()
            
            # Standard deviation
            std = df['price'].rolling(window=period).std()
            
            # Upper and lower bands
            upper_band = middle_band + (std * std_dev)
            lower_band = middle_band - (std * std_dev)
            
            return float(upper_band.iloc[-1]), float(middle_band.iloc[-1]), float(lower_band.iloc[-1])
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return None, None, None
    
    @staticmethod
    def stochastic_oscillator(highs: List[float], lows: List[float], closes: List[float], k_period: int = 14, d_period: int = 3) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate Stochastic Oscillator.
        
        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            k_period: %K period
            d_period: %D period
            
        Returns:
            Tuple of (%K, %D) or (None, None)
        """
        if len(closes) < k_period or len(highs) < k_period or len(lows) < k_period:
            return None, None
        
        try:
            df = pd.DataFrame({
                'high': highs,
                'low': lows,
                'close': closes
            })
            
            # Calculate %K
            lowest_low = df['low'].rolling(window=k_period).min()
            highest_high = df['high'].rolling(window=k_period).max()
            k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
            
            # Calculate %D (SMA of %K)
            d_percent = k_percent.rolling(window=d_period).mean()
            
            return float(k_percent.iloc[-1]), float(d_percent.iloc[-1])
        except Exception as e:
            logger.error(f"Error calculating Stochastic Oscillator: {e}")
            return None, None
    
    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate Average True Range (ATR).
        
        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: ATR period
            
        Returns:
            ATR value or None if insufficient data
        """
        if len(closes) < period + 1 or len(highs) < period + 1 or len(lows) < period + 1:
            return None
        
        try:
            df = pd.DataFrame({
                'high': highs,
                'low': lows,
                'close': closes
            })
            
            # Calculate True Range
            df['prev_close'] = df['close'].shift(1)
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['prev_close'])
            df['tr3'] = abs(df['low'] - df['prev_close'])
            df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # Calculate ATR
            atr = df['tr'].rolling(window=period).mean()
            
            return float(atr.iloc[-1])
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return None
    
    @staticmethod
    def detect_sma_crossover(short_sma_history: List[float], long_sma_history: List[float]) -> str:
        """
        Detect SMA crossover signals.
        
        Args:
            short_sma_history: List of short SMA values
            long_sma_history: List of long SMA values
            
        Returns:
            'BUY' for golden cross, 'SELL' for death cross, 'HOLD' for no signal
        """
        if len(short_sma_history) < 2 or len(long_sma_history) < 2:
            return 'HOLD'
        
        # Current values
        short_current = short_sma_history[-1]
        long_current = long_sma_history[-1]
        
        # Previous values
        short_previous = short_sma_history[-2]
        long_previous = long_sma_history[-2]
        
        # Golden Cross: Short SMA crosses above Long SMA
        if short_previous <= long_previous and short_current > long_current:
            return 'BUY'
        
        # Death Cross: Short SMA crosses below Long SMA
        if short_previous >= long_previous and short_current < long_current:
            return 'SELL'
        
        return 'HOLD'
    
    @staticmethod
    def detect_rsi_signals(rsi: float, overbought: float = 70, oversold: float = 30) -> str:
        """
        Detect RSI signals.
        
        Args:
            rsi: Current RSI value
            overbought: Overbought threshold
            oversold: Oversold threshold
            
        Returns:
            'BUY' for oversold, 'SELL' for overbought, 'HOLD' for neutral
        """
        if rsi >= overbought:
            return 'SELL'
        elif rsi <= oversold:
            return 'BUY'
        else:
            return 'HOLD'

# Global indicators instance
indicators = TechnicalIndicators()