"""録音エンドポイントのAPI契約テスト。

認証必須・所有権分離・上限ゲート(402)・入力検証を検証する。
実際の音声解析（バックグラウンド）は no-op に差し替えて、HTTP契約だけを見る。
"""
import io

import pytest

from app.core.config import settings
from app.models.recording import Recording
from app.models.user import User
from app.models.billing import UsageCounter
from app.security.passwords import hash_password
from app.services import billing_service


@pytest.fixture()
def auth_client(client, monkeypatch):
    """register + login 済みのクライアント。バックグラウンド解析は無効化。"""
    import app.api.v1.endpoints.recordings as rec
    monkeypatch.setattr(rec, "_evaluate_job", lambda recording_id: None)
    client.post("/api/v1/auth/register",
                json={"email": "u@example.com", "password": "password123"})
    client.post("/api/v1/auth/login",
                json={"email": "u@example.com", "password": "password123"})
    return client


def _seed_user(client, email):
    s = client.session_factory()
    try:
        u = User(email=email, password_hash=hash_password("password123"))
        s.add(u)
        s.commit()
        s.refresh(u)
        return u.id
    finally:
        s.close()


def _seed_recording(client, user_id, title="other"):
    s = client.session_factory()
    try:
        r = Recording(user_id=user_id, title=title, status="analyzing", audio_path="x")
        s.add(r)
        s.commit()
        s.refresh(r)
        return r.id
    finally:
        s.close()


def _upload(client, title="My take"):
    return client.post(
        "/api/v1/recordings",
        data={"title": title},
        files={"audio_file": ("take.webm", io.BytesIO(b"fake audio bytes"), "audio/webm")},
    )


class TestAuthRequired:
    def test_list_requires_auth(self, client):
        assert client.get("/api/v1/recordings").status_code == 401

    def test_get_requires_auth(self, client):
        assert client.get("/api/v1/recordings/1").status_code == 401


class TestUploadValidation:
    def test_empty_title_400(self, auth_client):
        assert _upload(auth_client, title="   ").status_code == 400

    def test_upload_ok_returns_analyzing(self, auth_client):
        r = _upload(auth_client)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "analyzing"
        assert isinstance(body["recording_id"], int)


class TestLimitGate:
    def test_402_when_free_limit_reached(self, auth_client, monkeypatch):
        monkeypatch.setattr(settings, "billing_enabled", True)
        monkeypatch.setattr(settings, "free_analysis_limit", 3)
        # 現在のユーザーIDを /me 経由で取得し、上限到達のカウンタを仕込む。
        uid = auth_client.get("/api/v1/auth/me").json()["user_id"]
        s = auth_client.session_factory()
        try:
            s.add(UsageCounter(user_id=uid, yyyymm=billing_service.current_yyyymm(),
                               analysis_count=3))
            s.commit()
        finally:
            s.close()
        assert _upload(auth_client).status_code == 402


class TestOwnership:
    def test_unknown_recording_404(self, auth_client):
        assert auth_client.get("/api/v1/recordings/99999").status_code == 404

    def test_cannot_read_other_users_recording(self, auth_client):
        # 別ユーザーの録音は 404（存在を漏らさない）。
        other_id = _seed_user(auth_client, "other@example.com")
        rec_id = _seed_recording(auth_client, other_id)
        assert auth_client.get(f"/api/v1/recordings/{rec_id}").status_code == 404

    def test_list_only_returns_own(self, auth_client):
        other_id = _seed_user(auth_client, "other@example.com")
        _seed_recording(auth_client, other_id, title="not mine")
        _upload(auth_client, title="mine")
        items = auth_client.get("/api/v1/recordings").json()["items"]
        titles = {i["title"] for i in items}
        assert "mine" in titles and "not mine" not in titles
