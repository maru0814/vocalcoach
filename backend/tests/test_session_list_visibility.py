"""レッスン一覧の表示条件の契約テスト。

「開始しただけ（挨拶のみ・ユーザー発話ゼロ）のレッスンは一覧に出さず、
ユーザー発話が1件でもあれば出す」を検証する。in-memory SQLite で完結。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_session_list_visibility -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: E402,F401
from app.api.v1.endpoints.coach import create_session, list_sessions  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models.coaching import ChatMessage, ChatSession  # noqa: E402
from app.models.user import User  # noqa: E402


class SessionListVisibilityTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.user = User(email="t@example.com", password_hash="x")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _new_session(self, **over):
        s = ChatSession(user_id=self.user.id, phase="A", **over)
        self.db.add(s)
        self.db.commit()
        # 実運用では作成時に必ずソラ先生の挨拶が入るため、それを再現する
        self.db.add(ChatMessage(session_id=s.id, role="coach", type="text", text="こんにちは！"))
        self.db.commit()
        return s

    def test_untouched_session_is_hidden(self):
        self._new_session()
        self.assertEqual(list_sessions(db=self.db, user=self.user), [])

    def test_session_with_user_message_is_listed(self):
        s = self._new_session()
        self.db.add(ChatMessage(session_id=s.id, role="user", type="text", text="TSUNAMIを練習したい"))
        self.db.commit()
        result = list_sessions(db=self.db, user=self.user)
        self.assertEqual([r.id for r in result], [s.id])

    def test_mixed_sessions_only_touched_are_listed(self):
        touched = self._new_session(song_title="TSUNAMI")
        self._new_session()  # 放置レッスン
        self.db.add(ChatMessage(session_id=touched.id, role="user", type="audio", audio_path="/tmp/a.webm"))
        self.db.commit()
        result = list_sessions(db=self.db, user=self.user)
        self.assertEqual([r.id for r in result], [touched.id])

    def test_create_session_returns_session_id(self):
        res = create_session(db=self.db, user=self.user)
        self.assertIsNotNone(res.session_id)
        s = self.db.get(ChatSession, res.session_id)
        self.assertIsNotNone(s, "session_id が実在セッションを指していない")
        # 作成直後（未着手）は一覧に出ない
        self.assertEqual(list_sessions(db=self.db, user=self.user), [])


if __name__ == "__main__":
    unittest.main()
