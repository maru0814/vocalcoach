"""課金エンドポイントのAPI契約テスト（docs/31〜33）。

認証必須・サマリ形・Stripe未設定時のガード・webhook署名失敗を検証する。
"""
import pytest

from app.core.config import settings


@pytest.fixture()
def auth_client(client):
    """register + login 済みの TestClient（Cookie保持）。"""
    client.post("/api/v1/auth/register",
                json={"email": "u@example.com", "password": "password123"})
    client.post("/api/v1/auth/login",
                json={"email": "u@example.com", "password": "password123"})
    return client


class TestBillingMe:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/billing/me").status_code == 401

    def test_free_user_default(self, auth_client):
        # 既定 billing_enabled=False → 無制限・free。
        body = auth_client.get("/api/v1/billing/me").json()
        assert body["plan"] == "free"
        assert body["analysis_limit"] is None

    def test_limit_shown_when_billing_enabled(self, auth_client, monkeypatch):
        monkeypatch.setattr(settings, "billing_enabled", True)
        monkeypatch.setattr(settings, "free_analysis_limit", 10)
        body = auth_client.get("/api/v1/billing/me").json()
        assert body["plan"] == "free"
        assert body["analysis_limit"] == 10


class TestCheckoutPortalGuards:
    def test_checkout_503_when_stripe_disabled(self, auth_client):
        assert auth_client.post("/api/v1/billing/checkout").status_code == 503

    def test_portal_503_when_stripe_disabled(self, auth_client):
        assert auth_client.post("/api/v1/billing/portal").status_code == 503

    def test_checkout_requires_auth(self, client):
        assert client.post("/api/v1/billing/checkout").status_code == 401


class TestPaywallEvent:
    def test_event_ok(self, auth_client):
        r = auth_client.post("/api/v1/billing/event",
                             json={"event": "paywall_view", "source": "limit"})
        assert r.status_code == 200 and r.json() == {"ok": True}

    def test_event_requires_auth(self, client):
        r = client.post("/api/v1/billing/event",
                        json={"event": "paywall_view", "source": "limit"})
        assert r.status_code == 401


class TestWebhook:
    def test_invalid_signature_400(self, client, monkeypatch):
        # webhook secret 未設定 → parse_event が例外 → 400。
        monkeypatch.setattr(settings, "stripe_webhook_secret", None)
        r = client.post("/api/v1/billing/webhook", content=b"{}",
                        headers={"stripe-signature": "bogus"})
        assert r.status_code == 400
