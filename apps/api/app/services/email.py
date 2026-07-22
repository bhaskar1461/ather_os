"""
Email Service Module — Async SMTP email dispatcher.
Supports sending OTP, verification, password reset, and transactional emails.
"""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import get_settings
from app.middleware.logging import get_logger

settings = get_settings()
logger = get_logger("email_service")


def send_email_sync(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> bool:
    """
    Synchronous helper to send email via SMTP using Python standard library smtplib.
    Runs inside a threadpool worker when invoked from async context.
    """
    if not settings.smtp_username or not settings.smtp_password:
        logger.warning("smtp_not_configured", detail="SMTP username or password missing")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email

    plain_body = text_content or html_content
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
            if settings.smtp_use_tls:
                server.starttls()

        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        server.quit()
        logger.info("email_sent_successfully", recipient=to_email, subject=subject)
        return True
    except Exception as e:
        logger.error("email_send_failed", recipient=to_email, error=str(e))
        return False


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> bool:
    """
    Asynchronous email dispatcher wrapper that executes SMTP sending in thread pool.
    """
    return await asyncio.to_thread(
        send_email_sync, to_email, subject, html_content, text_content
    )


async def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Send a 6-digit OTP code to the recipient email address.
    """
    subject = f"Your AetherOS Login Verification Code: {otp_code}"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #050505; color: #e5e5e5; margin: 0; padding: 40px 20px; }}
        .container {{ max-width: 500px; margin: 0 auto; background: #121215; border: 1px solid #27272a; border-radius: 12px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        .logo {{ text-align: center; font-size: 24px; font-weight: 700; color: #ffffff; letter-spacing: 1px; margin-bottom: 24px; }}
        .otp-box {{ background: #1a1a22; border: 1px dashed #3f3f46; border-radius: 8px; font-size: 36px; font-weight: 800; letter-spacing: 8px; text-align: center; padding: 20px; color: #60a5fa; margin: 24px 0; }}
        .info {{ font-size: 14px; color: #a1a1aa; line-height: 1.6; text-align: center; }}
        .footer {{ margin-top: 32px; pt: 20px; border-top: 1px solid #27272a; font-size: 12px; color: #71717a; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="logo">✦ AetherOS</div>
        <h2 style="text-align: center; color: #ffffff; margin-top: 0;">One-Time Verification Code</h2>
        <p class="info">Use the following security code to complete your login or authentication request. This code will expire in 10 minutes.</p>
        <div class="otp-box">{otp_code}</div>
        <p class="info">If you did not request this code, please ignore this email or contact security.</p>
        <div class="footer">
          &copy; AetherOS Private AI Node. All rights reserved.
        </div>
      </div>
    </body>
    </html>
    """
    text = f"Your AetherOS login verification code is: {otp_code}. This code expires in 10 minutes."
    return await send_email(to_email, subject, html, text)


async def send_verification_email(to_email: str, token: str) -> bool:
    """
    Send email verification link to new users.
    """
    subject = "Verify your AetherOS Account"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #050505; color: #e5e5e5; margin: 0; padding: 40px 20px; }}
        .container {{ max-width: 500px; margin: 0 auto; background: #121215; border: 1px solid #27272a; border-radius: 12px; padding: 32px; }}
        .btn {{ display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
      </style>
    </head>
    <body>
      <div class="container" style="text-align: center;">
        <h2 style="color: #ffffff;">Welcome to AetherOS</h2>
        <p style="color: #a1a1aa;">Please verify your email address by clicking the button below:</p>
        <p>Verification Code: <strong style="color: #60a5fa;">{token}</strong></p>
      </div>
    </body>
    </html>
    """
    text = f"Welcome to AetherOS. Your email verification token is: {token}"
    return await send_email(to_email, subject, html, text)


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Send password reset instructions.
    """
    subject = "Password Reset Request — AetherOS"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
    </head>
    <body style="background: #050505; color: #e5e5e5; font-family: sans-serif; padding: 40px;">
      <div style="max-width: 500px; margin: auto; background: #121215; padding: 30px; border-radius: 10px; border: 1px solid #27272a;">
        <h2 style="color: #fff;">Password Reset Request</h2>
        <p style="color: #a1a1aa;">Use the reset token below to reset your password:</p>
        <div style="background: #1a1a22; padding: 15px; text-align: center; border-radius: 6px; font-weight: bold; font-size: 18px; color: #60a5fa; margin: 20px 0;">{reset_token}</div>
        <p style="color: #71717a; font-size: 12px;">This token expires in 60 minutes.</p>
      </div>
    </body>
    </html>
    """
    text = f"AetherOS Password Reset Token: {reset_token}. Expires in 60 minutes."
    return await send_email(to_email, subject, html, text)
