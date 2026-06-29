"""認証フローのAPI契約テスト（FastAPI TestClient + インメモリSQLite）。

register → login(Cookie発行) → /me、および各種失敗系（重複登録・誤認証・未認証）。
"""


def _register(client, email="a@example.com", password="password123"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


class TestRegister:
    def test_register_returns_201_and_user_id(self, client):
        r = _register(client)
        assert r.status_code == 201
        assert isinstance(r.json()["user_id"], int)

    def test_duplicate_email_400(self, client):
        _register(client)
        r = _register(client)
        assert r.status_code == 400

    def test_short_password_422(self, client):
        r = _register(client, password="short")   # min_length=8
        assert r.status_code == 422

    def test_invalid_email_422(self, client):
        r = _register(client, email="not-an-email")
        assert r.status_code == 422


class TestLogin:
    def test_login_sets_cookie(self, client):
        _register(client)
        r = client.post("/api/v1/auth/login",
                        json={"email": "a@example.com", "password": "password123"})
        assert r.status_code == 200
        assert r.json()["access_token"]
        assert "access_token" in r.cookies

    def test_wrong_password_401(self, client):
        _register(client)
        r = client.post("/api/v1/auth/login",
                        json={"email": "a@example.com", "password": "WRONG"})
        assert r.status_code == 401

    def test_unknown_user_401(self, client):
        r = client.post("/api/v1/auth/login",
                        json={"email": "ghost@example.com", "password": "password123"})
        assert r.status_code == 401


class TestMe:
    def test_me_requires_auth(self, client):
        assert client.get("/api/v1/auth/me").status_code == 401

    def test_me_returns_identity_after_login(self, client):
        _register(client)
        client.post("/api/v1/auth/login",
                    json={"email": "a@example.com", "password": "password123"})
        # TestClient はログインで発行された Cookie を保持する。
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == "a@example.com"

    def test_garbage_token_rejected(self, client):
        client.cookies.set("access_token", "not.a.jwt")
        assert client.get("/api/v1/auth/me").status_code == 401


class TestErrorEnvelope:
    def test_error_has_code_and_request_id(self, client):
        r = client.get("/api/v1/auth/me")   # 401
        body = r.json()
        assert body["code"] == "UNAUTHORIZED"
        assert "request_id" in body and "timestamp" in body
        assert r.headers.get("X-Request-ID")


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
