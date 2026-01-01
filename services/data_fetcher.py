"""
Data fetching service for market data from exchanges.
"""

import ccxt
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import time
import logging

from config.settings import settings
from utils.logger import get_logger
from db.db_utils import db_manager

logger = get_logger(__name__)

class DataFetcher:
    """Fetches market data from cryptocurrency exchanges."""
    
    def __init__(self):
        self.exchange = None
        self.price_history = []
        self.ohlcv_history = []
        self.setup_exchange()
    
    def setup_exchange(self):
        """Initialize exchange connection."""
        try:
            # Initialize OKX exchange
            self.exchange = ccxt.okx(settings.get_okx_config())
            
            # Test connection
            if not settings.PAPER_TRADING:
                balance = self.exchange.fetch_balance()
                logger.info("Successfully connected to OKX exchange")
            else:
                logger.info("Running in paper trading mode - using public API only")
                
        except Exception as e:
            logger.error(f"Failed to setup exchange: {e}")
            if not settings.PAPER_TRADING:
                raise
    
    def fetch_current_price(self, symbol: str = None) -> Optional[float]:
        """
        Fetch current price for the trading pair.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Current price or None if error
        """
        if not symbol:
            symbol = settings.TRADING_PAIR
            
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = float(ticker['last'])
            logger.debug(f"Fetched price for {symbol}: ${price:.2f}")
            return price
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    def fetch_ohlcv(self, symbol: str = None, timeframe: str = '1m', limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV data for the trading pair.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe (1m, 5m, 1h, etc.)
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV dictionaries
        """
        if not symbol:
            symbol = settings.TRADING_PAIR
            
        try:
            ohlcv_data = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            formatted_data = []
            for candle in ohlcv_data:
                formatted_data.append({
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            logger.debug(f"Fetched {len(formatted_data)} OHLCV candles for {symbol}")
            return formatted_data
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV data for {symbol}: {e}")
            return []
    
    def update_price_history(self, price: float, max_history: int = 200):
        """
        Update price history with new price.
        
        Args:
            price: New price to add
            max_history: Maximum number of prices to keep
        """
        self.price_history.append(price)
        
        # Keep only necessary history
        if len(self.price_history) > max_history:
            self.price_history = self.price_history[-max_history:]
    
    def update_ohlcv_history(self, ohlcv_data: List[Dict[str, Any]], max_history: int = 200):
        """
        Update OHLCV history with new data.
        
        Args:
            ohlcv_data: List of OHLCV dictionaries
            max_history: Maximum number of candles to keep
        """
        self.ohlcv_history.extend(ohlcv_data)
        
        # Remove duplicates based on timestamp
        seen_timestamps = set()
        unique_data = []
        for candle in reversed(self.ohlcv_history):
            if candle['timestamp'] not in seen_timestamps:
                seen_timestamps.add(candle['timestamp'])
                unique_data.append(candle)
        
        # Sort by timestamp and keep recent data
        self.ohlcv_history = sorted(unique_data, key=lambda x: x['timestamp'])[-max_history:]
    
    def get_price_list(self) -> List[float]:
        """Get list of close prices from OHLCV history."""
        if not self.ohlcv_history:
            return self.price_history
        return [candle['close'] for candle in self.ohlcv_history]
    
    def get_high_low_close_lists(self) -> tuple:
        """Get separate lists of high, low, and close prices."""
        if not self.ohlcv_history:
            return [], [], self.price_history
        
        highs = [candle['high'] for candle in self.ohlcv_history]
        lows = [candle['low'] for candle in self.ohlcv_history]
        closes = [candle['close'] for candle in self.ohlcv_history]
        
        return highs, lows, closes
    
    def save_market_data_to_db(self, symbol: str = None):
        """Save current market data to database."""
        if not symbol:
            symbol = settings.TRADING_PAIR
            
        try:
            # Get recent OHLCV data
            ohlcv_data = self.fetch_ohlcv(symbol, limit=1)
            
            if ohlcv_data:
                latest_candle = ohlcv_data[-1]
                success = db_manager.save_market_data(
                    symbol=symbol,
                    timestamp=latest_candle['timestamp'],
                    ohlcv={
                        'open': latest_candle['open'],
                        'high': latest_candle['high'],
                        'low': latest_candle['low'],
                        'close': latest_candle['close'],
                        'volume': latest_candle['volume']
                    }
                )
                
                if success:
                    logger.debug(f"Saved market data for {symbol} to database")
                else:
                    logger.warning(f"Failed to save market data for {symbol}")
                    
        except Exception as e:
            logger.error(f"Error saving market data to database: {e}")
    
    def fetch_account_balance(self) -> Dict[str, float]:
        """
        Fetch account balance from exchange.
        
        Returns:
            Dictionary with balance information
        """
        if settings.PAPER_TRADING:
            return {
                'USDT': settings.INITIAL_BALANCE,
                'BTC': 0.0,
                'total_usd': settings.INITIAL_BALANCE
            }
        
        try:
            balance = self.exchange.fetch_balance()
            return {
                'USDT': float(balance.get('USDT', {}).get('free', 0)),
                'BTC': float(balance.get('BTC', {}).get('free', 0)),
                'total_usd': float(balance.get('total', {}).get('USDT', 0))
            }
        except Exception as e:
            logger.error(f"Error fetching account balance: {e}")
            return {'USDT': 0.0, 'BTC': 0.0, 'total_usd': 0.0}
    
    def get_market_info(self, symbol: str = None) -> Dict[str, Any]:
        """
        Get market information for the trading pair.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Market information dictionary
        """
        if not symbol:
            symbol = settings.TRADING_PAIR
            
        try:
            market = self.exchange.market(symbol)
            ticker = self.exchange.fetch_ticker(symbol)
            
            return {
                'symbol': symbol,
                'base': market['base'],
                'quote': market['quote'],
                'current_price': float(ticker['last']),
                'bid': float(ticker['bid']) if ticker['bid'] else None,
                'ask': float(ticker['ask']) if ticker['ask'] else None,
                'volume_24h': float(ticker['baseVolume']) if ticker['baseVolume'] else None,
                'change_24h': float(ticker['change']) if ticker['change'] else None,
                'change_24h_percent': float(ticker['percentage']) if ticker['percentage'] else None,
                'min_order_size': market.get('limits', {}).get('amount', {}).get('min', 0),
                'max_order_size': market.get('limits', {}).get('amount', {}).get('max', float('inf')),
                'price_precision': market.get('precision', {}).get('price', 8),
                'amount_precision': market.get('precision', {}).get('amount', 8)
            }
        except Exception as e:
            logger.error(f"Error fetching market info for {symbol}: {e}")
            return {}
    
    def is_market_open(self, symbol: str = None) -> bool:
        """
        Check if market is open for trading.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            True if market is open, False otherwise
        """
        # Crypto markets are typically open 24/7
        # This method can be extended for other asset classes
        return True

# Global data fetcher instance
data_fetcher = DataFetcher()