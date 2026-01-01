"""
Multi-cryptocurrency configuration manager with caching.
Handles configuration for multiple trading pairs and strategies with Redis/memory caching.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import threading

from config.db_config import SessionLocal
from utils.logger import get_logger

logger = get_logger(__name__)

class ConfigCache:
    """In-memory configuration cache with TTL support."""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self.cache = {}
        self.timestamps = {}
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
    
    def get(self, key: str, ttl: int = None) -> Any:
        """Get value from cache if not expired."""
        with self.lock:
            if key not in self.cache:
                return None
            
            ttl = ttl or self.default_ttl
            if time.time() - self.timestamps[key] > ttl:
                # Expired, remove from cache
                del self.cache[key]
                del self.timestamps[key]
                return None
            
            return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp."""
        with self.lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def delete(self, key: str) -> None:
        """Delete specific key from cache."""
        with self.lock:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        with self.lock:
            keys_to_delete = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_delete:
                del self.cache[key]
                del self.timestamps[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            current_time = time.time()
            expired_count = sum(1 for ts in self.timestamps.values() 
                              if current_time - ts > self.default_ttl)
            
            return {
                'total_entries': len(self.cache),
                'expired_entries': expired_count,
                'active_entries': len(self.cache) - expired_count,
                'cache_size_bytes': sum(len(str(v)) for v in self.cache.values())
            }

class MultiCryptoConfigManager:
    """Configuration manager for multi-cryptocurrency trading with caching."""
    
    def __init__(self, cache_ttl: int = 300):
        self.session = None
        self.cache = ConfigCache(cache_ttl)
        self.cache_ttl = cache_ttl
        
        # Cache keys
        self.SYSTEM_CONFIG_KEY = "system_config"
        self.TRADING_PAIRS_KEY = "trading_pairs"
        self.PAIR_CONFIG_KEY = "pair_config:{}"
        self.PAIR_STRATEGIES_KEY = "pair_strategies:{}"
        self.STRATEGY_CONFIG_KEY = "strategy_config:{}:{}"
        self.PAIR_RISK_KEY = "pair_risk:{}"
        
        logger.info(f"Initialized MultiCryptoConfigManager with {cache_ttl}s cache TTL")
    
    def get_session(self) -> Session:
        """Get database session."""
        if self.session is None:
            self.session = SessionLocal()
        return self.session
    
    def close_session(self):
        """Close database session."""
        if self.session:
            self.session.close()
            self.session = None
    
    def clear_cache(self):
        """Clear all cached configuration."""
        self.cache.clear()
        logger.info("Configuration cache cleared")
    
    def invalidate_cache_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        self.cache.invalidate_pattern(pattern)
        logger.debug(f"Invalidated cache entries matching pattern: {pattern}")
    
    # System Configuration Methods with Caching
    def get_system_config(self, key: str, default: Any = None, use_cache: bool = True) -> Any:
        """Get system configuration value with caching."""
        if use_cache:
            cache_key = f"{self.SYSTEM_CONFIG_KEY}:{key}"
            cached_value = self.cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for system config: {key}")
                return cached_value
        
        try:
            session = self.get_session()
            result = session.execute(
                text("SELECT config_value, config_type FROM system_config WHERE config_key = :key AND is_active = true"),
                {"key": key}
            ).fetchone()
            
            if result:
                value, config_type = result
                converted_value = self._convert_config_value(value, config_type)
                
                if use_cache:
                    self.cache.set(f"{self.SYSTEM_CONFIG_KEY}:{key}", converted_value)
                    logger.debug(f"Cached system config: {key}")
                
                return converted_value
            
            return default
            
        except Exception as e:
            logger.error(f"Error getting system config {key}: {e}")
            return default
    
    def set_system_config(self, key: str, value: Any, config_type: str = None, description: str = None, category: str = 'general') -> bool:
        """Set system configuration value and invalidate cache."""
        try:
            session = self.get_session()
            
            # Auto-detect config type if not provided
            if config_type is None:
                config_type = self._detect_config_type(value)
            
            # Convert value to string for storage
            str_value = str(value).lower() if isinstance(value, bool) else str(value)
            
            # Upsert configuration
            session.execute(
                text("""
                    INSERT INTO system_config (config_key, config_value, config_type, description, category)
                    VALUES (:key, :value, :type, :desc, :cat)
                    ON CONFLICT (config_key) 
                    DO UPDATE SET 
                        config_value = EXCLUDED.config_value,
                        config_type = EXCLUDED.config_type,
                        description = COALESCE(EXCLUDED.description, system_config.description),
                        category = COALESCE(EXCLUDED.category, system_config.category),
                        updated_at = CURRENT_TIMESTAMP
                """),
                {
                    "key": key, 
                    "value": str_value, 
                    "type": config_type, 
                    "desc": description, 
                    "cat": category
                }
            )
            session.commit()
            
            # Invalidate cache
            self.cache.delete(f"{self.SYSTEM_CONFIG_KEY}:{key}")
            self.cache.delete(self.SYSTEM_CONFIG_KEY)  # Also clear full system config cache
            logger.debug(f"Invalidated cache for system config: {key}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting system config {key}: {e}")
            if session:
                session.rollback()
            return False
    
    def get_all_system_config(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get all system configuration as a dictionary with caching."""
        if use_cache:
            cached_config = self.cache.get(self.SYSTEM_CONFIG_KEY)
            if cached_config is not None:
                logger.debug("Cache hit for all system config")
                return cached_config
        
        try:
            session = self.get_session()
            result = session.execute(
                text("SELECT config_key, config_value, config_type FROM system_config WHERE is_active = true")
            ).fetchall()
            
            config = {}
            for row in result:
                key, value, config_type = row
                config[key] = self._convert_config_value(value, config_type)
            
            if use_cache:
                self.cache.set(self.SYSTEM_CONFIG_KEY, config)
                logger.debug("Cached all system config")
            
            return config
            
        except Exception as e:
            logger.error(f"Error getting all system config: {e}")
            return {}
    
    # Trading Pairs Methods with Caching
    def get_active_trading_pairs(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all active trading pairs with caching."""
        if use_cache:
            cached_pairs = self.cache.get(self.TRADING_PAIRS_KEY)
            if cached_pairs is not None:
                logger.debug("Cache hit for active trading pairs")
                return cached_pairs
        
        try:
            session = self.get_session()
            result = session.execute(
                text("""
                    SELECT id, symbol, base_currency, quote_currency, initial_balance, 
                           trade_size_usd, max_position_percent, min_trade_amount, max_trade_amount,
                           price_precision, amount_precision
                    FROM trading_pairs 
                    WHERE is_active = true 
                    ORDER BY symbol
                """)
            ).fetchall()
            
            pairs = [dict(row._mapping) for row in result]
            
            if use_cache:
                self.cache.set(self.TRADING_PAIRS_KEY, pairs)
                logger.debug(f"Cached {len(pairs)} active trading pairs")
            
            return pairs
            
        except Exception as e:
            logger.error(f"Error getting active trading pairs: {e}")
            return []
    
    def get_trading_pair_config(self, symbol: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific trading pair with caching."""
        cache_key = self.PAIR_CONFIG_KEY.format(symbol)
        
        if use_cache:
            cached_config = self.cache.get(cache_key)
            if cached_config is not None:
                logger.debug(f"Cache hit for trading pair config: {symbol}")
                return cached_config
        
        try:
            session = self.get_session()
            result = session.execute(
                text("""
                    SELECT id, symbol, base_currency, quote_currency, initial_balance, 
                           trade_size_usd, max_position_percent, min_trade_amount, max_trade_amount,
                           price_precision, amount_precision
                    FROM trading_pairs 
                    WHERE symbol = :symbol AND is_active = true
                """),
                {"symbol": symbol}
            ).fetchone()
            
            if result:
                config = dict(result._mapping)
                
                if use_cache:
                    self.cache.set(cache_key, config)
                    logger.debug(f"Cached trading pair config: {symbol}")
                
                return config
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting trading pair config for {symbol}: {e}")
            return None
    
    def add_trading_pair(self, symbol: str, base_currency: str, quote_currency: str, **kwargs) -> bool:
        """Add a new trading pair and invalidate cache."""
        try:
            session = self.get_session()
            
            # Default values
            defaults = {
                'initial_balance': 1000.00,
                'trade_size_usd': 100.00,
                'max_position_percent': 20.00,
                'min_trade_amount': 0.001,
                'max_trade_amount': 10000.00,
                'price_precision': 2,
                'amount_precision': 6
            }
            defaults.update(kwargs)
            
            session.execute(
                text("""
                    INSERT INTO trading_pairs 
                    (symbol, base_currency, quote_currency, initial_balance, trade_size_usd, 
                     max_position_percent, min_trade_amount, max_trade_amount, price_precision, amount_precision)
                    VALUES (:symbol, :base, :quote, :balance, :trade_size, :max_pos, :min_trade, :max_trade, :price_prec, :amount_prec)
                """),
                {
                    'symbol': symbol,
                    'base': base_currency,
                    'quote': quote_currency,
                    'balance': defaults['initial_balance'],
                    'trade_size': defaults['trade_size_usd'],
                    'max_pos': defaults['max_position_percent'],
                    'min_trade': defaults['min_trade_amount'],
                    'max_trade': defaults['max_trade_amount'],
                    'price_prec': defaults['price_precision'],
                    'amount_prec': defaults['amount_precision']
                }
            )
            session.commit()
            
            # Invalidate related cache entries
            self.cache.delete(self.TRADING_PAIRS_KEY)
            self.cache.delete(self.PAIR_CONFIG_KEY.format(symbol))
            logger.debug(f"Invalidated cache for new trading pair: {symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding trading pair {symbol}: {e}")
            if session:
                session.rollback()
            return False
    
    # Strategy Configuration Methods with Caching
    def get_pair_strategies(self, symbol: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get enabled strategies for a trading pair with caching."""
        cache_key = self.PAIR_STRATEGIES_KEY.format(symbol)
        
        if use_cache:
            cached_strategies = self.cache.get(cache_key)
            if cached_strategies is not None:
                logger.debug(f"Cache hit for pair strategies: {symbol}")
                return cached_strategies
        
        try:
            session = self.get_session()
            result = session.execute(
                text("""
                    SELECT s.strategy_name, s.display_name, s.description, s.strategy_type,
                           psc.is_enabled, psc.weight, psc.parameters
                    FROM pair_strategy_config psc
                    JOIN strategies s ON psc.strategy_id = s.id
                    JOIN trading_pairs tp ON psc.pair_id = tp.id
                    WHERE tp.symbol = :symbol AND psc.is_enabled = true AND s.is_active = true
                    ORDER BY psc.weight DESC
                """),
                {"symbol": symbol}
            ).fetchall()
            
            strategies = []
            for row in result:
                strategy = dict(row._mapping)
                # Parse JSON parameters
                if strategy['parameters']:
                    try:
                        strategy['parameters'] = json.loads(strategy['parameters']) if isinstance(strategy['parameters'], str) else strategy['parameters']
                    except json.JSONDecodeError:
                        strategy['parameters'] = {}
                else:
                    strategy['parameters'] = {}
                strategies.append(strategy)
            
            if use_cache:
                self.cache.set(cache_key, strategies)
                logger.debug(f"Cached {len(strategies)} strategies for pair: {symbol}")
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error getting strategies for {symbol}: {e}")
            return []
    
    def get_strategy_config(self, symbol: str, strategy_name: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific strategy on a trading pair with caching."""
        cache_key = self.STRATEGY_CONFIG_KEY.format(symbol, strategy_name)
        
        if use_cache:
            cached_config = self.cache.get(cache_key)
            if cached_config is not None:
                logger.debug(f"Cache hit for strategy config: {symbol}/{strategy_name}")
                return cached_config
        
        try:
            session = self.get_session()
            result = session.execute(
                text("""
                    SELECT s.strategy_name, s.display_name, psc.is_enabled, psc.weight, psc.parameters
                    FROM pair_strategy_config psc
                    JOIN strategies s ON psc.strategy_id = s.id
                    JOIN trading_pairs tp ON psc.pair_id = tp.id
                    WHERE tp.symbol = :symbol AND s.strategy_name = :strategy
                """),
                {"symbol": symbol, "strategy": strategy_name}
            ).fetchone()
            
            if result:
                config = dict(result._mapping)
                # Parse JSON parameters
                if config['parameters']:
                    try:
                        config['parameters'] = json.loads(config['parameters']) if isinstance(config['parameters'], str) else config['parameters']
                    except json.JSONDecodeError:
                        config['parameters'] = {}
                else:
                    config['parameters'] = {}
                
                if use_cache:
                    self.cache.set(cache_key, config)
                    logger.debug(f"Cached strategy config: {symbol}/{strategy_name}")
                
                return config
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting strategy config for {symbol}/{strategy_name}: {e}")
            return None
    
    def update_strategy_config(self, symbol: str, strategy_name: str, parameters: Dict[str, Any], weight: float = None, enabled: bool = None) -> bool:
        """Update strategy configuration for a trading pair and invalidate cache."""
        try:
            session = self.get_session()
            
            # Build update query dynamically
            updates = ["parameters = :params"]
            params = {"symbol": symbol, "strategy": strategy_name, "params": json.dumps(parameters)}
            
            if weight is not None:
                updates.append("weight = :weight")
                params["weight"] = weight
            
            if enabled is not None:
                updates.append("is_enabled = :enabled")
                params["enabled"] = enabled
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            
            session.execute(
                text(f"""
                    UPDATE pair_strategy_config 
                    SET {', '.join(updates)}
                    FROM strategies s, trading_pairs tp
                    WHERE pair_strategy_config.strategy_id = s.id 
                      AND pair_strategy_config.pair_id = tp.id
                      AND tp.symbol = :symbol 
                      AND s.strategy_name = :strategy
                """),
                params
            )
            session.commit()
            
            # Invalidate related cache entries
            self.cache.delete(self.PAIR_STRATEGIES_KEY.format(symbol))
            self.cache.delete(self.STRATEGY_CONFIG_KEY.format(symbol, strategy_name))
            logger.debug(f"Invalidated cache for strategy config: {symbol}/{strategy_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating strategy config for {symbol}/{strategy_name}: {e}")
            if session:
                session.rollback()
            return False
    
    # Risk Configuration Methods with Caching
    def get_pair_risk_config(self, symbol: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get risk configuration for a trading pair with caching."""
        cache_key = self.PAIR_RISK_KEY.format(symbol)
        
        if use_cache:
            cached_config = self.cache.get(cache_key)
            if cached_config is not None:
                logger.debug(f"Cache hit for risk config: {symbol}")
                return cached_config
        
        try:
            session = self.get_session()
            result = session.execute(
                text("""
                    SELECT stop_loss_percent, take_profit_percent, max_daily_trades, 
                           max_daily_loss_percent, trailing_stop_enabled, trailing_stop_percent,
                           max_drawdown_percent, position_sizing_method, volatility_lookback_days
                    FROM pair_risk_config prc
                    JOIN trading_pairs tp ON prc.pair_id = tp.id
                    WHERE tp.symbol = :symbol
                """),
                {"symbol": symbol}
            ).fetchone()
            
            if result:
                config = dict(result._mapping)
                
                if use_cache:
                    self.cache.set(cache_key, config)
                    logger.debug(f"Cached risk config: {symbol}")
                
                return config
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting risk config for {symbol}: {e}")
            return None
    
    def update_pair_risk_config(self, symbol: str, **risk_params) -> bool:
        """Update risk configuration for a trading pair and invalidate cache."""
        try:
            session = self.get_session()
            
            # Build update query dynamically
            valid_fields = [
                'stop_loss_percent', 'take_profit_percent', 'max_daily_trades',
                'max_daily_loss_percent', 'trailing_stop_enabled', 'trailing_stop_percent',
                'max_drawdown_percent', 'position_sizing_method', 'volatility_lookback_days'
            ]
            
            updates = []
            params = {"symbol": symbol}
            
            for field, value in risk_params.items():
                if field in valid_fields:
                    updates.append(f"{field} = :{field}")
                    params[field] = value
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            
            session.execute(
                text(f"""
                    UPDATE pair_risk_config 
                    SET {', '.join(updates)}
                    FROM trading_pairs tp
                    WHERE pair_risk_config.pair_id = tp.id AND tp.symbol = :symbol
                """),
                params
            )
            session.commit()
            
            # Invalidate cache
            self.cache.delete(self.PAIR_RISK_KEY.format(symbol))
            logger.debug(f"Invalidated cache for risk config: {symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating risk config for {symbol}: {e}")
            if session:
                session.rollback()
            return False
    
    # Cache Management Methods
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.cache.get_stats()
        stats['cache_ttl_seconds'] = self.cache_ttl
        return stats
    
    def warm_cache(self) -> Dict[str, int]:
        """Pre-load frequently accessed configuration into cache."""
        logger.info("Warming configuration cache...")
        
        warmed = {
            'system_config': 0,
            'trading_pairs': 0,
            'strategies': 0,
            'risk_configs': 0
        }
        
        try:
            # Warm system config
            self.get_all_system_config(use_cache=True)
            warmed['system_config'] = 1
            
            # Warm trading pairs
            pairs = self.get_active_trading_pairs(use_cache=True)
            warmed['trading_pairs'] = len(pairs)
            
            # Warm strategies and risk configs for each pair
            for pair in pairs:
                symbol = pair['symbol']
                
                # Warm strategies
                strategies = self.get_pair_strategies(symbol, use_cache=True)
                warmed['strategies'] += len(strategies)
                
                # Warm risk config
                self.get_pair_risk_config(symbol, use_cache=True)
                warmed['risk_configs'] += 1
            
            logger.info(f"Cache warmed: {warmed}")
            return warmed
            
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
            return warmed
    
    # Utility Methods
    def _convert_config_value(self, value: str, config_type: str) -> Any:
        """Convert string config value to appropriate type."""
        try:
            if config_type == 'boolean':
                return value.lower() in ('true', '1', 'yes', 'on')
            elif config_type == 'integer':
                return int(value)
            elif config_type == 'float':
                return float(value)
            elif config_type == 'json':
                return json.loads(value)
            else:
                return value
        except (ValueError, json.JSONDecodeError):
            logger.warning(f"Failed to convert config value '{value}' to type '{config_type}'")
            return value
    
    def _detect_config_type(self, value: Any) -> str:
        """Auto-detect configuration type from value."""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, (dict, list)):
            return 'json'
        else:
            return 'string'
    
    def validate_multi_crypto_config(self) -> Dict[str, Any]:
        """Validate multi-cryptocurrency configuration."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'summary': {}
        }
        
        try:
            # Check active trading pairs
            pairs = self.get_active_trading_pairs()
            if not pairs:
                validation_result['errors'].append("No active trading pairs configured")
                validation_result['valid'] = False
            else:
                validation_result['summary']['active_pairs'] = len(pairs)
            
            # Check system configuration
            system_config = self.get_all_system_config()
            required_configs = ['paper_trading', 'check_interval', 'max_concurrent_positions', 'total_portfolio_balance']
            
            for config_key in required_configs:
                if config_key not in system_config:
                    validation_result['errors'].append(f"Missing required system config: {config_key}")
                    validation_result['valid'] = False
            
            # Check strategy configurations
            total_strategies = 0
            for pair in pairs:
                strategies = self.get_pair_strategies(pair['symbol'])
                if not strategies:
                    validation_result['warnings'].append(f"No strategies configured for {pair['symbol']}")
                else:
                    total_strategies += len(strategies)
            
            validation_result['summary']['total_strategies'] = total_strategies
            
            # Check portfolio allocation
            total_allocation = sum(float(pair['max_position_percent']) for pair in pairs)
            if total_allocation > 100:
                validation_result['warnings'].append(f"Total position allocation ({total_allocation}%) exceeds 100%")
            
            validation_result['summary']['total_allocation_percent'] = total_allocation
            
            # Add cache stats
            validation_result['summary']['cache_stats'] = self.get_cache_stats()
            
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {e}")
            validation_result['valid'] = False
        return validation_result

# Global multi-crypto config manager instance with caching
multi_crypto_config_manager = MultiCryptoConfigManager(cache_ttl=300)  # 5 minutes cache