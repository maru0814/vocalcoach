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

    # FR-04: 点数質問もチャット経路(LLM)に統一。点数(数字)を返さない。
    # （実LLMでの「点数はつけていない」方針は HTTP e2e TC-12 で確認済み。
    #   ここは LLM不可時に正直フォールバックへ落ち、点数を返さないことを担保する）
    def test_score_question_no_points(self):
        msgs, _ = rule_engine.handle_text(
            _state(phase="practice", current_task="pitch_wobble", baseline_analysis=ANALYSIS_ISSUE),
            "これ何点ですか？",
        )
        text = " ".join(m.get("text") or "" for m in msgs if m["role"] == "coach")
        self.assertIsNone(BAD_SCORE.search(text), "点数を返してはいけない")

    # FR-03: 動画依頼はカードでなく会話文＋リンク
    def test_video_request_inline_no_card(self):
        msgs = rule_engine.handle_video_request(_state(), "ミックスボイスの動画ある？")
        for m in msgs:
            self.assertEqual(m["type"], "text")
        self.assertEqual(len(msgs), 1)

    # 定型文廃止: ルールベースの answer_question は削除済み
    def test_rule_based_qa_removed(self):
        self.assertFalse(hasattr(rule_engine, "answer_question"),
                         "ルールベース定型Q&A(answer_question)は廃止されているべき")

    # 定型文廃止: LLM失敗時、はぐらかし定型でなく“正直な短いメッセージ”が返る
    def test_chat_llm_down_honest_not_hedge(self):
        # setUpModule で _complete→None（LLM不可）。LESSON中に質問する。
        st = _state(phase="practice", current_task="pitch_wobble",
                    baseline_analysis=ANALYSIS_ISSUE, last_analysis=ANALYSIS_ISSUE)
        msgs, _ = rule_engine.handle_text(st, "音程の揺れって具体的にどのあたり？")
        text = " ".join(m.get("text") or "" for m in msgs if m["role"] == "coach")
        # 旧・はぐらかし定型は出ない
        self.assertNotIn("なるほど😊", text)
        self.assertNotIn("準備ができたら", text)
        # 正直フォールバックである
        self.assertIn("うまく言葉が出せませんでした", text)


class TextReplyPromptFraming(unittest.TestCase):
    """テキスト質問のプロンプト構築（_build_contents）の契約。

    フォローアップの質問が「録音を解析したFB」テンプレで返る不具合の回帰ガード。
    LLM自体は叩かず、Gemini へ渡す contents の組み立てだけを検証する（hermetic）。
    """

    def _last_text(self, contents):
        return contents[-1].parts[0].text

    def test_followup_turn_marked_not_new_recording(self):
        # 録音解析済み(last_analysis あり)の状態でテキスト質問が来た場面。
        st = _state(phase="practice", current_task="pitch_wobble",
                    last_analysis=ANALYSIS_ISSUE, baseline_analysis=ANALYSIS_ISSUE)
        contents = llm._build_contents(st, "具体的にどう練習すればいいの？", [])
        last = self._last_text(contents)
        # 今回は新しい録音が来ていない、と明示している
        self.assertIn("新しく届いた録音ではない", last)
        # 講評の書き出しで始めない、という指示が入っている
        self.assertIn("録音を送ってくれてありがとう", last)
        self.assertIn("始めないこと", last)
        # ユーザーの発言はちゃんと載っている
        self.assertIn("具体的にどう練習すればいいの？", last)

    def test_history_preserved_before_question(self):
        st = _state(phase="practice", current_task="pitch_wobble",
                    last_analysis=ANALYSIS_ISSUE, baseline_analysis=ANALYSIS_ISSUE)
        history = [
            {"role": "user", "content": "ボーカルフライって何ですか？"},
            {"role": "assistant", "content": "ガラガラ声を作る練習です。"},
        ]
        contents = llm._build_contents(st, "次はどうする？", history)
        # 履歴が会話ターンとして渡る（user 始まりが保証される）
        joined = "\n".join(c.parts[0].text for c in contents)
        self.assertIn("ボーカルフライって何ですか？", joined)
        self.assertIn("ガラガラ声を作る練習です。", joined)
        self.assertEqual(contents[0].role, "user")


if __name__ == "__main__":
    unittest.main(verbosity=2)
