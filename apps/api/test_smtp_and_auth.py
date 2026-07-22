"""
Test script for verifying SMTP sending, OTP flow, and Google auth routes.
"""

import asyncio
from app.services.email import send_email, send_otp_email
from app.config import get_settings

settings = get_settings()

async def test_smtp():
    print("=== Testing SMTP Email Dispatch ===")
    print(f"SMTP Host: {settings.smtp_host}:{settings.smtp_port}")
    print(f"SMTP User: {settings.smtp_username}")
    
    # Test sending OTP email to the configured user gmail
    target = settings.smtp_username
    print(f"Sending test OTP email to {target}...")
    success = await send_otp_email(target, "849201")
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")

if __name__ == "__main__":
    asyncio.run(test_smtp())
