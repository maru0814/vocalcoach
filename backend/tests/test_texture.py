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
        # 較正用の生値（しきい値でふるう前の窓ごとのピーク）が記録される（docs/104 §4）
        self.assertTrue(p["windows"], "windows が空でない")
        for w in p["windows"]:
            self.assertTrue(0.0 <= w["strength"] <= 1.0)
            self.assertGreater(w["rate_hz"], 0.0)
        self.assertGreaterEqual(p["flutter_ratio"], 0.7, "全体で震えている")
        d = texture.describe(p)
        self.assertIn("ほぼ全体で", d)
        self.assertIn("唇・舌の震えやエッジボイスに典型的な帯域", d)
        for banned in ("リップロール", "巻き舌", "サイレン"):
            self.assertNotIn(banned, d, "記述文に練習名を含めない（docs/104 原則）")

    def test_partial_flutter_reported_as_partial(self):
        """冒頭だけきしむサイレン相当（先頭1.5秒のみ震え）→「一部のみ」と記述。"""
        sec = 4.0
        t = np.linspace(0, sec, int(SR * sec), endpoint=False)
        base = _sweep(sec=sec)
        am = 1.0 + 0.8 * np.sin(2 * np.pi * 25.0 * t) * (t < 1.5)
        path = _write_wav(base * am / np.abs(base * am).max() * 0.8)
        try:
            p = texture.modulation_profile(path)
        finally:
            os.unlink(path)
        self.assertIsNotNone(p)
        self.assertLess(p["flutter_ratio"], 0.7)
        self.assertGreater(p["flutter_ratio"], 0.0)
        d = texture.describe(p)
        self.assertIn("割の区間で", d)
        # 矮小化表現の禁止（較正第1号: 「のみ」「なめらか」がモデルの聴覚を上書きした）
        self.assertNotIn("のみ", d)
        self.assertNotIn("なめらか", d)

    def test_13hz_flutter_gets_lip_tongue_annotation(self):
        """回帰（較正第1号・2026-08-14）: 実物のリップロールは13.8Hzで震えることがある。
        10〜15Hz帯にも「唇・舌の震え」の帯域注釈を付ける（旧: 注釈なしの谷間）。"""
        t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
        y = _sweep() * (1.0 + 0.8 * np.sin(2 * np.pi * 13.0 * t)) / 1.8
        path = _write_wav(y)
        try:
            p = texture.modulation_profile(path)
        finally:
            os.unlink(path)
        self.assertIsNotNone(p)
        self.assertTrue(10 <= p["mod_rate_hz"] < 15, f"rate={p['mod_rate_hz']}")
        self.assertTrue(texture.has_modulation(p))
        self.assertIn("唇・舌の震えやエッジボイスに典型的な帯域", texture.describe(p))

    def test_plain_sweep_has_no_flutter(self):
        """変調なしスイープ（サイレン相当）→ 震えは検出されない。"""
        path = _write_wav(_sweep())
        try:
            p = texture.modulation_profile(path)
        finally:
            os.unlink(path)
        self.assertIsNotNone(p)
        d = texture.describe(p)
        self.assertEqual(d, "規則的な振幅の震え（毎秒4〜45回の帯域）は検出されない")

    def test_low_voice_sweep_f0_not_reported_as_pulses(self):
        """回帰（2026-08-14 実事故）: 低い声のサイレン（f0 94→382Hz・倍音つき）の
        基本周波数を「パルス状の震え」と誤検出しない。"""
        sec = 4.0
        t = np.linspace(0, sec, int(SR * sec), endpoint=False)
        f0_t = 94.0 * (382.0 / 94.0) ** (t / sec)  # 対数スイープ
        phase = 2 * np.pi * np.cumsum(f0_t) / SR
        # のこぎり波（声帯パルスに似た倍音構造）で声らしい信号を作る
        y = 0.4 * (2 * ((phase / (2 * np.pi)) % 1.0) - 1.0)
        path = _write_wav(y)
        try:
            p = texture.modulation_profile(path)
        finally:
            os.unlink(path)
        self.assertIsNotNone(p)
        d = texture.describe(p)
        self.assertIn("検出されない", d, f"f0漏れをパルスと主張しない: {p}")

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
