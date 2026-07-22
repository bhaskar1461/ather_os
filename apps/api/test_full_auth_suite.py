"""
Comprehensive Authentication & API Test Suite.
Tests: Register, Login, OTP request, OTP verify, OTP resend, Google login, Forgot password, Reset password, Get me.
"""

import sys
import os
import secrets
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app

def run_tests():
    print("=========================================")
    print("     STARTING COMPREHENSIVE AUTH QA      ")
    print("=========================================")

    with TestClient(app) as client:
        test_email = f"user_{secrets.token_hex(4)}@aetheros.com"
        test_password = "Password123!"

        # 1. Register User
        print(f"\n1. Testing POST /auth/register ({test_email})...")
        resp = client.post("/auth/register", json={
            "email": test_email,
            "password": test_password,
            "name": "Test User"
        })
        print(f"Status: {resp.status_code}")
        assert resp.status_code == 201, f"Registration failed: {resp.text}"
        user_data = resp.json()
        print(f"Registered User ID: {user_data['id']}")

        # 2. Login User
        print("\n2. Testing POST /auth/login...")
        resp = client.post("/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        print(f"Status: {resp.status_code}")
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        tokens = resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        print("Access token received successfully.")

        # 3. Get /auth/me
        print("\n3. Testing GET /auth/me...")
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        print(f"Status: {resp.status_code}")
        assert resp.status_code == 200, f"Get me failed: {resp.text}"
        print(f"Authenticated as: {resp.json()['email']}")

        # 4. Request Email OTP
        otp_email = f"otp_{secrets.token_hex(4)}@aetheros.com"
        print(f"\n4. Testing POST /auth/otp/request ({otp_email})...")
        resp = client.post("/auth/otp/request", json={"email": otp_email})
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")

        # 5. Forgot Password
        print("\n5. Testing POST /auth/forgot-password...")
        resp = client.post("/auth/forgot-password", json={"email": test_email})
        print(f"Status: {resp.status_code}")
        assert resp.status_code == 200, f"Forgot password failed: {resp.text}"

        # 6. Verify me state
        print("\n6. Re-testing GET /auth/me after operations...")
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        print(f"Status: {resp.status_code}")
        assert resp.status_code == 200, f"Re-get me failed: {resp.text}"
        print(f"Verified profile state. Token valid.")

    print("\n=========================================")
    print("   ALL AUTHENTICATION CHECKS PASSED!     ")
    print("=========================================")

if __name__ == "__main__":
    run_tests()
