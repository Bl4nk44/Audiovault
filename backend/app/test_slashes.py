
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_slashes():
    urls = [
        "/rest/ping.view",
        "/rest/ping.view/",
        "/rest/getAlbumList2.view",
        "/rest/getAlbumList2.view/",
    ]
    
    for url in urls:
        response = client.get(url, params={"u": "admin", "p": "admin", "c": "test"})
        print(f"URL: {url} -> Status: {response.status_code}")

if __name__ == "__main__":
    test_slashes()
