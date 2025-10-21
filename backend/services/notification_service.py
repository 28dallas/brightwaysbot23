import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)

class NotificationService:
    def __init__(self):
        self.telegram_token = Config.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = Config.TELEGRAM_CHAT_ID
        self.email_enabled = Config.EMAIL_NOTIFICATIONS
        self.notification_queue = asyncio.Queue()

    async def start_notification_worker(self):
        """Start background notification worker"""
        asyncio.create_task(self._notification_worker())

    async def _notification_worker(self):
        """Background worker to process notifications"""
        while True:
            try:
                notification = await self.notification_queue.get()
                await self._send_notification(notification)
                self.notification_queue.task_done()
            except Exception as e:
                logger.error(f"Notification worker error: {e}")
                await asyncio.sleep(1)

    async def notify_trade_executed(self, trade_data: Dict):
        """Notify when a trade is executed"""
        message = f"""
🤖 Trade Executed
Contract: {trade_data.get('contract_type', 'Unknown')}
Stake: ${trade_data.get('stake', 0):.2f}
Prediction: {trade_data.get('prediction', 'N/A')}
Confidence: {trade_data.get('confidence', 0):.1%}
        """.strip()

        await self._queue_notification('trade_executed', message, trade_data)

    async def notify_trade_closed(self, trade_data: Dict):
        """Notify when a trade is closed"""
        pnl = trade_data.get('pnl', 0)
        status = trade_data.get('status', 'unknown')
        emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "🟡"

        message = f"""
{emoji} Trade Closed
Contract ID: {trade_data.get('contract_id', 'N/A')}
Result: {status.upper()}
P&L: ${pnl:.2f}
        """.strip()

        await self._queue_notification('trade_closed', message, trade_data)

    async def notify_risk_alert(self, alert_type: str, message: str, data: Dict = None):
        """Notify for risk management alerts"""
        full_message = f"""
⚠️ Risk Alert: {alert_type}
{message}
        """.strip()

        await self._queue_notification('risk_alert', full_message, data or {})

    async def notify_system_status(self, status: str, details: str = ""):
        """Notify system status changes"""
        emoji = {
            'started': '🚀',
            'stopped': '⏹️',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }.get(status.lower(), '📢')

        message = f"""
{emoji} System {status.upper()}
{details}
        """.strip()

        await self._queue_notification('system_status', message, {'status': status})

    async def notify_daily_summary(self, stats: Dict):
        """Send daily trading summary"""
        win_rate = stats.get('win_rate', 0)
        total_pnl = stats.get('total_pnl', 0)
        trades = stats.get('trades', 0)

        emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "🟡"

        message = f"""
📊 Daily Trading Summary
{emoji} Total P&L: ${total_pnl:.2f}
📈 Win Rate: {win_rate:.1f}%
🎯 Total Trades: {trades}
📉 Max Drawdown: {stats.get('max_drawdown', 0):.1f}%
        """.strip()

        await self._queue_notification('daily_summary', message, stats)

    async def _queue_notification(self, notification_type: str, message: str, data: Dict):
        """Queue notification for processing"""
        notification = {
            'type': notification_type,
            'message': message,
            'data': data,
            'timestamp': asyncio.get_event_loop().time()
        }

        await self.notification_queue.put(notification)
        logger.info(f"Queued {notification_type} notification")

    async def _send_notification(self, notification: Dict):
        """Send notification through all enabled channels"""
        message = notification['message']

        # Send Telegram notification
        if self.telegram_token and self.telegram_chat_id:
            await self._send_telegram(message)

        # Send email notification (if enabled)
        if self.email_enabled:
            await self._send_email(
                subject=f"Brightbot {notification['type'].replace('_', ' ').title()}",
                body=message
            )

        # Log all notifications
        logger.info(f"Notification sent: {notification['type']} - {message[:100]}...")

    async def _send_telegram(self, message: str):
        """Send message via Telegram bot"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info("Telegram notification sent successfully")
                    else:
                        logger.error(f"Telegram notification failed: {response.status}")

        except Exception as e:
            logger.error(f"Telegram notification error: {e}")

    async def _send_email(self, subject: str, body: str, to_email: str = None):
        """Send email notification"""
        try:
            # Email configuration would need to be added to Config
            # This is a placeholder implementation
            smtp_server = getattr(Config, 'SMTP_SERVER', None)
            smtp_port = getattr(Config, 'SMTP_PORT', 587)
            smtp_username = getattr(Config, 'SMTP_USERNAME', None)
            smtp_password = getattr(Config, 'SMTP_PASSWORD', None)

            if not all([smtp_server, smtp_username, smtp_password]):
                logger.warning("Email configuration incomplete, skipping email notification")
                return

            msg = MIMEMultipart()
            msg['From'] = smtp_username
            msg['To'] = to_email or getattr(Config, 'NOTIFICATION_EMAIL', smtp_username)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            text = msg.as_string()
            server.sendmail(smtp_username, msg['To'], text)
            server.quit()

            logger.info("Email notification sent successfully")

        except Exception as e:
            logger.error(f"Email notification error: {e}")

    async def test_notifications(self):
        """Test all notification channels"""
        test_message = "🧪 Brightbot Notification Test"

        logger.info("Testing notification channels...")

        # Test Telegram
        if self.telegram_token and self.telegram_chat_id:
            await self._send_telegram(test_message)
            logger.info("Telegram test sent")
        else:
            logger.info("Telegram not configured")

        # Test Email
        if self.email_enabled:
            await self._send_email("Brightbot Test", test_message)
            logger.info("Email test sent")
        else:
            logger.info("Email not enabled")

        return {"telegram_configured": bool(self.telegram_token and self.telegram_chat_id),
                "email_enabled": self.email_enabled}
