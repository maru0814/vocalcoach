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
import app.models.coaching  # noqa: E402,F401  (ChatSession/ChatMessage を create_all に登録)
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

    def test_opener_never_mentions_homework(self):
        # 開始挨拶は宿題・練習名に言及しない（実ユーザーFB 2026-08-06 / AC-01改）。
        # 宿題があってもモードは continue（前回サマリ）に落ちる
        ctx = karte_service.session_opener_context(self._karte(3))
        self.assertEqual(ctx["mode"], "continue")
        msgs = rule_engine.initial_messages(ctx)
        self.assertNotIn("ストロー発声", msgs[0]["text"], "挨拶で宿題を蒸し返さない")
        self.assertIn("前回", msgs[0]["text"])

    def test_same_day_short_welcome(self):
        # 同日の再訪: 要約も宿題も読み上げず、短い出迎えだけ
        ctx = karte_service.session_opener_context(self._karte(0))
        self.assertEqual(ctx["mode"], "continue_recent")
        msgs = rule_engine.initial_messages(ctx)
        self.assertIn("おかえりなさい", msgs[0]["text"])
        self.assertNotIn("ストロー発声", msgs[0]["text"])
        self.assertNotIn("前回", msgs[0]["text"])
        self.assertNotIn("さっき", msgs[0]["text"], "「さっき◯◯した」系の記憶主張をしない")

    def test_reopen_after_30_days(self):
        ctx = karte_service.session_opener_context(self._karte(31))
        self.assertEqual(ctx["mode"], "reopen", "30日以上は宿題を詰問しない（AC-09）")
        msgs = rule_engine.initial_messages(ctx)
        self.assertIn("久しぶり", msgs[0]["text"])

    def test_no_karte_default_greeting(self):
        self.assertIsNone(karte_service.session_opener_context(None))
        msgs = rule_engine.initial_messages(None)
        self.assertIn("はじめまして", msgs[0]["text"], "初回は現行挨拶（AC-03）")


