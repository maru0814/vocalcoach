"""リリース告知メルマガ（docs/88 AC-01〜09 / docs/90 TC-01〜10）。

in-memory SQLite ＋ requests/send_mail モックで完結。
オプトイン取得・変更・ワンクリック配信停止・一斉送信バッチの冪等性を検証する。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_newsletter -v
"""
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.deps import get_current_user  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.newsletter import NewsletterSend  # noqa: E402
from app.models.user import User  # noqa: E402

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ops" / "send_newsletter.py"


def _load_batch_module():
    spec = importlib.util.spec_from_file_location("send_newsletter", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _DbTestBase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        def _test_db():
            yield self.db

        self.app = create_app()
        self.app.dependency_overrides[get_db] = _test_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.db.close()

    def _register(self, email, opt_in=None):
        body = {"email": email, "password": "password123"}
        if opt_in is not None:
            body["newsletter_opt_in"] = opt_in
        return self.client.post("/api/v1/auth/register", json=body)


class OptInRegistrationTest(_DbTestBase):
    # TC-01 (AC-01): チェックONで登録 → opt_in=true＋配信停止トークン発行
    def test_register_with_opt_in(self):
        resp = self._register("a@test.jp", opt_in=True)
        self.assertEqual(resp.status_code, 201, resp.text)
        u = self.db.query(User).filter_by(email="a@test.jp").one()
        self.assertTrue(u.newsletter_opt_in)
        self.assertTrue(u.unsubscribe_token and len(u.unsubscribe_token) >= 32)

    # TC-02 (AC-02): チェックOFF/省略 → opt_in=false・トークンなし
    def test_register_without_opt_in(self):
        self._register("b@test.jp", opt_in=False)
        self._register("c@test.jp")  # 省略
        for email in ("b@test.jp", "c@test.jp"):
            u = self.db.query(User).filter_by(email=email).one()
            self.assertFalse(u.newsletter_opt_in, email)
            self.assertIsNone(u.unsubscribe_token, email)


class OptInToggleTest(_DbTestBase):
    """/me と POST /newsletter（TC-03 / AC-03）。認証は get_current_user を差し替え。"""

    def setUp(self):
        super().setUp()
        self._register("t@test.jp", opt_in=False)
        self.user = self.db.query(User).filter_by(email="t@test.jp").one()
        self.app.dependency_overrides[get_current_user] = lambda: self.user

    def test_me_includes_opt_in(self):
        resp = self.client.get("/api/v1/auth/me")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["newsletter_opt_in"])

    def test_toggle_on_then_off(self):
        r1 = self.client.post("/api/v1/auth/newsletter", json={"opt_in": True})
        self.assertEqual(r1.json(), {"opt_in": True})
        self.db.refresh(self.user)
        self.assertTrue(self.user.newsletter_opt_in)
        self.assertTrue(self.user.unsubscribe_token, "ONにしたらトークンが発行される")
        r2 = self.client.post("/api/v1/auth/newsletter", json={"opt_in": False})
        self.assertEqual(r2.json(), {"opt_in": False})
        self.db.refresh(self.user)
        self.assertFalse(self.user.newsletter_opt_in)


