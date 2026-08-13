"""無料プランの月次解析上限（docs/31 v3 FR-01 / AC-01, 02, 10-12）。

in-memory SQLite で完結（LLM・実解析・ネットワーク不要）。
coach送信時カウント＋昇格の二重カウント防止（count_usage=False）を回帰で守る。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_analysis_limit -v
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: E402,F401  (User/Recording/billing/evaluation を登録)
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models.billing import Subscription  # noqa: E402
from app.models.coaching import ChatMessage, ChatSession  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import billing_service as bs  # noqa: E402
from app.services.evaluation_service import promote_coach_recording  # noqa: E402


class AnalysisLimitTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.user = User(email="t@example.com", password_hash="x")
        self.db.add(self.user)
        self.db.commit()
        self._orig_enabled = settings.billing_enabled
        self._orig_limit = settings.free_analysis_limit
        settings.billing_enabled = True
        settings.free_analysis_limit = 10

    def tearDown(self):
        settings.billing_enabled = self._orig_enabled
        settings.free_analysis_limit = self._orig_limit
        self.db.close()

    # AC-01/11: 10回目までは許可・カウントされ、11回目はブロックされる
    def test_block_after_limit(self):
        for i in range(10):
            self.assertTrue(bs.analysis_allowed(self.db, self.user.id), f"{i + 1}回目は許可")
            bs.increment_analysis_count(self.db, self.user.id)
        self.assertEqual(bs.get_analysis_used(self.db, self.user.id), 10)
        self.assertFalse(bs.analysis_allowed(self.db, self.user.id), "11回目はブロック")

    # AC-02: 月が変わるとカウントが0に戻る
    def test_month_reset(self):
        for _ in range(10):
            bs.increment_analysis_count(self.db, self.user.id)
        orig = bs.current_yyyymm
        bs.current_yyyymm = lambda now=None: "209901"
        try:
            self.assertEqual(bs.get_analysis_used(self.db, self.user.id), 0)
            self.assertTrue(bs.analysis_allowed(self.db, self.user.id))
        finally:
            bs.current_yyyymm = orig

    # FR-01例外: 既加入者はカウントも上限も対象外
    def test_premium_exempt(self):
        self.db.add(
            Subscription(
                user_id=self.user.id,
                stripe_customer_id="c",
                stripe_subscription_id="s",
                status="active",
                current_period_end=datetime.now(timezone.utc).replace(tzinfo=None)
                + timedelta(days=30),
            )
        )
        self.db.commit()
        for _ in range(15):
            bs.increment_analysis_count(self.db, self.user.id)
        self.assertEqual(bs.get_analysis_used(self.db, self.user.id), 0)
        self.assertTrue(bs.analysis_allowed(self.db, self.user.id))

    # docs/101: コンプ枠メールは課金なしでプレミアム扱い（上限・カウント対象外）
    def test_comp_premium_email_exempt(self):
        comp = User(email="Comp.User@Example.com", password_hash="x")
        self.db.add(comp)
        self.db.commit()
        orig = settings.comp_premium_emails
        settings.comp_premium_emails = "comp.user@example.com"
        try:
            self.assertTrue(bs.is_premium(self.db, comp.id), "大文字小文字違いでも一致")
            for _ in range(15):
                bs.increment_analysis_count(self.db, comp.id)
            self.assertEqual(bs.get_analysis_used(self.db, comp.id), 0, "カウントされない")
            self.assertTrue(bs.analysis_allowed(self.db, comp.id), "上限なし")
            me = bs.billing_me(self.db, comp.id)
            self.assertEqual(me["plan"], "premium")
            self.assertIsNone(me["analysis_limit"])
            # allowlist 外のユーザーは従来どおり（回帰）
            self.assertFalse(bs.is_premium(self.db, self.user.id))
        finally:
            settings.comp_premium_emails = orig

    # docs/101: allowlist が空文字ならコンプ枠は無効
    def test_comp_premium_disabled_when_empty(self):
        orig = settings.comp_premium_emails
        settings.comp_premium_emails = ""
        try:
            self.assertFalse(bs.is_premium(self.db, self.user.id))
        finally:
            settings.comp_premium_emails = orig

    # 緊急停止スイッチ: billing_enabled=False なら無制限
    def test_kill_switch(self):
        settings.billing_enabled = False
        for _ in range(15):
            bs.increment_analysis_count(self.db, self.user.id)
        self.assertTrue(bs.analysis_allowed(self.db, self.user.id))
        self.assertEqual(bs.get_analysis_used(self.db, self.user.id), 0)

    # AC-12: coach録音の昇格は解析カウントを増やさない（送信時にカウント済み）
    def test_promote_does_not_double_count(self):
        session = ChatSession(user_id=self.user.id, phase="C", song_title="残響散歌")
        self.db.add(session)
        self.db.commit()
        self.db.add(
            ChatMessage(
                session_id=session.id, role="user", type="audio", audio_path="/tmp/a.webm"
            )
        )
        self.db.commit()
        # coach送信時のカウント（endpoint側の increment に相当）
        bs.increment_analysis_count(self.db, self.user.id)
        self.assertEqual(bs.get_analysis_used(self.db, self.user.id), 1)

        rec = promote_coach_recording(self.db, session, self.user.id)
        self.assertEqual(rec.status, "completed")
        self.assertEqual(
            bs.get_analysis_used(self.db, self.user.id), 1, "昇格で二重カウントしない"
        )


if __name__ == "__main__":
    unittest.main()
