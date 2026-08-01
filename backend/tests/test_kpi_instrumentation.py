"""KPI計測強化の回帰テスト（docs/84 TC-KPI-02, TC-KPI-03）。

in-memory SQLite で完結。
- ログイン成功で login_events に1行入る／失敗では入らない（ログインUUの源泉）
- 診断イベントの user_id / visitor_hash 列がモデルに存在し保存できる
- visitor_hash は生IPを含まない一方向ハッシュで、同一IPなら安定

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_kpi_instrumentation -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.api.v1.endpoints.voice_type import _client_ip, _visitor_hash  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.login_event import LoginEvent  # noqa: E402
from app.models.voice_type import VoiceTypeDiagnosis  # noqa: E402


class KpiInstrumentationTest(unittest.TestCase):
    def setUp(self):
        # TestClient は別スレッドから触るため、単一接続を共有する StaticPool にする
        # （既定だと接続ごとに別の in-memory DB になり "no such table" になる）
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.app = create_app()

        def _test_db():
            yield self.db

        self.app.dependency_overrides[get_db] = _test_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.db.close()

    def _register(self, email="kpi@test.dev", password="secret123"):
        r = self.client.post("/api/v1/auth/register", json={"email": email, "password": password})
        self.assertEqual(r.status_code, 201, r.text)

    # TC-KPI-02: ログイン成功 → login_events に1行
    def test_login_success_records_event(self):
        self._register()
        r = self.client.post("/api/v1/auth/login", json={"email": "kpi@test.dev", "password": "secret123"})
        self.assertEqual(r.status_code, 200, r.text)
        events = self.db.query(LoginEvent).all()
        self.assertEqual(len(events), 1)
        self.assertIsNotNone(events[0].created_at)

    # TC-KPI-02: ログイン失敗 → 記録されない
    def test_login_failure_records_nothing(self):
        self._register()
        r = self.client.post("/api/v1/auth/login", json={"email": "kpi@test.dev", "password": "wrong"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.db.query(LoginEvent).count(), 0)

    # TC-KPI-03: 診断イベントに user_id / visitor_hash を保存できる
    def test_diagnosis_identity_columns(self):
        self.db.add(VoiceTypeDiagnosis(type_id="clear", score=80, user_id=1, visitor_hash=None))
        self.db.add(VoiceTypeDiagnosis(type_id="husky", score=60, user_id=None, visitor_hash="a" * 64))
        self.db.commit()
        rows = self.db.query(VoiceTypeDiagnosis).order_by(VoiceTypeDiagnosis.id).all()
        self.assertEqual(rows[0].user_id, 1)
        self.assertEqual(rows[1].visitor_hash, "a" * 64)

    # TC-KPI-03: visitor_hash は安定した64桁hexで、生IPを含まない
    def test_visitor_hash_is_pseudonymous(self):
        h1 = _visitor_hash("203.0.113.9")
        h2 = _visitor_hash("203.0.113.9")
        h3 = _visitor_hash("198.51.100.1")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)
        self.assertEqual(len(h1), 64)
        self.assertNotIn("203.0.113.9", h1)

    # X-Forwarded-For の先頭（実クライアント）を優先する
    def test_client_ip_prefers_forwarded_for(self):
        class Req:
            headers = {"x-forwarded-for": "203.0.113.9, 10.0.0.2"}
            client = type("C", (), {"host": "172.18.0.2"})()

        self.assertEqual(_client_ip(Req()), "203.0.113.9")


if __name__ == "__main__":
    unittest.main()
