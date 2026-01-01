"""
Telegram notification service for trading alerts and errors using pyTelegramBotAPI.
Based on: https://www.freecodecamp.org/news/how-to-create-a-telegram-bot-using-python/
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

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class TelegramNotifier:
    """Sends notifications via Telegram bot using pyTelegramBotAPI."""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.enabled = bool(self.bot_token and self.chat_id)
        
        self.bot = None
        self.use_telebot = False
        
        if TELEBOT_AVAILABLE and self.enabled:
            try:
                self.bot = telebot.TeleBot(self.bot_token)
                self.use_telebot = True
                logger.info("Telegram bot initialized with pyTelegramBotAPI")
            except Exception as e:
                logger.error(f"Error initializing Telegram bot: {e}")
                self.use_telebot = False
        
        if not self.enabled:
            logger.warning("Telegram notifications disabled - missing bot token or chat ID")
        elif not TELEBOT_AVAILABLE:
            logger.warning("pyTelegramBotAPI not available, using requests fallback")
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message to Telegram.
        
        Args:
            message: Message text
            parse_mode: Message parse mode (HTML or Markdown)
            
        Returns:
            True if message sent successfully
        """
        if not self.enabled:
            logger.debug(f"Telegram disabled - would send: {message}")
            return False
        
        # Try pyTelegramBotAPI first
        if self.use_telebot and self.bot:
            try:
                self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=parse_mode
                )
                logger.debug("Telegram message sent successfully via pyTelegramBotAPI")
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
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.debug("Telegram message sent successfully via requests")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message via requests: {e}")
            return False
    
    def send_message_with_keyboard(self, message: str, keyboard_options: list = None) -> bool:
        """
        Send a message with inline keyboard (only works with pyTelegramBotAPI).
        
        Args:
            message: Message text
            keyboard_options: List of keyboard button options
            
        Returns:
            True if message sent successfully
        """
        if not self.enabled or not self.use_telebot:
            return self.send_message(message)
        
        try:
            markup = None
            if keyboard_options:
                markup = types.InlineKeyboardMarkup()
                for option in keyboard_options:
                    button = types.InlineKeyboardButton(
                        text=option['text'],
                        callback_data=option.get('callback_data', option['text'])
                    )
                    markup.add(button)
            
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML",
                reply_markup=markup
            )
            logger.debug("Telegram message with keyboard sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message with keyboard: {e}")
            return self.send_message(message)
    
    def send_trade_notification(self, trade_data: Dict[str, Any]) -> bool:
        """
        Send trade notification.
        
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
            reason = trade_data.get('reason', 'No reason provided')
            balance_usd = trade_data.get('balance_usd', 0)
            balance_crypto = trade_data.get('balance_crypto', 0)
            
            # Determine emoji based on order type
            emoji = "🟢" if order_type == "BUY" else "🔴"
            
            message = f"""
{emoji} <b>TRADE EXECUTED</b> {emoji}

<b>Type:</b> {order_type}
<b>Symbol:</b> {symbol}
<b>Strategy:</b> {strategy}
<b>Price:</b> ${price:.2f}
<b>Amount:</b> {amount:.6f}
<b>Total Value:</b> ${total_value:.2f}
<b>Reason:</b> {reason}

<b>💰 Portfolio Status:</b>
<b>USD Balance:</b> ${balance_usd:.2f}
<b>Crypto Balance:</b> {balance_crypto:.6f}

<b>⏰ Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
<b>🧪 Mode:</b> {'Paper Trading' if settings.PAPER_TRADING else 'LIVE TRADING'}
            """.strip()
            
            # Add interactive buttons for trade notifications
            keyboard_options = [
                {'text': '📊 Portfolio Status', 'callback_data': 'portfolio_status'},
                {'text': '📈 Market Info', 'callback_data': 'market_info'},
                {'text': '⚙️ Bot Status', 'callback_data': 'bot_status'}
            ]
            
            return self.send_message_with_keyboard(message, keyboard_options)
            
        except Exception as e:
            logger.error(f"Error sending trade notification: {e}")
            return False
    
    def send_error_notification(self, error_message: str, context: str = None) -> bool:
        """
        Send error notification.
        
        Args:
            error_message: Error message
            context: Additional context (optional)
            
        Returns:
            True if notification sent successfully
        """
        try:
            message = f"""
