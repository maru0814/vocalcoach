"""音声解析（app/audio/analyzer.py）のテスト。

純粋ヘルパー（dict/array in, 値 out）は決定的に検証し、解析パイプライン全体は
合成サイン波で「既知の基本周波数を取り戻せるか」を確認する（音声ファイル不要）。
"""
import numpy as np
import pytest

from app.audio import analyzer


# --- hz_to_cents（純粋・numpy） ---

class TestHzToCents:
    def test_reference_is_zero(self):
        assert analyzer.hz_to_cents(np.array([440.0]))[0] == pytest.approx(0.0)

    def test_octave_is_1200_cents(self):
        assert analyzer.hz_to_cents(np.array([880.0]))[0] == pytest.approx(1200.0)

    def test_nonpositive_is_nan(self):
        out = analyzer.hz_to_cents(np.array([0.0, -10.0]))
        assert np.isnan(out).all()


# --- _voice_type / _register_vote（声区推定の純粋ロジック） ---

class TestRegisterHelpers:
    def test_voice_type_bands(self):
        assert analyzer._voice_type(7.0) == "chest"
        assert analyzer._voice_type(5.0) == "mix"
        assert analyzer._voice_type(2.0) == "head"
        assert analyzer._voice_type(None) is None

    def test_register_vote_chest(self):
        # 傾斜 浅い + H1-H2 小 + ロールオフ比 大 → chest, high。
        label, conf = analyzer._register_vote(-5.0, 1.0, 7.0)
        assert label == "chest" and conf == "high"

    def test_register_vote_head(self):
        label, conf = analyzer._register_vote(-12.0, 9.0, 3.0)
        assert label == "head" and conf == "high"

    def test_register_vote_mix_when_mixed_cues(self):
        label, _ = analyzer._register_vote(-5.0, 9.0, 5.0)   # chest票とhead票が拮抗
        assert label == "mix"

    def test_register_vote_none_without_cues(self):
        assert analyzer._register_vote(None, None, None) == (None, "low")


# --- _voiced_runs（連続発声区間の抽出） ---

class TestVoicedRuns:
    def test_single_run(self):
        mask = np.array([False, True, True, True, False])
        assert analyzer._voiced_runs(mask) == [(1, 4)]

    def test_run_touching_both_edges(self):
        mask = np.array([True, True, False, True])
        assert analyzer._voiced_runs(mask) == [(0, 2), (3, 4)]


# --- voice_summary / compare_voice / compare（純粋dict） ---

class TestVoiceSummary:
    def test_closure_labels(self):
        assert analyzer.voice_summary({"h1h2_db": 10.0})["closure"]["label"] == "breathy"
        assert analyzer.voice_summary({"h1h2_db": 0.5})["closure"]["label"] == "pressed"
        assert analyzer.voice_summary({"h1h2_db": 4.0})["closure"]["label"] == "balanced"

    def test_ring_and_support(self):
        out = analyzer.voice_summary({"singers_formant_ratio": 0.01, "long_tone_stability": 10.0})
        assert out["ring"]["label"] == "strong"
        assert out["support"]["label"] == "steady"


class TestCompareVoice:
    def test_ring_and_closure_verdicts(self):
        user = {"singers_formant_ratio": 0.002, "h1h2_db": 12.0}
        ref = {"singers_formant_ratio": 0.009, "h1h2_db": 4.0}
        out = analyzer.compare_voice(user, ref)
        assert out["ring"]["verdict"] == "weaker"        # 原曲より響きが弱い
        assert out["closure"]["verdict"] == "breathier"  # 原曲より息漏れ寄り

    def test_in_tune_passthrough_from_alignment(self):
        out = analyzer.compare_voice({}, {}, {"in_tune_score": 88, "pitch_error_cents": 20})
        assert out["in_tune"]["score"] == 88


class TestCompare:
    def test_key_match_and_semitone_diff(self):
        user = {"duration_sec": 20.0, "estimated_key": "C major", "f0_median_hz": 440.0,
                "tempo_bpm": 120.0, "voiced_ratio": 0.9, "rms_db_range": 12.0,
                "long_tone_stability": 20.0, "vibrato_rate_hz": None,
                "vibrato_depth_cents": None, "spectral_centroid_hz": 2000.0,
                "onset_rate_per_sec": 2.0}
        ref = dict(user, f0_median_hz=220.0, estimated_key="A minor")
        out = analyzer.compare(user, ref)
        assert out["key_match"] is False
        assert out["f0_median_diff_semitones"] == pytest.approx(12.0, abs=0.01)


class TestIsSameSource:
    def _base(self):
        return {"f0_median_hz": 220.0, "estimated_key": "C major", "tempo_bpm": 120.0,
                "voiced_ratio": 0.9, "spectral_centroid_hz": 2000.0}

    def test_identical_is_same(self):
        assert analyzer.is_same_source(self._base(), dict(self._base())) is True

    def test_different_key_not_same(self):
        assert analyzer.is_same_source(self._base(), dict(self._base(), estimated_key="D major")) is False

    def test_none_f0_not_same(self):
        assert analyzer.is_same_source(dict(self._base(), f0_median_hz=None), self._base()) is False


# --- パイプライン全体（合成サイン波 → 既知の基本周波数を取り戻す） ---

class TestAnalyzeFileSynthetic:
    def _write_sine(self, path, freq=220.0, dur=3.0):
        import soundfile as sf
        t = np.linspace(0, dur, int(analyzer.SR * dur), endpoint=False)
        # 倍音を少し足してpyinが安定して基本周波数を拾えるようにする。
        y = (0.6 * np.sin(2 * np.pi * freq * t)
             + 0.2 * np.sin(2 * np.pi * 2 * freq * t)).astype(np.float32)
        sf.write(str(path), y, analyzer.SR)

    def test_recovers_fundamental(self, tmp_path):
        p = tmp_path / "a220.wav"
        self._write_sine(p, freq=220.0)
        result = analyzer.analyze_file(p, light=True)
        # 220Hz ± 半音弱（pyinの量子化を許容）。
        assert result["f0_median_hz"] == pytest.approx(220.0, abs=8.0)
        assert 0.0 <= result["voiced_ratio"] <= 1.0
        assert result["duration_sec"] == pytest.approx(3.0, abs=0.2)

    def test_too_short_raises(self, tmp_path):
        import soundfile as sf
        p = tmp_path / "tiny.wav"
        sf.write(str(p), np.zeros(int(analyzer.SR * 0.1), dtype=np.float32), analyzer.SR)
        with pytest.raises(ValueError):
            analyzer.analyze_file(p, light=True)
