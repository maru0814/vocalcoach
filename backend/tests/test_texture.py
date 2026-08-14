"""質感DSP（backend/app/audio/texture.py・docs/104）の hermetic テスト。

合成信号で「震えの検出」を検証する（実音源・API不要）。
- リップロール相当: 25Hz の振幅変調 → 15〜45Hz帯の震えとして検出
- サイレン相当: 変調なしの連続スイープ → 「震えは検出されない」
- ビブラート相当: 6Hz の緩い揺れ → ビブラート帯域の記述
"""
import os
import sys
import tempfile
import unittest

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.audio import texture  # noqa: E402

SR = 16000


def _write_wav(y: np.ndarray) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(f.name, y.astype(np.float32), SR)
    return f.name


def _sweep(sec: float = 3.0, f0: float = 220.0, f1: float = 880.0) -> np.ndarray:
    """サイレン相当: 連続グリッサンド（振幅は一定）。"""
    t = np.linspace(0, sec, int(SR * sec), endpoint=False)
    phase = 2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * sec))
    return 0.5 * np.sin(phase)


class TextureProfile(unittest.TestCase):
    def test_am_25hz_detected_as_flutter_band(self):
        """25Hz変調（リップロール相当）→ 15〜45Hz帯の規則的な震え。"""
        t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
        y = _sweep() * (1.0 + 0.8 * np.sin(2 * np.pi * 25.0 * t)) / 1.8
        path = _write_wav(y)
        try:
            p = texture.modulation_profile(path)
        finally:
            os.unlink(path)
        self.assertIsNotNone(p)
        self.assertGreaterEqual(p["mod_strength"], texture.STRENGTH_THRESHOLD)
        self.assertTrue(15 <= p["mod_rate_hz"] <= 45, f"rate={p['mod_rate_hz']}")
        d = texture.describe(p)
        self.assertIn("震えを毎秒約", d)
        self.assertIn("唇・舌の震えやエッジボイスに典型的な帯域", d)
        for banned in ("リップロール", "巻き舌", "サイレン"):
            self.assertNotIn(banned, d, "記述文に練習名を含めない（docs/104 原則）")

    def test_plain_sweep_has_no_flutter(self):
        """変調なしスイープ（サイレン相当）→ 震えは検出されない。"""
        path = _write_wav(_sweep())
        try:
            p = texture.modulation_profile(path)
        finally:
            os.unlink(path)
        self.assertIsNotNone(p)
        d = texture.describe(p)
        self.assertEqual(d, "規則的な振幅の震えは検出されない（なめらかな発声）")

    def test_slow_am_is_vibrato_band(self):
        """6Hz の緩い揺れ → ビブラート帯域の記述。"""
        t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
        y = 0.4 * np.sin(2 * np.pi * 440.0 * t) * (1.0 + 0.6 * np.sin(2 * np.pi * 6.0 * t))
        path = _write_wav(y / np.abs(y).max())
        try:
            p = texture.modulation_profile(path)
        finally:
            os.unlink(path)
        self.assertIsNotNone(p)
        d = texture.describe(p)
        self.assertIn("ビブラートに典型的な帯域", d)

    def test_too_short_or_silent_returns_none(self):
        short = _write_wav(np.zeros(int(SR * 0.5)))
        silent = _write_wav(np.zeros(int(SR * 2.0)))
        try:
            self.assertIsNone(texture.modulation_profile(short))
            self.assertIsNone(texture.modulation_profile(silent))
        finally:
            os.unlink(short)
            os.unlink(silent)
        self.assertIsNone(texture.describe(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
