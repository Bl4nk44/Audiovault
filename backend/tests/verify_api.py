import requests
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Health Check Passed")
        else:
            print(f"❌ Health Check Failed: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Health Check Error: {e}")
        sys.exit(1)

def test_login():
    try:
        payload = {
            "email": "admin",
            "password": "admin"
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=payload)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("✅ Login Passed")
            return token
        else:
            print(f"❌ Login Failed: {response.status_code} - {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Login Error: {e}")
        sys.exit(1)

def test_me(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        if response.status_code == 200:
            user = response.json()
            print(f"✅ Get Profile Passed (User: {user['username']})")
        else:
            print(f"❌ Get Profile Failed: {response.status_code} - {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Get Profile Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting API Verification...")
    test_health()
    token = test_login()
    test_me(token)
    print("All tests passed!")
