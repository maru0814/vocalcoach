"""採点ロジック（app/coaching/scoring.py）のユニットテスト。

純粋関数（dict in / int out）なのでDB・ネットワーク・音声ファイル不要。
docs/04・docs/21 の閾値表に対応する境界値を中心に検証する。
"""
from app.coaching import scoring


# --- pitch_score（ジッター帯域・原曲比較・オクターブ除外） ---

class TestPitchScore:
    def test_jitter_bands(self):
        assert scoring.pitch_score({"f0_jitter_cents": 3.0}, None) == 95
        assert scoring.pitch_score({"f0_jitter_cents": 10.0}, None) == 85
        assert scoring.pitch_score({"f0_jitter_cents": 25.0}, None) == 70
        assert scoring.pitch_score({"f0_jitter_cents": 40.0}, None) == 50

    def test_jitter_band_boundaries(self):
        # 境界はその帯域に含まれる（<=）。
        assert scoring.pitch_score({"f0_jitter_cents": 5.0}, None) == 95
        assert scoring.pitch_score({"f0_jitter_cents": 15.0}, None) == 85
        assert scoring.pitch_score({"f0_jitter_cents": 30.0}, None) == 70

    def test_missing_jitter_is_neutral(self):
        assert scoring.pitch_score({}, None) == 60

    def test_alignment_in_tune_dominates(self):
        # in_tune_score があれば 7:3 で主成分になる（base=95, in_tune=50 → 50*.7+95*.3=63.5→64）。
        a = {"f0_jitter_cents": 3.0}
        c = {"alignment": {"in_tune_score": 50}}
        assert scoring.pitch_score(a, c) == 64

    def test_semitone_diff_penalizes(self):
        # 半音差4 → base95 から min(15, (4-1)*5=15) 減点 = 80。
        a = {"f0_jitter_cents": 3.0}
        c = {"f0_median_diff_semitones": 4.0}
        assert scoring.pitch_score(a, c) == 80

    def test_octave_difference_ignored(self):
        # 12半音（オクターブずれ）は 10.5〜13.5 として無視され、減点されない。
        a = {"f0_jitter_cents": 3.0}
        c = {"f0_median_diff_semitones": 12.0}
        assert scoring.pitch_score(a, c) == 95


# --- rhythm_score（原曲なしは中立・tempo差・DTWラグ） ---

class TestRhythmScore:
    def test_no_reference_is_neutral(self):
        assert scoring.rhythm_score({}, None) == 80

    def test_tempo_diff_bands(self):
        assert scoring.rhythm_score({}, {"tempo_diff_bpm": 1.0}) == 88
        assert scoring.rhythm_score({}, {"tempo_diff_bpm": 5.0}) == 78
        assert scoring.rhythm_score({}, {"tempo_diff_bpm": 10.0}) == 68
        assert scoring.rhythm_score({}, {"tempo_diff_bpm": 30.0}) == 60

    def test_alignment_lag_adjusts(self):
        # base80 + 小ラグ加点 / 大ラグ減点。
        assert scoring.rhythm_score({}, {"alignment": {"mean_lag_sec": 0.05}}) == 85
        assert scoring.rhythm_score({}, {"alignment": {"mean_lag_sec": 0.5}}) == 70
        assert scoring.rhythm_score({}, {"alignment": {"mean_lag_sec": 0.3}}) == 75


# --- yokuyou_level（抑揚◎○△×・原曲基準） ---

class TestYokuyouLevel:
    def test_none_range_is_ok(self):
        assert scoring.yokuyou_level(None, None) == "ok"

    def test_no_reference_absolute_bands(self):
        assert scoring.yokuyou_level(20.0, None) == "good"
        assert scoring.yokuyou_level(10.0, None) == "ok"
        assert scoring.yokuyou_level(5.0, None) == "weak"

    def test_flat_reference_is_lenient(self):
        # 原曲が平坦(ref<12)なら抑揚控えめでも good 寄り。
        c = {"ref_rms_db_range": 8.0}
        assert scoring.yokuyou_level(7.0, c) == "good"   # rng >= ref-2
        assert scoring.yokuyou_level(3.0, c) == "ok"

    def test_dynamic_reference_gap_bands(self):
        # 原曲が抑揚あり(ref>=12)。gap = ref - rng で段階評価。
        c = {"ref_rms_db_range": 20.0}
        assert scoring.yokuyou_level(19.0, c) == "good"   # gap 1
        assert scoring.yokuyou_level(15.0, c) == "ok"     # gap 5
        assert scoring.yokuyou_level(10.0, c) == "weak"   # gap 10
        assert scoring.yokuyou_level(2.0, c) == "bad"     # gap 18


# --- voice 系（発声4軸） ---

class TestVoiceScores:
    def test_phonation_no_reference_balanced(self):
        # H1-H2 がバランス域(2〜6) → 84、響き加点なし。
        assert scoring.phonation_score({"h1h2_db": 4.0}, None) == 84

    def test_phonation_breathy_penalized(self):
        # H1-H2 > 12（顕著な息漏れ） → 60。
        assert scoring.phonation_score({"h1h2_db": 15.0}, None) == 60

    def test_phonation_singers_formant_bonus(self):
        # バランス84 + シンガーズフォルマント加点8 = 92。
        assert scoring.phonation_score({"h1h2_db": 4.0, "singers_formant_ratio": 0.01}, None) == 92

    def test_phonation_voice_compare_closure_mismatch(self):
        c = {"voice_compare": {"closure": {"verdict": "breathy"}}}
        assert scoring.phonation_score({}, c) == 72   # 84 - 12

    def test_registration_chest_when_ref_mix(self):
        c = {"voice_compare": {"register_high": {"verdict": "diff", "user": "chest", "ref": "mix"}}}
        assert scoring.registration_score({}, c) == 62

    def test_support_band(self):
        assert scoring.support_score({"long_tone_stability": 10.0}, None) == 90
        assert scoring.support_score({"long_tone_stability": 50.0}, None) == 58
        assert scoring.support_score({}, None) == 70


# --- 合成（重み付き合計とclamp） ---

class TestComposite:
    def test_compute_scores_keys_and_clamp(self):
        out = scoring.compute_scores({"f0_jitter_cents": 3.0}, None)
        assert set(out) == {"pitch_score", "rhythm_score", "expression_score", "total_score"}
        assert all(0 <= v <= 100 for v in out.values())

    def test_compute_scores_weighted_total(self):
        # pitch=95, rhythm=80(原曲なし), expression=? を実値で検算する。
        a = {"f0_jitter_cents": 3.0, "rms_db_range": 20.0}
        out = scoring.compute_scores(a, None)
        expected = round(out["pitch_score"] * 0.35
                         + out["rhythm_score"] * 0.30
                         + out["expression_score"] * 0.35)
        assert out["total_score"] == expected

    def test_voice_scores_keys(self):
        out = scoring.voice_scores({"f0_jitter_cents": 3.0}, None)
        assert set(out) == {
            "pitch_score", "phonation_score", "registration_score",
            "support_score", "total_score",
        }
        assert all(0 <= v <= 100 for v in out.values())
