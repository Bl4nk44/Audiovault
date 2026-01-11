import asyncio
import logging

import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
# Default credentials (from init_data.py usually)
USERNAME = "admin"
PASSWORD = "admin"


async def verify_api():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Login
        logger.info("🔐 Logging in...")
        try:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": f"{USERNAME}@example.com", "password": PASSWORD}
                if "@" not in USERNAME
                else {"email": USERNAME, "password": PASSWORD},
                # Attempting with email since UserLogin usually requires email.
                # If username is supported, adapt.
                # Let's try standard username first if that's what UserLogin uses.
                # Actually, check auth.py imports UserLogin.
            )
            # Retrying with simple username payload just in case schema matches
            if response.status_code == 422:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": USERNAME, "password": PASSWORD},
                )

            if response.status_code != 200:
                logger.error(f"❌ Login failed: {response.text}")
                return

            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            logger.info("✅ Login successful")
        except Exception as e:
            logger.error(f"❌ Could not connect to API: {e}")
            return

        # 2. Test /users/me (GET)
        logger.info("👤 Testing /api/v1/users/me (GET)...")
        try:
            response = await client.get("/api/v1/users/me", headers=headers)
            if response.status_code == 200:
                logger.info("✅ /users/me (GET) OK")
            else:
                logger.error(f"❌ /users/me (GET) Failed: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"❌ /users/me (GET) Error: {e}")

        # 3. Test /users/me (PUT) - Simulate update
        logger.info("📝 Testing /api/v1/users/me (PUT)...")
        try:
            # Send a valid update
            response = await client.put(
                "/api/v1/users/me",
                headers=headers,
                json={"username": USERNAME},  # Keep same username
            )
            if response.status_code == 200:
                logger.info("✅ /users/me (PUT) OK")
            else:
                logger.error(f"❌ /users/me (PUT) Failed: {response.status_code} {response.text}")

            # Send update with avatar_url (simulate old frontend)
            logger.info("📝 Testing /api/v1/users/me (PUT) with avatar_url...")
            response = await client.put(
                "/api/v1/users/me",
                headers=headers,
                json={"username": USERNAME, "avatar_url": "http://example.com/foo.jpg"},
            )
            if response.status_code == 200:
                logger.info("✅ /users/me (PUT with avatar_url) OK (ignored)")
            elif response.status_code == 422:
                logger.info("ℹ️ /users/me (PUT with avatar_url) 422 (Expected if forbidden)")
            else:
                logger.error(f"❌ /users/me (PUT with avatar_url) Failed: {response.status_code} {response.text}")

        except Exception as e:
            logger.error(f"❌ /users/me (PUT) Error: {e}")

        # 4. Test Subsonic API
        logger.info("🎵 Testing Subsonic API...")
        SUBSONIC_PARAMS = {
            "u": USERNAME,
            "p": PASSWORD,  # Plaintext for simplicity in test
            "v": "1.16.1",
            "c": "verify_script",
            "f": "json",
        }

        # 4.1 Ping
        try:
            response = await client.get("/rest/ping.view", params=SUBSONIC_PARAMS)
            if response.status_code == 200 and response.json()["subsonic-response"]["status"] == "ok":
                logger.info("✅ Subsonic Ping OK")
            else:
                try:
                    logger.error(f"❌ Subsonic Ping Failed: {response.status_code} {response.text}")
                except Exception:
                    logger.error(f"❌ Subsonic Ping Failed: {response.status_code} (Binary response)")
        except Exception as e:
            logger.error(f"❌ Subsonic Ping Error: {e}")

        # 4.2 Get Indexes
        try:
            response = await client.get("/rest/getIndexes.view", params=SUBSONIC_PARAMS)
            if response.status_code == 200:
                data = response.json()["subsonic-response"]
                if data["status"] == "ok":
                    logger.info("✅ Subsonic getIndexes OK")

                    # Try to get an artist ID for Cover Art test
                    artists = []
                    if "indexes" in data and "index" in data["indexes"]:
                        for index in data["indexes"]["index"]:
                            if "artist" in index:
                                artists.extend(index["artist"])

                    if artists:
                        artist_id = artists[0]["id"]
                        logger.info(f"🎨 Testing getCoverArt for ID: {artist_id}")
                        cover_response = await client.get(
                            "/rest/getCoverArt.view", params={**SUBSONIC_PARAMS, "id": artist_id}
                        )
                        if cover_response.status_code == 200:
                            logger.info(
                                f"✅ Subsonic getCoverArt (ID: {artist_id}) OK (Size: {len(cover_response.content)})"
                            )
                            if "X-Cache" in cover_response.headers:
                                logger.info(f"   Cache Status: {cover_response.headers['X-Cache']}")
                        else:
                            try:
                                logger.error(
                                    f"❌ Subsonic getCoverArt Failed: {cover_response.status_code} {cover_response.text[:200]}"
                                )
                            except Exception:
                                logger.error(f"❌ Subsonic getCoverArt Failed: {cover_response.status_code}")
                    else:
                        logger.warning("⚠️ No artists found to test Cover Art")

                else:
                    logger.error(f"❌ Subsonic getIndexes Failed (Status not OK): {data}")
            else:
                logger.error(f"❌ Subsonic getIndexes Failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Subsonic getIndexes Error: {e}")

        except Exception as e:
            logger.error(f"❌ Subsonic getIndexes Error: {e}")

        # 5. Fetch System Logs to debug the reported crash
        logger.info("📜 Fetching System Logs via API...")
        try:
            response = await client.get("/api/v1/system/logs?lines=500", headers=headers)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    logs = (
                        "".join(data) if data and isinstance(data[0], str) else "\n".join([str(line) for line in data])
                    )
                else:
                    logs = data.get("logs", "")

                logger.info(f"✅ Fetched {len(logs)} characters of logs")
                with open("/app/fetched_logs.txt", "w", encoding="utf-8") as f:
                    f.write(logs)
            else:
                logger.error(f"❌ Failed to fetch logs: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error fetching logs: {e}")


if __name__ == "__main__":
    asyncio.run(verify_api())
