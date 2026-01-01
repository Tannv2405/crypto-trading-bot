"""
Risk management service for position sizing and risk controls.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import logging

from config.settings import settings
from utils.logger import get_logger
from db.db_utils import db_manager

logger = get_logger(__name__)

class RiskManager:
    """Manages trading risk and position sizing."""
    
    def __init__(self):
        self.max_daily_trades = 10
        self.max_daily_loss_percent = 5.0
        self.max_position_size_percent = 20.0
        self.daily_trades_count = 0
        self.daily_loss = 0.0
        self.last_reset_date = datetime.now(timezone.utc).date()
    
    def reset_daily_counters(self):
        """Reset daily counters if it's a new day."""
        current_date = datetime.now(timezone.utc).date()
        if current_date > self.last_reset_date:
            self.daily_trades_count = 0
            self.daily_loss = 0.0
            self.last_reset_date = current_date
            logger.info("Reset daily risk counters for new trading day")
    
    def can_place_trade(self, trade_type: str, current_balance: float) -> tuple[bool, str]:
        """
        Check if a trade can be placed based on risk rules.
        
        Args:
            trade_type: 'BUY' or 'SELL'
            current_balance: Current account balance
            
        Returns:
            Tuple of (can_trade, reason)
        """
        self.reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trades_count >= self.max_daily_trades:
            return False, f"Daily trade limit reached ({self.max_daily_trades})"
        
        # Check daily loss limit
        initial_balance = 10000.0  # Default initial balance for multi-crypto system
        daily_loss_percent = (self.daily_loss / initial_balance) * 100
        if daily_loss_percent >= self.max_daily_loss_percent:
            return False, f"Daily loss limit reached ({self.max_daily_loss_percent}%)"
        
        # Check minimum balance
        default_trade_size = 100.0  # Default trade size for multi-crypto system
        if current_balance < default_trade_size:
            return False, f"Insufficient balance for trade size (${default_trade_size})"
        
        return True, "Trade allowed"
    
    def calculate_position_size(self, price: float, balance: float, volatility: float = None) -> float:
        """
        Calculate optimal position size based on risk management rules.
        
        Args:
            price: Current asset price
            balance: Available balance
            volatility: Asset volatility (optional)
            
        Returns:
            Position size in asset units
        """
        try:
            # Base position size from default settings
            default_trade_size = 100.0  # Default trade size for multi-crypto system
            base_size_usd = min(default_trade_size, balance)
            
            # Adjust for maximum position size percentage
            max_position_usd = balance * (self.max_position_size_percent / 100)
            position_size_usd = min(base_size_usd, max_position_usd)
            
            # Adjust for volatility if provided
            if volatility and volatility > 0.05:  # High volatility (>5%)
                position_size_usd *= 0.7  # Reduce position size by 30%
                logger.info(f"Reduced position size due to high volatility ({volatility:.2%})")
            
            # Convert to asset units
            position_size = position_size_usd / price
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def calculate_stop_loss_price(self, entry_price: float, position_type: str) -> float:
        """
        Calculate stop loss price.
        
        Args:
            entry_price: Entry price of the position
            position_type: 'long' or 'short'
            
        Returns:
            Stop loss price
        """
        if position_type == 'long':
            return entry_price * (1 - settings.STOP_LOSS_PERCENT / 100)
        elif position_type == 'short':
            return entry_price * (1 + settings.STOP_LOSS_PERCENT / 100)
        else:
            return entry_price
    
    def calculate_take_profit_price(self, entry_price: float, position_type: str) -> float:
        """
        Calculate take profit price.
        
        Args:
            entry_price: Entry price of the position
            position_type: 'long' or 'short'
            
        Returns:
            Take profit price
        """
        if position_type == 'long':
            return entry_price * (1 + settings.TAKE_PROFIT_PERCENT / 100)
        elif position_type == 'short':
            return entry_price * (1 - settings.TAKE_PROFIT_PERCENT / 100)
        else:
            return entry_price
    
    def check_drawdown(self, current_balance: float, peak_balance: float) -> Dict[str, Any]:
        """
        Check current drawdown levels.
        
        Args:
            current_balance: Current account balance
            peak_balance: Peak account balance
            
        Returns:
            Dictionary with drawdown information
        """
        drawdown = peak_balance - current_balance
        drawdown_percent = (drawdown / peak_balance) * 100 if peak_balance > 0 else 0
        
        # Risk levels
        risk_level = "LOW"
        if drawdown_percent > 10:
            risk_level = "HIGH"
        elif drawdown_percent > 5:
            risk_level = "MEDIUM"
        
        return {
            'drawdown_amount': drawdown,
            'drawdown_percent': drawdown_percent,
            'risk_level': risk_level,
            'should_reduce_size': drawdown_percent > 10,
            'should_stop_trading': drawdown_percent > 20
        }
    
    def update_daily_stats(self, trade_result: Dict[str, Any]):
        """
        Update daily trading statistics.
        
        Args:
            trade_result: Trade result dictionary
        """
        self.reset_daily_counters()
        self.daily_trades_count += 1
        
        # Update daily loss if it's a losing trade
        if 'pnl' in trade_result and trade_result['pnl'] < 0:
            self.daily_loss += abs(trade_result['pnl'])
    
    def get_risk_metrics(self, symbol: str = None) -> Dict[str, Any]:
        """
        Get current risk metrics.
        
        Args:
            symbol: Trading symbol (optional)
            
        Returns:
            Dictionary with risk metrics
        """
        try:
            # Get recent trades from database
            recent_trades = db_manager.get_trade_history(symbol=symbol, limit=50)
            
            if not recent_trades:
                return {
                    'total_trades': 0,
                    'win_rate': 0.0,
                    'avg_profit': 0.0,
                    'avg_loss': 0.0,
                    'profit_factor': 0.0,
                    'max_consecutive_losses': 0,
                    'daily_trades_remaining': self.max_daily_trades - self.daily_trades_count
                }
            
            # Calculate metrics
            total_trades = len(recent_trades)
            winning_trades = 0
            total_profit = 0.0
            total_loss = 0.0
            consecutive_losses = 0
            max_consecutive_losses = 0
            
            for trade in recent_trades:
                # Calculate P&L (simplified)
                if trade.order_type == 'SELL':
                    # This is a simplified calculation
                    # In reality, you'd need to match buy/sell pairs
                    pnl = float(trade.total_value) - float(trade.price * trade.amount)
                    
                    if pnl > 0:
                        winning_trades += 1
                        total_profit += pnl
                        consecutive_losses = 0
                    else:
                        total_loss += abs(pnl)
                        consecutive_losses += 1
                        max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
            avg_loss = total_loss / (total_trades - winning_trades) if (total_trades - winning_trades) > 0 else 0
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_consecutive_losses': max_consecutive_losses,
                'daily_trades_count': self.daily_trades_count,
                'daily_trades_remaining': self.max_daily_trades - self.daily_trades_count,
                'daily_loss_percent': (self.daily_loss / 10000.0) * 100  # Default initial balance
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {}
    
    def should_reduce_position_size(self, recent_performance: Dict[str, Any]) -> bool:
        """
        Determine if position size should be reduced based on recent performance.
        
        Args:
            recent_performance: Recent performance metrics
            
        Returns:
            True if position size should be reduced
        """
        # Reduce size if win rate is low
        if recent_performance.get('win_rate', 100) < 30:
            return True
        
        # Reduce size if too many consecutive losses
        if recent_performance.get('max_consecutive_losses', 0) >= 3:
            return True
        
        # Reduce size if daily loss is high
        if recent_performance.get('daily_loss_percent', 0) > 3:
            return True
        
        return False
    
    def get_position_size_multiplier(self, recent_performance: Dict[str, Any]) -> float:
        """
        Get position size multiplier based on recent performance.
        
        Args:
            recent_performance: Recent performance metrics
            
        Returns:
            Multiplier for position size (0.5 to 1.5)
        """
        base_multiplier = 1.0
        
        # Reduce size for poor performance
        if self.should_reduce_position_size(recent_performance):
            base_multiplier = 0.5
        
        # Increase size for good performance (with caution)
        elif recent_performance.get('win_rate', 0) > 70 and recent_performance.get('total_trades', 0) > 10:
            base_multiplier = 1.2
        
        return base_multiplier
    
    def validate_trade_parameters(self, symbol: str, price: float, amount: float, order_type: str) -> tuple[bool, str]:
        """
        Validate trade parameters before execution.
        
        Args:
            symbol: Trading symbol
            price: Trade price
            amount: Trade amount
            order_type: 'BUY' or 'SELL'
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check price sanity
        if price <= 0:
            return False, "Invalid price: must be positive"
        
        # Check amount sanity
        if amount <= 0:
            return False, "Invalid amount: must be positive"
        
        # Check minimum trade size
        trade_value = price * amount
        if trade_value < 10:  # Minimum $10 trade
            return False, f"Trade value too small: ${trade_value:.2f} (minimum $10)"
        
        # Check maximum trade size
        default_trade_size = 100.0  # Default trade size for multi-crypto system
        if trade_value > default_trade_size * 2:
            return False, f"Trade value too large: ${trade_value:.2f} (maximum ${default_trade_size * 2})"
        
        return True, "Valid trade parameters"

# Global risk manager instance
risk_manager = RiskManager()