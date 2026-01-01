"""
Multi-pair data fetching service for market data from exchanges.
"""

import ccxt
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import time
import logging
import threading

from config.settings import settings
from utils.logger import get_logger
from db.db_utils import db_manager

logger = get_logger(__name__)

class MultiPairDataFetcher:
    """Fetches market data for multiple cryptocurrency pairs."""
    
    def __init__(self):
        self.exchange = None
        self.pair_data = {}  # Store data per trading pair
        self.lock = threading.RLock()
        self.setup_exchange()
    
    def setup_exchange(self):
        """Initialize exchange connection."""
        try:
            # For paper trading, use public API only
            # For live trading, use private API with credentials
            from config.multi_crypto_config_manager import multi_crypto_config_manager
            paper_trading = multi_crypto_config_manager.get_system_config('paper_trading', True)
            
            if paper_trading:
                # Use public API for paper trading
                self.exchange = ccxt.okx({
                    'sandbox': False,
                    'enableRateLimit': True,
                })
                logger.info("Successfully connected to OKX exchange (public API for paper trading)")
            else:
                # Use private API for live trading
                self.exchange = ccxt.okx(settings.get_okx_config())
                logger.info("Successfully connected to OKX exchange (private API for live trading)")
                
        except Exception as e:
            logger.error(f"Failed to setup exchange: {e}")
            raise
    
    def _ensure_pair_data(self, symbol: str):
        """Ensure data structure exists for a trading pair."""
        with self.lock:
            if symbol not in self.pair_data:
                self.pair_data[symbol] = {
                    'price_history': [],
                    'ohlcv_history': [],
                    'last_update': None
                }
    
    def fetch_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current price for a specific trading pair.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Current price or None if error
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = float(ticker['last'])
            logger.debug(f"Fetched price for {symbol}: ${price:.2f}")
            
            # Update price history for this pair
            self._ensure_pair_data(symbol)
            with self.lock:
                self.pair_data[symbol]['price_history'].append(price)
                # Keep only last 200 prices
                if len(self.pair_data[symbol]['price_history']) > 200:
                    self.pair_data[symbol]['price_history'] = self.pair_data[symbol]['price_history'][-200:]
                self.pair_data[symbol]['last_update'] = datetime.now(timezone.utc)
            
            return price
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV data for a specific trading pair.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe (1m, 5m, 1h, etc.)
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV dictionaries
        """
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
    
    def update_ohlcv_history(self, symbol: str, ohlcv_data: List[Dict[str, Any]], max_history: int = 200):
        """
        Update OHLCV history for a specific pair.
        
        Args:
            symbol: Trading pair symbol
            ohlcv_data: List of OHLCV dictionaries
            max_history: Maximum number of candles to keep
        """
        self._ensure_pair_data(symbol)
        
        with self.lock:
            self.pair_data[symbol]['ohlcv_history'].extend(ohlcv_data)
            
            # Remove duplicates based on timestamp
            seen_timestamps = set()
            unique_data = []
            for candle in reversed(self.pair_data[symbol]['ohlcv_history']):
                if candle['timestamp'] not in seen_timestamps:
                    seen_timestamps.add(candle['timestamp'])
                    unique_data.append(candle)
            
            # Sort by timestamp and keep recent data
            self.pair_data[symbol]['ohlcv_history'] = sorted(unique_data, key=lambda x: x['timestamp'])[-max_history:]
            self.pair_data[symbol]['last_update'] = datetime.now(timezone.utc)
    
    def get_ohlcv_history(self, symbol: str) -> List[Dict[str, Any]]:
        """Get OHLCV history for a specific pair."""
        self._ensure_pair_data(symbol)
        with self.lock:
            return self.pair_data[symbol]['ohlcv_history'].copy()
    
    def get_price_list(self, symbol: str) -> List[float]:
        """Get list of close prices for a specific pair."""
        self._ensure_pair_data(symbol)
        with self.lock:
            ohlcv_history = self.pair_data[symbol]['ohlcv_history']
            if ohlcv_history:
                return [candle['close'] for candle in ohlcv_history]
            return self.pair_data[symbol]['price_history'].copy()
    
    def get_high_low_close_lists(self, symbol: str) -> tuple:
        """Get separate lists of high, low, and close prices for a specific pair."""
        self._ensure_pair_data(symbol)
        with self.lock:
            ohlcv_history = self.pair_data[symbol]['ohlcv_history']
            if ohlcv_history:
                highs = [candle['high'] for candle in ohlcv_history]
                lows = [candle['low'] for candle in ohlcv_history]
                closes = [candle['close'] for candle in ohlcv_history]
                return highs, lows, closes
            
            price_history = self.pair_data[symbol]['price_history']
            return [], [], price_history.copy()
    
    def save_market_data_to_db(self, symbol: str):
        """Save current market data to database for a specific pair."""
        try:
            # Get recent OHLCV data
            ohlcv_data = self.fetch_ohlcv(symbol, limit=1)
            
            if ohlcv_data:
                latest_candle = ohlcv_data[-1]
                
                # Use INSERT ... ON CONFLICT to handle duplicates
                success = db_manager.save_market_data_upsert(
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
            logger.error(f"Error saving market data for {symbol}: {e}")
    
    def fetch_account_balance(self) -> Dict[str, float]:
        """
        Fetch account balance from exchange.
        Note: In multi-crypto system, balance is managed at portfolio level.
        
        Returns:
            Dictionary with balance information
        """
        # In multi-crypto system, we don't use this method for balance tracking
        # Balance is managed through the database configuration system
        logger.warning("fetch_account_balance called - balance should be managed through portfolio system")
        
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
    
    def get_market_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get market information for a specific trading pair.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Market information dictionary
        """
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
    
    def is_market_open(self, symbol: str) -> bool:
        """
        Check if market is open for trading.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            True if market is open, False otherwise
        """
        # Crypto markets are typically open 24/7
        return True
    
    def get_all_pair_data(self) -> Dict[str, Dict[str, Any]]:
        """Get data for all tracked pairs."""
        with self.lock:
            return {
                symbol: {
                    'price_history_count': len(data['price_history']),
                    'ohlcv_history_count': len(data['ohlcv_history']),
                    'last_update': data['last_update']
                }
                for symbol, data in self.pair_data.items()
            }
    
    def clear_pair_data(self, symbol: str):
        """Clear data for a specific pair."""
        with self.lock:
            if symbol in self.pair_data:
                del self.pair_data[symbol]
                logger.info(f"Cleared data for {symbol}")

# Global multi-pair data fetcher instance
multi_pair_data_fetcher = MultiPairDataFetcher()