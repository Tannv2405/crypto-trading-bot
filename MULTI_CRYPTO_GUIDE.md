# Multi-Cryptocurrency Trading Bot Guide

## Overview

The trading bot now supports multiple cryptocurrency pairs with individual configuration for each pair. This allows you to:

- Trade multiple crypto pairs simultaneously
- Configure different strategies per pair
- Set individual risk parameters for each pair
- Manage portfolio allocation across pairs
- Control which strategies run for each pair

## Database Architecture

### New Tables Structure

1. **`system_config`** - Global system settings
2. **`trading_pairs`** - Available cryptocurrency pairs
3. **`strategies`** - Available trading strategies
4. **`pair_strategy_config`** - Strategy configuration per trading pair
5. **`pair_risk_config`** - Risk management per trading pair

## Configuration Management

### CLI Tool Usage

The `multi_crypto_config_cli.py` tool provides comprehensive configuration management:

```bash
# List all trading pairs
python multi_crypto_config_cli.py list pairs

# List strategies for a specific pair
python multi_crypto_config_cli.py list strategies --symbol BTC/USDT

# List risk configuration for a pair
python multi_crypto_config_cli.py list risk --symbol ETH/USDT

# Show portfolio allocation
python multi_crypto_config_cli.py list portfolio

# Show system configuration
python multi_crypto_config_cli.py list system

# Validate configuration
python multi_crypto_config_cli.py validate
```

### Adding New Trading Pairs

```bash
# Add a new trading pair
python multi_crypto_config_cli.py add-pair MATIC/USDT MATIC USDT \
  --balance 1000 \
  --trade-size 80 \
  --max-position 15
```

### Updating Strategy Configuration

```bash
# Update SMA strategy parameters for BTC/USDT
python multi_crypto_config_cli.py update-strategy BTC/USDT sma_crossover \
  --parameters '{"short_period": 12, "long_period": 26}' \
  --weight 0.8

# Disable RSI strategy for a pair
python multi_crypto_config_cli.py update-strategy ETH/USDT rsi \
  --enabled false
```

### Updating Risk Configuration

```bash
# Update risk parameters for SOL/USDT
python multi_crypto_config_cli.py update-risk SOL/USDT \
  --stop-loss 7.5 \
  --take-profit 15.0 \
  --max-trades 5 \
  --max-loss 4.0
```

### System Configuration

```bash
# Set global system parameters
python multi_crypto_config_cli.py set-config max_concurrent_positions 5
python multi_crypto_config_cli.py set-config total_portfolio_balance 15000
python multi_crypto_config_cli.py set-config paper_trading true
```

## Default Configuration

### Pre-configured Trading Pairs

| Symbol    | Base | Quote | Balance | Trade Size | Max Position % |
|-----------|------|-------|---------|------------|----------------|
| BTC/USDT  | BTC  | USDT  | $3,000  | $200       | 30%            |
| ETH/USDT  | ETH  | USDT  | $2,500  | $150       | 25%            |
| SOL/USDT  | SOL  | USDT  | $2,000  | $100       | 20%            |
| ADA/USDT  | ADA  | USDT  | $1,500  | $80        | 15%            |
| DOT/USDT  | DOT  | USDT  | $1,000  | $70        | 10%            |

### Available Strategies

1. **SMA Crossover** (`sma_crossover`)
   - Simple Moving Average crossover strategy
   - Configurable short and long periods
   - Default weight: 0.6

2. **RSI Strategy** (`rsi`)
   - Relative Strength Index overbought/oversold strategy
   - Configurable RSI period and thresholds
   - Default weight: 0.4

### Strategy Parameters by Pair

#### BTC/USDT
- **SMA**: Short=10, Long=30
- **RSI**: Period=14, Overbought=70, Oversold=30

#### ETH/USDT
- **SMA**: Short=12, Long=26
- **RSI**: Period=14, Overbought=75, Oversold=25

