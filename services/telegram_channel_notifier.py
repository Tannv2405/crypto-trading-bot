"""
Telegram channel notification service for trading signals.
Sends trading signals to a specific Telegram channel when strategies generate valid signals.
"""

import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
import logging

try:
    import telebot
    from telebot import types
    TELEBOT_AVAILABLE = True
except ImportError:
    TELEBOT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("pyTelegramBotAPI not installed, falling back to requests")

import requests

from utils.logger import get_logger

logger = get_logger(__name__)

class TelegramChannelNotifier:
    """Sends trading signals to Telegram channel."""
    
    def __init__(self, bot_token: str, channel_id: str):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.enabled = bool(self.bot_token and self.channel_id)
        
        self.bot = None
        self.use_telebot = False
        
        if TELEBOT_AVAILABLE and self.enabled:
            try:
                self.bot = telebot.TeleBot(self.bot_token)
                self.use_telebot = True
                logger.info(f"Telegram channel bot initialized for channel: {self.channel_id}")
            except Exception as e:
                logger.error(f"Error initializing Telegram channel bot: {e}")
                self.use_telebot = False
        
        if not self.enabled:
            logger.warning("Telegram channel notifications disabled - missing bot token or channel ID")
        elif not TELEBOT_AVAILABLE:
            logger.warning("pyTelegramBotAPI not available, using requests fallback")
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message to Telegram channel.
        
        Args:
            message: Message text
            parse_mode: Message parse mode (HTML or Markdown)
            
        Returns:
            True if message sent successfully
        """
        if not self.enabled:
            logger.debug(f"Telegram channel disabled - would send: {message}")
            return False
        
        # Try pyTelegramBotAPI first
        if self.use_telebot and self.bot:
            try:
                self.bot.send_message(
                    chat_id=self.channel_id,
                    text=message,
                    parse_mode=parse_mode
                )
                logger.debug("Telegram channel message sent successfully via pyTelegramBotAPI")
                return True
            except Exception as e:
                logger.error(f"Error sending message via pyTelegramBotAPI: {e}")
                # Fall back to requests method
                return self._send_message_requests(message, parse_mode)
        else:
            # Use requests fallback
            return self._send_message_requests(message, parse_mode)
    
    def _send_message_requests(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send message using requests (fallback method).
        
        Args:
            message: Message text
            parse_mode: Message parse mode
            
        Returns:
            True if message sent successfully
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.channel_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.debug("Telegram channel message sent successfully via requests")
                return True
            else:
                logger.error(f"Failed to send Telegram channel message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram channel message via requests: {e}")
            return False
    
    def send_trading_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Send trading signal to channel.
        
        Args:
            signal_data: Signal data dictionary
            
        Returns:
            True if notification sent successfully
        """
        try:
            signal = signal_data.get('signal', 'UNKNOWN')
            symbol = signal_data.get('symbol', 'UNKNOWN')
            price = signal_data.get('price', 0)
            strategy = signal_data.get('strategy', 'UNKNOWN')
            indicators = signal_data.get('indicators', {})
            confidence = signal_data.get('confidence', 'Medium')
            reason = signal_data.get('reason', 'Strategy conditions met')
            
            # Only send BUY and SELL signals, skip HOLD
            if signal == 'HOLD':
                return True
            
            signal_emojis = {
                'BUY': '🟢📈',
                'SELL': '🔴📉'
            }
            
            emoji = signal_emojis.get(signal, '❓')
            
            message = f"""
{emoji} <b>CRYPTO TRADING SIGNAL</b> {emoji}

🎯 <b>Signal:</b> {signal}
💰 <b>Symbol:</b> {symbol}
📊 <b>Strategy:</b> {strategy}
💵 <b>Price:</b> ${price:.2f}
🔥 <b>Confidence:</b> {confidence}

📈 <b>Technical Indicators:</b>
"""
            
            # Add indicators with proper formatting
            for indicator, value in indicators.items():
                if value is not None:
                    if isinstance(value, float):
                        if 'sma' in indicator.lower():
                            message += f"• <b>{indicator.upper()}:</b> ${value:.2f}\n"
                        elif 'rsi' in indicator.lower():
                            message += f"• <b>{indicator.upper()}:</b> {value:.1f}\n"
                        else:
                            message += f"• <b>{indicator.upper()}:</b> {value:.2f}\n"
                    else:
                        message += f"• <b>{indicator.upper()}:</b> {value}\n"
            
            message += f"""
💡 <b>Reason:</b> {reason}

⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
🤖 <b>Bot:</b> Multi-Crypto Trading Bot
⚠️ <b>Disclaimer:</b> This is not financial advice. Trade at your own risk.

#CryptoSignal #{symbol.replace('/', '')} #{strategy.replace('_', '').upper()}
            """.strip()
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending trading signal to channel: {e}")
            return False
    
    def send_trade_execution(self, trade_data: Dict[str, Any]) -> bool:
        """
        Send trade execution notification to channel.
        
        Args:
            trade_data: Trade information dictionary
            
        Returns:
            True if notification sent successfully
        """
        try:
            order_type = trade_data.get('order_type', 'UNKNOWN')
            symbol = trade_data.get('symbol', 'UNKNOWN')
            price = trade_data.get('price', 0)
            amount = trade_data.get('amount', 0)
            total_value = trade_data.get('total_value', 0)
            strategy = trade_data.get('strategy', 'UNKNOWN')
            is_paper = trade_data.get('is_paper_trade', True)
            
            # Determine emoji based on order type
            emoji = "✅🟢" if order_type == "BUY" else "✅🔴"
            mode_emoji = "📝" if is_paper else "💰"
            
            message = f"""
{emoji} <b>TRADE EXECUTED</b> {emoji}

🎯 <b>Action:</b> {order_type}
💰 <b>Symbol:</b> {symbol}
📊 <b>Strategy:</b> {strategy}
💵 <b>Price:</b> ${price:.2f}
📦 <b>Amount:</b> {amount:.6f}
💸 <b>Total Value:</b> ${total_value:.2f}

{mode_emoji} <b>Mode:</b> {'Paper Trading' if is_paper else 'LIVE TRADING'}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

🤖 <b>Bot:</b> Multi-Crypto Trading Bot
⚠️ <b>Note:</b> This is an automated trade execution.

#TradeExecution #{symbol.replace('/', '')} #{order_type}
            """.strip()
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending trade execution to channel: {e}")
            return False
    
    def send_market_analysis(self, analysis_data: Dict[str, Any]) -> bool:
        """
        Send market analysis to channel.
        
        Args:
            analysis_data: Market analysis data
            
        Returns:
            True if notification sent successfully
        """
        try:
            symbol = analysis_data.get('symbol', 'UNKNOWN')
            price = analysis_data.get('price', 0)
            price_change_24h = analysis_data.get('price_change_24h', 0)
            volume_24h = analysis_data.get('volume_24h', 0)
            market_trend = analysis_data.get('market_trend', 'NEUTRAL')
            
            trend_emojis = {
                'BULLISH': '🐂📈',
                'BEARISH': '🐻📉',
                'NEUTRAL': '🦘➡️'
            }
            
            emoji = trend_emojis.get(market_trend, '📊')
            change_emoji = "🟢" if price_change_24h >= 0 else "🔴"
            
            message = f"""
{emoji} <b>MARKET ANALYSIS</b> {emoji}

💰 <b>Symbol:</b> {symbol}
💵 <b>Current Price:</b> ${price:.2f}
{change_emoji} <b>24h Change:</b> {price_change_24h:+.2f}%
📊 <b>24h Volume:</b> ${volume_24h:,.0f}
📈 <b>Trend:</b> {market_trend}

⏰ <b>Analysis Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
🤖 <b>Bot:</b> Multi-Crypto Trading Bot

#MarketAnalysis #{symbol.replace('/', '')} #{market_trend}
            """.strip()
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending market analysis to channel: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test Telegram channel connection.
        
        Returns:
            True if connection successful
        """
        if not self.enabled:
            logger.warning("Telegram channel notifications not configured")
            return False
        
        test_message = f"""
