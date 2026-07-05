"""zero-base FB の上限ゲート（docs/52 FR-02/03）。

有料ユーザーは月次上限の対象外、無料ユーザーは上限で停止することを、
LLM・DB・ネットワーク非依存（hermetic）で検証する。

実行: cd backend && ./.venv/bin/python -m unittest tests.test_zero_base_gate -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import llm_budget  # noqa: E402
from app.core.config import settings  # noqa: E402


class ZeroBaseGate(unittest.TestCase):
    # AC-02/03: 上限到達状態でも有料は呼べる／無料は止まる
    def test_premium_bypasses_cap_free_stops(self):
        orig = llm_budget.would_exceed
        llm_budget.would_exceed = lambda est: True  # 当月上限に到達している状態
        try:
            self.assertTrue(llm_budget.zero_base_allowed(True, 1.5), "有料は上限対象外で呼べる")
            self.assertFalse(llm_budget.zero_base_allowed(False, 1.5), "無料は上限で停止する")
        finally:
            llm_budget.would_exceed = orig

    def test_free_allowed_under_cap(self):
        orig = llm_budget.would_exceed
        llm_budget.would_exceed = lambda est: False  # まだ上限未満
        try:
            self.assertTrue(llm_budget.zero_base_allowed(False, 1.5))
            self.assertTrue(llm_budget.zero_base_allowed(True, 1.5))
        finally:
            llm_budget.would_exceed = orig


class BudgetLedgerCounting(unittest.TestCase):
    # AC-05 / FR-03: 呼び出しごとに原価と回数を記録する
    def setUp(self):
        self._orig_path = settings.llm_cost_ledger_path
        self._orig_cap = settings.llm_monthly_budget_jpy
        d = os.path.join(os.path.dirname(__file__), "_tmp_ledger.json")
        if os.path.exists(d):
            os.remove(d)
        settings.llm_cost_ledger_path = d
        settings.llm_monthly_budget_jpy = 0  # 無制限（通知副作用を避ける）

    def tearDown(self):
        if os.path.exists(settings.llm_cost_ledger_path):
            os.remove(settings.llm_cost_ledger_path)
        settings.llm_cost_ledger_path = self._orig_path
        settings.llm_monthly_budget_jpy = self._orig_cap

    def test_record_increments_cost_and_count(self):
        self.assertEqual(llm_budget.month_calls(), 0)
        llm_budget.record(1.5)
        llm_budget.record(1.5)
        self.assertEqual(llm_budget.month_calls(), 2)
        self.assertAlmostEqual(llm_budget.month_spend_jpy(), 3.0, places=2)


class IntentAwareListening(unittest.TestCase):
    """zero-base の意図判定（docs/52 FR-04）。

    「勧めた基礎練の実演」を zero-base が曲として講評して、resolve_kind の修正を
    上書きしてしまう再発（表示テキストと状態遷移の食い違い）の回帰ガード。
    """

    def test_split_intent_tag_practice(self):
        from app.coaching import llm
        heard, rest = llm._split_intent_tag("INTENT: practice\n\nフライ、いい感じです。")
        self.assertEqual(heard, "practice")
        self.assertEqual(rest, "フライ、いい感じです。")

    def test_split_intent_tag_song_case_insensitive(self):
        from app.coaching import llm
        heard, rest = llm._split_intent_tag("intent: SONG\n本文です。")
        self.assertEqual(heard, "song")
        self.assertEqual(rest, "本文です。")

    def test_split_intent_tag_absent_returns_none(self):
        from app.coaching import llm
        heard, rest = llm._split_intent_tag("タグの無い普通の講評。")
        self.assertIsNone(heard)
        self.assertEqual(rest, "タグの無い普通の講評。")

    def test_generate_feedback_strips_tag_and_writes_back(self):
        """モデルが INTENT タグ付きで返したら、タグは本文から消え intent_ctx に書き戻る。"""
        from unittest import mock
        from app.coaching import llm

        fake = "INTENT: practice\n\nガラガラからの繋ぎ、狙いどおりです。次は曲で試しましょう。"

        class _Resp:
            text = fake

        class _Models:
            def generate_content(self, **kw):
                return _Resp()

        class _Client:
            def __init__(self, **kw):
                self.models = _Models()

        state = {"phase": "practice", "current_task": "breathy_closure",
                 "last_analysis": {"duration_sec": 5.0}, "baseline_analysis": None,
                 "song_ref_url": None, "song_ref_path": None}
        ictx = {"kind_hint": "song", "task_label": "息漏れを減らす", "practice_name": "ボーカルフライからのアタック"}
        orig_flag, orig_key = settings.enable_zero_base_fb, settings.gemini_api_key
        settings.enable_zero_base_fb, settings.gemini_api_key = True, "TEST_DUMMY"
        try:
            with mock.patch("google.genai.Client", _Client):
                reply = llm.generate_feedback(state, user_wav=b"RIFFfake", intent_ctx=ictx)
        finally:
            settings.enable_zero_base_fb, settings.gemini_api_key = orig_flag, orig_key
        self.assertIsNotNone(reply)
        self.assertNotIn("INTENT", reply, "意図タグをユーザーに見せない")
        self.assertIn("ガラガラ", reply)
        self.assertEqual(ictx.get("heard"), "practice", "聴いた判定が書き戻る")


if __name__ == "__main__":
    unittest.main(verbosity=2)