#### SOL/USDT
- **SMA**: Short=8, Long=21
- **RSI**: Period=14, Overbought=70, Oversold=30

### Risk Configuration by Pair

| Pair      | Stop Loss % | Take Profit % | Max Daily Trades | Max Daily Loss % |
|-----------|-------------|---------------|------------------|------------------|
| BTC/USDT  | 5.0%        | 10.0%         | 8                | 3.0%             |
| ETH/USDT  | 6.0%        | 12.0%         | 6                | 4.0%             |
| SOL/USDT  | 7.0%        | 15.0%         | 5                | 5.0%             |
| ADA/USDT  | 8.0%        | 16.0%         | 5                | 5.0%             |
| DOT/USDT  | 8.0%        | 18.0%         | 5                | 5.0%             |

## Running Multi-Pair Trading

### Option 1: Use the Multi-Pair Bot

```bash
# Run the multi-pair trading bot
python main_multi_pair.py
```

### Option 2: Use Docker Compose for Multi-Pair

```bash
# Use the multi-pair Docker configuration
docker-compose -f docker-compose.multi-pair.yml up
```

## Portfolio Management

### Allocation Strategy

- **Total Portfolio**: $10,000 (configurable)
- **Max Concurrent Positions**: 3 (configurable)
- **Allocation**: Based on `max_position_percent` per pair
- **Risk Management**: Individual stop-loss and take-profit per pair

### Portfolio Monitoring

```bash
# Check current allocation
python multi_crypto_config_cli.py list portfolio

# Validate configuration
python multi_crypto_config_cli.py validate
```

## Advanced Features

### Strategy Weighting

Each strategy has a weight (0.0 to 1.0) that determines its influence in combined signals:
- Higher weight = more influence on trading decisions
- Weights are normalized across all enabled strategies for a pair

### Risk Management Levels

1. **Pair Level**: Individual stop-loss, take-profit, daily limits
2. **Portfolio Level**: Global daily loss limits, correlation checks
3. **System Level**: Emergency stops, maximum concurrent positions

### Dynamic Configuration

All configuration is stored in the database and can be updated without restarting the bot:
- Strategy parameters
- Risk settings
- Trading pair settings
- System configuration

## Monitoring and Alerts

### Telegram Notifications

The bot sends notifications for:
- Multi-pair trade executions
- Portfolio summaries
- Risk management alerts
- System status updates

### Database Tracking

All trades, market data, and portfolio snapshots are stored per trading pair for:
- Performance analysis
- Risk monitoring
- Strategy optimization

## Best Practices

1. **Start Small**: Begin with paper trading and small allocations
2. **Diversify**: Don't allocate more than 30% to any single pair
3. **Monitor Correlation**: Avoid highly correlated pairs
4. **Regular Review**: Check performance and adjust parameters
5. **Risk Management**: Always set appropriate stop-losses

## Troubleshooting

### Common Issues

1. **Configuration Validation Errors**
   ```bash
   python multi_crypto_config_cli.py validate
   ```

2. **Database Connection Issues**
   - Check PostgreSQL container status
   - Verify connection parameters

3. **Strategy Not Working**
   - Check if strategy is enabled for the pair
   - Verify strategy parameters
   - Check minimum data requirements

### Logs and Debugging

- Container logs: `docker logs trading_bot_app`
- Database logs: `docker logs trading_bot_postgres`
- Configuration validation: Use the CLI validate command

## Migration from Single-Pair

If migrating from the single-pair setup:

1. **Backup Data**: Export existing trades and configuration
2. **Update Schema**: The new schema is backward compatible
3. **Configure Pairs**: Add your desired trading pairs
4. **Test Configuration**: Use paper trading mode first
5. **Gradual Migration**: Start with one pair and add more gradually

## Support

For issues or questions:
1. Check the validation output
2. Review container logs
3. Verify database connectivity
4. Test with paper trading mode first