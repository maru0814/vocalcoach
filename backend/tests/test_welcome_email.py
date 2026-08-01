"""ウェルカムメール自動送信（docs/84 AC-01〜06 / docs/87 TC-01〜09）。

in-memory SQLite ＋ requests モックで完結（実送信・ネットワーク不要）。
送信失敗が登録(201)を絶対に妨げないこと（FR-02）を回帰で守る。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_welcome_email -v
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services import mail_service  # noqa: E402


class _MailSettingsMixin(unittest.TestCase):
    """settings の mail_* を退避・復元する共通処理。"""

    def setUp(self):
        self._orig = (
            settings.mail_api_key,
            settings.mail_from_address,
            settings.frontend_base_url,
        )

    def tearDown(self):
        (
            settings.mail_api_key,
            settings.mail_from_address,
            settings.frontend_base_url,
        ) = self._orig

    def _enable_mail(self):
        settings.mail_api_key = "xkeysib-test"
        settings.mail_from_address = "sora@example.com"

    def _disable_mail(self):
        settings.mail_api_key = None
        settings.mail_from_address = None


class MailServiceUnitTest(_MailSettingsMixin):
    # TC-01 (AC-01/05): 設定ありで正しいリクエストが1回飛び、"sent" ログ
    def test_send_posts_to_brevo_and_logs_sent(self):
        self._enable_mail()
        resp = MagicMock(status_code=201)
        with patch("requests.post", return_value=resp) as post:
            with self.assertLogs("app.mail", level="INFO") as logs:
                mail_service.send_welcome_email(7, "singer@example.com")
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], mail_service.BREVO_SEND_URL)
        self.assertEqual(kwargs["headers"]["api-key"], "xkeysib-test")
        body = kwargs["json"]
        self.assertEqual(body["to"], [{"email": "singer@example.com"}])
        self.assertEqual(body["sender"]["email"], "sora@example.com")
        self.assertEqual(body["subject"], mail_service.WELCOME_SUBJECT)
        self.assertIn("/coach", body["textContent"])
        self.assertIn("/coach", body["htmlContent"])  # HTML版も同梱（docs/86 HTML版）
        self.assertTrue(any("sent" in m and "user_id=7" in m for m in logs.output))

    # TC-02 (AC-02/05): 未設定なら HTTP 呼び出しゼロで "skip" ログ
    def test_skip_when_not_configured(self):
        self._disable_mail()
        with patch("requests.post") as post:
            with self.assertLogs("app.mail", level="INFO") as logs:
                mail_service.send_welcome_email(1, "a@example.com")
        post.assert_not_called()
        self.assertTrue(any("skip" in m for m in logs.output))

    # TC-03 (AC-03/05): 接続例外でも raise しない
    def test_exception_is_swallowed(self):
        self._enable_mail()
        with patch("requests.post", side_effect=ConnectionError("boom")):
            with self.assertLogs("app.mail", level="WARNING") as logs:
                mail_service.send_welcome_email(2, "b@example.com")  # raiseしないこと
        self.assertTrue(any("failed" in m for m in logs.output))

    # TC-04 (AC-05): 4xx でも raise せず status 付き warning
    def test_non_2xx_logs_failed(self):
        self._enable_mail()
        resp = MagicMock(status_code=401)
        with patch("requests.post", return_value=resp):
            with self.assertLogs("app.mail", level="WARNING") as logs:
                mail_service.send_welcome_email(3, "c@example.com")
        self.assertTrue(any("failed" in m and "status=401" in m for m in logs.output))

    # TC-05 (AC-06): CTA は frontend_base_url に追随し二重スラッシュにならない
    def test_cta_follows_frontend_base_url(self):
        self._enable_mail()
        for base in ("https://sora-vocal-ai.duckdns.org", "https://sora-vocal-ai.duckdns.org/"):
            settings.frontend_base_url = base
            _, body, html = mail_service.build_welcome_email()
            self.assertIn("https://sora-vocal-ai.duckdns.org/coach", body)
            self.assertNotIn(".org//coach", body)
            self.assertIn("https://sora-vocal-ai.duckdns.org/coach", html)
        self.assertIn("sora@example.com", body)  # 連絡先フッター（FR-04）

    # TC-10: HTML版の成立要件（docs/86 HTML版デザイン仕様）
    def test_html_version_is_well_formed(self):
        self._enable_mail()
        settings.frontend_base_url = "https://sora-vocal-ai.duckdns.org"
        _, _, html = mail_service.build_welcome_email()
        # ロゴは https絶対URL（Gmailは data URI 不可）
        self.assertIn('src="https://sora-vocal-ai.duckdns.org/icons/icon-192.png"', html)
        self.assertNotIn("data:image", html)
        # プレースホルダの埋め残しがない
        self.assertNotIn("{cta_url}", html)
        self.assertNotIn("{logo_url}", html)
        self.assertNotIn("{contact_email}", html)
        # 連絡先フッター（FR-04）と画像altの存在
        self.assertIn("sora@example.com", html)
        self.assertIn('alt="ソラ先生"', html)
        # Who/CTA（docs/86 Who/What/How 改訂 2026-08-01）: 対外正式名＋LPと同一の読み手主語CTA
        self.assertIn("AIボーカルトレーナー ソラ先生", html)
        self.assertNotIn("ソラのステージ", html)  # 内輪ブランド名は使わない
        self.assertIn("無料で歌を見てもらう", html)


class RegisterHookTest(_MailSettingsMixin):
    """POST /api/v1/auth/register との結合（TC-06〜09）。"""

    def setUp(self):
        super().setUp()
        # TestClient は別スレッドで DB を触るため、in-memory を単一接続に固定する
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

        def _test_db():
            yield self.db

        self.app = create_app()
        self.app.dependency_overrides[get_db] = _test_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.db.close()
        super().tearDown()

    def _register(self, email="new@example.com"):
        return self.client.post(
            "/api/v1/auth/register", json={"email": email, "password": "password123"}
        )

    # TC-06 (AC-01): 登録成功時に新規ユーザーの id/email で1回呼ばれる
    def test_register_triggers_welcome_email(self):
        self._enable_mail()
        with patch("app.api.v1.endpoints.auth.send_welcome_email") as send:
            resp = self._register()
        self.assertEqual(resp.status_code, 201, resp.text)
        user_id = resp.json()["user_id"]
        send.assert_called_once_with(user_id, "new@example.com")

    # TC-07 (AC-03): 送信レイヤの例外（実物の send_welcome_email 経由）でも 201
    def test_register_succeeds_when_mail_api_down(self):
        self._enable_mail()
        with patch("requests.post", side_effect=TimeoutError("mail api down")):
            resp = self._register()
        self.assertEqual(resp.status_code, 201, f"送信失敗が登録を壊した: {resp.text}")

    # TC-08 (AC-04): 重複メールの 400 では送信されない
    def test_duplicate_email_does_not_send(self):
        self._enable_mail()
        with patch("app.api.v1.endpoints.auth.send_welcome_email") as send:
            self._register("dup@example.com")
            resp = self._register("dup@example.com")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(send.call_count, 1, "重複400でも送信された（AC-04違反）")

    # TC-09 (AC-02): mail未設定でも登録は現行どおり 201
    def test_register_without_mail_config(self):
        self._disable_mail()
        resp = self._register("plain@example.com")
        self.assertEqual(resp.status_code, 201, resp.text)


if __name__ == "__main__":
    unittest.main()
