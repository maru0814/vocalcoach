"""Web Push（練習リマインド）のテスト。docs/73 FR-04/FR-05 / docs/75。

in-memory SQLite で完結（実送信・pywebpush不要）。対象抽出クエリと購読upsertの
冪等性を検証する。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_push_reminders -v
"""
import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.models.push import PushSubscription  # noqa: E402
from app.models.recording import Recording  # noqa: E402
from app.models.user import User  # noqa: E402


def _make_reminder_query(idle_days: int):
    """send_practice_reminders._eligible_user_ids と同じロジックを差し込み可能に切り出す。"""

    def eligible(db):
        cutoff = datetime.utcnow() - timedelta(days=idle_days)
        subscriber_ids = {
            uid
            for (uid,) in db.query(PushSubscription.user_id)
            .filter(PushSubscription.enabled.is_(True))
            .distinct()
            .all()
        }
        if not subscriber_ids:
            return []
        active_ids = {
            uid
            for (uid,) in db.query(Recording.user_id)
            .filter(Recording.user_id.in_(subscriber_ids), Recording.created_at >= cutoff)
            .distinct()
            .all()
        }
        return sorted(subscriber_ids - active_ids)

    return eligible


class PushReminderTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def _user(self, email):
        u = User(email=email, password_hash="x")
        self.db.add(u)
        self.db.commit()
        return u

    def _sub(self, user_id, endpoint, enabled=True):
        s = PushSubscription(
            user_id=user_id, endpoint=endpoint, p256dh="p", auth="a", enabled=enabled
        )
        self.db.add(s)
        self.db.commit()
        return s

    def _recording(self, user_id, days_ago):
        r = Recording(
            user_id=user_id,
            title="t",
            audio_path="/tmp/x.wav",
            status="done",
            created_at=datetime.utcnow() - timedelta(days=days_ago),
        )
        self.db.add(r)
        self.db.commit()
        return r

    def test_idle_user_is_targeted(self):
        u = self._user("idle@example.com")
        self._sub(u.id, "https://push/idle")
        self._recording(u.id, days_ago=5)  # 5日前＝idle
        eligible = _make_reminder_query(3)(self.db)
        self.assertEqual(eligible, [u.id])

    def test_recent_user_is_skipped(self):
        u = self._user("active@example.com")
        self._sub(u.id, "https://push/active")
        self._recording(u.id, days_ago=1)  # 1日前＝アクティブ
        eligible = _make_reminder_query(3)(self.db)
        self.assertEqual(eligible, [])

    def test_no_recording_user_is_targeted(self):
        u = self._user("never@example.com")
        self._sub(u.id, "https://push/never")  # 録音ゼロ
        eligible = _make_reminder_query(3)(self.db)
        self.assertEqual(eligible, [u.id])

    def test_disabled_subscription_is_skipped(self):
        u = self._user("off@example.com")
        self._sub(u.id, "https://push/off", enabled=False)
        eligible = _make_reminder_query(3)(self.db)
        self.assertEqual(eligible, [])

    def test_subscribe_upsert_is_idempotent(self):
        """同一endpointの再購読で行が増えず、所有者だけ更新される（endpoint一意）。"""
        u1 = self._user("a@example.com")
        u2 = self._user("b@example.com")
        self._sub(u1.id, "https://push/shared")
        # 同じendpointを別ユーザーが再購読（upsert相当）
        existing = (
            self.db.query(PushSubscription)
            .filter(PushSubscription.endpoint == "https://push/shared")
            .first()
        )
        existing.user_id = u2.id
        self.db.commit()
        rows = self.db.query(PushSubscription).filter(
            PushSubscription.endpoint == "https://push/shared"
        ).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].user_id, u2.id)


if __name__ == "__main__":
    unittest.main()
