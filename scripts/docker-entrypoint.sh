#!/bin/bash
set -e

# Docker entrypoint script for trading bot
echo "🚀 Starting Trading Bot Container..."

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
python -c "
import time
import sys
import psycopg2
from config.settings import settings

max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        conn = psycopg2.connect(settings.POSTGRES_URL)
        conn.close()
        print('✅ Database connection successful')
        sys.exit(0)
    except Exception as e:
        print(f'❌ Database connection failed (attempt {attempt + 1}/{max_attempts}): {e}')
    
    attempt += 1
    time.sleep(2)

print('❌ Failed to connect to database after 30 attempts')
sys.exit(1)
"

# Initialize database schema
echo "🗄️ Initializing database schema..."
python -c "
from config.db_config import init_database
try:
    init_database()
    print('✅ Database schema initialized')
except Exception as e:
    print(f'❌ Database schema initialization failed: {e}')
    exit(1)
"

# Configuration is now managed by the multi-crypto system
echo "🔧 Configuration managed by multi-crypto system..."

# Test Telegram connection (optional)
if [ "${TELEGRAM_BOT_TOKEN:-}" != "" ] || [ "${TELEGRAM_API_ID:-}" != "" ]; then
    echo "📱 Testing Telegram connection..."
    python -c "
from services.telegram_notifier import telegram_notifier
try:
    if telegram_notifier.enabled or telegram_notifier.use_bot_fallback:
        success = telegram_notifier.test_connection()
        if success:
            print('✅ Telegram connection successful')
        else:
            print('⚠️ Telegram connection failed - notifications may not work')
    else:
        print('ℹ️ Telegram not configured - notifications disabled')
except Exception as e:
    print(f'⚠️ Telegram test failed: {e}')
"
fi

echo "🎯 All checks passed! Starting trading bot..."
echo "📊 Configuration:"
echo "  • Trading Pair: ${TRADING_PAIR:-BTC/USDT}"
echo "  • Paper Trading: ${PAPER_TRADING:-true}"
echo "  • Check Interval: ${CHECK_INTERVAL:-60}s"
echo "  • Log Level: ${LOG_LEVEL:-INFO}"

# Execute the main command
exec "$@"