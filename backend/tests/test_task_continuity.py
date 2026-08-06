"""課題継続コーチング（docs/91）と Gemini thinking ガードの契約テスト。

DB・ネットワーク不要。LLM(_complete / _complete_with_tools)を無効化し、
確定的なフォールバック文だけで検証する（hermetic）。

実行:
    cd backend && python -m unittest tests.test_task_continuity -v
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coaching import feedback_builder, llm, rule_engine  # noqa: E402
from app.core.config import Settings  # noqa: E402

BAD_SCORE = re.compile(r"\d+\s*/\s*100|\d+\s*点|[◎○△×]")

_ORIG_COMPLETE = None
_ORIG_COMPLETE_TOOLS = None


def setUpModule():
    global _ORIG_COMPLETE, _ORIG_COMPLETE_TOOLS
    _ORIG_COMPLETE = llm._complete
    _ORIG_COMPLETE_TOOLS = llm._complete_with_tools
    llm._complete = lambda *a, **k: None  # type: ignore
    llm._complete_with_tools = lambda *a, **k: (None, set())  # type: ignore


def tearDownModule():
    if _ORIG_COMPLETE is not None:
        llm._complete = _ORIG_COMPLETE  # type: ignore
    if _ORIG_COMPLETE_TOOLS is not None:
        llm._complete_with_tools = _ORIG_COMPLETE_TOOLS  # type: ignore


def _state(**over):
    s = {
        "phase": "A", "song_ref_url": None, "song_ref_path": None,
        "user_range": None, "ref_range": None, "current_task": None,
        "focus_task": None, "avoid_task": None,
        "baseline_analysis": None, "last_analysis": None, "d_retry_count": 0,
    }
    s.update(over)
    return s


def _analysis(**over):
    """課題あり（音程ジッター大・伸ばし不安定・息漏れ気味）の解析値。"""
    a = {
        "duration_sec": 20.0, "rms_mean": 0.03, "voiced_ratio": 0.9,
        "f0_median_hz": 220.0, "f0_jitter_cents": 40.0, "long_tone_stability": 90.0,
        "rms_db_range": 6.0, "h1h2_db": 9.0, "cpp_db": 5.0, "hnr_db": 10.0,
        "harmonic_ratio": 0.4, "singers_formant_ratio": 0.001,
        "vibrato_rate_hz": None, "vibrato_depth_cents": None,
        "timeline": {"sustained_segments": [
            {"start_sec": 10.0, "end_sec": 14.0, "duration_sec": 4.0, "mean_f0_hz": 330.0,
             "register": "chest", "register_confidence": "high", "spectral_centroid_hz": 2900.0},
        ], "per_window": [{"f0_mean_hz": 220.0}, {"f0_mean_hz": 330.0}]},
    }
    a.update(over)
    return a


BASELINE = _analysis()
# わずかに改善したが未クリア（ジッター 40→34cents は 20cents 超で pitch_wobble 継続）
SLIGHTLY_BETTER = _analysis(f0_jitter_cents=34.0, long_tone_stability=80.0, cpp_db=5.5)
# クリア相当（安定・効率的・良い響き。どの課題も検知されない）
CLEARED = _analysis(
    f0_jitter_cents=5.0, long_tone_stability=15.0, rms_db_range=16.0,
    h1h2_db=4.0, cpp_db=12.0, hnr_db=18.0, harmonic_ratio=0.6,
    singers_formant_ratio=0.009, vibrato_rate_hz=5.5, vibrato_depth_cents=50.0,
    timeline={"sustained_segments": [
        {"start_sec": 10.0, "end_sec": 14.0, "duration_sec": 4.0, "mean_f0_hz": 300.0,
         "register": "mix", "register_confidence": "high", "spectral_centroid_hz": 2400.0},
    ], "per_window": [{"f0_mean_hz": 220.0}, {"f0_mean_hz": 300.0}]},
)


class TaskContinuity(unittest.TestCase):
    """歌い直しで課題を乗り換えない（exclude 廃止・クリアまでフォーカス継続）。"""

    def test_recheck_stays_on_same_task_until_cleared(self):
        st = _state(phase="practice", current_task="pitch_wobble", baseline_analysis=BASELINE)
        msgs, updates = rule_engine.handle_audio(st, SLIGHTLY_BETTER, None, "song")
        text = " ".join(m.get("text") or "" for m in msgs)
        # 課題は変わらない（別のダメ出しに乗り換えない）
        self.assertEqual(updates.get("current_task"), "pitch_wobble")
        self.assertEqual(updates.get("phase"), rule_engine.LESSON)
        # 次回は「前回 vs 今回」で比べる＝基準を今回の解析へ更新
        self.assertIs(updates.get("baseline_analysis"), SLIGHTLY_BETTER)
        # 微改善を励ます（フォールバック文の契約）
        self.assertIn("少しずつ良くなっていますよ", text)
        self.assertIn("その感覚です", text)
        self.assertIsNone(BAD_SCORE.search(text), "点数/記号は出さない")
        # 数値の生読みはしない。体感語に翻訳して伝える（docs/42 §6・運用者FB）
        # （"→" は練習名『リップロール → 母音ロングトーン』に正当に含まれるため禁止対象外）
        for banned in ("cents", "dB", "40", "34"):
            self.assertNotIn(banned, text)
        self.assertIn("声の揺れが落ち着いて", text)  # ジッター減の体感語

    def test_recheck_no_gain_is_honest_not_scolding(self):
        st = _state(phase="practice", current_task="pitch_wobble", baseline_analysis=BASELINE)
        msgs, updates = rule_engine.handle_audio(st, BASELINE, None, "song")
        text = " ".join(m.get("text") or "" for m in msgs)
        # 改善ゼロで「良くなっています」と嘘をつかない
        self.assertNotIn("少しずつ良くなっていますよ", text)
        self.assertIn("焦らず", text)
        self.assertEqual(updates.get("current_task"), "pitch_wobble")

    def test_recheck_clear_celebrates_and_finishes(self):
        st = _state(phase="practice", current_task="pitch_wobble", baseline_analysis=BASELINE)
        msgs, updates = rule_engine.handle_audio(st, CLEARED, None, "song")
        text = " ".join(m.get("text") or "" for m in msgs)
        self.assertIn("クリア", text)
        # クリア後の録音では他の課題も検知されない → 気持ちよく締める
        self.assertEqual(updates.get("phase"), rule_engine.DONE)
        self.assertIsNone(BAD_SCORE.search(text))

    def test_focus_task_never_falsely_cleared(self):
        # 主訴(focus)が解析で検知できない場合、「クリアしました」と言わない
        st = _state(phase="practice", current_task="pitch_wobble",
                    focus_task="mixed_voice", baseline_analysis=BASELINE)
        msgs, updates = rule_engine.handle_audio(st, SLIGHTLY_BETTER, None, "song")
        text = " ".join(m.get("text") or "" for m in msgs)
        self.assertNotIn("クリア", text)
        # 主訴が最優先で課題になる
        self.assertEqual(updates.get("current_task"), "mixed_voice")


class FocusTaskPriority(unittest.TestCase):
    """主訴（focus_task）は解析での検知有無に関わらず最優先（docs/91）。"""

    def test_diagnose_uses_focus_task_first(self):
        # 解析上は pitch_wobble 等が検知される録音でも、主訴 mixed_voice を最優先で採用
        st = _state(focus_task="mixed_voice")
        msgs, updates = rule_engine.handle_audio(st, BASELINE, None, "song")
        self.assertEqual(updates.get("current_task"), "mixed_voice")
        self.assertEqual(len(msgs), 2, "課題あり扱い＝①感想②練習の2吹き出し")


class MicroProgress(unittest.TestCase):
    """build_micro_progress: ノイズ床を超えた微改善だけを実測で拾う。"""

    def test_detects_small_gains(self):
        r = feedback_builder.build_micro_progress(BASELINE, SLIGHTLY_BETTER)
        self.assertTrue(r["any_gain"])
        joined = " ".join(r["gains"])
        self.assertIn("音程の細かな揺れ", joined)
        self.assertIn("40", joined)
        self.assertIn("34", joined)

    def test_spoken_translation_has_no_raw_numbers(self):
        """spoken はユーザーに口に出す体感語。数値・単位を含まない（docs/42 §6・運用者FB）。"""
        r = feedback_builder.build_micro_progress(BASELINE, SLIGHTLY_BETTER)
        self.assertEqual(len(r["spoken"]), len(r["gains"]))  # gains と同順で対応
        for s in r["spoken"]:
            for banned in ("cents", "dB", "%", "Hz", "→"):
                self.assertNotIn(banned, s)
            self.assertFalse(any(ch.isdigit() for ch in s), s)

    def test_every_metric_has_spoken_phrase(self):
        """全指標に体感語が定義されている（追加した指標の翻訳漏れを防ぐ）。"""
        for row in feedback_builder._MICRO_METRICS:
            self.assertEqual(len(row), 7, row[0])
            self.assertTrue(row[6], row[0])
            self.assertFalse(any(ch.isdigit() for ch in row[6]), row[0])

    def test_no_gain_when_identical(self):
        r = feedback_builder.build_micro_progress(BASELINE, BASELINE)
        self.assertFalse(r["any_gain"])
        self.assertEqual(r["gains"], [])

    def test_h1h2_gain_is_move_toward_target_band(self):
        # 9dB(息漏れ寄り) → 7dB は目標帯(≈4.5dB)へ接近＝方向性が合っている
        r = feedback_builder.build_micro_progress({"h1h2_db": 9.0}, {"h1h2_db": 7.0})
        self.assertTrue(r["any_gain"])
        self.assertIn("声帯の閉じ", r["gains"][0])
        # 逆に目標帯から離れたら拾わない（1dB → 0dB は締めすぎ方向）
        r2 = feedback_builder.build_micro_progress({"h1h2_db": 1.0}, {"h1h2_db": 0.0})
        self.assertFalse(r2["any_gain"])

    def test_noise_floor_filters_measurement_jitter(self):
        # 0.5cents の変化は測定ゆらぎ（床 1.0cents 未満）→ 拾わない
        r = feedback_builder.build_micro_progress(
            {"f0_jitter_cents": 40.0}, {"f0_jitter_cents": 39.5})
        self.assertFalse(r["any_gain"])


class ThinkingBudgetGuard(unittest.TestCase):
    """Gemini 3 系での INVALID_ARGUMENT（会話全滅）の回帰ガード（docs/91 原因1）。"""

    def test_thinking_budget_only_for_2_5_family(self):
        self.assertTrue(llm._supports_thinking_budget("gemini-2.5-flash-lite"))
        self.assertTrue(llm._supports_thinking_budget("gemini-2.5-flash"))
        # 浮動エイリアス・新世代には thinking_budget を明示指定しない
        self.assertFalse(llm._supports_thinking_budget("gemini-flash-lite-latest"))
        self.assertFalse(llm._supports_thinking_budget("gemini-3.5-flash"))
        self.assertFalse(llm._supports_thinking_budget(None))

    def test_thinking_off_returns_none_for_unsupported(self):
        # SDK 不要のパス（未対応モデルは types を import せず None を返す）
        self.assertIsNone(llm._thinking_off("gemini-3.5-flash-lite"))
        self.assertIsNone(llm._thinking_off("gemini-flash-lite-latest"))

    def test_default_models_are_pinned_versions(self):
        # "-latest" エイリアス禁止（世代切替でテキスト会話が壊れた障害の再発防止）。
        # かつ世代番号が明示されていること（gemini-3.5-flash-lite のように x.y を含む）。
        #
        # 以前はここで「必ず '2.5' を含む」と断言していたが、その前提自体が壊れた:
        # gemini-2.5-flash-lite は 404 で死んでおり、2.5 縛りは死んだ世代への固定を
        # 強制してしまう。世代の妥当性は実APIの疎通確認で担保する（docs/92 §0）。
        import re
        for field in ("llm_model", "llm_chat_model", "llm_audio_model", "llm_analysis_model"):
            default = Settings.model_fields[field].default
            self.assertNotIn("latest", default, field)
            self.assertRegex(default, r"^gemini-\d+\.\d+-", field)


if __name__ == "__main__":
    unittest.main(verbosity=2)
