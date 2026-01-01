# Cryptocurrency Trading Bot

A comprehensive, production-ready cryptocurrency trading bot with multiple strategies, PostgreSQL database integration, and Telegram notifications.

## Features

### Trading Strategies
- **SMA Crossover Strategy**: Buy on golden cross, sell on death cross
- **RSI Strategy**: Buy when oversold (RSI < 30), sell when overbought (RSI > 70)
- **Combined Strategy Logic**: Uses voting system from multiple strategies

### Technical Features
- **Exchange Integration**: OKX exchange support via CCXT
- **Database Integration**: PostgreSQL for trade history and market data
- **Real-time Notifications**: Telegram bot for trade alerts and errors
- **Risk Management**: Position sizing, stop loss, take profit
- **Paper Trading**: Safe testing mode (enabled by default)
- **Comprehensive Logging**: Rotating file logs with multiple levels

### Safety Features
- **Paper Trading Default**: No real money at risk
- **Risk Management**: Daily trade limits, loss limits, position sizing
- **Error Handling**: Robust error handling with automatic recovery
- **Database Backup**: All trades and market data stored in PostgreSQL

## Project Structure

```
trading_bot/
├── config/
│   ├── settings.py          # Configuration management
│   └── db_config.py         # Database connection settings
├── data/
│   ├── raw/                 # Raw market data
│   └── processed/           # Processed data
├── db/
│   ├── schema.sql           # Database schema
│   ├── migrations/          # Database migrations
│   └── db_utils.py          # Database utilities and ORM models
├── strategies/
│   ├── base_strategy.py     # Abstract base strategy class
│   ├── moving_average.py    # SMA crossover strategy
│   └── rsi_strategy.py      # RSI strategy
├── services/
│   ├── data_fetcher.py      # Market data fetching
│   ├── order_executor.py    # Trade execution
│   ├── risk_manager.py      # Risk management
│   └── telegram_notifier.py # Telegram notifications
├── tests/
│   ├── test_strategies.py   # Strategy tests
│   └── test_db.py          # Database tests
├── utils/
│   ├── logger.py           # Centralized logging
│   └── indicators.py       # Technical indicators
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Docker Deployment

The trading bot is fully containerized with Docker and Docker Compose for easy deployment and management.

### Quick Start with Docker

```bash
# 1. Clone and setup
git clone <repository>
cd trading_bot

# 2. Quick setup (creates .env file)
make dev-setup

# 3. Edit configuration
nano .env  # Add your API keys and settings

# 4. Build and start
make build
make up

# 5. View logs
make logs
```

### Docker Services

The Docker Compose setup includes:

- **trading_bot**: Main application container
- **postgres**: PostgreSQL database
- **config_cli**: Configuration management tool
- **pgadmin**: Database administration interface (optional)

### Available Commands

```bash
# Development
make build          # Build Docker images
make up             # Start services
make down           # Stop services
make logs           # View logs
make restart        # Restart services

# Production
make prod-up        # Start in production mode
make prod-down      # Stop production services
make prod-logs      # View production logs

# Management
make shell          # Access bot shell
make config-shell   # Configuration CLI
make db-shell       # Database shell
make pgadmin        # Start admin interface

# Configuration
make config-list    # List all configuration
make config-validate # Validate configuration
make config-export  # Export configuration
make config-import  # Import configuration

# Maintenance
make backup-db      # Backup database
make restore-db     # Restore database
make clean          # Clean containers/volumes
make health         # Check service health
```

### Environment Configuration

Create a `.env` file with your configuration:

```env
# Database (automatically configured for Docker)
POSTGRES_PASSWORD=your_secure_password

# OKX API
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_PASSPHRASE=your_passphrase
OKX_IS_DEMO=true

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading
TRADING_PAIR=BTC/USDT
PAPER_TRADING=true
TRADE_SIZE_USD=100
```

### Production Deployment

For production deployment:

```bash
# 1. Create production environment file
cp .env.example .env.prod

# 2. Edit with production settings
nano .env.prod

