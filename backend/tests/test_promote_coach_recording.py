"""coach録音→Recording昇格の契約テスト（docs/50 T-2 / TC: 昇格・冪等・NO_AUDIO）。

in-memory SQLite で完結（ffmpeg/実解析不要＝evaluate_recording は決定論的）。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_promote_coach_recording -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: E402,F401  (User/Recording/billing/evaluation を登録)
from app.db.base import Base  # noqa: E402
from app.models.coaching import ChatMessage, ChatSession  # noqa: E402
from app.models.evaluation import Evaluation  # noqa: E402
from app.models.recording import Recording  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.evaluation_service import (  # noqa: E402
    NoCoachAudioError,
    promote_coach_recording,
)


class PromoteCoachRecordingTest(unittest.TestCase):
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
        self.session = ChatSession(user_id=self.user.id, phase="C", song_title="残響散歌")
        self.db.add(self.session)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _add_audio(self, path="/tmp/coach_audio.webm"):
        m = ChatMessage(session_id=self.session.id, role="user", type="audio", audio_path=path)
        self.db.add(m)
        self.db.commit()
        return m

    def test_promote_creates_recording_and_evaluation(self):
        msg = self._add_audio()
        rec = promote_coach_recording(self.db, self.session, self.user.id)
        self.assertEqual(rec.source_message_id, msg.id)
        self.assertEqual(rec.source_session_id, self.session.id)
        self.assertEqual(rec.title, "残響散歌")
        self.assertEqual(rec.status, "completed")
        ev = self.db.query(Evaluation).filter(Evaluation.recording_id == rec.id).first()
        self.assertIsNotNone(ev, "評価が作られていない")

    def test_promote_is_idempotent(self):
        self._add_audio()
        rec1 = promote_coach_recording(self.db, self.session, self.user.id)
        rec2 = promote_coach_recording(self.db, self.session, self.user.id)
        self.assertEqual(rec1.id, rec2.id, "同じ録音から二重に Recording が作られた")
        count = self.db.query(Recording).filter(
            Recording.source_session_id == self.session.id
        ).count()
        self.assertEqual(count, 1, f"Recording が重複生成された: {count}")

    def test_no_audio_raises(self):
        with self.assertRaises(NoCoachAudioError):
            promote_coach_recording(self.db, self.session, self.user.id)


if __name__ == "__main__":
    unittest.main()
