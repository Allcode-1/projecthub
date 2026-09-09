from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings

"""
overkill async is intentional; celery bg exec
"""


async def send_email(recipient: str, subject: str, html_body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.sender_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content("This email requires an HTML-capable email client.")
    message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        sender=settings.sender_email,
        hostname=settings.smtp_hostname,
        port=settings.smtp_port,
        username=settings.sender_email,
        password=settings.smtp_password.get_secret_value(),
        start_tls=True,
    )
