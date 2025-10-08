import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List
import os
from utils.logger import setup_logger

logger = setup_logger(__name__)

class NotificationService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        
    async def send_trade_alert(self, user_email: str, trade_data: Dict):
        """Send trade execution alert"""
        try:
            subject = f"Trade Alert - {trade_data['result'].upper()}"
            
            body = f"""
            Trade Executed:
            
            Contract Type: {trade_data['contract_type']}
            Symbol: {trade_data['symbol']}
            Stake: ${trade_data['stake']}
            Result: {trade_data['result'].upper()}
            P&L: ${trade_data['pnl']}
            Contract ID: {trade_data['contract_id']}
            
            Account: {trade_data['account_type'].upper()}
            """
            
            await self._send_email(user_email, subject, body)
            
        except Exception as e:
            logger.error(f"Trade alert error: {e}")
    
    async def send_risk_alert(self, user_email: str, alert_type: str, details: Dict):
        """Send risk management alerts"""
        try:
            subject = f"Risk Alert - {alert_type}"
            
            if alert_type == "DAILY_LIMIT":
                body = f"Daily loss limit reached: ${details['daily_loss']}"
            elif alert_type == "CONSECUTIVE_LOSSES":
                body = f"5 consecutive losses detected. Trading halted."
            elif alert_type == "DRAWDOWN":
                body = f"Maximum drawdown exceeded: ${details['drawdown']}"
            else:
                body = f"Risk alert: {details}"
                
            await self._send_email(user_email, subject, body)
            
        except Exception as e:
            logger.error(f"Risk alert error: {e}")
    
    async def send_performance_report(self, user_email: str, metrics: Dict):
        """Send daily/weekly performance report"""
        try:
            subject = "Trading Performance Report"
            
            body = f"""
            Performance Summary:
            
            Total Trades: {metrics['total_trades']}
            Win Rate: {metrics['win_rate']}%
            Profit Factor: {metrics['profit_factor']}
            Total P&L: ${metrics['total_pnl']}
            Sharpe Ratio: {metrics['sharpe_ratio']}
            Max Drawdown: ${metrics['max_drawdown']}
            
            Keep up the great work!
            """
            
            await self._send_email(user_email, subject, body)
            
        except Exception as e:
            logger.error(f"Performance report error: {e}")
    
    async def _send_email(self, to_email: str, subject: str, body: str):
        """Send email notification"""
        if not self.email_user or not self.email_password:
            logger.warning("Email credentials not configured")
            return
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            
            text = msg.as_string()
            server.sendmail(self.email_user, to_email, text)
            server.quit()
            
            logger.info(f"Email sent to {to_email}")
            
        except Exception as e:
            logger.error(f"Email send error: {e}")