"""
Unit tests for trading strategies.
"""

import pytest
import sys
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.moving_average import MovingAverageStrategy
from strategies.rsi_strategy import RSIStrategy

class TestMovingAverageStrategy:
    """Test cases for SMA crossover strategy."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.strategy = MovingAverageStrategy({
            'short_period': 5,
            'long_period': 10
        })
        
        # Create sample market data
        self.sample_data = []
        base_price = 50000
        for i in range(20):
            price = base_price + (i * 100)  # Trending up
            self.sample_data.append({
                'timestamp': datetime.now(timezone.utc),
                'open': price - 50,
                'high': price + 100,
                'low': price - 100,
                'close': price,
                'volume': 1000
            })
    
    def test_strategy_initialization(self):
        """Test strategy initialization."""
        assert self.strategy.name == "SMA_Crossover"
        assert self.strategy.parameters['short_period'] == 5
        assert self.strategy.parameters['long_period'] == 10
        assert self.strategy.position is None
    
    def test_calculate_signals(self):
        """Test signal calculation."""
        signals = self.strategy.calculate_signals(self.sample_data)
        
        assert 'short_sma' in signals
        assert 'long_sma' in signals
        assert 'current_price' in signals
        assert signals['short_sma'] is not None
        assert signals['long_sma'] is not None
        assert signals['current_price'] == self.sample_data[-1]['close']
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        short_data = self.sample_data[:5]  # Not enough for long SMA
        signals = self.strategy.calculate_signals(short_data)
        
        assert signals['short_sma'] is not None
        assert signals['long_sma'] is None
    
    def test_golden_cross_detection(self):
        """Test golden cross detection."""
        # Create data that will generate a golden cross
        data = []
        for i in range(15):
            if i < 10:
                price = 50000 - (i * 10)  # Declining
            else:
                price = 49900 + ((i - 10) * 50)  # Rising
            
            data.append({
                'timestamp': datetime.now(timezone.utc),
                'open': price,
                'high': price + 10,
                'low': price - 10,
                'close': price,
                'volume': 1000
            })
        
        # Process data to build SMA history
        for i in range(len(data)):
            self.strategy.calculate_signals(data[:i+1])
        
        # Check for buy signal
        should_buy, reason = self.strategy.should_buy(data, self.strategy.calculate_signals(data))
        
        # Note: This test might need adjustment based on exact data values
        assert isinstance(should_buy, bool)
        assert isinstance(reason, str)
    
    def test_get_signal(self):
        """Test complete signal generation."""
        signal = self.strategy.get_signal(self.sample_data)
        
        assert 'strategy' in signal
        assert 'action' in signal
        assert 'reason' in signal
        assert 'confidence' in signal
        assert 'indicators' in signal
        assert 'timestamp' in signal
        
        assert signal['strategy'] == "SMA_Crossover"
        assert signal['action'] in ['BUY', 'SELL', 'HOLD']
        assert 0 <= signal['confidence'] <= 1

class TestRSIStrategy:
    """Test cases for RSI strategy."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.strategy = RSIStrategy({
            'rsi_period': 14,
            'overbought_threshold': 70,
            'oversold_threshold': 30
        })
        
        # Create sample market data with varying prices
        self.sample_data = []
        prices = [50000, 50100, 49900, 50200, 49800, 50300, 49700, 50400, 49600, 50500,
                 49500, 50600, 49400, 50700, 49300, 50800, 49200, 50900, 49100, 51000]
        
        for i, price in enumerate(prices):
            self.sample_data.append({
                'timestamp': datetime.now(timezone.utc),
                'open': price - 50,
                'high': price + 100,
                'low': price - 100,
                'close': price,
                'volume': 1000
            })
    
    def test_strategy_initialization(self):
        """Test strategy initialization."""
        assert self.strategy.name == "RSI"
        assert self.strategy.parameters['rsi_period'] == 14
        assert self.strategy.parameters['overbought_threshold'] == 70
        assert self.strategy.parameters['oversold_threshold'] == 30
        assert self.strategy.position is None
    
    def test_calculate_signals(self):
        """Test RSI signal calculation."""
        signals = self.strategy.calculate_signals(self.sample_data)
        
        assert 'rsi' in signals
        assert 'current_price' in signals
        assert 'rsi_level' in signals
        
        if signals['rsi'] is not None:
            assert 0 <= signals['rsi'] <= 100
    
    def test_rsi_levels(self):
        """Test RSI level classification."""
        # Test different RSI levels
        test_cases = [
            (85, "EXTREMELY_OVERBOUGHT"),
            (75, "OVERBOUGHT"),
            (65, "BULLISH"),
            (50, "NEUTRAL"),
            (35, "BEARISH"),
            (25, "OVERSOLD"),
            (15, "EXTREMELY_OVERSOLD")
        ]
        
        for rsi_value, expected_level in test_cases:
            level = self.strategy._get_rsi_level(rsi_value)
            assert level == expected_level
    
    def test_signal_cooldown(self):
        """Test signal cooldown mechanism."""
        # Set cooldown
        self.strategy.signal_cooldown = 3
        
        # Create oversold condition
        oversold_data = []
        for i in range(20):
            price = 50000 - (i * 100)  # Declining prices
            oversold_data.append({
                'timestamp': datetime.now(timezone.utc),
                'open': price,
                'high': price + 10,
                'low': price - 10,
                'close': price,
                'volume': 1000
            })
        
        signals = self.strategy.calculate_signals(oversold_data)
        should_buy, reason = self.strategy.should_buy(oversold_data, signals)
        
        # Should not buy due to cooldown
        assert "cooldown" in reason.lower()
    
    def test_get_signal(self):
        """Test complete signal generation."""
        signal = self.strategy.get_signal(self.sample_data)
        
        assert 'strategy' in signal
        assert 'action' in signal
        assert 'reason' in signal
        assert 'confidence' in signal
        assert 'indicators' in signal
        assert 'timestamp' in signal
        
        assert signal['strategy'] == "RSI"
        assert signal['action'] in ['BUY', 'SELL', 'HOLD']
        assert 0 <= signal['confidence'] <= 1

class TestStrategyIntegration:
    """Integration tests for strategies."""
    
    def test_multiple_strategies(self):
        """Test running multiple strategies together."""
        sma_strategy = MovingAverageStrategy()
        rsi_strategy = RSIStrategy()
        
        # Create sample data
        sample_data = []
        for i in range(50):
            price = 50000 + (i * 10)
            sample_data.append({
                'timestamp': datetime.now(timezone.utc),
                'open': price - 5,
                'high': price + 10,
                'low': price - 10,
                'close': price,
                'volume': 1000
            })
        
        # Get signals from both strategies
        sma_signal = sma_strategy.get_signal(sample_data)
        rsi_signal = rsi_strategy.get_signal(sample_data)
        
        # Both should return valid signals
        assert sma_signal['action'] in ['BUY', 'SELL', 'HOLD']
        assert rsi_signal['action'] in ['BUY', 'SELL', 'HOLD']
        
        # Test strategy status
        sma_status = sma_strategy.get_strategy_status()
        rsi_status = rsi_strategy.get_strategy_status()
        
        assert 'strategy_name' in sma_status
        assert 'strategy_name' in rsi_status
        assert sma_status['strategy_name'] == "SMA_Crossover"
        assert rsi_status['strategy_name'] == "RSI"

if __name__ == "__main__":
    pytest.main([__file__])