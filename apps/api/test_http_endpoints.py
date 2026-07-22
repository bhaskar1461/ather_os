import asyncio
import json
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from main import app
from app.security.dependencies import get_current_user
from packages.database.models import User

# Mock get_current_user dependency to bypass authentication
class DummyUser:
    id = 1
    email = "test@example.com"

async def mock_get_current_user():
    return DummyUser()

app.dependency_overrides[get_current_user] = mock_get_current_user
client = TestClient(app)

def test_compatibility():
    print("=== Testing POST /astrology/compatibility ===")
    payload = {
        "partner_a": {
            "year": 1990, "month": 5, "day": 15, "hour": 10, "minute": 30,
            "location_name": "Mumbai, India", "location_lat": 19.076, "location_lon": 72.877, "location_timezone": "Asia/Kolkata"
        },
        "partner_b": {
            "year": 1992, "month": 8, "day": 20, "hour": 14, "minute": 15,
            "location_name": "Delhi, India", "location_lat": 28.613, "location_lon": 77.209, "location_timezone": "Asia/Kolkata"
        },
        "partner_a_name": "Groom A",
        "partner_b_name": "Bride B",
        "force_refresh": True
    }
    
    response = client.post("/astrology/compatibility", json=payload)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Guna Score: {data['score']}/36")
        print("Reading preview:")
        print(data["reading"][:500].encode("ascii", "ignore").decode("ascii") + "...")
    else:
        print(response.text)

def test_transit():
    print("\n=== Testing POST /astrology/transit ===")
    payload = {
        "birth_year": 1990, "birth_month": 5, "birth_day": 15, "birth_hour": 10, "birth_minute": 30,
        "birth_lat": 19.076, "birth_lon": 72.877, "birth_timezone": "Asia/Kolkata",
        
        "current_lat": 19.076, "current_lon": 72.877, "current_timezone": "Asia/Kolkata",
        "force_refresh": True
    }
    response = client.post("/astrology/transit", json=payload)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Horoscope date: {data['date']}")
        print("Horoscope preview:")
        print(data["horoscope"][:500].encode("ascii", "ignore").decode("ascii") + "...")

    else:
        print(response.text)

if __name__ == "__main__":
    test_compatibility()
    test_transit()
