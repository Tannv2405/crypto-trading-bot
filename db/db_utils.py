"""
Database utility functions and ORM models.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, UniqueConstraint
from sqlalchemy.types import Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging

from config.db_config import Base, SessionLocal

logger = logging.getLogger(__name__)

# ORM Models
class MarketData(Base):
    """Market data model for OHLCV data."""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    open_price = Column(Numeric(20, 8), nullable=False)
    high_price = Column(Numeric(20, 8), nullable=False)
    low_price = Column(Numeric(20, 8), nullable=False)
    close_price = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('symbol', 'timestamp', name='_symbol_timestamp_uc'),)

class TradeOrder(Base):
    """Trade order model."""
    __tablename__ = "trade_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    order_type = Column(String(10), nullable=False)  # BUY or SELL
    strategy = Column(String(50), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    total_value = Column(Numeric(20, 8), nullable=False)
    balance_usd = Column(Numeric(20, 8), nullable=False)
    balance_crypto = Column(Numeric(20, 8), nullable=False)
    short_sma = Column(Numeric(20, 8))
    long_sma = Column(Numeric(20, 8))
    rsi = Column(Numeric(10, 4))
    reason = Column(Text)
    is_paper_trade = Column(Boolean, default=True)
    exchange_order_id = Column(String(100))
    status = Column(String(20), default='PENDING')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class PortfolioSnapshot(Base):
    """Portfolio snapshot model."""
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    total_value_usd = Column(Numeric(20, 8), nullable=False)
    cash_balance = Column(Numeric(20, 8), nullable=False)
    crypto_balance = Column(Numeric(20, 8), nullable=False)
    current_price = Column(Numeric(20, 8), nullable=False)
    profit_loss = Column(Numeric(20, 8), nullable=False)
    profit_loss_percent = Column(Numeric(10, 4), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StrategyPerformance(Base):
    """Strategy performance model."""
    __tablename__ = "strategy_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_profit_loss = Column(Numeric(20, 8), default=0)
    win_rate = Column(Numeric(10, 4), default=0)
    avg_profit = Column(Numeric(20, 8), default=0)
    avg_loss = Column(Numeric(20, 8), default=0)
    max_drawdown = Column(Numeric(10, 4), default=0)
    sharpe_ratio = Column(Numeric(10, 4), default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (UniqueConstraint('strategy_name', 'symbol', name='_strategy_symbol_uc'),)

class BotStatus(Base):
    """Bot status model."""
    __tablename__ = "bot_status"
    
    id = Column(Integer, primary_key=True, index=True)
    bot_name = Column(String(50), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default='STOPPED')
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())
    current_position = Column(String(10))
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class EventLog(Base):
    """Event log model for comprehensive order and error tracking."""
    __tablename__ = "event_log"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)  # ORDER_ATTEMPT, ORDER_SUCCESS, ORDER_FAILED, etc.
    event_category = Column(String(30), nullable=False)  # TRADING, SYSTEM, ERROR, NOTIFICATION, STRATEGY
    symbol = Column(String(20))  # Trading pair (nullable for system events)
    strategy = Column(String(50))  # Strategy name (nullable for system events)
    severity = Column(String(20), default='INFO')  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)  # Human-readable event description
    details = Column(Text)  # JSON string for structured event data
    
    # Order-specific fields (nullable for non-order events)
    order_type = Column(String(10))  # BUY, SELL
    order_status = Column(String(20))  # PENDING, COMPLETED, FAILED, CANCELLED
    price = Column(Numeric(20, 8))
    amount = Column(Numeric(20, 8))
    total_value = Column(Numeric(20, 8))
    
    # Error-specific fields (nullable for non-error events)
    error_code = Column(String(50))
    error_message = Column(Text)
    stack_trace = Column(Text)
    
    # Context fields
    bot_name = Column(String(50), default='trading_bot')
    session_id = Column(String(100))
    correlation_id = Column(String(100))
    user_id = Column(String(50))
    
    # Metadata
    source_file = Column(String(100))
    source_function = Column(String(100))
    execution_time_ms = Column(Integer)
    
    # Timestamps
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Database utility functions
class DatabaseManager:
    """Database manager for common operations."""
    
    def __init__(self):
        self.session = None
    
    def get_session(self) -> Session:
        """Get database session."""
        if not self.session:
            self.session = SessionLocal()
        return self.session
    
    def close_session(self):
        """Close database session."""
        if self.session:
            self.session.close()
            self.session = None
    
    def save_market_data(self, symbol: str, timestamp: datetime, ohlcv: Dict[str, float]) -> bool:
        """Save market data to database."""
        try:
            session = self.get_session()
            market_data = MarketData(
                symbol=symbol,
                timestamp=timestamp,
                open_price=ohlcv['open'],
                high_price=ohlcv['high'],
                low_price=ohlcv['low'],
                close_price=ohlcv['close'],
                volume=ohlcv['volume']
            )
            session.merge(market_data)  # Use merge to handle duplicates
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving market data: {e}")
            session.rollback()
            return False
    
    def save_market_data_upsert(self, symbol: str, timestamp: datetime, ohlcv: Dict[str, float]) -> bool:
        """Save market data to database using INSERT ... ON CONFLICT to handle duplicates."""
        try:
            from sqlalchemy import text
            session = self.get_session()
            
            # Use raw SQL with ON CONFLICT to handle duplicates gracefully
            sql = text("""
                INSERT INTO market_data (symbol, timestamp, open_price, high_price, low_price, close_price, volume, created_at)
                VALUES (:symbol, :timestamp, :open_price, :high_price, :low_price, :close_price, :volume, NOW())
                ON CONFLICT (symbol, timestamp) 
                DO UPDATE SET 
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    created_at = NOW()
            """)
            
            session.execute(sql, {
                'symbol': symbol,
                'timestamp': timestamp,
                'open_price': float(ohlcv['open']),
                'high_price': float(ohlcv['high']),
                'low_price': float(ohlcv['low']),
                'close_price': float(ohlcv['close']),
                'volume': float(ohlcv['volume'])
            })
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving market data with upsert for {symbol}: {e}")
            session.rollback()
            return False
    
    def save_trade_order(self, trade_data: Dict[str, Any]) -> Optional[int]:
        """Save trade order to database."""
        try:
            session = self.get_session()
            trade_order = TradeOrder(**trade_data)
            session.add(trade_order)
            session.commit()
            session.refresh(trade_order)
            return trade_order.id
        except Exception as e:
            logger.error(f"Error saving trade order: {e}")
            session.rollback()
            return None
    
    def get_recent_market_data(self, symbol: str, limit: int = 100) -> List[MarketData]:
        """Get recent market data for a symbol."""
        try:
            session = self.get_session()
            return session.query(MarketData)\
                         .filter(MarketData.symbol == symbol)\
                         .order_by(MarketData.timestamp.desc())\
                         .limit(limit)\
                         .all()
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return []
    
    def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[TradeOrder]:
        """Get trade history."""
        try:
            session = self.get_session()
            query = session.query(TradeOrder)
            if symbol:
                query = query.filter(TradeOrder.symbol == symbol)
            return query.order_by(TradeOrder.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error fetching trade history: {e}")
            return []
    
    def save_portfolio_snapshot(self, snapshot_data: Dict[str, Any]) -> bool:
        """Save portfolio snapshot."""
        try:
            session = self.get_session()
            snapshot = PortfolioSnapshot(**snapshot_data)
            session.add(snapshot)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving portfolio snapshot: {e}")
            session.rollback()
            return False
    
    def update_bot_status(self, bot_name: str, status: str, position: str = None, error: str = None) -> bool:
        """Update bot status."""
        try:
            session = self.get_session()
            bot_status = session.query(BotStatus).filter(BotStatus.bot_name == bot_name).first()
            
            if not bot_status:
                bot_status = BotStatus(bot_name=bot_name)
                session.add(bot_status)
            
            bot_status.status = status
            bot_status.last_heartbeat = datetime.now(timezone.utc)
            if position:
                bot_status.current_position = position
            if error:
                bot_status.last_error = error
                bot_status.error_count += 1
            
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating bot status: {e}")
            session.rollback()
            return False
    
    def log_event(self, event_type: str, event_category: str, message: str, 
                  symbol: str = None, strategy: str = None, severity: str = 'INFO',
                  details: Dict[str, Any] = None, order_data: Dict[str, Any] = None,
                  error_data: Dict[str, Any] = None, context: Dict[str, Any] = None) -> Optional[int]:
        """
        Log an event to the event log table.
        
        Args:
            event_type: Type of event (ORDER_ATTEMPT, ORDER_SUCCESS, ORDER_FAILED, etc.)
            event_category: Category (TRADING, SYSTEM, ERROR, NOTIFICATION, STRATEGY)
            message: Human-readable event description
            symbol: Trading pair symbol (optional)
            strategy: Strategy name (optional)
            severity: Event severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            details: Additional structured data (optional)
            order_data: Order-specific data (optional)
            error_data: Error-specific data (optional)
            context: Context data (session_id, correlation_id, etc.) (optional)
            
        Returns:
            Event log ID if successful, None if failed
        """
        try:
            import json
            session = self.get_session()
            
            # Prepare event data
            event_log = EventLog(
                event_type=event_type,
                event_category=event_category,
                symbol=symbol,
                strategy=strategy,
                severity=severity,
                message=message,
                details=json.dumps(details) if details else None
            )
            
            # Add order-specific data if provided
            if order_data:
                event_log.order_type = order_data.get('order_type')
                event_log.order_status = order_data.get('order_status')
                event_log.price = order_data.get('price')
                event_log.amount = order_data.get('amount')
                event_log.total_value = order_data.get('total_value')
            
            # Add error-specific data if provided
            if error_data:
                event_log.error_code = error_data.get('error_code')
                event_log.error_message = error_data.get('error_message')
                event_log.stack_trace = error_data.get('stack_trace')
            
            # Add context data if provided
            if context:
                event_log.bot_name = context.get('bot_name', 'trading_bot')
                event_log.session_id = context.get('session_id')
                event_log.correlation_id = context.get('correlation_id')
                event_log.user_id = context.get('user_id')
                event_log.source_file = context.get('source_file')
                event_log.source_function = context.get('source_function')
                event_log.execution_time_ms = context.get('execution_time_ms')
            
            session.add(event_log)
            session.commit()
            session.refresh(event_log)
            return event_log.id
            
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            session.rollback()
            return None
    
    def log_order_attempt(self, symbol: str, order_type: str, strategy: str, 
                         price: float, amount: float, reason: str,
                         correlation_id: str = None) -> Optional[int]:
        """Log an order attempt event."""
        return self.log_event(
            event_type='ORDER_ATTEMPT',
            event_category='TRADING',
            message=f"Attempting {order_type} order for {symbol}: {amount:.6f} at ${price:.2f}",
            symbol=symbol,
            strategy=strategy,
            severity='INFO',
            details={'reason': reason},
            order_data={
                'order_type': order_type,
                'order_status': 'PENDING',
                'price': price,
                'amount': amount,
                'total_value': price * amount
            },
            context={'correlation_id': correlation_id}
        )
    
    def log_order_success(self, symbol: str, order_type: str, strategy: str,
                         price: float, amount: float, order_id: str = None,
                         correlation_id: str = None) -> Optional[int]:
        """Log a successful order event."""
        return self.log_event(
            event_type='ORDER_SUCCESS',
            event_category='TRADING',
            message=f"{order_type} order completed for {symbol}: {amount:.6f} at ${price:.2f}",
            symbol=symbol,
            strategy=strategy,
            severity='INFO',
            details={'exchange_order_id': order_id},
            order_data={
                'order_type': order_type,
                'order_status': 'COMPLETED',
                'price': price,
                'amount': amount,
                'total_value': price * amount
            },
            context={'correlation_id': correlation_id}
        )
    
    def log_order_failed(self, symbol: str, order_type: str, strategy: str,
                        price: float, amount: float, error: str,
                        correlation_id: str = None) -> Optional[int]:
        """Log a failed order event."""
        return self.log_event(
            event_type='ORDER_FAILED',
            event_category='TRADING',
            message=f"{order_type} order failed for {symbol}: {error}",
            symbol=symbol,
            strategy=strategy,
            severity='ERROR',
            order_data={
                'order_type': order_type,
                'order_status': 'FAILED',
                'price': price,
                'amount': amount,
                'total_value': price * amount
            },
            error_data={
                'error_code': 'ORDER_EXECUTION_FAILED',
                'error_message': error
            },
            context={'correlation_id': correlation_id}
        )
    
    def log_strategy_signal(self, symbol: str, strategy: str, signal: str,
                           indicators: Dict[str, Any], reason: str) -> Optional[int]:
        """Log a strategy signal event."""
        return self.log_event(
            event_type='SIGNAL_GENERATED',
            event_category='STRATEGY',
            message=f"{strategy} generated {signal} signal for {symbol}: {reason}",
            symbol=symbol,
            strategy=strategy,
            severity='INFO',
            details={
                'signal': signal,
                'indicators': indicators,
                'reason': reason
            }
        )
    
    def log_error(self, error_code: str, error_message: str, 
                  symbol: str = None, strategy: str = None,
                  stack_trace: str = None, context: Dict[str, Any] = None) -> Optional[int]:
        """Log an error event."""
        return self.log_event(
            event_type='ERROR',
            event_category='ERROR',
            message=f"Error occurred: {error_message}",
            symbol=symbol,
            strategy=strategy,
            severity='ERROR',
            error_data={
                'error_code': error_code,
                'error_message': error_message,
                'stack_trace': stack_trace
            },
            context=context
        )
    
    def log_system_event(self, event_type: str, message: str, 
                        severity: str = 'INFO', details: Dict[str, Any] = None) -> Optional[int]:
        """Log a system event."""
        return self.log_event(
            event_type=event_type,
            event_category='SYSTEM',
            message=message,
            severity=severity,
            details=details
        )
    
    def get_event_logs(self, limit: int = 100, event_type: str = None, 
                      symbol: str = None, severity: str = None,
                      start_date: datetime = None, end_date: datetime = None) -> List[EventLog]:
        """
        Get event logs with optional filtering.
        
        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type (optional)
            symbol: Filter by trading pair (optional)
            severity: Filter by severity level (optional)
            start_date: Filter events after this date (optional)
            end_date: Filter events before this date (optional)
            
        Returns:
            List of EventLog objects
        """
        try:
            session = self.get_session()
            query = session.query(EventLog)
            
            # Apply filters
            if event_type:
                query = query.filter(EventLog.event_type == event_type)
            if symbol:
                query = query.filter(EventLog.symbol == symbol)
            if severity:
                query = query.filter(EventLog.severity == severity)
            if start_date:
                query = query.filter(EventLog.event_timestamp >= start_date)
            if end_date:
                query = query.filter(EventLog.event_timestamp <= end_date)
            
            return query.order_by(EventLog.event_timestamp.desc()).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error fetching event logs: {e}")
            return []
    
    def get_order_history_from_events(self, symbol: str = None, limit: int = 50) -> List[EventLog]:
        """Get order history from event logs."""
        try:
            session = self.get_session()
            query = session.query(EventLog).filter(
                EventLog.event_category == 'TRADING',
                EventLog.event_type.in_(['ORDER_ATTEMPT', 'ORDER_SUCCESS', 'ORDER_FAILED'])
            )
            
            if symbol:
                query = query.filter(EventLog.symbol == symbol)
            
            return query.order_by(EventLog.event_timestamp.desc()).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error fetching order history from events: {e}")
            return []

# Global database manager instance
db_manager = DatabaseManager()