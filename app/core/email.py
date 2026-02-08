import smtplib
from email.mime.text import MIMEText
import asyncio

from app.core.config import Config

async def send_email(to_email: str, subject: str, body: str):
    """
    Async SMTP email sender.
    Runs blocking SMTP in background thread.
    """

    def _send():
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = Config.FROM_EMAIL
        msg["To"] = to_email

        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.sendmail(Config.FROM_EMAIL, [to_email], msg.as_string())

    await asyncio.to_thread(_send)