# 3. Start in production mode
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or use make command
make prod-up
```

### Docker Features

- **Health Checks**: Automatic health monitoring
- **Auto-restart**: Services restart on failure
- **Resource Limits**: Production resource constraints
- **Security**: Non-root user, minimal attack surface
- **Logging**: Structured logging with rotation
- **Persistence**: Database and logs persist across restarts
- **Networking**: Isolated network for services

### Volumes and Data Persistence

- `postgres_data`: Database files
- `./logs`: Application logs
- `./data`: Market data and exports
- `/tmp/.tdlib_files`: Telegram client files

### Monitoring and Logs

```bash
# View real-time logs
make logs

# Check service status
make status

# Health check
make health

# Access pgAdmin (database admin)
make pgadmin
# Then visit http://localhost:8080
```

### Troubleshooting Docker Issues

**Database Connection Issues:**
```bash
# Check database status
make status

# View database logs
docker-compose logs postgres

# Test database connection
make db-shell
```

**Bot Not Starting:**
```bash
# Check bot logs
docker-compose logs trading_bot

# Access bot shell for debugging
make shell

# Validate configuration
make config-validate
```

**Permission Issues:**
```bash
# Fix log directory permissions
sudo chown -R $USER:$USER logs/

# Rebuild with clean slate
make clean-all
make build
```

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- OKX API account (for live trading)
- Telegram Bot (for notifications)

### Setup Steps

1. **Clone and setup environment**:
```bash
cd trading_bot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Setup PostgreSQL database**:
```bash
# Create database
createdb trading_bot

# Run schema
psql -d trading_bot -f db/schema.sql
```

3. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Configure your settings in `.env`**:
```env
# Database
POSTGRES_URL=postgresql://username:password@localhost:5432/trading_bot

# OKX API (use demo/testnet for testing)
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_PASSPHRASE=your_passphrase
OKX_IS_DEMO=true

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading
PAPER_TRADING=true
TRADING_PAIR=BTC/USDT
TRADE_SIZE_USD=100
```

## Usage

### Running the Bot

```bash
python main.py
```

### Configuration Management

The bot supports dynamic configuration management through a PostgreSQL database table. This allows you to modify trading parameters without restarting the bot.

### Configuration Categories

- **Trading**: Basic trading parameters (pair, balance, trade size)
- **Strategy**: Strategy-specific parameters (SMA periods, RSI thresholds)
- **Risk**: Risk management settings (stop loss, take profit, limits)
- **Notification**: Telegram notification preferences
- **General**: General bot settings

### Using the Configuration CLI

The bot includes a command-line tool for managing configuration:

```bash
# List all configuration
python config_cli.py list

# List specific category
python config_cli.py list --category trading

# Get a specific value
python config_cli.py get trading_pair

# Set a configuration value
python config_cli.py set trade_size_usd 150 --type float --description "Trade size per order"

# Validate configuration
python config_cli.py validate

# Export configuration to file
python config_cli.py export my_config.json

# Import configuration from file
python config_cli.py import my_config.json
```


### Dynamic Configuration Loading

The bot automatically loads configuration from the database with fallback to environment variables:

2. **Environment Fallback**: Uses `.env` file values if database unavailable
3. **Caching**: Caches configuration for 5 minutes for performance
4. **Validation**: Validates configuration on load

## Configuration Options

Key configuration parameters in `.env`:

- `PAPER_TRADING`: Enable/disable paper trading (default: true)
- `TRADING_PAIR`: Cryptocurrency pair to trade (default: BTC/USDT)
- `TRADE_SIZE_USD`: Amount per trade in USD (default: 100)
- `CHECK_INTERVAL`: Seconds between checks (default: 60)
- `SHORT_SMA_PERIOD`: Short SMA period (default: 10)
- `LONG_SMA_PERIOD`: Long SMA period (default: 30)
- `RSI_PERIOD`: RSI calculation period (default: 14)
- `RSI_OVERBOUGHT`: RSI overbought threshold (default: 70)
- `RSI_OVERSOLD`: RSI oversold threshold (default: 30)

## Strategy Details

