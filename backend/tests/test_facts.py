"""測定事実の組み立て（backend/app/audio/facts.py・docs/104）の hermetic テスト。

本番（coach.py）と eval（scripts/blind_listen_eval.py）が共有する単一ソースなので、
ここが仕様の正本になる。実音源・API不要。
"""
import os
import sys
import tempfile
import unittest

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.audio import facts  # noqa: E402

SR = 16000


def _analysis(f0_list):
    return {"timeline": {"per_window": [{"f0_mean_hz": f} for f in f0_list]}}


class PitchSpanFact(unittest.TestCase):
    def test_large_glissando_reported(self):
        """10半音以上の連続移動 → グリッサンド系を支持する測定事実になる。"""
        d = facts.pitch_span_fact(_analysis([110.0, 220.0, 440.0]))  # 24半音
        self.assertIsNotNone(d)
        self.assertIn("約24半音", d)
        self.assertIn("110→440Hz", d)

    def test_small_span_returns_none(self):
        """10半音未満は主張しない（普通の歌の音域と区別できないため）。"""
        self.assertIsNone(facts.pitch_span_fact(_analysis([220.0, 260.0, 290.0])))

    def test_missing_or_sparse_f0_returns_none(self):
        self.assertIsNone(facts.pitch_span_fact(None))
        self.assertIsNone(facts.pitch_span_fact({}))
        self.assertIsNone(facts.pitch_span_fact(_analysis([220.0, 440.0])))  # 3点未満


class Assemble(unittest.TestCase):
    def _sweep_wav(self) -> str:
        t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
        phase = 2 * np.pi * (220.0 * t + (880.0 - 220.0) * t * t / 6.0)
        f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(f.name, (0.5 * np.sin(phase)).astype(np.float32), SR)
        return f.name

    def test_joins_texture_and_pitch_span(self):
        """質感＋音程移動幅を本番と同じ「。」区切りで組み立てる。"""
        path = self._sweep_wav()
        try:
            d = facts.assemble(path, _analysis([110.0, 220.0, 440.0]))
        finally:
            os.unlink(path)
        self.assertIsNotNone(d)
        self.assertIn("検出されない", d)   # 変調なしスイープ → 震えなしの記述
        self.assertIn("約24半音", d)
        self.assertIn("。", d)
        for banned in ("リップロール", "巻き舌", "サイレン", "フライ"):
            self.assertNotIn(banned, d, "測定事実に練習名を含めない（docs/104 原則）")

    def test_coexist_note_when_flutter_and_glide(self):
        """較正第1号: 震え＋大きな音程移動が同時に測れたら共存注記を添える
        （リップロールをサイレン音形でやった録音の誤認対策。docs/106 §4）。"""
        t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
        phase = 2 * np.pi * (220.0 * t + (880.0 - 220.0) * t * t / 6.0)
        y = 0.5 * np.sin(phase) * (1.0 + 0.8 * np.sin(2 * np.pi * 25.0 * t)) / 1.8
        f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(f.name, y.astype(np.float32), SR)
        try:
            d = facts.assemble(f.name, _analysis([110.0, 220.0, 440.0]))
        finally:
            os.unlink(f.name)
        self.assertIsNotNone(d)
        self.assertIn("震え", d)
        self.assertIn("約24半音", d)
        self.assertIn("同時に成立し得る", d)

    def test_no_coexist_note_without_flutter(self):
        """震えが無い（なめらかなスイープ）なら共存注記は付けない。"""
        path = self._sweep_wav()
        try:
            d = facts.assemble(path, _analysis([110.0, 220.0, 440.0]))
        finally:
            os.unlink(path)
        self.assertIsNotNone(d)
        self.assertNotIn("同時に成立し得る", d)

    def test_texture_only_when_no_analysis(self):
        path = self._sweep_wav()
        try:
            d = facts.assemble(path, None)
        finally:
            os.unlink(path)
        self.assertIsNotNone(d)
        self.assertNotIn("半音", d)

    def test_none_when_nothing_measurable(self):
        f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(f.name, np.zeros(int(SR * 0.5), dtype=np.float32), SR)  # 1秒未満
        try:
            self.assertIsNone(facts.assemble(f.name, None))
        finally:
            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
