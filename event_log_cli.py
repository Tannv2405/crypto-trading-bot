#!/usr/bin/env python3
"""
Event Log CLI tool for querying and analyzing trading bot events.
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Optional
import json

from db.db_utils import db_manager, EventLog
from utils.logger import setup_logger

logger = setup_logger('event_log_cli')

class EventLogCLI:
    """CLI for querying and analyzing event logs."""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def list_events(self, limit: int = 50, event_type: str = None, 
                   symbol: str = None, severity: str = None,
                   hours: int = None, days: int = None):
        """List recent events with optional filtering."""
        try:
            # Calculate date range if specified
            start_date = None
            if hours:
                start_date = datetime.utcnow() - timedelta(hours=hours)
            elif days:
                start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get events
            events = self.db_manager.get_event_logs(
                limit=limit,
                event_type=event_type,
                symbol=symbol,
                severity=severity,
                start_date=start_date
            )
            
            if not events:
                print("No events found matching the criteria.")
                return
            
            print(f"\n📊 Event Log ({len(events)} events)")
            print("=" * 100)
            
            for event in events:
                # Format timestamp
                timestamp = event.event_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # Format severity with colors/emojis
                severity_icon = {
                    'DEBUG': '🔍',
                    'INFO': 'ℹ️',
                    'WARNING': '⚠️',
                    'ERROR': '❌',
                    'CRITICAL': '🚨'
                }.get(event.severity, '📝')
                
                print(f"\n{severity_icon} [{event.severity}] {timestamp}")
                print(f"   Type: {event.event_type} | Category: {event.event_category}")
                
                if event.symbol:
                    print(f"   Symbol: {event.symbol}")
                if event.strategy:
                    print(f"   Strategy: {event.strategy}")
                
                print(f"   Message: {event.message}")
                
                # Show order details if available
                if event.order_type:
                    print(f"   Order: {event.order_type} | Status: {event.order_status}")
                    if event.price and event.amount:
                        print(f"   Price: ${event.price:.2f} | Amount: {event.amount:.6f}")
                        if event.total_value:
                            print(f"   Total Value: ${event.total_value:.2f}")
                
                # Show error details if available
                if event.error_code:
                    print(f"   Error Code: {event.error_code}")
                    if event.error_message:
                        print(f"   Error: {event.error_message}")
                
                # Show additional details if available
                if event.details:
                    try:
                        details = json.loads(event.details)
                        if details:
                            print(f"   Details: {details}")
                    except:
                        print(f"   Details: {event.details}")
                
                if event.correlation_id:
                    print(f"   Correlation ID: {event.correlation_id}")
                
                print("-" * 100)
        
        except Exception as e:
            print(f"Error listing events: {e}")
            logger.error(f"Error listing events: {e}")
    
    def show_order_history(self, symbol: str = None, limit: int = 30):
        """Show order history from event logs."""
        try:
            events = self.db_manager.get_order_history_from_events(symbol=symbol, limit=limit)
            
            if not events:
                print("No order history found.")
                return
            
            print(f"\n📈 Order History ({len(events)} orders)")
            if symbol:
                print(f"Symbol: {symbol}")
            print("=" * 100)
            
            for event in events:
                timestamp = event.event_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # Status icon
                status_icon = {
                    'ORDER_ATTEMPT': '🔄',
                    'ORDER_SUCCESS': '✅',
                    'ORDER_FAILED': '❌'
                }.get(event.event_type, '📝')
                
                print(f"\n{status_icon} {timestamp} | {event.symbol}")
                print(f"   {event.event_type}: {event.order_type} | {event.strategy}")
                
                if event.price and event.amount:
                    print(f"   Price: ${event.price:.2f} | Amount: {event.amount:.6f}")
                    if event.total_value:
                        print(f"   Total: ${event.total_value:.2f}")
                
                if event.order_status:
                    print(f"   Status: {event.order_status}")
                
                print(f"   Message: {event.message}")
                
                if event.correlation_id:
                    print(f"   ID: {event.correlation_id}")
                
                print("-" * 50)
        
        except Exception as e:
            print(f"Error showing order history: {e}")
            logger.error(f"Error showing order history: {e}")
    
    def show_errors(self, limit: int = 20, hours: int = None):
        """Show recent errors."""
        try:
            start_date = None
            if hours:
                start_date = datetime.utcnow() - timedelta(hours=hours)
            
            events = self.db_manager.get_event_logs(
                limit=limit,
                severity='ERROR',
                start_date=start_date
            )
            
            if not events:
                print("No errors found.")
                return
            
            print(f"\n🚨 Error Log ({len(events)} errors)")
            print("=" * 100)
            
            for event in events:
                timestamp = event.event_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
                
                print(f"\n❌ {timestamp}")
                if event.symbol:
                    print(f"   Symbol: {event.symbol}")
                if event.strategy:
                    print(f"   Strategy: {event.strategy}")
                
                print(f"   Message: {event.message}")
                
                if event.error_code:
                    print(f"   Error Code: {event.error_code}")
                if event.error_message:
                    print(f"   Error Details: {event.error_message}")
                
                if event.source_function:
                    print(f"   Source: {event.source_function}")
                
                print("-" * 100)
        
        except Exception as e:
            print(f"Error showing errors: {e}")
            logger.error(f"Error showing errors: {e}")
    
    def show_statistics(self, hours: int = 24):
        """Show event statistics for the specified time period."""
        try:
            start_date = datetime.utcnow() - timedelta(hours=hours)
            
            events = self.db_manager.get_event_logs(
                limit=1000,  # Get more events for statistics
                start_date=start_date
            )
            
            if not events:
                print("No events found for statistics.")
                return
            
            # Calculate statistics
            stats = {
                'total_events': len(events),
                'by_type': {},
                'by_category': {},
                'by_severity': {},
                'by_symbol': {},
                'orders': {
                    'attempts': 0,
                    'successes': 0,
                    'failures': 0
                }
            }
            
            for event in events:
                # Count by type
                stats['by_type'][event.event_type] = stats['by_type'].get(event.event_type, 0) + 1
                
                # Count by category
                stats['by_category'][event.event_category] = stats['by_category'].get(event.event_category, 0) + 1
                
                # Count by severity
                stats['by_severity'][event.severity] = stats['by_severity'].get(event.severity, 0) + 1
                
                # Count by symbol
                if event.symbol:
                    stats['by_symbol'][event.symbol] = stats['by_symbol'].get(event.symbol, 0) + 1
                
                # Count orders
                if event.event_type == 'ORDER_ATTEMPT':
                    stats['orders']['attempts'] += 1
                elif event.event_type == 'ORDER_SUCCESS':
                    stats['orders']['successes'] += 1
                elif event.event_type == 'ORDER_FAILED':
                    stats['orders']['failures'] += 1
            
            # Display statistics
            print(f"\n📊 Event Statistics (Last {hours} hours)")
            print("=" * 60)
            
            print(f"\nTotal Events: {stats['total_events']}")
            
            print(f"\nBy Event Type:")
            for event_type, count in sorted(stats['by_type'].items()):
                print(f"  {event_type}: {count}")
            
            print(f"\nBy Category:")
            for category, count in sorted(stats['by_category'].items()):
                print(f"  {category}: {count}")
            
            print(f"\nBy Severity:")
            for severity, count in sorted(stats['by_severity'].items()):
                print(f"  {severity}: {count}")
            
            if stats['by_symbol']:
                print(f"\nBy Symbol:")
                for symbol, count in sorted(stats['by_symbol'].items(), key=lambda x: x[1], reverse=True):
                    print(f"  {symbol}: {count}")
            
            print(f"\nOrder Statistics:")
            print(f"  Attempts: {stats['orders']['attempts']}")
            print(f"  Successes: {stats['orders']['successes']}")
            print(f"  Failures: {stats['orders']['failures']}")
            
            if stats['orders']['attempts'] > 0:
                success_rate = (stats['orders']['successes'] / stats['orders']['attempts']) * 100
                print(f"  Success Rate: {success_rate:.1f}%")
        
        except Exception as e:
            print(f"Error showing statistics: {e}")
            logger.error(f"Error showing statistics: {e}")

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description='Event Log CLI for Trading Bot')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List events command
    list_parser = subparsers.add_parser('list', help='List recent events')
    list_parser.add_argument('--limit', type=int, default=50, help='Number of events to show')
    list_parser.add_argument('--type', help='Filter by event type')
    list_parser.add_argument('--symbol', help='Filter by trading pair')
    list_parser.add_argument('--severity', help='Filter by severity level')
    list_parser.add_argument('--hours', type=int, help='Show events from last N hours')
    list_parser.add_argument('--days', type=int, help='Show events from last N days')
    
    # Order history command
    orders_parser = subparsers.add_parser('orders', help='Show order history')
    orders_parser.add_argument('--symbol', help='Filter by trading pair')
    orders_parser.add_argument('--limit', type=int, default=30, help='Number of orders to show')
    
    # Errors command
    errors_parser = subparsers.add_parser('errors', help='Show recent errors')
    errors_parser.add_argument('--limit', type=int, default=20, help='Number of errors to show')
    errors_parser.add_argument('--hours', type=int, help='Show errors from last N hours')
    
    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show event statistics')
    stats_parser.add_argument('--hours', type=int, default=24, help='Time period for statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = EventLogCLI()
    
    try:
        if args.command == 'list':
            cli.list_events(
                limit=args.limit,
                event_type=args.type,
                symbol=args.symbol,
                severity=args.severity,
                hours=args.hours,
                days=args.days
            )
        elif args.command == 'orders':
            cli.show_order_history(symbol=args.symbol, limit=args.limit)
        elif args.command == 'errors':
            cli.show_errors(limit=args.limit, hours=args.hours)
        elif args.command == 'stats':
            cli.show_statistics(hours=args.hours)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"CLI error: {e}")

if __name__ == "__main__":
    main()