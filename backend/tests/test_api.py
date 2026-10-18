def test_login_success(client):
    r = client.post("/auth/login", json={"email": "nurse@caregrid.com", "password": "nurse123"})
    assert r.status_code == 200
    assert r.json()["role"] == "nurse"


def test_login_wrong_password(client):
    r = client.post("/auth/login", json={"email": "nurse@caregrid.com", "password": "wrong"})
    assert r.status_code == 401


def test_protected_route_needs_token(client):
    assert client.get("/wards").status_code in (401, 403)


def test_nurse_blocked_from_other_ward(client, nurse_headers, admin_headers):
    other = client.get("/wards/2/beds", headers=admin_headers).json()[0]
    r = client.patch(
        f"/beds/{other['id']}/status",
        json={"status": "cleaning", "version": other["version"]},
        headers=nurse_headers,
    )
    assert r.status_code == 403


def test_unknown_bed_is_404(client, nurse_headers):
    r = client.patch("/beds/999999/status", json={"status": "cleaning", "version": 1}, headers=nurse_headers)
    assert r.status_code == 404


def test_cannot_occupy_through_status_endpoint(client, nurse_headers):
    bed = client.get("/wards/1/beds", headers=nurse_headers).json()[0]
    r = client.patch(
        f"/beds/{bed['id']}/status",
        json={"status": "occupied", "version": bed["version"]},
        headers=nurse_headers,
    )
    assert r.status_code == 400


def test_nurse_cannot_read_audit(client, nurse_headers):
    assert client.get("/audit", headers=nurse_headers).status_code == 403


def test_admin_can_read_audit(client, admin_headers):
    r = client.get("/audit?page=1&page_size=5", headers=admin_headers)
    assert r.status_code == 200
    assert {"items", "total", "pages"} <= set(r.json())


def test_nurse_sees_only_own_ward_stats(client, nurse_headers):
    stats = client.get("/stats/occupancy", headers=nurse_headers).json()
    assert len(stats) == 1


def test_admin_sees_all_wards_stats(client, admin_headers):
    stats = client.get("/stats/occupancy", headers=admin_headers).json()
    assert len(stats) >= 3