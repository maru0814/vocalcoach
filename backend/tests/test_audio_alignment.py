"""DTWアライメント（app/audio/alignment.py）のテスト。

純粋ヘルパー（音程スコア・キー差推定・外し箇所抽出）は決定的に検証し、
align() は合成サイン波で「同一信号なら高信頼・キー差0・ラグ≈0」を確認する。
"""
import numpy as np
import pytest

from app.audio import alignment as al


# --- _hz_to_cents ---

class TestHzToCents:
    def test_reference_zero_and_nan(self):
        out = al._hz_to_cents(np.array([440.0, 0.0, np.nan]))
        assert out[0] == pytest.approx(0.0)
        assert np.isnan(out[1]) and np.isnan(out[2])


# --- _intune_score（MAD帯域 + 外れ割合ペナルティ） ---

class TestIntuneScore:
    def test_bands_descend_with_mad(self):
        assert al._intune_score(10, 0.0) == 92
        assert al._intune_score(30, 0.0) == 82
        assert al._intune_score(45, 0.0) == 70
        assert al._intune_score(70, 0.0) == 56
        assert al._intune_score(120, 0.0) == 42

    def test_off_ratio_penalizes(self):
        # off_ratio=0.5 → -min(30, 30) = -30。base92 → 62。
        assert al._intune_score(10, 0.5) == 62

    def test_clamped_to_floor(self):
        assert al._intune_score(200, 1.0) >= 20


# --- _best_pc_shift（クロマ回転＝キー差推定） ---

class TestBestPcShift:
    def test_identical_chroma_zero_shift(self):
        rng = np.random.default_rng(0)
        c = np.abs(rng.standard_normal((12, 40)))
        shift, sim = al._best_pc_shift(c, c.copy())
        assert shift == 0
        assert sim == pytest.approx(1.0, abs=1e-6)

    def test_rotated_chroma_detected(self):
        rng = np.random.default_rng(1)
        c = np.abs(rng.standard_normal((12, 40)))
        rolled = np.roll(c, 2, axis=0)   # cr を 2半音ぶん回転
        shift, _ = al._best_pc_shift(c, rolled)
        # roll(mu, k)·mr が最大になる k。mr=roll(mu,2) なので k=2 で一致。
        assert shift == 2


# --- _pitch_off_spots（明確に外している箇所だけ抽出） ---

class TestPitchOffSpots:
    def test_detects_sustained_sharp_region(self):
        hop_sec = 1024 / 22050
        n = 60
        rel = np.zeros(n)
        rel[20:40] = 90.0          # 0.9秒ほど +90c シャープに外す
        times = np.arange(n) * hop_sec
        spots = al._pitch_off_spots(rel, times, hop_sec)
        assert len(spots) >= 1
        assert spots[0]["direction"] == "sharp"
        assert 80 <= spots[0]["cents"] <= 100

    def test_no_spots_when_in_tune(self):
        hop_sec = 1024 / 22050
        rel = np.full(60, 10.0)    # わずかなゆらぎのみ
        times = np.arange(60) * hop_sec
        assert al._pitch_off_spots(rel, times, hop_sec) == []


# --- align（合成信号での結合テスト） ---

class TestAlign:
    def _sine(self, freq=220.0, dur=5.0):
        sr = 22050
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        y = (0.6 * np.sin(2 * np.pi * freq * t)
             + 0.2 * np.sin(2 * np.pi * 2 * freq * t)).astype(np.float32)
        return y, sr

    def _melody(self, freqs=(220.0, 277.0, 330.0, 392.0, 330.0), note_sec=1.0):
        """音が時間で変化するメロディ。定常音と違い時間構造があるのでDTWで照合できる。"""
        sr = 22050
        parts = []
        for f in freqs:
            t = np.linspace(0, note_sec, int(sr * note_sec), endpoint=False)
            parts.append(0.6 * np.sin(2 * np.pi * f * t)
                         + 0.2 * np.sin(2 * np.pi * 2 * f * t))
        return np.concatenate(parts).astype(np.float32), sr

    def test_too_short_returns_none(self):
        y, sr = self._sine(dur=2.0)   # <3s
        assert al.align(y, y, sr) is None

    def test_identical_melody_high_confidence_zero_shift(self):
        y, sr = self._melody()
        out = al.align(y, y.copy(), sr)
        assert out is not None
        assert out["low_confidence"] is False       # 同一メロディは高信頼で照合できる
        assert out["key_shift_semitones"] == 0
        assert out["mean_lag_sec"] == pytest.approx(0.0, abs=0.05)

    def test_unrelated_noise_low_confidence(self):
        # 無関係なノイズ同士は同一曲として照合できない → low_confidence で数値を出さない。
        rng = np.random.default_rng(0)
        sr = 22050
        u = rng.standard_normal(sr * 5).astype(np.float32)
        r = rng.standard_normal(sr * 5).astype(np.float32)
        out = al.align(u, r, sr)
        if out is not None:
            assert out["low_confidence"] is True
            assert out["in_tune_score"] is None

    def test_length_ratio_guard(self):
        # 長さが2倍超に違う場合は誤対応を避けて None。
        u, sr = self._sine(dur=4.0)
        r, _ = self._sine(dur=12.0)
        assert al.align(u, r, sr) is None
