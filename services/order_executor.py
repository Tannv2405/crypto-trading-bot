"""
Order execution service for placing and managing trades.
"""

import ccxt
from datetime import datetime, timezone
from typing import Dict, Optional, Any
import logging

from config.settings import settings
from utils.logger import get_logger
from db.db_utils import db_manager
from services.multi_pair_data_fetcher import multi_pair_data_fetcher

logger = get_logger(__name__)

class OrderExecutor:
    """Handles order execution and trade management."""
    
    def __init__(self):
        self.exchange = multi_pair_data_fetcher.exchange
        self.position = None  # 'long', 'short', or None
        # Use default balance - this should be managed by portfolio system
        self.balance_usd = 10000.0  # Default paper trading balance
        self.balance_crypto = 0.0
        self.entry_price = None
        self.entry_time = None
    
    def _get_paper_trading_setting(self) -> bool:
        """Get paper trading setting from database configuration."""
        try:
            from config.multi_crypto_config_manager import multi_crypto_config_manager
            return multi_crypto_config_manager.get_system_config('paper_trading', True)
        except Exception as e:
            logger.warning(f"Could not get paper_trading setting, defaulting to True: {e}")
            return True
    
    def execute_buy_order(self, symbol: str, price: float, amount: float, strategy: str, 
                         indicators: Dict[str, float], reason: str) -> Optional[Dict[str, Any]]:
        """
        Execute a buy order.
        
        Args:
            symbol: Trading pair symbol
            price: Current price
            amount: Amount to buy (in crypto units)
            strategy: Strategy name
            indicators: Technical indicators values
            reason: Reason for the trade
            
        Returns:
            Order result dictionary or None if failed
        """
        try:
            total_cost = amount * price
            
            # Check if we have enough balance
            if total_cost > self.balance_usd:
                logger.warning(f"Insufficient balance for buy order. Need: ${total_cost:.2f}, Have: ${self.balance_usd:.2f}")
                return None
            
            order_result = None
            paper_trading = self._get_paper_trading_setting()
            
            if paper_trading:
                # Paper trading
                self.balance_usd -= total_cost
                self.balance_crypto += amount
                self.position = 'long'
                self.entry_price = price
                self.entry_time = datetime.now(timezone.utc)
                
                order_result = {
                    'id': f"paper_{datetime.now().timestamp()}",
                    'symbol': symbol,
                    'type': 'market',
                    'side': 'buy',
                    'amount': amount,
                    'price': price,
                    'cost': total_cost,
                    'status': 'closed',
                    'timestamp': datetime.now(timezone.utc)
                }
                
                logger.info(f"PAPER BUY: {amount:.6f} {symbol.split('/')[0]} at ${price:.2f} (Total: ${total_cost:.2f})")
                
            else:
                # Live trading (demo account)
                logger.info(f"LIVE BUY ORDER: Placing {amount:.6f} {symbol} at market price ${price:.2f}")
                
                order = self.exchange.create_market_buy_order(symbol, amount)
                self.position = 'long'
                self.entry_price = price
                self.entry_time = datetime.now(timezone.utc)
                
                # Update balances based on actual order
                if order and order.get('status') == 'closed':
                    actual_cost = float(order.get('cost', total_cost))
                    actual_amount = float(order.get('filled', amount))
                    self.balance_usd -= actual_cost
                    self.balance_crypto += actual_amount
                
                order_result = order
                logger.info(f"LIVE BUY ORDER COMPLETED: {order}")
            
            # Save to database
            trade_data = {
                'symbol': symbol,
                'order_type': 'BUY',
                'strategy': strategy,
                'price': price,
                'amount': amount,
                'total_value': total_cost,
                'balance_usd': self.balance_usd,
                'balance_crypto': self.balance_crypto,
                'short_sma': indicators.get('short_sma'),
                'long_sma': indicators.get('long_sma'),
                'rsi': indicators.get('rsi'),
                'reason': reason,
                'is_paper_trade': paper_trading,
                'exchange_order_id': order_result.get('id') if order_result else None,
                'status': 'COMPLETED'
            }
            
            trade_id = db_manager.save_trade_order(trade_data)
            if trade_id:
                logger.debug(f"Saved buy order to database with ID: {trade_id}")
            
            return order_result
            
        except Exception as e:
            logger.error(f"Error executing buy order: {e}")
            return None
    
    def execute_sell_order(self, symbol: str, price: float, amount: float, strategy: str,
                          indicators: Dict[str, float], reason: str) -> Optional[Dict[str, Any]]:
        """
        Execute a sell order.
        
        Args:
            symbol: Trading pair symbol
            price: Current price
            amount: Amount to sell (in crypto units)
            strategy: Strategy name
            indicators: Technical indicators values
            reason: Reason for the trade
            
        Returns:
            Order result dictionary or None if failed
        """
        try:
            if amount > self.balance_crypto:
                logger.warning(f"Insufficient crypto balance for sell order. Need: {amount:.6f}, Have: {self.balance_crypto:.6f}")
                return None
            
            total_value = amount * price
            order_result = None
            paper_trading = self._get_paper_trading_setting()
            
            if paper_trading:
                # Paper trading
                self.balance_usd += total_value
                self.balance_crypto -= amount
                self.position = None
                
                order_result = {
                    'id': f"paper_{datetime.now().timestamp()}",
                    'symbol': symbol,
                    'type': 'market',
                    'side': 'sell',
                    'amount': amount,
                    'price': price,
                    'cost': total_value,
                    'status': 'closed',
                    'timestamp': datetime.now(timezone.utc)
                }
                
                logger.info(f"PAPER SELL: {amount:.6f} {symbol.split('/')[0]} at ${price:.2f} (Total: ${total_value:.2f})")
                
            else:
                # Live trading (demo account)
                logger.info(f"LIVE SELL ORDER: Placing {amount:.6f} {symbol} at market price ${price:.2f}")
                
                order = self.exchange.create_market_sell_order(symbol, amount)
                self.position = None
                
                # Update balances based on actual order
                if order and order.get('status') == 'closed':
                    actual_value = float(order.get('cost', total_value))
                    actual_amount = float(order.get('filled', amount))
                    self.balance_usd += actual_value
                    self.balance_crypto -= actual_amount
                
                order_result = order
                logger.info(f"LIVE SELL ORDER COMPLETED: {order}")
            
            # Save to database
            trade_data = {
                'symbol': symbol,
                'order_type': 'SELL',
                'strategy': strategy,
                'price': price,
                'amount': amount,
                'total_value': total_value,
                'balance_usd': self.balance_usd,
                'balance_crypto': self.balance_crypto,
                'short_sma': indicators.get('short_sma'),
                'long_sma': indicators.get('long_sma'),
                'rsi': indicators.get('rsi'),
                'reason': reason,
                'is_paper_trade': paper_trading,
                'exchange_order_id': order_result.get('id') if order_result else None,
                'status': 'COMPLETED'
            }
            
            trade_id = db_manager.save_trade_order(trade_data)
            if trade_id:
                logger.debug(f"Saved sell order to database with ID: {trade_id}")
            
            return order_result
            
        except Exception as e:
            logger.error(f"Error executing sell order: {e}")
            return None
    
    def calculate_position_size(self, price: float, risk_percent: float = 2.0) -> float:
        """
        Calculate position size based on risk management.
        
        Args:
            price: Current price
            risk_percent: Risk percentage of total balance
            
        Returns:
            Position size in crypto units
        """
        try:
            # Use default trade size for multi-crypto system
            default_trade_size = 100.0  # Default $100 per trade
            trade_size_usd = min(default_trade_size, self.balance_usd)
            position_size = trade_size_usd / price
            
            # Apply minimum order size constraints
            min_order_size = 0.001  # Default minimum order size
            
            if position_size < min_order_size:
                logger.warning(f"Calculated position size {position_size:.6f} is below minimum {min_order_size:.6f}")
                return 0.0
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def check_stop_loss(self, current_price: float) -> bool:
        """
        Check if stop loss should be triggered.
        
        Args:
            current_price: Current market price
            
        Returns:
            True if stop loss should be triggered
        """
        if not self.position or not self.entry_price:
            return False
        
        if self.position == 'long':
            price_change_percent = ((current_price - self.entry_price) / self.entry_price) * 100
            default_stop_loss = 5.0  # Default 5% stop loss
            return price_change_percent <= -default_stop_loss
        
        return False
    
    def check_take_profit(self, current_price: float) -> bool:
        """
        Check if take profit should be triggered.
        
        Args:
            current_price: Current market price
            
        Returns:
            True if take profit should be triggered
        """
        if not self.position or not self.entry_price:
            return False
        
        if self.position == 'long':
            price_change_percent = ((current_price - self.entry_price) / self.entry_price) * 100
            default_take_profit = 10.0  # Default 10% take profit
            return price_change_percent >= default_take_profit
        
        return False
    
    def get_portfolio_value(self, current_price: float) -> float:
        """
        Calculate total portfolio value in USD.
        
        Args:
            current_price: Current market price
            
        Returns:
            Total portfolio value in USD
        """
        return self.balance_usd + (self.balance_crypto * current_price)
    
    def get_profit_loss(self, current_price: float) -> Dict[str, float]:
        """
        Calculate profit/loss information.
        
        Args:
            current_price: Current market price
            
        Returns:
            Dictionary with P&L information
        """
        portfolio_value = self.get_portfolio_value(current_price)
        initial_balance = 10000.0  # Default initial balance for multi-crypto system
        profit_loss = portfolio_value - initial_balance
        profit_loss_percent = (profit_loss / initial_balance) * 100
        
        unrealized_pnl = 0.0
        unrealized_pnl_percent = 0.0
        
        if self.position == 'long' and self.entry_price:
            unrealized_pnl = (current_price - self.entry_price) * self.balance_crypto
            unrealized_pnl_percent = ((current_price - self.entry_price) / self.entry_price) * 100
        
        return {
            'total_pnl': profit_loss,
            'total_pnl_percent': profit_loss_percent,
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pnl_percent': unrealized_pnl_percent,
            'portfolio_value': portfolio_value
        }
    
    def save_portfolio_snapshot(self, current_price: float):
        """
        Save current portfolio snapshot to database.
        
        Args:
            current_price: Current market price
        """
        try:
            pnl_info = self.get_profit_loss(current_price)
            
            snapshot_data = {
                'timestamp': datetime.now(timezone.utc),
                'total_value_usd': pnl_info['portfolio_value'],
                'cash_balance': self.balance_usd,
                'crypto_balance': self.balance_crypto,
                'current_price': current_price,
                'profit_loss': pnl_info['total_pnl'],
                'profit_loss_percent': pnl_info['total_pnl_percent']
            }
            
            success = db_manager.save_portfolio_snapshot(snapshot_data)
            if success:
                logger.debug("Saved portfolio snapshot to database")
            
        except Exception as e:
            logger.error(f"Error saving portfolio snapshot: {e}")
    
    def get_position_info(self) -> Dict[str, Any]:
        """
        Get current position information.
        
        Returns:
            Dictionary with position information
        """
        return {
            'position': self.position,
            'balance_usd': self.balance_usd,
            'balance_crypto': self.balance_crypto,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time
        }

# Global order executor instance
order_executor = OrderExecutor()