"""SMTP mail delivery. Configuration must be supplied at deployment."""
import os
import smtplib
import ssl
from email.message import EmailMessage


def send_security_email(email: str, subject: str, url: str) -> None:
    host = os.getenv('SMTP_HOST')
    username = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASSWORD')
    sender = os.getenv('SMTP_FROM')
    if not all((host, username, password, sender)):
        raise RuntimeError('SMTP delivery is not configured')
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = email
    msg.set_content(f'RouletteIQ security link:\n\n{url}\n\nIf you did not request this, ignore it.')
    port = int(os.getenv('SMTP_PORT', '465'))
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15, context=ssl.create_default_context()) as smtp:
            smtp.login(username, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(username, password)
            smtp.send_message(msg)
