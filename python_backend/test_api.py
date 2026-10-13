import sys
import os

# Add directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_endpoints():
    print("1. Testing Health Check...")
    r = client.get("/health")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("   Health Check OK:", r.json())

    print("\n2. Testing Services List...")
    r = client.get("/api/v1/services")
    assert r.status_code == 200
    services = r.json()
    print(f"   Found {len(services)} services:")
    for s in services[:3]:
        print(f"   - {s['name']} ({s['estimated_time']}) [Prefix: {s['prefix']}]")

    print("\n3. Testing Counters List...")
    r = client.get("/api/v1/counters")
    assert r.status_code == 200
    counters = r.json()
    print(f"   Found {len(counters)} counters:")
    for c in counters:
        print(f"   - {c['name']} ({c['desk_label']}): Now Serving: {c['current_token_number']}, Waiting: {c['waiting_count']}")

    print("\n4. Testing Live Queue Overview...")
    r = client.get("/api/v1/queue/live")
    assert r.status_code == 200
    q = r.json()
    print(f"   Total Waiting: {q['total_waiting']}, Served Today: {q['total_served_today']}")
    print(f"   Now serving tokens: {[x['token_number'] for x in q['now_serving']]}")
    print(f"   Recent updates count: {len(q['recent_updates'])}")

    print("\n5. Testing Token Tracking (Demo Token A108)...")
    r = client.get("/api/v1/tokens/track/A108")
    assert r.status_code == 200
    t = r.json()
    print(f"   Token A108: Status={t['status']}, People Ahead={t['people_ahead']}, Wait={t['estimated_wait_minutes']}m")
    print(f"   Notice: {t['notice']}")

    print("\n6. Testing Token Booking (/get-token)...")
    book_payload = {
        "customer_name": "Deepak Sharma",
        "customer_phone": "+919876543219",
        "customer_email": "deepak@example.com",
        "customer_account_number": "1002938475",
        "service_id": services[0]["id"],
        "booking_date": "Today",
        "time_slot": "11:30 AM"
    }
    r = client.post("/api/v1/tokens/book", json=book_payload)
    assert r.status_code == 200
    booked = r.json()
    print(f"   Booked new token: {booked['token_number']} for {booked['customer_name']}")
    print(f"   Assigned: {booked['counter_name']} ({booked['desk_label']}), Est. Wait: {booked['estimated_wait_minutes']}m")

    print("\n7. Testing Counter Staff Call-Next Operation...")
    r = client.post(f"/api/v1/counters/{counters[0]['id']}/call-next")
    assert r.status_code == 200
    call_res = r.json()
    print("   Call Next Result:", call_res["message"])

    print("\n8. Testing User Registration & Login...")
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_phone = f"+919{int(uuid.uuid4().int % 1000000000):09d}"
    test_email = f"testuser_{uid}@example.com"
    reg_payload = {
        "full_name": "Test User",
        "phone": test_phone,
        "email": test_email,
        "password": "Password123"
    }
    r = client.post("/api/v1/auth/register", json=reg_payload)
    assert r.status_code == 200, f"Registration failed: {r.text}"
    auth_data = r.json()
    print(f"   Registered successfully! JWT Access Token received (length: {len(auth_data['access_token'])})")

    login_payload = {
        "identifier": test_phone,
        "password": "Password123"
    }
    r = client.post("/api/v1/auth/login", json=login_payload)
    assert r.status_code == 200, f"Login failed: {r.text}"
    print("   Login successful with phone number!")

    print("\n9. Testing Contact Inquiry Submission...")
    contact_payload = {
        "name": "Sarah Connor",
        "email": "sarah@example.com",
        "message": "Do I need to carry original KYC documents for account opening?"
    }
    r = client.post("/api/v1/contact", json=contact_payload)
    assert r.status_code == 200
    print("   Contact submission OK:", r.json()["message"])

    print("\nALL PYTHON BACKEND TESTS PASSED SUCCESSFULLY! 100% OPERATIONAL.")

if __name__ == "__main__":
    test_endpoints()