🚨 <b>TRADING BOT ERROR</b> 🚨

<b>Error:</b> {error_message}
"""
            
            if context:
                message += f"\n<b>Context:</b> {context}"
            
            message += f"\n\n<b>⏰ Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            
            # Add action buttons for error notifications
            keyboard_options = [
                {'text': '🔄 Restart Bot', 'callback_data': 'restart_bot'},
                {'text': '📋 View Logs', 'callback_data': 'view_logs'},
                {'text': '⚙️ Check Config', 'callback_data': 'check_config'}
            ]
            
            return self.send_message_with_keyboard(message, keyboard_options)
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
            return False
    
    def send_bot_status_notification(self, status: str, additional_info: Dict[str, Any] = None) -> bool:
        """
        Send bot status notification.
        
        Args:
            status: Bot status (STARTED, STOPPED, ERROR, etc.)
            additional_info: Additional information dictionary
            
        Returns:
            True if notification sent successfully
        """
        try:
            status_emojis = {
                'STARTING': '🚀',
                'STARTED': '🟢',
                'STOPPED': '🔴',
                'ERROR': '🚨',
                'WARNING': '⚠️',
                'INFO': 'ℹ️',
                'INITIALIZING': '⚙️',
                'INITIALIZED': '✅'
            }
            
            emoji = status_emojis.get(status, 'ℹ️')
            
            message = f"""
{emoji} <b>BOT STATUS UPDATE</b> {emoji}

<b>Status:</b> {status}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
            
            if additional_info:
                message += "\n<b>📊 Additional Info:</b>\n"
                for key, value in additional_info.items():
                    message += f"<b>{key.replace('_', ' ').title()}:</b> {value}\n"
            
            # Add status-specific buttons
            keyboard_options = []
            if status in ['STARTED', 'INITIALIZED']:
                keyboard_options = [
                    {'text': '📊 Portfolio', 'callback_data': 'portfolio'},
                    {'text': '⚙️ Configuration', 'callback_data': 'config'},
                    {'text': '📈 Performance', 'callback_data': 'performance'}
                ]
            elif status == 'ERROR':
                keyboard_options = [
                    {'text': '🔄 Restart', 'callback_data': 'restart'},
                    {'text': '📋 Logs', 'callback_data': 'logs'}
                ]
            
            return self.send_message_with_keyboard(message, keyboard_options)
            
        except Exception as e:
            logger.error(f"Error sending status notification: {e}")
            return False
    
    def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """
        Send daily trading summary.
        
        Args:
            summary_data: Summary data dictionary
            
        Returns:
            True if notification sent successfully
        """
        try:
            total_trades = summary_data.get('total_trades', 0)
            winning_trades = summary_data.get('winning_trades', 0)
            total_pnl = summary_data.get('total_pnl', 0)
            win_rate = summary_data.get('win_rate', 0)
            portfolio_value = summary_data.get('portfolio_value', 0)
            
            pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
            
            message = f"""
📊 <b>DAILY TRADING SUMMARY</b> 📊

<b>📈 Performance:</b>
<b>Total Trades:</b> {total_trades}
<b>Winning Trades:</b> {winning_trades}
<b>Win Rate:</b> {win_rate:.1f}%
{pnl_emoji} <b>Total P&L:</b> ${total_pnl:.2f}

<b>💰 Portfolio:</b>
<b>Total Value:</b> ${portfolio_value:.2f}

<b>📅 Date:</b> {datetime.now().strftime('%Y-%m-%d')}
<b>🧪 Mode:</b> Paper Trading (Multi-Crypto System)
            """.strip()
            
            keyboard_options = [
                {'text': '📊 Detailed Report', 'callback_data': 'detailed_report'},
                {'text': '📈 Charts', 'callback_data': 'charts'},
                {'text': '⚙️ Adjust Settings', 'callback_data': 'adjust_settings'}
            ]
            
            return self.send_message_with_keyboard(message, keyboard_options)
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            return False
    
    def send_signal_notification(self, signal_data: Dict[str, Any]) -> bool:
        """
        Send trading signal notification.
        
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
            
            signal_emojis = {
                'BUY': '🟢📈',
                'SELL': '🔴📉',
                'HOLD': '🟡⏸️'
            }
            
            emoji = signal_emojis.get(signal, '❓')
            
            message = f"""
{emoji} <b>TRADING SIGNAL</b> {emoji}

