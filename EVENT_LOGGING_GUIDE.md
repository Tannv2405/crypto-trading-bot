# Event Logging System Guide

The trading bot includes a comprehensive event logging system that tracks all order history, strategy signals, errors, and system events in a structured database table.

## Features

### Event Types
- **ORDER_ATTEMPT**: When an order is about to be placed
- **ORDER_SUCCESS**: When an order is successfully executed
- **ORDER_FAILED**: When an order execution fails
- **SIGNAL_GENERATED**: When a trading strategy generates a signal
- **ERROR**: When an error occurs in the system
- **SYSTEM_EVENT**: General system events (startup, shutdown, etc.)

### Event Categories
- **TRADING**: Order-related events
- **STRATEGY**: Strategy signal events
- **ERROR**: Error events
- **SYSTEM**: System-level events
- **NOTIFICATION**: Notification-related events

### Severity Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General information events
- **WARNING**: Warning events that don't stop execution
- **ERROR**: Error events that may affect functionality
- **CRITICAL**: Critical errors that may stop the bot

## Database Schema

The `event_log` table includes:

### Core Fields
- `event_type`: Type of event (ORDER_ATTEMPT, ORDER_SUCCESS, etc.)
- `event_category`: Category (TRADING, STRATEGY, ERROR, etc.)
- `severity`: Severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message`: Human-readable event description
- `details`: JSON field with structured event data

### Trading-Specific Fields
- `symbol`: Trading pair (e.g., BTC/USDT)
- `strategy`: Strategy name (e.g., sma_crossover, rsi)
- `order_type`: BUY or SELL
- `order_status`: PENDING, COMPLETED, FAILED, CANCELLED
- `price`: Order price
- `amount`: Order amount
- `total_value`: Total order value

### Error-Specific Fields
- `error_code`: Error classification code
- `error_message`: Detailed error message
- `stack_trace`: Full stack trace for debugging

### Context Fields
- `correlation_id`: For tracking related events
- `session_id`: Bot session identifier
- `bot_name`: Name of the bot instance
- `source_function`: Function where event occurred

## CLI Usage

The `event_log_cli.py` tool provides easy access to event data:

### List Recent Events
```bash
# Show last 50 events
python3 event_log_cli.py list

# Show last 20 events with filters
python3 event_log_cli.py list --limit 20 --symbol BTC/USDT --severity ERROR

# Show events from last 24 hours
python3 event_log_cli.py list --hours 24

# Show events from last 7 days
python3 event_log_cli.py list --days 7
```

### Show Order History
```bash
# Show all order history
python3 event_log_cli.py orders

# Show orders for specific symbol
python3 event_log_cli.py orders --symbol ETH/USDT

# Show last 10 orders
python3 event_log_cli.py orders --limit 10
```

### Show Errors
```bash
# Show recent errors
python3 event_log_cli.py errors

# Show errors from last 6 hours
python3 event_log_cli.py errors --hours 6

# Show last 10 errors
python3 event_log_cli.py errors --limit 10
```

### Show Statistics
```bash
# Show statistics for last 24 hours
python3 event_log_cli.py stats

# Show statistics for last week
python3 event_log_cli.py stats --hours 168
```

## Programmatic Usage

### Logging Events in Code

```python
from db.db_utils import db_manager

# Log an order attempt
db_manager.log_order_attempt(
    symbol='BTC/USDT',
    order_type='BUY',
    strategy='sma_crossover',
    price=50000.0,
    amount=0.001,
    reason='SMA crossover signal',
    correlation_id='uuid-string'
)

# Log a successful order
db_manager.log_order_success(
    symbol='BTC/USDT',
    order_type='BUY',
    strategy='sma_crossover',
    price=50000.0,
    amount=0.001,
    order_id='exchange-order-id',
    correlation_id='uuid-string'
)

# Log a strategy signal
db_manager.log_strategy_signal(
    symbol='BTC/USDT',
    strategy='rsi',
    signal='BUY',
    indicators={'rsi': 25.5, 'rsi_level': 'OVERSOLD'},
    reason='RSI oversold condition'
)

# Log an error
db_manager.log_error(
    error_code='API_CONNECTION_ERROR',
    error_message='Failed to connect to exchange API',
    symbol='BTC/USDT',
    strategy='sma_crossover',
    stack_trace='Full stack trace...',
    context={'source_function': 'fetch_market_data'}
)
```

### Querying Events

```python
from db.db_utils import db_manager
from datetime import datetime, timedelta

# Get recent events
events = db_manager.get_event_logs(limit=100)

# Get events with filters
events = db_manager.get_event_logs(
    limit=50,
    event_type='ORDER_SUCCESS',
    symbol='BTC/USDT',
    severity='INFO',
    start_date=datetime.utcnow() - timedelta(hours=24)
)

# Get order history
orders = db_manager.get_order_history_from_events(
    symbol='ETH/USDT',
    limit=30
)
```

## Benefits

1. **Complete Audit Trail**: Every order attempt, success, and failure is logged
2. **Error Tracking**: Comprehensive error logging with stack traces
3. **Strategy Analysis**: Track strategy performance and signal generation
4. **Debugging**: Correlation IDs link related events for easier debugging
5. **Performance Monitoring**: Track execution times and system events
6. **Compliance**: Maintain detailed records for regulatory requirements

## Best Practices

1. **Use Correlation IDs**: Link related events (order attempt → success/failure)
2. **Include Context**: Add source function and relevant metadata
3. **Structured Details**: Use the JSON details field for additional data
4. **Appropriate Severity**: Use correct severity levels for filtering
5. **Regular Cleanup**: Consider archiving old events to manage database size

## Database Maintenance

The event log table can grow large over time. Consider:

1. **Indexing**: Indexes are created on commonly queried fields
2. **Partitioning**: Consider partitioning by date for large datasets
3. **Archiving**: Archive old events to separate tables or files
4. **Cleanup**: Implement retention policies for old events

## Integration with Monitoring

The event log system integrates with:

1. **Telegram Notifications**: Critical events trigger notifications
2. **Log Files**: Events are also written to standard log files
3. **Metrics**: Event counts can be used for monitoring dashboards
4. **Alerts**: Set up alerts based on error rates or failed orders