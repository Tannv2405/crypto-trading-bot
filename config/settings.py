"""
Application-wide settings and configuration management.
Loads environment variables and provides centralized access to configuration.

REFACTORING NOTE: Removed obsolete variables that are now managed through the database-driven 
multi-crypto configuration system:
- TRADING_PAIR (now managed per-pair in database)
- INITIAL_BALANCE (now managed as portfolio settings)
- TRADE_SIZE_USD (now managed per-pair in database)
- CHECK_INTERVAL (now managed in system config)
- PAPER_TRADING (now managed in system config)
- Strategy parameters (SHORT_SMA_PERIOD, LONG_SMA_PERIOD, RSI_PERIOD, etc.)
- Risk parameters (STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT)

These settings are now configured through:
- multi_crypto_config_cli.py for pair and strategy configuration
- Database tables: system_config, trading_pairs, strategies, pair_strategy_config, pair_risk_config
- cached_config_service for high-performance access

This file now only contains essential system-level settings that are not pair-specific.
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Essential system configuration management."""
    
    # Database Configuration
    POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://username:password@localhost:5432/trading_bot")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "trading_bot")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "username")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
    
    # OKX API Configuration
    OKX_API_KEY = os.getenv("OKX_API_KEY", "")
    OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
    OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
    OKX_IS_DEMO = os.getenv("OKX_IS_DEMO", "true").lower() == "true"
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "trading_bot.log")
    
    @classmethod
    def get_okx_config(cls) -> Dict[str, Any]:
        """Get OKX exchange configuration."""
        return {
            "apiKey": cls.OKX_API_KEY,
            "secret": cls.OKX_SECRET_KEY,
            "password": cls.OKX_PASSPHRASE,
            "sandbox": cls.OKX_IS_DEMO,
            "enableRateLimit": True,
        }
    
    @classmethod
    def get_telegram_config(cls) -> Dict[str, str]:
        """Get Telegram bot configuration."""
        return {
            "bot_token": cls.TELEGRAM_BOT_TOKEN,
            "chat_id": cls.TELEGRAM_CHAT_ID,
        }

# Global settings instance
settings = Settings()