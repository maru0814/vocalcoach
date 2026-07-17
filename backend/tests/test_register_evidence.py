"""「高音の声区」evidence 行の契約テスト（docs/42 §4 核心差分の明示・§5 事実忠実性）。

audio-analyst 監査（2026-07-17）: LLM に渡す声区比較行は
(1)「（推定）」を明記し (2) 比較区間の user_hz/ref_hz を含めることで、
LLM が自力でヘッジ・スコープ限定できるようにする（プロンプト強制への依存を減らす）。

DB・ネットワーク不要（hermetic）。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_register_evidence -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coaching import voice_coach  # noqa: E402
from app.coaching.llm import build_session_context  # noqa: E402
from app.coaching.rule_engine import _voice_facts  # noqa: E402


def _rh(**over):
    base = {"user": "chest", "ref": "mix", "user_hz": 392, "ref_hz": 440, "verdict": "differ"}
    base.update(over)
    return base


def _facts(rh):
    return _voice_facts({}, {"voice_compare": {"register_high": rh}})


class VoiceFactsRegisterLine(unittest.TestCase):
    """rule_engine._voice_facts（録音FBコーチ文の facts）。"""

    def test_differ_has_suitei_and_hz(self):
        line = _facts(_rh())
        self.assertIn("高音の声区（推定）", line)
        self.assertIn("あなた≈392Hz", line)
        self.assertIn("原曲≈440Hz", line)
        self.assertIn("地声", line)
        self.assertIn("ミックス", line)

    def test_match_has_suitei_and_hz(self):
        line = _facts(_rh(user="mix", user_hz=415, verdict="match"))
        self.assertIn("高音の声区（推定）", line)
        self.assertIn("原曲と同じミックス", line)
        self.assertIn("あなた≈415Hz", line)

    def test_hz_missing_falls_back_without_hz(self):
        # 片方でも欠けたら Hz 部分ごと省略（片側だけの数値を出すと誤読を招く）
        for rh in (_rh(user_hz=None), _rh(ref_hz=None), {"user": "chest", "ref": "mix", "verdict": "differ"}):
            line = _facts(rh)
            self.assertIn("高音の声区（推定）", line)
            self.assertNotIn("Hz", line)

    def test_no_register_high_no_line(self):
        self.assertNotIn("高音の声区", _voice_facts({}, {"voice_compare": {}}))


class SessionContextRegisterLine(unittest.TestCase):
    """llm.build_session_context（会話セッションの facts）。"""

    def _ctx(self, rh):
        state = {"last_analysis": {"_compare": {"voice_compare": {"register_high": rh}}}}
        return build_session_context(state)

    def test_differ_has_suitei_and_hz(self):
        ctx = self._ctx(_rh())
        line = next(l for l in ctx.splitlines() if l.startswith("- 高音の声区"))
        self.assertIn("高音の声区（推定）", line)
        self.assertIn("あなた≈392Hz", line)
        self.assertIn("原曲≈440Hz", line)

    def test_match_has_suitei_and_hz(self):
        ctx = self._ctx(_rh(user="mix", user_hz=415, verdict="match"))
        line = next(l for l in ctx.splitlines() if l.startswith("- 高音の声区"))
        self.assertIn("（推定）", line)
        self.assertIn("原曲と同じミックス", line)
        self.assertIn("あなた≈415Hz", line)

    def test_hz_missing_falls_back(self):
        ctx = self._ctx(_rh(user_hz=None))
        line = next(l for l in ctx.splitlines() if l.startswith("- 高音の声区"))
        self.assertIn("（推定）", line)
        self.assertNotIn("Hz", line)


class VoiceCoachCompareBits(unittest.TestCase):
    """voice_coach.build_llm_block の「原曲との発声比較」行（同じプロンプトに載るため整合必須）。"""

    def _line(self, rh):
        blk = voice_coach.build_llm_block({"voice": {}}, {"voice_compare": {"register_high": rh}})
        return next((l for l in blk.splitlines() if "高音の声区が原曲と違う" in l), "")

    def test_differ_has_suitei_and_hz(self):
        line = self._line(_rh())
        self.assertIn("推定", line)
        self.assertIn("地声≈392Hz", line)
        self.assertIn("ミックス≈440Hz", line)

    def test_hz_missing_falls_back(self):
        line = self._line({"user": "chest", "ref": "mix", "verdict": "differ"})
        self.assertIn("推定", line)
        self.assertNotIn("Hz", line)

    def test_match_no_differ_line(self):
        self.assertEqual(self._line(_rh(user="mix", verdict="match")), "")


if __name__ == "__main__":
    unittest.main()
