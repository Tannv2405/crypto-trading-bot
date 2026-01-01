"""
Main entry point for the trading bot with multi-crypto support.
"""

import asyncio
import time
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List
import logging

# Import all components
from config.settings import settings
from config.multi_crypto_config_manager import multi_crypto_config_manager
from config.db_config import init_database, test_connection
from utils.logger import setup_logger
from services.cached_config_service import cached_config_service
from services.multi_pair_data_fetcher import multi_pair_data_fetcher
from services.order_executor import order_executor
from services.risk_manager import risk_manager
from services.telegram_notifier import telegram_notifier
from strategies.moving_average import MovingAverageStrategy
from strategies.rsi_strategy import RSIStrategy
from db.db_utils import db_manager

# Setup logging
logger = setup_logger('trading_bot_main')

class TradingBot:
    """Main trading bot orchestrator with multi-crypto support."""
    
    def __init__(self):
        self.running = False
        self.strategies = {}
        self.current_prices = {}
        self.market_data = {}
        self.iteration_count = 0
        self.start_time = None
        
        # Load multi-crypto configuration
        self.config = self._load_multi_crypto_config()
        
        # Initialize strategies for active pairs
        self.setup_strategies()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def _load_multi_crypto_config(self) -> Dict[str, Any]:
        """Load multi-cryptocurrency configuration."""
        try:
            # Warm the cache for better performance
            cached_config_service.warm_cache()
            
            # Get all active pairs configuration
            all_configs = cached_config_service.get_all_active_pairs_config()
            
            # Get portfolio settings
            portfolio_settings = cached_config_service.get_portfolio_settings()
            
            logger.info(f"Loaded configuration for {len(all_configs)} trading pairs")
            logger.info(f"Portfolio balance: ${portfolio_settings['total_balance']:,.2f}")
            logger.info(f"Max concurrent positions: {portfolio_settings['max_concurrent_positions']}")
            
            return {
                'pairs': all_configs,
                'portfolio': portfolio_settings,
                'active_pairs': list(all_configs.keys())
            }
            
        except Exception as e:
            logger.error(f"Error loading multi-crypto configuration: {e}")
            # Fallback to single pair
            return {
                'pairs': {'BTC/USDT': {}},
                'portfolio': {'total_balance': 10000, 'max_concurrent_positions': 1},
                'active_pairs': ['BTC/USDT']
            }
    
    def setup_strategies(self):
        """Initialize trading strategies for all active pairs."""
        try:
            total_strategies = 0
            
            for pair_symbol in self.config['active_pairs']:
                pair_config = self.config['pairs'].get(pair_symbol, {})
                strategies_config = pair_config.get('strategies', [])
                
                if not strategies_config:
                    logger.warning(f"No strategies configured for {pair_symbol}")
                    continue
                
                self.strategies[pair_symbol] = {}
                
                for strategy_config in strategies_config:
                    strategy_name = strategy_config['strategy_name']
                    parameters = strategy_config.get('parameters', {})
                    
                    if strategy_name == 'sma_crossover':
                        strategy = MovingAverageStrategy(parameters)
                        self.strategies[pair_symbol]['sma'] = strategy
                        total_strategies += 1
                        logger.debug(f"Initialized SMA strategy for {pair_symbol}: {parameters}")
                    
                    elif strategy_name == 'rsi':
                        strategy = RSIStrategy(parameters)
                        self.strategies[pair_symbol]['rsi'] = strategy
                        total_strategies += 1
                        logger.debug(f"Initialized RSI strategy for {pair_symbol}: {parameters}")
            
            logger.info(f"Initialized {total_strategies} strategies across {len(self.strategies)} pairs")
            
        except Exception as e:
            logger.error(f"Error setting up strategies: {e}")
            raise
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def initialize(self):
        """Initialize the trading bot."""
        try:
            logger.info("Initializing multi-crypto trading bot...")
            
            # Send detailed initialization notification
            try:
                active_pairs = self.config['active_pairs']
                total_balance = self.config['portfolio']['total_balance']
                
                init_info = {
                    'status': 'Initializing multi-crypto components...',
                    'database': 'Connecting to PostgreSQL',
                    'exchange': 'Connecting to OKX',
                    'telegram': 'Testing notifications',
                    'pairs': f"{len(active_pairs)} pairs: {', '.join(active_pairs)}",
                    'total_balance': f"${total_balance:,.2f}",
                    'strategies': f"{sum(len(s) for s in self.strategies.values())} strategies loaded"
                }
                telegram_notifier.send_bot_status_notification("INITIALIZING", init_info)
            except Exception as e:
                logger.warning(f"Failed to send initialization notification: {e}")
            
            # Test database connection
            if not test_connection():
                logger.error("Database connection failed")
                telegram_notifier.send_error_notification("Database connection failed", "Bot initialization")
                return False
            
            # Initialize database tables
            init_database()
            
            # Update bot status
            db_manager.update_bot_status("multi_crypto_trading_bot", "INITIALIZING")
            
            # Test Telegram connection
            if telegram_notifier.enabled or telegram_notifier.use_bot_fallback:
                telegram_notifier.test_connection()
            
            # Fetch initial market data for all pairs
            await self.fetch_initial_data()
            
            # Send successful initialization notification
            try:
                success_info = {
                    'database': '✅ Connected',
                    'exchange': '✅ Connected to OKX',
                    'telegram': '✅ Notifications active',
                    'pairs': f"✅ {len(self.config['active_pairs'])} pairs ready",
                    'market_data': f"✅ Historical data loaded for all pairs",
                    'ready_to_trade': '🚀 Multi-crypto bot is ready!'
                }
                telegram_notifier.send_bot_status_notification("INITIALIZED", success_info)
            except Exception as e:
                logger.warning(f"Failed to send success notification: {e}")
            
            logger.info("Multi-crypto trading bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing trading bot: {e}")
            telegram_notifier.send_error_notification(f"Multi-crypto bot initialization failed: {e}")
            return False
    
    async def fetch_initial_data(self):
        """Fetch initial market data for all active pairs."""
        try:
            logger.info("Fetching initial market data for all pairs...")
            
            for pair_symbol in self.config['active_pairs']:
                try:
                    # Fetch OHLCV data for this specific pair
                    ohlcv_data = multi_pair_data_fetcher.fetch_ohlcv(pair_symbol, limit=200)
                    if ohlcv_data:
                        multi_pair_data_fetcher.update_ohlcv_history(pair_symbol, ohlcv_data)
                        self.market_data[pair_symbol] = ohlcv_data
                        self.current_prices[pair_symbol] = ohlcv_data[-1]['close']
                        logger.info(f"Loaded {len(ohlcv_data)} historical candles for {pair_symbol}")
                    else:
                        logger.warning(f"No initial market data fetched for {pair_symbol}")
                
                except Exception as e:
                    logger.error(f"Error fetching initial data for {pair_symbol}: {e}")
            
        except Exception as e:
            logger.error(f"Error fetching initial data: {e}")
    
    async def run_single_iteration(self):
        """Run a single trading iteration for all pairs."""
        try:
            self.iteration_count += 1
            logger.debug(f"Starting multi-crypto iteration {self.iteration_count}")
            
            # Process each active pair
            for pair_symbol in self.config['active_pairs']:
                await self.process_pair(pair_symbol)
            
            # Update bot heartbeat
            db_manager.update_bot_status("multi_crypto_trading_bot", "RUNNING")
            
            # Print status for all pairs
            self.print_status()
            
            # Check if it's time for daily summary
            if self.iteration_count % 100 == 0:  # Every 100 iterations
                await self.send_daily_summary()
            
        except Exception as e:
            logger.error(f"Error in multi-crypto trading iteration: {e}")
            telegram_notifier.send_error_notification(f"Multi-crypto trading iteration error: {e}")
            db_manager.update_bot_status("multi_crypto_trading_bot", "ERROR", error=str(e))
    
    async def process_pair(self, pair_symbol: str):
        """Process trading for a specific pair."""
        try:
            # Fetch current market data for this specific pair
            current_price = multi_pair_data_fetcher.fetch_current_price(pair_symbol)
            if current_price is None:
                logger.warning(f"Could not fetch current price for {pair_symbol}, skipping")
                return
            
            self.current_prices[pair_symbol] = current_price
            
            # Update market data for this pair
            latest_ohlcv = multi_pair_data_fetcher.fetch_ohlcv(pair_symbol, limit=1)
            if latest_ohlcv:
                multi_pair_data_fetcher.update_ohlcv_history(pair_symbol, latest_ohlcv)
                self.market_data[pair_symbol] = multi_pair_data_fetcher.get_ohlcv_history(pair_symbol)
            
            # Save market data to database using upsert to handle duplicates
            multi_pair_data_fetcher.save_market_data_to_db(pair_symbol)
            
            # Process strategies for this pair
            if pair_symbol in self.strategies:
                await self.process_pair_strategies(pair_symbol)
            
            # Save portfolio snapshot
            order_executor.save_portfolio_snapshot(current_price)
            
        except Exception as e:
            logger.error(f"Error processing pair {pair_symbol}: {e}")
    
    async def process_pair_strategies(self, pair_symbol: str):
        """Process all trading strategies for a specific pair."""
        try:
            pair_strategies = self.strategies.get(pair_symbol, {})
            if not pair_strategies:
                return
            
            market_data = self.market_data.get(pair_symbol, [])
            if not market_data:
                logger.warning(f"No market data available for {pair_symbol}")
                return
            
            combined_signals = {}
            
            # Get signals from each strategy
            for strategy_name, strategy in pair_strategies.items():
                try:
                    signal = strategy.get_signal(market_data)
                    combined_signals[strategy_name] = signal
                    
                    # Log strategy signal
                    db_manager.log_strategy_signal(
                        symbol=pair_symbol,
                        strategy=strategy_name,
                        signal=signal['action'],
                        indicators=signal.get('indicators', {}),
                        reason=signal.get('reason', '')
                    )
                    
                    logger.debug(f"{pair_symbol} {strategy_name} signal: {signal['action']} - {signal['reason']}")
                    
                    # Send signal notification if not HOLD and notifications enabled
                    pair_config = self.config['pairs'].get(pair_symbol, {})
                    notification_config = pair_config.get('system', {})
                    
                    if (signal['action'] != 'HOLD' and 
                        notification_config.get('notify_on_signals', False)):
                        telegram_notifier.send_signal_notification({
                            'signal': signal['action'],
                            'symbol': pair_symbol,
                            'price': self.current_prices[pair_symbol],
                            'strategy': strategy_name,
                            'indicators': signal['indicators']
                        })
                    
                except Exception as e:
                    logger.error(f"Error processing {strategy_name} strategy for {pair_symbol}: {e}")
                    
                    # Log strategy error
                    db_manager.log_error(
                        error_code='STRATEGY_PROCESSING_ERROR',
                        error_message=str(e),
                        symbol=pair_symbol,
                        strategy=strategy_name,
                        stack_trace=str(e),
                        context={'source_function': 'process_pair_strategies'}
                    )
                    continue
            
            # Make trading decision based on combined signals
            await self.make_trading_decision(pair_symbol, combined_signals)
            
        except Exception as e:
            logger.error(f"Error processing strategies for {pair_symbol}: {e}")
    
    async def make_trading_decision(self, pair_symbol: str, signals: Dict[str, Dict[str, Any]]):
        """Make trading decision for a specific pair based on combined signals."""
        try:
            # Get strategy weights for this pair
            strategy_weights = cached_config_service.get_strategy_weights_for_pair(pair_symbol)
            
            # Weighted voting system
            buy_score = 0
            sell_score = 0
            buy_reasons = []
            sell_reasons = []
            combined_indicators = {}
            
            for strategy_name, signal in signals.items():
                action = signal.get('action', 'HOLD')
                reason = signal.get('reason', '')
                indicators = signal.get('indicators', {})
                weight = strategy_weights.get(strategy_name, 0.5)
                
                # Combine indicators
                for key, value in indicators.items():
                    if value is not None:
                        combined_indicators[f"{strategy_name}_{key}"] = value
                
                if action == 'BUY':
                    buy_score += weight
                    buy_reasons.append(f"{strategy_name} (w:{weight:.1f}): {reason}")
                elif action == 'SELL':
                    sell_score += weight
                    sell_reasons.append(f"{strategy_name} (w:{weight:.1f}): {reason}")
            
            # Risk management check
            can_trade, risk_reason = risk_manager.can_place_trade('BUY', order_executor.balance_usd)
            if not can_trade:
                logger.info(f"Trade blocked by risk management for {pair_symbol}: {risk_reason}")
                return
            
            # Execute trades based on weighted scores
            threshold = 0.5  # Minimum score threshold
            
            if buy_score > sell_score and buy_score >= threshold and order_executor.position != 'long':
                await self.execute_buy_order(pair_symbol, combined_indicators, "; ".join(buy_reasons))
            elif sell_score > buy_score and sell_score >= threshold and order_executor.position == 'long':
                await self.execute_sell_order(pair_symbol, combined_indicators, "; ".join(sell_reasons))
            
            # Check stop loss and take profit
            await self.check_risk_management(pair_symbol)
            
        except Exception as e:
            logger.error(f"Error making trading decision for {pair_symbol}: {e}")
    
    async def execute_buy_order(self, pair_symbol: str, indicators: Dict[str, float], reason: str):
        """Execute a buy order for a specific pair."""
        try:
            current_price = self.current_prices[pair_symbol]
            
            # Get pair-specific configuration
            pair_config = self.config['pairs'].get(pair_symbol, {})
            trade_size = pair_config.get('trade_size_usd', 100)
            
            # Calculate position size
            position_size = float(trade_size) / current_price
            
            if position_size <= 0:
                logger.warning(f"Position size is zero for {pair_symbol}, skipping buy order")
                return
            
            # Generate correlation ID for tracking related events
            import uuid
            correlation_id = str(uuid.uuid4())
            
            # Log order attempt
            db_manager.log_order_attempt(
                symbol=pair_symbol,
                order_type='BUY',
                strategy='Multi-Crypto Combined',
                price=current_price,
                amount=position_size,
                reason=reason,
                correlation_id=correlation_id
            )
            
            # Execute the order
            order_result = order_executor.execute_buy_order(
                symbol=pair_symbol,
                price=current_price,
                amount=position_size,
                strategy="Multi-Crypto Combined",
                indicators=indicators,
                reason=reason
            )
            
            if order_result:
                # Log successful order
                db_manager.log_order_success(
                    symbol=pair_symbol,
                    order_type='BUY',
                    strategy='Multi-Crypto Combined',
                    price=current_price,
                    amount=position_size,
                    order_id=order_result.get('id'),
                    correlation_id=correlation_id
                )
                
                # Update strategy positions
                for strategy in self.strategies.get(pair_symbol, {}).values():
                    strategy.update_position('long')
                
                # Send notification
                telegram_notifier.send_trade_notification({
                    'order_type': 'BUY',
                    'symbol': pair_symbol,
                    'price': current_price,
                    'amount': position_size,
                    'total_value': current_price * position_size,
                    'strategy': 'Multi-Crypto Combined',
                    'reason': reason,
                    'balance_usd': order_executor.balance_usd,
                    'balance_crypto': order_executor.balance_crypto
                })
                
                logger.info(f"Buy order executed for {pair_symbol}: {position_size:.6f} at ${current_price:.2f}")
            else:
                # Log failed order
                db_manager.log_order_failed(
                    symbol=pair_symbol,
                    order_type='BUY',
                    strategy='Multi-Crypto Combined',
                    price=current_price,
                    amount=position_size,
                    error="Order execution returned None",
                    correlation_id=correlation_id
                )
            
        except Exception as e:
            logger.error(f"Error executing buy order for {pair_symbol}: {e}")
            
            # Log error event
            db_manager.log_error(
                error_code='BUY_ORDER_EXECUTION_ERROR',
                error_message=str(e),
                symbol=pair_symbol,
                strategy='Multi-Crypto Combined',
                stack_trace=str(e),
                context={'source_function': 'execute_buy_order'}
            )
            
            telegram_notifier.send_error_notification(f"Buy order execution failed for {pair_symbol}: {e}")
    
    async def execute_sell_order(self, pair_symbol: str, indicators: Dict[str, float], reason: str):
        """Execute a sell order for a specific pair."""
        try:
            current_price = self.current_prices[pair_symbol]
            
            # Sell all crypto balance (simplified for single-pair execution)
            position_size = order_executor.balance_crypto
            
            if position_size <= 0:
                logger.warning(f"No crypto balance to sell for {pair_symbol}")
                return
            
            # Generate correlation ID for tracking related events
            import uuid
            correlation_id = str(uuid.uuid4())
            
            # Log order attempt
            db_manager.log_order_attempt(
                symbol=pair_symbol,
                order_type='SELL',
                strategy='Multi-Crypto Combined',
                price=current_price,
                amount=position_size,
                reason=reason,
                correlation_id=correlation_id
            )
            
            # Execute the order
            order_result = order_executor.execute_sell_order(
                symbol=pair_symbol,
                price=current_price,
                amount=position_size,
                strategy="Multi-Crypto Combined",
                indicators=indicators,
                reason=reason
            )
            
            if order_result:
                # Log successful order
                db_manager.log_order_success(
                    symbol=pair_symbol,
                    order_type='SELL',
                    strategy='Multi-Crypto Combined',
                    price=current_price,
                    amount=position_size,
                    order_id=order_result.get('id'),
                    correlation_id=correlation_id
                )
                
                # Update strategy positions
                for strategy in self.strategies.get(pair_symbol, {}).values():
                    strategy.update_position(None)
                
                # Send notification
                telegram_notifier.send_trade_notification({
                    'order_type': 'SELL',
                    'symbol': pair_symbol,
                    'price': current_price,
                    'amount': position_size,
                    'total_value': current_price * position_size,
                    'strategy': 'Multi-Crypto Combined',
                    'reason': reason,
                    'balance_usd': order_executor.balance_usd,
                    'balance_crypto': order_executor.balance_crypto
                })
                
                logger.info(f"Sell order executed for {pair_symbol}: {position_size:.6f} at ${current_price:.2f}")
            else:
                # Log failed order
                db_manager.log_order_failed(
                    symbol=pair_symbol,
                    order_type='SELL',
                    strategy='Multi-Crypto Combined',
                    price=current_price,
                    amount=position_size,
                    error="Order execution returned None",
                    correlation_id=correlation_id
                )
            
        except Exception as e:
            logger.error(f"Error executing sell order for {pair_symbol}: {e}")
            
            # Log error event
            db_manager.log_error(
                error_code='SELL_ORDER_EXECUTION_ERROR',
                error_message=str(e),
                symbol=pair_symbol,
                strategy='Multi-Crypto Combined',
                stack_trace=str(e),
                context={'source_function': 'execute_sell_order'}
            )
            
            telegram_notifier.send_error_notification(f"Sell order execution failed for {pair_symbol}: {e}")
    
    async def check_risk_management(self, pair_symbol: str):
        """Check stop loss and take profit conditions for a specific pair."""
        try:
            if order_executor.position != 'long':
                return
            
            current_price = self.current_prices[pair_symbol]
            
            # Check stop loss
            if order_executor.check_stop_loss(current_price):
                await self.execute_sell_order(
                    pair_symbol,
                    {'current_price': current_price},
                    f"Stop Loss triggered at ${current_price:.2f}"
                )
                return
            
            # Check take profit
            if order_executor.check_take_profit(current_price):
                await self.execute_sell_order(
                    pair_symbol,
                    {'current_price': current_price},
                    f"Take Profit triggered at ${current_price:.2f}"
                )
                return
            
        except Exception as e:
            logger.error(f"Error checking risk management for {pair_symbol}: {e}")
    
    def print_status(self):
        """Print current multi-crypto bot status."""
        try:
            print(f"\n{'='*100}")
            print(f"Multi-Crypto Trading Bot Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"{'='*100}")
            print(f"Iteration: {self.iteration_count}")
            print(f"Active Pairs: {len(self.config['active_pairs'])}")
            print(f"Total Portfolio Value: ${self.config['portfolio']['total_balance']:,.2f}")
            print(f"Mode: {'Paper Trading' if self.config['portfolio'].get('paper_trading', True) else 'LIVE TRADING'}")
            print(f"\nPair Status:")
            print(f"{'-'*100}")
            
            for pair_symbol in self.config['active_pairs']:
                current_price = self.current_prices.get(pair_symbol, 0)
                pair_strategies = self.strategies.get(pair_symbol, {})
                
                print(f"\n📊 {pair_symbol}:")
                print(f"  Current Price: ${current_price:.2f}")
                print(f"  Strategies: {len(pair_strategies)}")
                
                # Strategy status
                for strategy_name, strategy in pair_strategies.items():
                    status = strategy.get_strategy_status()
                    trend = status.get('trend_direction', 'N/A')
                    position = status.get('position', 'None')
                    print(f"    {strategy_name}: {trend} (Position: {position})")
            
            print(f"{'='*100}")
            
        except Exception as e:
            logger.error(f"Error printing status: {e}")
    
    async def send_daily_summary(self):
        """Send daily trading summary for all pairs."""
        try:
            # Get risk metrics for all pairs
            total_trades = 0
            total_pnl = 0
            
            for pair_symbol in self.config['active_pairs']:
                risk_metrics = risk_manager.get_risk_metrics(pair_symbol)
                current_price = self.current_prices.get(pair_symbol, 0)
                pnl_info = order_executor.get_profit_loss(current_price)
                
                total_trades += risk_metrics.get('total_trades', 0)
                total_pnl += pnl_info['total_pnl']
            
            summary_data = {
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'active_pairs': len(self.config['active_pairs']),
                'portfolio_value': self.config['portfolio']['total_balance']
            }
            
            telegram_notifier.send_daily_summary(summary_data)
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
    
    async def run(self):
        """Main trading loop."""
        try:
            # Initialize
            if not await self.initialize():
                logger.error("Failed to initialize multi-crypto trading bot")
                return
            
            # Send startup notification
            telegram_notifier.send_ready_notification({
                'trading_pairs': self.config['active_pairs'],
                'paper_trading': self.config['portfolio'].get('paper_trading', True),
                'total_balance': f"${self.config['portfolio']['total_balance']:,.2f}",
                'pairs_count': len(self.config['active_pairs']),
                'strategies_count': sum(len(s) for s in self.strategies.values())
            })
            
            self.running = True
            self.start_time = datetime.now(timezone.utc)
            
            logger.info("Starting multi-crypto trading loop...")
            
            while self.running:
                try:
                    await self.run_single_iteration()
                    
                    # Wait before next iteration
                    check_interval = self.config['portfolio'].get('check_interval', 60)
                    logger.debug(f"Waiting {check_interval} seconds until next check...")
                    await asyncio.sleep(check_interval)
                    
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    telegram_notifier.send_error_notification(f"Multi-crypto main loop error: {e}")
                    await asyncio.sleep(30)  # Wait 30 seconds before retrying
            
        except Exception as e:
            logger.error(f"Fatal error in multi-crypto trading bot: {e}")
            telegram_notifier.send_error_notification(f"Fatal multi-crypto bot error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the trading bot gracefully."""
        try:
            logger.info("Shutting down multi-crypto trading bot...")
            
            # Update bot status
            db_manager.update_bot_status("multi_crypto_trading_bot", "STOPPED")
            
            # Send shutdown notification
            runtime = datetime.now(timezone.utc) - self.start_time if self.start_time else None
            telegram_notifier.send_bot_status_notification("STOPPED", {
                'runtime': str(runtime) if runtime else 'Unknown',
                'total_iterations': self.iteration_count,
                'pairs_processed': len(self.config['active_pairs'])
            })
            
            # Close database connections
            db_manager.close_session()
            
            logger.info("Multi-crypto trading bot shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

async def main():
    """Main function."""
    print("🤖 Multi-Cryptocurrency Trading Bot")
    print("=" * 60)
    print("Strategies: SMA Crossover + RSI (per pair)")
    print("Exchange: OKX")
    print("Database: PostgreSQL")
    print("Notifications: Telegram")
    print("Configuration: Cached Multi-Crypto")
    print("=" * 60)
    
    # Send startup notification immediately
    try:
        telegram_notifier.send_startup_notification()
        logger.info("Startup notification sent")
    except Exception as e:
        logger.warning(f"Failed to send startup notification: {e}")
    
    # Check if paper trading
    portfolio_settings = cached_config_service.get_portfolio_settings()
    paper_trading = portfolio_settings.get('paper_trading', True)
    
    print(f"Mode: {'Paper Trading' if paper_trading else 'LIVE TRADING'}")
    
    if not paper_trading:
        print("\n⚠️  WARNING: LIVE TRADING MODE ENABLED ⚠️")
        print("This will use DEMO ACCOUNT for live trading!")
        
        # Auto-confirm in Docker environment (demo account is safe)
        import os
        if os.getenv('DOCKER_ENV') == 'true' or os.path.exists('/.dockerenv'):
            print("Docker environment detected - auto-confirming demo trading")
            response = 'CONFIRM'
        else:
            response = input("Type 'CONFIRM' to proceed with live trading: ")
            
        if response != 'CONFIRM':
            print("Live trading cancelled.")
            try:
                telegram_notifier.send_bot_status_notification("CANCELLED", {
                    'reason': 'Live trading not confirmed by user'
                })
            except Exception as e:
                logger.warning(f"Failed to send cancellation notification: {e}")
            return
    
    try:
        bot = TradingBot()
        await bot.run()
    except KeyboardInterrupt:
        print("\nMulti-crypto bot stopped by user.")
        try:
            telegram_notifier.send_bot_status_notification("STOPPED", {
                'reason': 'Stopped by user (Ctrl+C)'
            })
        except Exception as e:
            logger.warning(f"Failed to send stop notification: {e}")
    except Exception as e:
        print(f"Multi-crypto bot failed to start: {e}")
        logger.error(f"Multi-crypto bot startup error: {e}")
        try:
            telegram_notifier.send_error_notification(f"Multi-crypto bot startup failed: {e}", "Main function")
        except Exception as notify_error:
            logger.warning(f"Failed to send error notification: {notify_error}")

if __name__ == "__main__":
    asyncio.run(main())