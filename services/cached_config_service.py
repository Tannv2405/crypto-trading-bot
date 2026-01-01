"""
Cached configuration service for trading bot.
Provides high-performance access to configuration with automatic cache warming.
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from config.multi_crypto_config_manager import multi_crypto_config_manager
from utils.logger import get_logger

logger = get_logger(__name__)

class CachedConfigService:
    """High-performance configuration service with automatic cache management."""
    
    def __init__(self, auto_warm: bool = True, warm_interval: int = 3600):
        self.config_manager = multi_crypto_config_manager
        self.auto_warm = auto_warm
        self.warm_interval = warm_interval  # 1 hour default
        self.last_warm_time = None
        self.warm_thread = None
        self.running = False
        
        if auto_warm:
            self.start_auto_warm()
    
    def start_auto_warm(self):
        """Start automatic cache warming in background thread."""
        if self.warm_thread and self.warm_thread.is_alive():
            return
        
        self.running = True
        self.warm_thread = threading.Thread(target=self._auto_warm_worker, daemon=True)
        self.warm_thread.start()
        logger.info(f"Started automatic cache warming (interval: {self.warm_interval}s)")
    
    def stop_auto_warm(self):
        """Stop automatic cache warming."""
        self.running = False
        if self.warm_thread:
            self.warm_thread.join(timeout=5)
        logger.info("Stopped automatic cache warming")
    
    def _auto_warm_worker(self):
        """Background worker for automatic cache warming."""
        while self.running:
            try:
                current_time = time.time()
                
                # Check if it's time to warm cache
                if (self.last_warm_time is None or 
                    current_time - self.last_warm_time >= self.warm_interval):
                    
                    logger.debug("Auto-warming configuration cache...")
                    self.warm_cache()
                    self.last_warm_time = current_time
                
                # Sleep for 60 seconds before next check
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in auto-warm worker: {e}")
                time.sleep(60)
    
    def warm_cache(self) -> Dict[str, int]:
        """Warm the configuration cache."""
        return self.config_manager.warm_cache()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.config_manager.get_cache_stats()
    
    # High-level configuration methods with caching
    def get_trading_config_for_pair(self, symbol: str) -> Dict[str, Any]:
        """Get complete trading configuration for a pair (cached)."""
        try:
            # Get pair config
            pair_config = self.config_manager.get_trading_pair_config(symbol)
            if not pair_config:
                logger.warning(f"No configuration found for trading pair: {symbol}")
                return {}
            
            # Get strategies
            strategies = self.config_manager.get_pair_strategies(symbol)
            
            # Get risk config
            risk_config = self.config_manager.get_pair_risk_config(symbol)
            
            # Get relevant system config
            system_config = self.config_manager.get_all_system_config()
            
            return {
                'pair': pair_config,
                'strategies': strategies,
                'risk': risk_config,
                'system': {
                    'paper_trading': system_config.get('paper_trading', True),
                    'check_interval': system_config.get('check_interval', 60),
                    'max_concurrent_positions': system_config.get('max_concurrent_positions', 3)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting trading config for {symbol}: {e}")
            return {}
    
    def get_all_active_pairs_config(self) -> Dict[str, Dict[str, Any]]:
        """Get configuration for all active trading pairs (cached)."""
        try:
            pairs = self.config_manager.get_active_trading_pairs()
            configs = {}
            
            for pair in pairs:
                symbol = pair['symbol']
                configs[symbol] = self.get_trading_config_for_pair(symbol)
            
            return configs
            
        except Exception as e:
            logger.error(f"Error getting all pairs config: {e}")
            return {}
    
    def get_portfolio_settings(self) -> Dict[str, Any]:
        """Get portfolio-level settings (cached)."""
        try:
            system_config = self.config_manager.get_all_system_config()
            pairs = self.config_manager.get_active_trading_pairs()
            
            total_allocation = sum(float(pair['max_position_percent']) for pair in pairs)
            
            return {
                'total_balance': system_config.get('total_portfolio_balance', 10000),
                'max_concurrent_positions': system_config.get('max_concurrent_positions', 3),
                'paper_trading': system_config.get('paper_trading', True),
                'check_interval': system_config.get('check_interval', 60),
                'total_allocation_percent': total_allocation,
                'active_pairs_count': len(pairs),
                'correlation_check_enabled': system_config.get('correlation_check_enabled', True),
                'emergency_stop_enabled': system_config.get('emergency_stop_enabled', True),
                'global_max_daily_loss_percent': system_config.get('global_max_daily_loss_percent', 10.0)
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio settings: {e}")
            return {}
    
    def get_strategy_weights_for_pair(self, symbol: str) -> Dict[str, float]:
        """Get strategy weights for a trading pair (cached)."""
        try:
            strategies = self.config_manager.get_pair_strategies(symbol)
            weights = {}
            
            total_weight = sum(float(s['weight']) for s in strategies if s['is_enabled'])
            
            for strategy in strategies:
                if strategy['is_enabled']:
                    # Normalize weights
                    normalized_weight = float(strategy['weight']) / total_weight if total_weight > 0 else 0
                    weights[strategy['strategy_name']] = normalized_weight
            
            return weights
            
        except Exception as e:
            logger.error(f"Error getting strategy weights for {symbol}: {e}")
            return {}
    
    def is_pair_active(self, symbol: str) -> bool:
        """Check if a trading pair is active (cached)."""
        try:
            pair_config = self.config_manager.get_trading_pair_config(symbol)
            return pair_config is not None
        except Exception as e:
            logger.error(f"Error checking if pair {symbol} is active: {e}")
            return False
    
    def get_risk_limits_for_pair(self, symbol: str) -> Dict[str, float]:
        """Get risk limits for a trading pair (cached)."""
        try:
            risk_config = self.config_manager.get_pair_risk_config(symbol)
            if not risk_config:
                return {}
            
            return {
                'stop_loss_percent': float(risk_config['stop_loss_percent']),
                'take_profit_percent': float(risk_config['take_profit_percent']),
                'max_daily_trades': int(risk_config['max_daily_trades']),
                'max_daily_loss_percent': float(risk_config['max_daily_loss_percent']),
                'max_drawdown_percent': float(risk_config['max_drawdown_percent']),
                'trailing_stop_enabled': bool(risk_config['trailing_stop_enabled']),
                'trailing_stop_percent': float(risk_config['trailing_stop_percent'])
            }
            
        except Exception as e:
            logger.error(f"Error getting risk limits for {symbol}: {e}")
            return {}
    
    def get_enabled_strategies_for_pair(self, symbol: str) -> List[str]:
        """Get list of enabled strategy names for a pair (cached)."""
        try:
            strategies = self.config_manager.get_pair_strategies(symbol)
            return [s['strategy_name'] for s in strategies if s['is_enabled']]
        except Exception as e:
            logger.error(f"Error getting enabled strategies for {symbol}: {e}")
            return []
    
    def should_trade_pair(self, symbol: str) -> bool:
        """Check if trading should be enabled for a pair (cached)."""
        try:
            # Check if pair is active
            if not self.is_pair_active(symbol):
                return False
            
            # Check if pair has enabled strategies
            enabled_strategies = self.get_enabled_strategies_for_pair(symbol)
            if not enabled_strategies:
                logger.warning(f"No enabled strategies for {symbol}")
                return False
            
            # Check system-level paper trading setting
            system_config = self.config_manager.get_all_system_config()
            if not system_config.get('paper_trading', True):
                # In live trading mode, add additional checks
                logger.info(f"Live trading mode - additional checks for {symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if should trade {symbol}: {e}")
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get configuration service performance metrics."""
        try:
            cache_stats = self.get_cache_stats()
            
            return {
                'cache_stats': cache_stats,
                'auto_warm_enabled': self.auto_warm,
                'warm_interval_seconds': self.warm_interval,
                'last_warm_time': self.last_warm_time,
                'service_uptime_seconds': time.time() - (self.last_warm_time or time.time())
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    def __del__(self):
        """Cleanup when service is destroyed."""
        self.stop_auto_warm()

# Global cached config service instance
cached_config_service = CachedConfigService(auto_warm=True, warm_interval=3600)