<b>Signal:</b> {signal}
<b>Symbol:</b> {symbol}
<b>Strategy:</b> {strategy}
<b>Price:</b> ${price:.2f}

<b>📊 Indicators:</b>
"""
            
            for indicator, value in indicators.items():
                if value is not None:
                    if isinstance(value, float):
                        message += f"<b>{indicator.upper()}:</b> {value:.2f}\n"
                    else:
                        message += f"<b>{indicator.upper()}:</b> {value}\n"
            
            message += f"\n<b>⏰ Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            
            # Add signal-specific buttons
            keyboard_options = []
            if signal in ['BUY', 'SELL']:
                keyboard_options = [
                    {'text': f'✅ Confirm {signal}', 'callback_data': f'confirm_{signal.lower()}'},
                    {'text': '❌ Ignore Signal', 'callback_data': 'ignore_signal'},
                    {'text': '📊 More Info', 'callback_data': 'signal_info'}
                ]
            
            return self.send_message_with_keyboard(message, keyboard_options)
            
        except Exception as e:
            logger.error(f"Error sending signal notification: {e}")
            return False
    
    def send_startup_notification(self) -> bool:
        """
        Send application startup notification.
        
        Returns:
            True if notification sent successfully
        """
        try:
            message = f"""
🚀 <b>MULTI-CRYPTO TRADING BOT STARTING UP</b> 🚀

<b>🤖 Bot Information:</b>
• Exchange: OKX
• Mode: 📝 Paper Trading (Multi-Crypto System)
• System: Database-driven configuration

<b>⚙️ Configuration:</b>
• Multi-cryptocurrency support
• Individual pair configurations
• Cached configuration system
• Comprehensive event logging

<b>📊 Strategies:</b>
• SMA Crossover Strategy (per pair)
• RSI Strategy (per pair)

<b>🔧 Risk Management:</b>
• Per-pair risk settings
• Portfolio-level controls
• Real-time monitoring

<b>⏰ Startup Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

🔄 Initializing multi-crypto components...
            """.strip()
            
            keyboard_options = [
                {'text': '📊 Monitor Progress', 'callback_data': 'monitor_startup'},
                {'text': '⚙️ View Config', 'callback_data': 'view_config'},
                {'text': '🛑 Stop Bot', 'callback_data': 'stop_bot'}
            ]
            
            return self.send_message_with_keyboard(message, keyboard_options)
            
        except Exception as e:
            logger.error(f"Error sending startup notification: {e}")
            return False
    
    def send_ready_notification(self, bot_info: Dict[str, Any]) -> bool:
        """
        Send bot ready notification.
        
        Args:
            bot_info: Bot information dictionary
            
        Returns:
            True if notification sent successfully
        """
        try:
            trading_pairs = bot_info.get('trading_pairs', [])
            paper_trading = bot_info.get('paper_trading', True)
            total_balance = bot_info.get('total_balance', '$10,000.00')
            pairs_count = bot_info.get('pairs_count', 0)
            strategies_count = bot_info.get('strategies_count', 0)
            
            message = f"""
