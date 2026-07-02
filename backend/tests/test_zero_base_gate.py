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


if __name__ == "__main__":
    unittest.main(verbosity=2)
