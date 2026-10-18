from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from backend.app.main import app


def test_only_one_of_twenty_writers_wins(client, nurse_headers):
    beds = client.get("/wards/1/beds", headers=nurse_headers).json()
    bed = next(b for b in beds if b["status"] == "available")
    url = f"/beds/{bed['id']}/status"

    def attempt(_):
        c = TestClient(app)
        r = c.patch(url, json={"status": "reserved", "version": bed["version"]}, headers=nurse_headers)
        return r.status_code

    try:
        with ThreadPoolExecutor(max_workers=20) as pool_:
            codes = list(pool_.map(attempt, range(20)))

        assert codes.count(200) == 1
        # The losers get 409 (stale version). A loser that reads the bed after the winner
        # committed gets 400 instead (reserved to reserved is not allowed). Both are rejections.
        assert set(codes) <= {200, 400, 409}
    finally:
        # Put the bed back to available so the database stays tidy
        now = next(b for b in client.get("/wards/1/beds", headers=nurse_headers).json() if b["id"] == bed["id"])
        if now["status"] == "reserved":
            client.patch(url, json={"status": "available", "version": now["version"]}, headers=nurse_headers)