✅ <b>MULTI-CRYPTO TRADING BOT READY</b> ✅

🎯 <b>All systems operational and ready to trade!</b>

<b>📊 Current Status:</b>
• Trading Pairs: {pairs_count} active pairs
• Total Balance: {total_balance}
• Strategies: {strategies_count} active strategies
• Mode: {'📝 Paper Trading' if paper_trading else '💰 LIVE TRADING'}

<b>🔄 Bot will now:</b>
• Monitor multiple cryptocurrency pairs
• Execute trades based on individual pair strategies
• Send notifications for all activities
• Maintain comprehensive risk management

<b>💡 Multi-Crypto Features:</b>
• Individual pair configurations
• Cached configuration system
• Real-time event logging
• Portfolio-level risk management

🚀 <b>Happy Trading!</b>
<b>⏰ Started:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            """.strip()
            
            keyboard_options = [
                {'text': '📊 Live Dashboard', 'callback_data': 'dashboard'},
                {'text': '📈 Market Analysis', 'callback_data': 'market_analysis'},
                {'text': '⚙️ Settings', 'callback_data': 'settings'},
                {'text': '🛑 Stop Trading', 'callback_data': 'stop_trading'}
            ]
            
            return self.send_message_with_keyboard(message, keyboard_options)
            
        except Exception as e:
            logger.error(f"Error sending ready notification: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test Telegram bot connection.
        
        Returns:
            True if connection successful
        """
        if not self.enabled:
            logger.warning("Telegram notifications not configured")
            return False
        
        test_message = f"""
🤖 <b>TRADING BOT TEST</b> 🤖

This is a test message to verify Telegram notifications are working.

<b>⏰ Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
<b>🧪 Mode:</b> Paper Trading (Multi-Crypto System)
<b>🔧 Library:</b> {'pyTelegramBotAPI' if self.use_telebot else 'requests fallback'}
        """.strip()
        
        keyboard_options = [
            {'text': '✅ Test Successful', 'callback_data': 'test_success'},
            {'text': '📊 Bot Status', 'callback_data': 'bot_status'}
        ]
        
        success = self.send_message_with_keyboard(test_message, keyboard_options)
        if success:
            logger.info("Telegram test message sent successfully")
        else:
            logger.error("Failed to send Telegram test message")
        
        return success
    
    def setup_webhook_handlers(self):
        """
        Setup webhook handlers for interactive buttons (optional feature).
        This would be used if you want to handle button callbacks.
        """
        if not self.use_telebot or not self.bot:
            return
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback_query(call):
            """Handle callback queries from inline keyboards."""
            try:
                callback_data = call.data
                chat_id = call.message.chat.id
                
                # Handle different callback actions
                if callback_data == 'portfolio_status':
                    self.bot.answer_callback_query(call.id, "Portfolio status requested")
                    # Here you would implement portfolio status logic
                    
                elif callback_data == 'bot_status':
                    self.bot.answer_callback_query(call.id, "Bot status requested")
                    # Here you would implement bot status logic
                    
                elif callback_data == 'restart_bot':
                    self.bot.answer_callback_query(call.id, "Restart request received")
                    # Here you would implement restart logic
                    
                else:
                    self.bot.answer_callback_query(call.id, f"Action: {callback_data}")
                
            except Exception as e:
                logger.error(f"Error handling callback query: {e}")
    
    def start_webhook_polling(self):
        """
        Start polling for webhook updates in a separate thread.
        This is optional and only needed if you want interactive buttons.
        """
        if not self.use_telebot or not self.bot:
            return
        
        def polling_thread():
            try:
                self.setup_webhook_handlers()
                self.bot.polling(none_stop=True, interval=1)
            except Exception as e:
                logger.error(f"Error in webhook polling: {e}")
        
        thread = threading.Thread(target=polling_thread, daemon=True)
        thread.start()
        logger.info("Telegram webhook polling started")

# Global telegram notifier instance
telegram_notifier = TelegramNotifier()