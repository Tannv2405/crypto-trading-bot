"""
Unit tests for database functionality.
"""

import pytest
import sys
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_utils import DatabaseManager, MarketData, TradeOrder, PortfolioSnapshot

class TestDatabaseManager:
    """Test cases for database manager."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.db_manager = DatabaseManager()
    
    @patch('db.db_utils.SessionLocal')
    def test_save_market_data(self, mock_session_local):
        """Test saving market data."""
        # Mock session
        mock_session = Mock()
        mock_session_local.return_value = mock_session
        
        # Test data
        symbol = "BTC/USDT"
        timestamp = datetime.now(timezone.utc)
        ohlcv = {
            'open': 50000.0,
            'high': 50500.0,
            'low': 49500.0,
            'close': 50200.0,
            'volume': 1000.0
        }
        
        # Test successful save
        result = self.db_manager.save_market_data(symbol, timestamp, ohlcv)
        
        # Verify session methods were called
        mock_session.merge.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Should return True for success
        assert result is True
    
    @patch('db.db_utils.SessionLocal')
    def test_save_trade_order(self, mock_session_local):
        """Test saving trade order."""
        # Mock session
        mock_session = Mock()
        mock_session_local.return_value = mock_session
        
        # Mock trade order with ID
        mock_trade_order = Mock()
        mock_trade_order.id = 123
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        
        # Patch the TradeOrder constructor to return our mock
        with patch('db.db_utils.TradeOrder', return_value=mock_trade_order):
            trade_data = {
                'symbol': 'BTC/USDT',
                'order_type': 'BUY',
                'strategy': 'SMA',
                'price': Decimal('50000.00'),
                'amount': Decimal('0.001'),
                'total_value': Decimal('50.00'),
                'balance_usd': Decimal('10000.00'),
                'balance_crypto': Decimal('0.001'),
                'reason': 'Test trade'
            }
            
            result = self.db_manager.save_trade_order(trade_data)
            
            # Verify session methods were called
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once()
            
            # Should return the trade ID
            assert result == 123
    
    @patch('db.db_utils.SessionLocal')
    def test_get_recent_market_data(self, mock_session_local):
        """Test fetching recent market data."""
        # Mock session and query
        mock_session = Mock()
        mock_query = Mock()
        mock_session_local.return_value = mock_session
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        # Mock market data results
        mock_market_data = [Mock(), Mock(), Mock()]
        mock_query.all.return_value = mock_market_data
        
        result = self.db_manager.get_recent_market_data("BTC/USDT", limit=100)
        
        # Verify query was built correctly
        mock_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.limit.assert_called_once_with(100)
        mock_query.all.assert_called_once()
        
        # Should return the mock data
        assert result == mock_market_data
    
    @patch('db.db_utils.SessionLocal')
    def test_update_bot_status(self, mock_session_local):
        """Test updating bot status."""
        # Mock session and query
        mock_session = Mock()
        mock_query = Mock()
        mock_session_local.return_value = mock_session
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Test case 1: Existing bot status
        mock_bot_status = Mock()
        mock_query.first.return_value = mock_bot_status
        
        result = self.db_manager.update_bot_status("test_bot", "RUNNING", "long", "No error")
        
        # Verify status was updated
        assert mock_bot_status.status == "RUNNING"
        assert mock_bot_status.current_position == "long"
        assert mock_bot_status.last_error == "No error"
        mock_session.commit.assert_called_once()
        assert result is True
        
        # Reset mocks
        mock_session.reset_mock()
        
        # Test case 2: New bot status
        mock_query.first.return_value = None
        
        with patch('db.db_utils.BotStatus') as mock_bot_status_class:
            mock_new_status = Mock()
            mock_bot_status_class.return_value = mock_new_status
            
            result = self.db_manager.update_bot_status("new_bot", "STARTED")
            
            # Verify new status was created and added
            mock_bot_status_class.assert_called_once_with(bot_name="new_bot")
            mock_session.add.assert_called_once_with(mock_new_status)
            mock_session.commit.assert_called_once()
            assert result is True

class TestDatabaseModels:
    """Test database ORM models."""
    
    def test_market_data_model(self):
        """Test MarketData model."""
        timestamp = datetime.now(timezone.utc)
        market_data = MarketData(
            symbol="BTC/USDT",
            timestamp=timestamp,
            open_price=Decimal('50000.00'),
            high_price=Decimal('50500.00'),
            low_price=Decimal('49500.00'),
            close_price=Decimal('50200.00'),
            volume=Decimal('1000.00')
        )
        
        assert market_data.symbol == "BTC/USDT"
        assert market_data.timestamp == timestamp
        assert market_data.open_price == Decimal('50000.00')
        assert market_data.close_price == Decimal('50200.00')
    
    def test_trade_order_model(self):
        """Test TradeOrder model."""
        trade_order = TradeOrder(
            symbol="BTC/USDT",
            order_type="BUY",
            strategy="SMA",
            price=Decimal('50000.00'),
            amount=Decimal('0.001'),
            total_value=Decimal('50.00'),
            balance_usd=Decimal('10000.00'),
            balance_crypto=Decimal('0.001'),
            reason="Test trade"
        )
        
        assert trade_order.symbol == "BTC/USDT"
        assert trade_order.order_type == "BUY"
        assert trade_order.strategy == "SMA"
        assert trade_order.price == Decimal('50000.00')
        assert trade_order.is_paper_trade is True  # Default value
    
    def test_portfolio_snapshot_model(self):
        """Test PortfolioSnapshot model."""
        timestamp = datetime.now(timezone.utc)
        snapshot = PortfolioSnapshot(
            timestamp=timestamp,
            total_value_usd=Decimal('10050.00'),
            cash_balance=Decimal('9950.00'),
            crypto_balance=Decimal('0.002'),
            current_price=Decimal('50000.00'),
            profit_loss=Decimal('50.00'),
            profit_loss_percent=Decimal('0.50')
        )
        
        assert snapshot.timestamp == timestamp
        assert snapshot.total_value_usd == Decimal('10050.00')
        assert snapshot.profit_loss == Decimal('50.00')

class TestDatabaseIntegration:
    """Integration tests for database functionality."""
    
    @pytest.mark.integration
    def test_database_connection(self):
        """Test actual database connection (requires running PostgreSQL)."""
        # This test requires a real database connection
        # Skip if not in integration test mode
        pytest.skip("Integration test - requires running PostgreSQL")
        
        from config.db_config import test_connection
        
        # This would test actual database connectivity
        result = test_connection()
        assert result is True
    
    @pytest.mark.integration
    def test_full_database_workflow(self):
        """Test complete database workflow."""
        # This test requires a real database connection
        pytest.skip("Integration test - requires running PostgreSQL")
        
        db_manager = DatabaseManager()
        
        # Test saving market data
        symbol = "BTC/USDT"
        timestamp = datetime.now(timezone.utc)
        ohlcv = {
            'open': 50000.0,
            'high': 50500.0,
            'low': 49500.0,
            'close': 50200.0,
            'volume': 1000.0
        }
        
        success = db_manager.save_market_data(symbol, timestamp, ohlcv)
        assert success is True
        
        # Test retrieving market data
        recent_data = db_manager.get_recent_market_data(symbol, limit=1)
        assert len(recent_data) >= 1
        
        # Test saving trade order
        trade_data = {
            'symbol': symbol,
            'order_type': 'BUY',
            'strategy': 'TEST',
            'price': Decimal('50000.00'),
            'amount': Decimal('0.001'),
            'total_value': Decimal('50.00'),
            'balance_usd': Decimal('10000.00'),
            'balance_crypto': Decimal('0.001'),
            'reason': 'Integration test'
        }
        
        trade_id = db_manager.save_trade_order(trade_data)
        assert trade_id is not None
        
        # Test retrieving trade history
        trades = db_manager.get_trade_history(symbol, limit=1)
        assert len(trades) >= 1

if __name__ == "__main__":
    pytest.main([__file__])