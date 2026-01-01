You are an expert Python developer specializing in algorithmic trading.  

Generate a complete, runnable Python program for a simulated auto-trading bot that:


1. Uses the `ccxt` library to connect to a cryptocurrency exchange (e.g., Binance testnet, okx).

2. Fetches live market data (price, volume) for a given trading pair (e.g., BTC/USDT).

3. Implements a simple moving average (SMA)  crossover strategy:

   - Buy when short SMA crosses above long SMA.

   - Sell when short SMA crosses below long SMA.

3. Implements a simple Relative Strength Index (RSI)  crossover strategy:

   - Sell when the RSI is above 70 
   - By when the RSI is30.

4. Includes:

   - Configurable parameters (API keys, trading pair, SMA periods, trade size).

   - Paper trading mode (no real money).

   - Logging of all trades to a CSV file.

   - Error handling for network/API issues.

5. Code must be:

   - Self-contained and runnable.

   - Well-commented for beginners.

   - Safe for testing (no real trades unless explicitly enabled).

6. Add a `main()` function that runs the bot in a loop with a delay between checks.

Do not include any financial advice.  

Focus on code correctness, safety, and clarity.
7. intergrate telegram bot to noti when order or errors
8. intergrate postgres to save tradeOrder and market data


key 
  "OKX": {
        "ApiKey": "aed6abd-74c4-44b1-abb3-e0786bd8d326",
        "SecretKey": "55192F0D88D3FF934F26E00ACAC846C5",
        "Passphrase": "",
        "IsDemo": true
    },
    "Telegram": {
        "BotToken": "8566112159:AAHMpwGX-ePsH9SpzaQ1Q9tXzkiRYAkyFq4",
        "ChatId": "5386085849"
    },

trading_bottrading_bot/
│
├── config/
│   ├── settings.py          # App-wide constants, API keys (use env vars)
│   ├── db_config.py         # PostgreSQL connection settings
│
├── data/
│   ├── raw/                 # Unprocessed market data
│   ├── processed/           # Cleaned & transformed data
│
├── db/
│   ├── schema.sql           # Table definitions
│   ├── migrations/          # Alembic or Flyway migration scripts
│   ├── db_utils.py          # Helper functions for DB queries
│
├── strategies/
│   ├── moving_average.py    # Example strategy
│   ├── rsi_strategy.py      # Another strategy
│   ├── base_strategy.py     # Abstract base class for strategies
│
├── services/
│   ├── data_fetcher.py      # Fetch data from APIs (yfinance, MT5, etc.)
│   ├── order_executor.py    # Place/cancel orders
│   ├── risk_manager.py      # Position sizing, stop-loss logic
│
├── tests/
│   ├── test_strategies.py
│   ├── test_db.py
│
├── utils/
│   ├── logger.py            # Centralized logging
│   ├── indicators.py        # Technical indicator calculations
│
├── main.py                  # Entry point for running the bot
├── requirements.txt         # Python dependencies
├── README.md
└── .env                     # Environment variables (never commit to Git)
Best Practices

Environment Variables

- Store DB credentials, API keys in .env and load with python-dotenv.
Example:
Python
 
from dotenv import load_dotenv
import os

load_dotenv()
DB_URL = os.getenv("POSTGRES_URL")
- Database Layer

Use SQLAlchemy or asyncpg for cleaner queries.
Keep schema changes tracked with Alembic migrations.
- Modular Strategies

Each strategy in its own file, inheriting from a BaseStrategy class.
Makes backtesting and live trading interchangeable.
Logging & Error Handling

Centralize logging in utils/logger.py with rotating file handlers.
Catch DB connection errors early and retry with exponential backoff.
Testing

- Use pytest for unit tests.
Mock API calls and DB queries for faster test runs.