🤖 <b>CHANNEL TEST MESSAGE</b> 🤖

This is a test message to verify the trading signals channel is working correctly.

📡 <b>Channel ID:</b> {self.channel_id}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
🔧 <b>Library:</b> {'pyTelegramBotAPI' if self.use_telebot else 'requests fallback'}

✅ If you can see this message, the channel notifications are working properly!

#ChannelTest #TradingBot
        """.strip()
        
        success = self.send_message(test_message)
        if success:
            logger.info("Telegram channel test message sent successfully")
        else:
            logger.error("Failed to send Telegram channel test message")
        
        return success

# Global channel notifier instance - will be initialized in main.py
channel_notifier = None

def initialize_channel_notifier(bot_token: str, channel_id: str) -> TelegramChannelNotifier:
    """
    Initialize the global channel notifier instance.
    
    Args:
        bot_token: Telegram bot token
        channel_id: Telegram channel ID
        
    Returns:
        TelegramChannelNotifier instance
    """
    global channel_notifier
    channel_notifier = TelegramChannelNotifier(bot_token, channel_id)
    return channel_notifier

def get_channel_notifier() -> Optional[TelegramChannelNotifier]:
    """
    Get the global channel notifier instance.
    
    Returns:
        TelegramChannelNotifier instance or None if not initialized
    """
    return channel_notifier