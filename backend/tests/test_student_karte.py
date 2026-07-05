"""生徒カルテと主観問診（docs/53/54）の hermetic テスト。

sqlite in-memory ＋ LLM 無し。カルテの更新/要約・問診の発火/回答/レッドフラグ・
引き継ぎ挨拶・プロンプト注入を検証する。

実行: cd backend && ./.venv/bin/python -m unittest tests.test_student_karte -v
"""
import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402,F401  (全モデル登録)
from app.services import karte_service  # noqa: E402
from app.coaching import llm, rule_engine  # noqa: E402


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


class _FakeSession:
    def __init__(self, checkin_count=0, awaiting=None):
        self.checkin_count = checkin_count
        self.awaiting_checkin = awaiting


class KarteUpdateAndRender(unittest.TestCase):
    def test_update_from_audio_builds_karte(self):
        db = _db()
        karte_service.update_from_audio(
            db, 1, diagnosed_task="breathy_closure", song_title="曲A",
            analysis={"f0_median_hz": 220.0}, practice_name="ストロー発声（SOVT）",
        )
        k = karte_service.get_or_none(db, 1)
        self.assertEqual(k.tendencies, {"breathy_closure": 1})
        self.assertEqual(k.homework["practice_name"], "ストロー発声（SOVT）")
        self.assertIn("曲A", k.last_summary)
        self.assertIsNotNone(k.last_session_at)

    def test_achieved_clears_homework_and_records_history(self):
        db = _db()
        karte_service.update_from_audio(db, 1, diagnosed_task="breathy_closure",
                                        practice_name="ストロー発声（SOVT）")
        karte_service.update_from_audio(db, 1, achieved=True)
        k = karte_service.get_or_none(db, 1)
        self.assertIsNone(k.homework, "達成した宿題は消える")
        self.assertEqual(k.practice_history[-1]["result"], "pass")

    def test_render_context_limits_500(self):
        db = _db()
        for i in range(12):
            karte_service.update_from_audio(db, 1, diagnosed_task=f"task_{i}",
                                            song_title=f"とても長い曲名{i}" * 5)
        k = karte_service.get_or_none(db, 1)
        ctx = karte_service.render_context(k)
        self.assertLessEqual(len(ctx), 500, "注入は500字以内（docs/53 FR-02）")
        self.assertIn("参考情報", ctx, "断定材料にしない注意書きを含む")

    def test_render_context_empty_for_none(self):
        self.assertEqual(karte_service.render_context(None), "", "カルテ無し＝注入なし（AC-03）")


class SubjectiveCheckin(unittest.TestCase):
    def test_record_subjective_and_red_flag(self):
        db = _db()
        res = karte_service.record_subjective(db, 1, "高音のとき喉が痛い感じがした")
        self.assertTrue(res["red_flag"])
        k = karte_service.get_or_none(db, 1)
        self.assertTrue(k.subjective_notes[0]["red_flag"])

    def test_record_subjective_normal(self):
        db = _db()
        res = karte_service.record_subjective(db, 1, "けっこうラクに出せました！")
        self.assertFalse(res["red_flag"])

    def test_notes_capped_at_5(self):
        db = _db()
        for i in range(8):
            karte_service.record_subjective(db, 1, f"メモ{i}")
        k = karte_service.get_or_none(db, 1)
        self.assertEqual(len(k.subjective_notes), 5)

    def test_should_ask_checkin_rules(self):
        # 力み系課題 → strain（優先）
        self.assertEqual(
            karte_service.should_ask_checkin(_FakeSession(), first_audio_in_session=True,
                                             diagnosed_task="throat_tension",
                                             after_practice_check=False),
            "strain")
        # 初回録音 → first_audio
        self.assertEqual(
            karte_service.should_ask_checkin(_FakeSession(), first_audio_in_session=True,
                                             diagnosed_task=None, after_practice_check=False),
            "first_audio")
        # 上限2回で打ち止め（AC-05）
        self.assertIsNone(
            karte_service.should_ask_checkin(_FakeSession(checkin_count=2),
                                             first_audio_in_session=True,
                                             diagnosed_task="throat_tension",
                                             after_practice_check=False))
        # 回答待ち中は出さない（連続禁止）
        self.assertIsNone(
            karte_service.should_ask_checkin(_FakeSession(awaiting="strain"),
                                             first_audio_in_session=True,
                                             diagnosed_task=None, after_practice_check=False))
        # 条件なし → 出さない
        self.assertIsNone(
            karte_service.should_ask_checkin(_FakeSession(), first_audio_in_session=False,
                                             diagnosed_task=None, after_practice_check=False))


class SessionOpener(unittest.TestCase):
    def _karte(self, days_ago, homework=None, summary=None):
        db = _db()
        karte_service.update_from_audio(db, 1, diagnosed_task="breathy_closure",
                                        practice_name="ストロー発声（SOVT）", song_title="曲A")
        k = karte_service.get_or_none(db, 1)
        k.last_session_at = datetime.utcnow() - timedelta(days=days_ago)
        if homework is False:
            k.homework = None
        if summary is not None:
            k.last_summary = summary
        return k

    def test_homework_opener(self):
        ctx = karte_service.session_opener_context(self._karte(3))
        self.assertEqual(ctx["mode"], "homework")
        msgs = rule_engine.initial_messages(ctx)
        self.assertIn("ストロー発声", msgs[0]["text"], "宿題に言及する（AC-01）")

    def test_reopen_after_30_days(self):
        ctx = karte_service.session_opener_context(self._karte(31))
        self.assertEqual(ctx["mode"], "reopen", "30日以上は宿題を詰問しない（AC-09）")
        msgs = rule_engine.initial_messages(ctx)
        self.assertIn("久しぶり", msgs[0]["text"])

    def test_no_karte_default_greeting(self):
        self.assertIsNone(karte_service.session_opener_context(None))
        msgs = rule_engine.initial_messages(None)
        self.assertIn("はじめまして", msgs[0]["text"], "初回は現行挨拶（AC-03）")


class PromptInjection(unittest.TestCase):
    def test_karte_context_injected_into_session_context(self):
        state = {"phase": "practice", "song_ref_url": None, "song_ref_path": None,
                 "current_task": None, "baseline_analysis": None, "last_analysis": None,
                 "karte_context": "この生徒について（カルテ。過去の記録＝参考情報）:\n- 持ち癖: breathy_closure×3"}
        ctx = llm.build_session_context(state)
        self.assertIn("この生徒について", ctx)
        self.assertIn("breathy_closure×3", ctx)

    def test_no_karte_no_injection(self):
        state = {"phase": "A", "song_ref_url": None, "song_ref_path": None,
                 "current_task": None, "baseline_analysis": None, "last_analysis": None}
        ctx = llm.build_session_context(state)
        self.assertNotIn("この生徒について", ctx, "カルテ無し＝現行の文脈のまま（AC-03）")


if __name__ == "__main__":
    unittest.main(verbosity=2)