class HomeworkTruthfulness(unittest.TestCase):
    """宿題は「会話に実際に登場した練習」だけ（docs/53 FR-06 捏造防止・2026-08-06 実ユーザー報告）。

    ゼロベースFBは初回に練習を出さないため、診断時に無条件でカタログ練習名を
    記録すると、次回の開始挨拶が「さっき『◯◯』のお話をしましたね」と
    実在しない会話を引用する。
    """

    def test_practice_mentioned_full_name(self):
        self.assertTrue(karte_service.practice_mentioned(
            ["おすすめ基礎練『ストロー発声（SOVT）』を試しましょう"], "ストロー発声（SOVT）"))

    def test_practice_mentioned_by_keyword(self):
        # LLMが言い換えても、練習名に含まれる既知語彙（ハミング）で言及ありとみなす
        self.assertTrue(karte_service.practice_mentioned(
            ["まずはハミングで響きを確かめましょう"], "ハミング → 母音（マスクに集める）"))

    def test_practice_not_mentioned(self):
        self.assertFalse(karte_service.practice_mentioned(
            ["高音で喉が締まる傾向がありますね。原因は…"], "ハミング → 母音（マスクに集める）"))
        self.assertFalse(karte_service.practice_mentioned([], "ハミング → 母音（マスクに集める）"))
        self.assertFalse(karte_service.practice_mentioned(["何か"], None))

    def test_record_prescription_sets_homework(self):
        db = _db()
        karte_service.record_prescription(db, 1, task_id="mixed_voice",
                                          practice_name="ハミング → 母音（マスクに集める）")
        k = karte_service.get_or_none(db, 1)
        self.assertEqual(k.homework["practice_name"], "ハミング → 母音（マスクに集める）")
        self.assertEqual(k.homework["task_id"], "mixed_voice")

    def _seed_conversation(self, db, user_id, coach_texts_after_user, opener_text=None):
        """セッション1件: （opener→）ユーザー発言→コーチ発言…の順で会話を作る。"""
        from app.models.coaching import ChatMessage, ChatSession
        s = ChatSession(user_id=user_id, phase="A")
        db.add(s)
        db.flush()
        if opener_text:
            db.add(ChatMessage(session_id=s.id, role="coach", type="text", text=opener_text))
        db.add(ChatMessage(session_id=s.id, role="user", type="text", text="録音送ります"))
        for t in coach_texts_after_user:
            db.add(ChatMessage(session_id=s.id, role="coach", type="text", text=t))
        db.flush()

    def test_drop_unmentioned_homework_clears_fabricated(self):
        db = _db()
        # 汚染データ: 宿題はあるが、会話でその練習を一度も提示していない
        karte_service.record_prescription(db, 1, task_id="mixed_voice",
                                          practice_name="ハミング → 母音（マスクに集める）")
        self._seed_conversation(db, 1, ["高音で喉が締まる傾向がありますね"])
        karte_service.drop_unmentioned_homework(db, 1)
        self.assertIsNone(karte_service.get_or_none(db, 1).homework,
                          "会話に無い練習の宿題は破棄（開始挨拶の捏造防止）")

    def test_drop_ignores_opener_self_mention(self):
        db = _db()
        # 過去の捏造挨拶（ユーザー発言より前のコーチ発言）だけが練習名を口にしているケース。
        # これを根拠に宿題を自己正当化してはいけない
        karte_service.record_prescription(db, 1, task_id="mixed_voice",
                                          practice_name="ハミング → 母音（マスクに集める）")
        self._seed_conversation(
            db, 1, ["高音で喉が締まる傾向がありますね"],
            opener_text="おかえりなさい😊 さっきは『ハミング → 母音（マスクに集める）』のお話をしましたね。")
        karte_service.drop_unmentioned_homework(db, 1)
        self.assertIsNone(karte_service.get_or_none(db, 1).homework,
                          "開始挨拶自身の言及は照合対象にしない")

    def test_drop_keeps_actually_prescribed(self):
        db = _db()
        karte_service.record_prescription(db, 1, task_id="breathy_closure",
                                          practice_name="ストロー発声（SOVT）")
        self._seed_conversation(
            db, 1, ["おすすめ基礎練『ストロー発声（SOVT）』: 細いストローで…"])
        karte_service.drop_unmentioned_homework(db, 1)
        k = karte_service.get_or_none(db, 1)
        self.assertIsNotNone(k.homework, "実際に提示した宿題は残す")

    def test_last_summary_uses_label_not_task_id(self):
        db = _db()
        karte_service.update_from_audio(db, 1, diagnosed_task="breathy_closure",
                                        song_title="曲A")
        k = karte_service.get_or_none(db, 1)
        self.assertNotIn("breathy_closure", k.last_summary,
                         "内部IDを挨拶（continueモード）に露出させない")
        self.assertIn("息漏れ", k.last_summary)


class PromptInjection(unittest.TestCase):
    def test_karte_context_injected_into_session_context(self):
        state = {"phase": "practice", "song_ref_url": None, "song_ref_path": None,
                 "current_task": None, "baseline_analysis": None, "last_analysis": None,
                 "karte_context": "この生徒について（カルテ。過去の記録＝参考情報）:\n- 持ち癖: breathy_closure×3"}
        ctx = llm.build_session_context(state)
        self.assertIn("この生徒について", ctx)
        self.assertIn("breathy_closure×3", ctx)

    def test_homework_usage_guidance_injected(self):
        # 宿題があるカルテには「挨拶で蒸し返さず、FB・提案の流れでだけ言及」の作法を添える
        state = {"phase": "practice", "song_ref_url": None, "song_ref_path": None,
                 "current_task": None, "baseline_analysis": None, "last_analysis": None,
                 "karte_context": "この生徒について:\n- 宿題: 『ストロー発声（SOVT）』（2026-08-01に出した）"}
        ctx = llm.build_session_context(state)
        self.assertIn("宿題の使い方", ctx)
        self.assertIn("持ち出さない", ctx)

    def test_no_karte_no_injection(self):
        state = {"phase": "A", "song_ref_url": None, "song_ref_path": None,
                 "current_task": None, "baseline_analysis": None, "last_analysis": None}
        ctx = llm.build_session_context(state)
        self.assertNotIn("この生徒について", ctx, "カルテ無し＝現行の文脈のまま（AC-03）")


if __name__ == "__main__":
    unittest.main(verbosity=2)
