#!/usr/bin/env python3
"""
Multi-cryptocurrency configuration CLI tool.
Manage trading pairs, strategies, and risk settings.
"""

import argparse
import json
import sys
from typing import Dict, Any
from tabulate import tabulate

from config.multi_crypto_config_manager import multi_crypto_config_manager
from utils.logger import setup_logger

logger = setup_logger('multi_crypto_config_cli')

class MultiCryptoConfigCLI:
    """CLI for managing multi-cryptocurrency configuration."""
    
    def __init__(self):
        self.config_manager = multi_crypto_config_manager
    
    def list_trading_pairs(self):
        """List all active trading pairs."""
        pairs = self.config_manager.get_active_trading_pairs()
        
        if not pairs:
            print("No active trading pairs found.")
            return
        
        headers = ['Symbol', 'Base', 'Quote', 'Balance', 'Trade Size', 'Max Position %', 'Min Trade', 'Max Trade']
        rows = []
        
        for pair in pairs:
            rows.append([
                pair['symbol'],
                pair['base_currency'],
                pair['quote_currency'],
                f"${pair['initial_balance']:,.2f}",
                f"${pair['trade_size_usd']:,.2f}",
                f"{pair['max_position_percent']:.1f}%",
                f"{pair['min_trade_amount']:.6f}",
                f"{pair['max_trade_amount']:,.2f}"
            ])
        
        print("\n📊 Active Trading Pairs:")
        print(tabulate(rows, headers=headers, tablefmt='grid'))
    
    def add_trading_pair(self, symbol: str, base: str, quote: str, **kwargs):
        """Add a new trading pair."""
        success = self.config_manager.add_trading_pair(symbol, base, quote, **kwargs)
        
        if success:
            print(f"✅ Successfully added trading pair: {symbol}")
        else:
            print(f"❌ Failed to add trading pair: {symbol}")
    
    def list_strategies(self, symbol: str = None):
        """List strategies for a trading pair or all pairs."""
        if symbol:
            strategies = self.config_manager.get_pair_strategies(symbol)
            if not strategies:
                print(f"No strategies found for {symbol}")
                return
            
            print(f"\n🎯 Strategies for {symbol}:")
            headers = ['Strategy', 'Display Name', 'Type', 'Enabled', 'Weight', 'Parameters']
            rows = []
            
            for strategy in strategies:
                params_str = json.dumps(strategy['parameters'], indent=2) if strategy['parameters'] else '{}'
                rows.append([
                    strategy['strategy_name'],
                    strategy['display_name'],
                    strategy['strategy_type'],
                    '✅' if strategy['is_enabled'] else '❌',
                    f"{strategy['weight']:.2f}",
                    params_str[:50] + '...' if len(params_str) > 50 else params_str
                ])
            
            print(tabulate(rows, headers=headers, tablefmt='grid'))
        else:
            # List strategies for all pairs
            pairs = self.config_manager.get_active_trading_pairs()
            for pair in pairs:
                self.list_strategies(pair['symbol'])
    
    def update_strategy(self, symbol: str, strategy_name: str, parameters: str = None, weight: float = None, enabled: bool = None):
        """Update strategy configuration."""
        params_dict = {}
        if parameters:
            try:
                params_dict = json.loads(parameters)
            except json.JSONDecodeError:
                print("❌ Invalid JSON parameters")
                return
        
        success = self.config_manager.update_strategy_config(
            symbol, strategy_name, params_dict, weight, enabled
        )
        
        if success:
            print(f"✅ Successfully updated strategy {strategy_name} for {symbol}")
        else:
            print(f"❌ Failed to update strategy {strategy_name} for {symbol}")
    
    def list_risk_config(self, symbol: str = None):
        """List risk configuration for a trading pair or all pairs."""
        if symbol:
            risk_config = self.config_manager.get_pair_risk_config(symbol)
            if not risk_config:
                print(f"No risk configuration found for {symbol}")
                return
            
            print(f"\n⚠️  Risk Configuration for {symbol}:")
            headers = ['Setting', 'Value']
            rows = [
                ['Stop Loss %', f"{risk_config['stop_loss_percent']:.2f}%"],
                ['Take Profit %', f"{risk_config['take_profit_percent']:.2f}%"],
                ['Max Daily Trades', risk_config['max_daily_trades']],
                ['Max Daily Loss %', f"{risk_config['max_daily_loss_percent']:.2f}%"],
                ['Trailing Stop', '✅' if risk_config['trailing_stop_enabled'] else '❌'],
                ['Trailing Stop %', f"{risk_config['trailing_stop_percent']:.2f}%"],
                ['Max Drawdown %', f"{risk_config['max_drawdown_percent']:.2f}%"],
                ['Position Sizing', risk_config['position_sizing_method']],
                ['Volatility Lookback', f"{risk_config['volatility_lookback_days']} days"]
            ]
            
            print(tabulate(rows, headers=headers, tablefmt='grid'))
        else:
            # List risk config for all pairs
            pairs = self.config_manager.get_active_trading_pairs()
            for pair in pairs:
                self.list_risk_config(pair['symbol'])
    
    def update_risk_config(self, symbol: str, **risk_params):
        """Update risk configuration for a trading pair."""
        success = self.config_manager.update_pair_risk_config(symbol, **risk_params)
        
        if success:
            print(f"✅ Successfully updated risk configuration for {symbol}")
        else:
            print(f"❌ Failed to update risk configuration for {symbol}")
    
    def list_system_config(self):
        """List system configuration."""
        config = self.config_manager.get_all_system_config()
        
        if not config:
            print("No system configuration found.")
            return
        
        print("\n⚙️  System Configuration:")
        headers = ['Key', 'Value', 'Type']
        rows = []
        
        for key, value in sorted(config.items()):
            value_type = type(value).__name__
            if isinstance(value, bool):
                display_value = '✅' if value else '❌'
            else:
                display_value = str(value)
            
            rows.append([key, display_value, value_type])
        
        print(tabulate(rows, headers=headers, tablefmt='grid'))
    
    def set_system_config(self, key: str, value: str, config_type: str = None):
        """Set system configuration value."""
        # Auto-convert value based on type
        if config_type == 'boolean' or value.lower() in ('true', 'false'):
            actual_value = value.lower() == 'true'
        elif config_type == 'integer' or value.isdigit():
            actual_value = int(value)
        elif config_type == 'float':
            try:
                actual_value = float(value)
            except ValueError:
                actual_value = value
        else:
            actual_value = value
        
        success = self.config_manager.set_system_config(key, actual_value, config_type)
        
        if success:
            print(f"✅ Successfully set {key} = {actual_value}")
        else:
            print(f"❌ Failed to set {key}")
    
    def validate_config(self):
        """Validate multi-cryptocurrency configuration."""
        validation = self.config_manager.validate_multi_crypto_config()
        
        print("\n🔍 Configuration Validation:")
        print(f"Status: {'✅ Valid' if validation['valid'] else '❌ Invalid'}")
        
        if validation['summary']:
            print("\n📊 Summary:")
            for key, value in validation['summary'].items():
                print(f"  • {key.replace('_', ' ').title()}: {value}")
        
        if validation['errors']:
            print("\n❌ Errors:")
            for error in validation['errors']:
                print(f"  • {error}")
        
        if validation['warnings']:
            print("\n⚠️  Warnings:")
            for warning in validation['warnings']:
                print(f"  • {warning}")
    
    def show_portfolio_allocation(self):
        """Show portfolio allocation across trading pairs."""
        pairs = self.config_manager.get_active_trading_pairs()
        system_config = self.config_manager.get_all_system_config()
        
        total_balance = float(system_config.get('total_portfolio_balance', 10000))
        
        print(f"\n💰 Portfolio Allocation (Total: ${total_balance:,.2f}):")
        headers = ['Symbol', 'Max Position %', 'Allocated Amount', 'Trade Size', 'Remaining']
        rows = []
        
        total_allocated = 0
        for pair in pairs:
            max_position_percent = float(pair['max_position_percent'])
            trade_size_usd = float(pair['trade_size_usd'])
            
            allocated_amount = total_balance * (max_position_percent / 100)
            remaining = allocated_amount - trade_size_usd
            total_allocated += max_position_percent
            
            rows.append([
                pair['symbol'],
                f"{max_position_percent:.1f}%",
                f"${allocated_amount:,.2f}",
                f"${trade_size_usd:,.2f}",
                f"${remaining:,.2f}"
            ])
        
        print(tabulate(rows, headers=headers, tablefmt='grid'))
        print(f"\nTotal Allocation: {total_allocated:.1f}%")
        print(f"Unallocated: {100 - total_allocated:.1f}%")
    
    def show_cache_stats(self):
        """Show cache statistics."""
        stats = self.config_manager.get_cache_stats()
        
        print("\n🚀 Configuration Cache Statistics:")
        headers = ['Metric', 'Value']
        rows = [
            ['Total Entries', stats['total_entries']],
            ['Active Entries', stats['active_entries']],
            ['Expired Entries', stats['expired_entries']],
            ['Cache Size (bytes)', f"{stats['cache_size_bytes']:,}"],
            ['Cache TTL (seconds)', stats['cache_ttl_seconds']]
        ]
        
        print(tabulate(rows, headers=headers, tablefmt='grid'))
    
    def warm_cache(self):
        """Warm the configuration cache."""
        print("🔥 Warming configuration cache...")
        warmed = self.config_manager.warm_cache()
        
        print("\n✅ Cache warming completed:")
        headers = ['Component', 'Entries Cached']
        rows = [
            ['System Config', warmed['system_config']],
            ['Trading Pairs', warmed['trading_pairs']],
            ['Strategies', warmed['strategies']],
            ['Risk Configs', warmed['risk_configs']]
        ]
        
        print(tabulate(rows, headers=headers, tablefmt='grid'))
    
    def clear_cache(self):
        """Clear the configuration cache."""
        self.config_manager.clear_cache()
        print("✅ Configuration cache cleared")
    
    def benchmark_cache(self):
        """Benchmark cache performance."""
        import time
        
        print("🏃 Running cache performance benchmark...")
        
        # Clear cache first
        self.config_manager.clear_cache()
        
        # Test without cache
        start_time = time.time()
        for _ in range(10):
            self.config_manager.get_all_system_config(use_cache=False)
            pairs = self.config_manager.get_active_trading_pairs(use_cache=False)
            for pair in pairs[:3]:  # Test first 3 pairs
                self.config_manager.get_pair_strategies(pair['symbol'], use_cache=False)
                self.config_manager.get_pair_risk_config(pair['symbol'], use_cache=False)
        
        no_cache_time = time.time() - start_time
        
        # Test with cache (first run will populate cache)
        start_time = time.time()
        for _ in range(10):
            self.config_manager.get_all_system_config(use_cache=True)
            pairs = self.config_manager.get_active_trading_pairs(use_cache=True)
            for pair in pairs[:3]:  # Test first 3 pairs
                self.config_manager.get_pair_strategies(pair['symbol'], use_cache=True)
                self.config_manager.get_pair_risk_config(pair['symbol'], use_cache=True)
        
        with_cache_time = time.time() - start_time
        
        # Calculate improvement
        improvement = ((no_cache_time - with_cache_time) / no_cache_time) * 100
        
        print("\n📊 Cache Performance Results:")
        headers = ['Metric', 'Value']
        rows = [
            ['Without Cache (10 iterations)', f"{no_cache_time:.3f} seconds"],
            ['With Cache (10 iterations)', f"{with_cache_time:.3f} seconds"],
            ['Performance Improvement', f"{improvement:.1f}%"],
            ['Speed Multiplier', f"{no_cache_time / with_cache_time:.1f}x faster"]
        ]
        
        print(tabulate(rows, headers=headers, tablefmt='grid'))

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description='Multi-cryptocurrency configuration management')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List commands
    list_parser = subparsers.add_parser('list', help='List configurations')
    list_subparsers = list_parser.add_subparsers(dest='list_type')
    
    list_subparsers.add_parser('pairs', help='List trading pairs')
    list_subparsers.add_parser('system', help='List system configuration')
    list_subparsers.add_parser('portfolio', help='Show portfolio allocation')
    
    strategies_parser = list_subparsers.add_parser('strategies', help='List strategies')
    strategies_parser.add_argument('--symbol', help='Trading pair symbol')
    
    risk_parser = list_subparsers.add_parser('risk', help='List risk configuration')
    risk_parser.add_argument('--symbol', help='Trading pair symbol')
    
    # Cache management commands
    cache_parser = subparsers.add_parser('cache', help='Cache management')
    cache_subparsers = cache_parser.add_subparsers(dest='cache_action')
    
    cache_subparsers.add_parser('stats', help='Show cache statistics')
    cache_subparsers.add_parser('warm', help='Warm the cache')
    cache_subparsers.add_parser('clear', help='Clear the cache')
    cache_subparsers.add_parser('benchmark', help='Benchmark cache performance')
    
    # Add trading pair
    add_pair_parser = subparsers.add_parser('add-pair', help='Add trading pair')
    add_pair_parser.add_argument('symbol', help='Trading pair symbol (e.g., BTC/USDT)')
    add_pair_parser.add_argument('base', help='Base currency (e.g., BTC)')
    add_pair_parser.add_argument('quote', help='Quote currency (e.g., USDT)')
    add_pair_parser.add_argument('--balance', type=float, default=1000.0, help='Initial balance')
    add_pair_parser.add_argument('--trade-size', type=float, default=100.0, help='Trade size in USD')
    add_pair_parser.add_argument('--max-position', type=float, default=20.0, help='Max position percentage')
    
    # Update strategy
    update_strategy_parser = subparsers.add_parser('update-strategy', help='Update strategy configuration')
    update_strategy_parser.add_argument('symbol', help='Trading pair symbol')
    update_strategy_parser.add_argument('strategy', help='Strategy name')
    update_strategy_parser.add_argument('--parameters', help='Strategy parameters (JSON)')
    update_strategy_parser.add_argument('--weight', type=float, help='Strategy weight')
    update_strategy_parser.add_argument('--enabled', type=bool, help='Enable/disable strategy')
    
    # Update risk config
    update_risk_parser = subparsers.add_parser('update-risk', help='Update risk configuration')
    update_risk_parser.add_argument('symbol', help='Trading pair symbol')
    update_risk_parser.add_argument('--stop-loss', type=float, help='Stop loss percentage')
    update_risk_parser.add_argument('--take-profit', type=float, help='Take profit percentage')
    update_risk_parser.add_argument('--max-trades', type=int, help='Max daily trades')
    update_risk_parser.add_argument('--max-loss', type=float, help='Max daily loss percentage')
    
    # Set system config
    set_config_parser = subparsers.add_parser('set-config', help='Set system configuration')
    set_config_parser.add_argument('key', help='Configuration key')
    set_config_parser.add_argument('value', help='Configuration value')
    set_config_parser.add_argument('--type', help='Value type (string, integer, float, boolean)')
    
    # Validate config
    subparsers.add_parser('validate', help='Validate configuration')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = MultiCryptoConfigCLI()
    
    try:
        if args.command == 'list':
            if args.list_type == 'pairs':
                cli.list_trading_pairs()
            elif args.list_type == 'strategies':
                cli.list_strategies(getattr(args, 'symbol', None))
            elif args.list_type == 'risk':
                cli.list_risk_config(getattr(args, 'symbol', None))
            elif args.list_type == 'system':
                cli.list_system_config()
            elif args.list_type == 'portfolio':
                cli.show_portfolio_allocation()
            else:
                list_parser.print_help()
        
        elif args.command == 'cache':
            if args.cache_action == 'stats':
                cli.show_cache_stats()
            elif args.cache_action == 'warm':
                cli.warm_cache()
            elif args.cache_action == 'clear':
                cli.clear_cache()
            elif args.cache_action == 'benchmark':
                cli.benchmark_cache()
            else:
                cache_parser.print_help()
        
        elif args.command == 'add-pair':
            cli.add_trading_pair(
                args.symbol, args.base, args.quote,
                initial_balance=args.balance,
                trade_size_usd=args.trade_size,
                max_position_percent=args.max_position
            )
        
        elif args.command == 'update-strategy':
            cli.update_strategy(
                args.symbol, args.strategy,
                args.parameters, args.weight, args.enabled
            )
        
        elif args.command == 'update-risk':
            risk_params = {}
            if args.stop_loss is not None:
                risk_params['stop_loss_percent'] = args.stop_loss
            if args.take_profit is not None:
                risk_params['take_profit_percent'] = args.take_profit
            if args.max_trades is not None:
                risk_params['max_daily_trades'] = args.max_trades
            if args.max_loss is not None:
                risk_params['max_daily_loss_percent'] = args.max_loss
            
            cli.update_risk_config(args.symbol, **risk_params)
        
        elif args.command == 'set-config':
            cli.set_system_config(args.key, args.value, args.type)
        
        elif args.command == 'validate':
            cli.validate_config()
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"CLI error: {e}")
    finally:
        cli.config_manager.close_session()

if __name__ == '__main__':
    main()