### SMA Crossover Strategy
- **Golden Cross**: Short SMA crosses above Long SMA → BUY signal
- **Death Cross**: Short SMA crosses below Long SMA → SELL signal
- **Confirmation**: Includes spread percentage and momentum checks

### RSI Strategy
- **Oversold**: RSI ≤ 30 with positive momentum → BUY signal
- **Overbought**: RSI ≥ 70 with negative momentum → SELL signal
- **Cooldown**: 5-period cooldown to prevent rapid signals

### Combined Strategy Logic
- Uses voting system from multiple strategies
- Majority vote determines final action
- Risk management validation before execution

## Risk Management

### Built-in Safety Features
- **Daily Trade Limits**: Maximum trades per day
- **Daily Loss Limits**: Maximum loss percentage per day
- **Position Sizing**: Automatic position size calculation
- **Stop Loss**: Configurable stop loss percentage
- **Take Profit**: Configurable take profit percentage

### Risk Parameters
- `STOP_LOSS_PERCENT`: Stop loss percentage (default: 5%)
- `TAKE_PROFIT_PERCENT`: Take profit percentage (default: 10%)
- Maximum daily trades: 10
- Maximum daily loss: 5% of initial balance

## Database Schema

The bot stores comprehensive data:

- **market_data**: OHLCV price data
- **trade_orders**: All trading activity
- **portfolio_snapshots**: Portfolio value over time
- **strategy_performance**: Strategy metrics
- **bot_status**: Bot operational status

## Telegram Notifications

The bot sends notifications for:
- Trade executions (buy/sell orders)
- Trading signals from strategies
- Error alerts and warnings
- Daily performance summaries
- Bot status updates (start/stop)

## Testing

### Paper Trading
- Enabled by default (`PAPER_TRADING=true`)
- Uses simulated balance and trades
- All features work except real money execution
- Perfect for strategy testing and validation

### Unit Tests
```bash
pytest tests/
```

## Monitoring and Logs

### Log Files
- `trading_bot.log`: Main application log
- `trading_bot_errors.log`: Error-only log
- Automatic log rotation (10MB max, 5 backups)

### Database Monitoring
- All trades stored with full context
- Portfolio snapshots for performance tracking
- Strategy performance metrics
- Bot status and error tracking

## Production Deployment

### Security Checklist
- [ ] Use environment variables for all secrets
- [ ] Enable database SSL connections
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Set up monitoring alerts
- [ ] Use dedicated server/VPS
- [ ] Enable firewall protection

### Recommended Setup
1. **VPS/Cloud Server**: Ubuntu 20.04+ with 2GB+ RAM
2. **Database**: Managed PostgreSQL service
3. **Process Management**: systemd or supervisor
4. **Monitoring**: Set up alerts for bot failures
5. **Backups**: Automated database backups

## API Keys Setup

### OKX Exchange
1. Create account at OKX
2. Enable API access
3. Generate API keys with trading permissions
4. Use testnet/demo for initial testing

### Telegram Bot
1. Create bot via @BotFather on Telegram
2. Get bot token
3. Get your chat ID (message @userinfobot)
4. Test notifications before live trading

## Troubleshooting

### Common Issues

**Database Connection Error**:
- Check PostgreSQL is running
- Verify connection string in `.env`
- Ensure database exists

**API Connection Error**:
- Verify API keys are correct
- Check if using testnet/demo mode
- Ensure API permissions include trading

**No Trading Signals**:
- Check if enough market data is available
- Verify strategy parameters
- Review logs for calculation errors

**Telegram Not Working**:
- Verify bot token and chat ID
- Check bot permissions
- Test with simple message first

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit pull request

## Disclaimer

⚠️ **Important Disclaimers**:
- This software is for educational purposes only
- Cryptocurrency trading involves significant financial risk
- Never invest more than you can afford to lose
- Always test with paper trading first
- Past performance does not guarantee future results
- The authors are not responsible for any financial losses

## License

MIT License - Use at your own risk. No warranty provided.

## Support

For issues and questions:
1. Check the logs first (`trading_bot.log`)
2. Review this README
3. Check database connectivity
4. Verify API configurations
5. Test with paper trading mode