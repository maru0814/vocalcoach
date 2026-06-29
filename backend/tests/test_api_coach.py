"""コーチ（チャット）の純粋ヘルパーとセッションAPI契約テスト。

純粋ヘルパー（時間パース・歌声ゲート）は決定的に検証し、セッションCRUDは
TestClient + インメモリSQLite で認証必須・所有権分離・初期メッセージ・
PHASE_A の確定的応答（LLM不要）を確認する。
"""
import pytest

from app.api.v1.endpoints import coach


# --- 純粋ヘルパー ---

class TestTimeParsing:
    def test_parse_range_mmss(self):
        assert coach._parse_range("0:48-1:13") == (48.0, 73.0)

    def test_parse_range_none(self):
        assert coach._parse_range(None) == (None, None)
        assert coach._parse_range("なし") == (None, None)

    def test_parse_ref_spec_range(self):
        assert coach._parse_ref_spec("0:45-1:13 を重ねて") == (45.0, 73.0)

    def test_parse_ref_spec_japanese_minutes(self):
        assert coach._parse_ref_spec("1分20秒から") == (80.0, None)

    def test_parse_ref_spec_atari_kara(self):
        assert coach._parse_ref_spec("45あたりから") == (45.0, None)

    def test_fmt_time(self):
        assert coach._fmt_time(45) == "45秒"
        assert coach._fmt_time(80) == "1分20秒"
        assert coach._fmt_time(None) == ""


class TestLooksLikeSinging:
    def test_real_singing_passes(self):
        assert coach._looks_like_singing(
            {"duration_sec": 20.0, "rms_mean": 0.03, "voiced_ratio": 0.94}) is True

    def test_silence_rejected(self):
        assert coach._looks_like_singing(
            {"duration_sec": 20.0, "rms_mean": 1e-4, "voiced_ratio": 0.1}) is False

    def test_too_short_rejected(self):
        assert coach._looks_like_singing(
            {"duration_sec": 0.5, "rms_mean": 0.03, "voiced_ratio": 0.94}) is False


# --- セッションAPI契約 ---

@pytest.fixture()
def auth_client(client):
    client.post("/api/v1/auth/register",
                json={"email": "u@example.com", "password": "password123"})
    client.post("/api/v1/auth/login",
                json={"email": "u@example.com", "password": "password123"})
    return client


def _other_users_session(client):
    """別ユーザーを作り、その人のセッションを1件作って返す（所有権テスト用）。"""
    from app.models.coaching import ChatSession
    from app.models.user import User
    from app.security.passwords import hash_password
    s = client.session_factory()
    try:
        u = User(email="other@example.com", password_hash=hash_password("password123"))
        s.add(u)
        s.commit()
        s.refresh(u)
        sess = ChatSession(user_id=u.id, phase="A")
        s.add(sess)
        s.commit()
        s.refresh(sess)
        return sess.id
    finally:
        s.close()


class TestSessionAuth:
    def test_create_requires_auth(self, client):
        assert client.post("/api/v1/coach/sessions").status_code == 401

    def test_list_requires_auth(self, client):
        assert client.get("/api/v1/coach/sessions").status_code == 401


class TestSessionCrud:
    def test_create_returns_initial_messages(self, auth_client):
        r = auth_client.post("/api/v1/coach/sessions")
        assert r.status_code == 200
        body = r.json()
        assert body["phase"] == "A"
        assert len(body["messages"]) >= 1
        assert body["messages"][0]["role"] == "coach"

    def test_list_returns_own_session(self, auth_client):
        auth_client.post("/api/v1/coach/sessions")
        sessions = auth_client.get("/api/v1/coach/sessions").json()
        assert len(sessions) == 1

    def test_get_unknown_session_404(self, auth_client):
        assert auth_client.get("/api/v1/coach/sessions/99999").status_code == 404

    def test_cannot_read_other_users_session(self, auth_client):
        other_id = _other_users_session(auth_client)
        assert auth_client.get(f"/api/v1/coach/sessions/{other_id}").status_code == 404

    def test_rename_empty_title_400(self, auth_client):
        sid = auth_client.post("/api/v1/coach/sessions").json()["messages"][0]["id"]
        # セッションIDが必要なので list から取得
        session_id = auth_client.get("/api/v1/coach/sessions").json()[0]["id"]
        r = auth_client.patch(f"/api/v1/coach/sessions/{session_id}",
                              json={"song_title": "   "})
        assert r.status_code == 400


class TestSendMessageDeterministic:
    def test_phase_a_url_acknowledged_without_llm(self, auth_client):
        # gemini 未設定 → URL受領は確定的なテンプレ応答（LLM経路に入らない）。
        auth_client.post("/api/v1/coach/sessions")
        session_id = auth_client.get("/api/v1/coach/sessions").json()[0]["id"]
        r = auth_client.post(f"/api/v1/coach/sessions/{session_id}/messages",
                             json={"text": "原曲です https://youtu.be/abc123"})
        assert r.status_code == 200
        coach_texts = [m["text"] for m in r.json()["messages"] if m["role"] == "coach"]
        assert any("受け取りました" in (t or "") or "確認しました" in (t or "")
                   for t in coach_texts)