class UnsubscribeTest(_DbTestBase):
    # TC-04 (AC-04): 有効トークン → opt_in=false＋完了画面。再実行も200（冪等）
    def test_unsubscribe_valid_token(self):
        self._register("u@test.jp", opt_in=True)
        u = self.db.query(User).filter_by(email="u@test.jp").one()
        resp = self.client.get(f"/api/v1/mail/unsubscribe?token={u.unsubscribe_token}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("配信停止しました", resp.text)
        self.db.refresh(u)
        self.assertFalse(u.newsletter_opt_in)
        again = self.client.get(f"/api/v1/mail/unsubscribe?token={u.unsubscribe_token}")
        self.assertEqual(again.status_code, 200, "冪等: 2回目も200")

    # TC-05 (AC-04): 無効/欠落トークンでも 200 のHTMLで完結（500を出さない）
    def test_unsubscribe_invalid_token(self):
        for q in ("?token=not-a-real-token", "?token=", ""):
            resp = self.client.get(f"/api/v1/mail/unsubscribe{q}")
            self.assertEqual(resp.status_code, 200, q)
            self.assertIn("無効", resp.text)


class NewsletterBatchTest(_DbTestBase):
    """send_newsletter.py の対象抽出・冪等性・上限（TC-06〜10 / AC-05〜09）。"""

    def setUp(self):
        super().setUp()
        self.mod = _load_batch_module()
        self.mod.SessionLocal = self.Session  # テストDBに向ける
        # 対象: opt_in=true 2人 / opt_in=false 1人 / テストドメイン1人
        self._register("m1@test.jp", opt_in=True)
        self._register("m2@test.jp", opt_in=True)
        self._register("m3@test.jp", opt_in=False)
        self._register("skip@example.com", opt_in=True)
        self.body_file = Path(self.enterContext(_TempDir()).name) / "body.txt"
        self.body_file.write_text("新機能のお知らせです。", encoding="utf-8")

    def _run(self, campaign="rel-test"):
        argv = ["send_newsletter.py", "--campaign-key", campaign,
                "--subject", "テスト件名", "--body-file", str(self.body_file)]
        with patch.object(sys, "argv", argv):
            return self.mod.main()

    # TC-06 (AC-05): opt_in=true の実会員だけに送る。台帳に記録される
    def test_targets_and_ledger(self):
        self.mod.DRY_RUN = False
        sent_to = []
        with patch.object(self.mod.mail_service, "mail_enabled", return_value=True), \
             patch.object(self.mod.mail_service, "send_mail",
                          side_effect=lambda uid, to, s, t, h=None: sent_to.append(to) or True):
            code = self._run()
        self.assertEqual(code, 0)
        self.assertEqual(sorted(sent_to), ["m1@test.jp", "m2@test.jp"])
        self.assertEqual(self.db.query(NewsletterSend).count(), 2)

    # TC-07 (AC-05): 同一campaign再実行で二重送信しない
    def test_idempotent_rerun(self):
        self.mod.DRY_RUN = False
        with patch.object(self.mod.mail_service, "mail_enabled", return_value=True), \
             patch.object(self.mod.mail_service, "send_mail", return_value=True) as send:
            self._run()
            first = send.call_count
            self._run()
            self.assertEqual(send.call_count, first, "再実行で追加送信ゼロ")

    # TC-08 (AC-05/再送): 失敗者は台帳に載らず、再実行で再送される
    def test_failed_user_retried(self):
        self.mod.DRY_RUN = False
        results = iter([True, False])  # m1成功・m2失敗
        with patch.object(self.mod.mail_service, "mail_enabled", return_value=True), \
             patch.object(self.mod.mail_service, "send_mail",
                          side_effect=lambda *a, **k: next(results)):
            self.assertEqual(self._run(), 1, "失敗ありは終了コード1")
        self.assertEqual(self.db.query(NewsletterSend).count(), 1)
        with patch.object(self.mod.mail_service, "mail_enabled", return_value=True), \
             patch.object(self.mod.mail_service, "send_mail", return_value=True) as send:
            self._run()
            self.assertEqual(send.call_count, 1, "失敗した1人だけ再送")

    # TC-09 (AC-06): 上限で打ち切り、再実行で続きから
    def test_batch_limit(self):
        self.mod.DRY_RUN = False
        self.mod.BATCH_LIMIT = 1
        with patch.object(self.mod.mail_service, "mail_enabled", return_value=True), \
             patch.object(self.mod.mail_service, "send_mail", return_value=True) as send:
            self._run()
            self.assertEqual(send.call_count, 1, "上限1で打ち切り")
            self._run()
            self.assertEqual(send.call_count, 2, "再実行で残り1人")

    # TC-10 (AC-07/09): DRY_RUNは1通も送らない。mail未設定は送信ゼロで正常終了
    def test_dry_run_and_disabled(self):
        self.mod.DRY_RUN = True
        with patch.object(self.mod.mail_service, "send_mail") as send:
            self.assertEqual(self._run("dry"), 0)
        send.assert_not_called()
        self.assertEqual(self.db.query(NewsletterSend).count(), 0)
        self.mod.DRY_RUN = False
        with patch.object(self.mod.mail_service, "mail_enabled", return_value=False), \
             patch.object(self.mod.mail_service, "send_mail") as send:
            self.assertEqual(self._run("off"), 0)
        send.assert_not_called()


class _TempDir:
    """enterContext 用の極小テンポラリディレクトリ。"""
    def __enter__(self):
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self.name = self._td.name
        return self
    def __exit__(self, *exc):
        self._td.cleanup()


if __name__ == "__main__":
    unittest.main()
