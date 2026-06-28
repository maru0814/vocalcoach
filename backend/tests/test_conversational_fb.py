"""会話型FBの契約テスト（docs/36-38, docs/39）。

DB・ネットワーク不要。LLM(_complete)を無効化し、ルールベースの確定的な
フォールバック文だけで「会話チャット契約」を検証する（hermetic）。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_conversational_fb -v
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coaching import llm, rule_engine  # noqa: E402

# 点数(NN/100, NN点) と ◎○△× が出力に現れたら NG。
BAD_SCORE = re.compile(r"\d+\s*/\s*100|\d+\s*点|[◎○△×]")
CARD_TYPES = {"feedback", "practice", "judge", "progress", "diagnosis"}


def setUpModule():
    # LLMを無効化 → _llm_or / generate_reply は確定的なテンプレ文へフォールバック。
    llm._complete = lambda *a, **k: None  # type: ignore


def _state(**over):
    s = {
        "phase": "A", "song_ref_url": None, "song_ref_path": None,
        "user_range": None, "ref_range": None, "current_task": None,
        "focus_task": None, "avoid_task": None,
        "baseline_analysis": None, "last_analysis": None, "d_retry_count": 0,
    }
    s.update(over)
    return s


# 明確な課題あり（伸ばしが大きく揺れる＋音程ジッター大＋息漏れ）
ANALYSIS_ISSUE = {
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

# 大きな課題なし（安定・効率的・良い響き）
ANALYSIS_GOOD = {
    "duration_sec": 20.0, "rms_mean": 0.03, "voiced_ratio": 0.95,
    "f0_median_hz": 220.0, "f0_jitter_cents": 5.0, "long_tone_stability": 15.0,
    "rms_db_range": 16.0, "h1h2_db": 4.0, "cpp_db": 12.0, "hnr_db": 18.0,
    "harmonic_ratio": 0.6, "singers_formant_ratio": 0.009,
    "vibrato_rate_hz": 5.5, "vibrato_depth_cents": 50.0,
    "timeline": {"sustained_segments": [
        {"start_sec": 10.0, "end_sec": 14.0, "duration_sec": 4.0, "mean_f0_hz": 300.0,
         "register": "mix", "register_confidence": "high", "spectral_centroid_hz": 2400.0},
    ], "per_window": [{"f0_mean_hz": 220.0}, {"f0_mean_hz": 300.0}]},
}


class ConversationalFBContract(unittest.TestCase):
    def _assert_text_only_no_score(self, msgs):
        for m in msgs:
            self.assertEqual(m["type"], "text", f"カード型が混入: {m['type']}")
            self.assertNotIn(m["type"], CARD_TYPES)
            hit = BAD_SCORE.search(m.get("text") or "")
            self.assertIsNone(hit, f"点数/記号が出力に: {hit.group(0) if hit else ''}")

    # AC-01/02/03: 課題あり録音 → text 2吹き出し・点数なし・課題確定
    def test_diagnose_issue_two_text_bubbles(self):
        msgs, updates = rule_engine.handle_audio(_state(), ANALYSIS_ISSUE, None, "song")
        self._assert_text_only_no_score(msgs)
        self.assertEqual(len(msgs), 2, "課題ありは①感想②練習の2吹き出し")
        self.assertIsNotNone(updates.get("current_task"), "課題が確定するはず")

    # AC-01/02/03: 良い録音 → text 1吹き出し・練習を出さない
    def test_diagnose_good_single_bubble(self):
        msgs, updates = rule_engine.handle_audio(_state(), ANALYSIS_GOOD, None, "song")
        self._assert_text_only_no_score(msgs)
        self.assertEqual(len(msgs), 1, "良い録音は褒めのみ1吹き出し")
        self.assertIsNone(updates.get("current_task"), "練習(課題)を出さない")

    # AC-02: 基礎練の達成判定はカード/点数なしの会話文
    def test_practice_check_text_only(self):
        st = _state(current_task="long_tone_decay")
        msgs, _ = rule_engine.handle_audio(st, ANALYSIS_GOOD, None, "practice")
        self._assert_text_only_no_score(msgs)
        self.assertTrue(1 <= len(msgs) <= 2)

    # AC-02: 歌い直しの改善判定はカード/点数なしの会話文
    def test_recheck_text_only(self):
        st = _state(current_task="long_tone_decay", baseline_analysis=ANALYSIS_ISSUE)
        msgs, _ = rule_engine.handle_audio(st, ANALYSIS_GOOD, None, "song")
        self._assert_text_only_no_score(msgs)
        self.assertTrue(1 <= len(msgs) <= 2)

    # FR-04: 点数を聞かれたら「つけていない」方針を返す（数字で採点しない）
    def test_score_question_no_points(self):
        reply = rule_engine.answer_question(_state(), "これ何点ですか？")
        self.assertIsNotNone(reply)
        self.assertIsNone(BAD_SCORE.search(reply), "点数を返してはいけない")
        self.assertIn("点", reply)  # 「点数はつけていない」の文言は含む

    # FR-03: 動画依頼はカードでなく会話文＋リンク
    def test_video_request_inline_no_card(self):
        msgs = rule_engine.handle_video_request(_state(), "ミックスボイスの動画ある？")
        for m in msgs:
            self.assertEqual(m["type"], "text")
        self.assertEqual(len(msgs), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
