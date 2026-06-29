"""課題タクソノミー（app/coaching/taxonomy.py）の診断・達成・選定ロジックのテスト。

解析dictから、各課題の発火条件・達成条件・優先度つき選定・弱点列挙・換声点推定・
張りどころ判定を決定的に検証する（LLM・DB不要）。
"""
from app.coaching import taxonomy as tx


# --- 個別の diagnose / achieve しきい値 ---

class TestPitchWobble:
    def test_diag_fires_above_20(self):
        assert tx._diag_pitch_wobble({"f0_jitter_cents": 25.0}, None) is True
        assert tx._diag_pitch_wobble({"f0_jitter_cents": 15.0}, None) is False

    def test_achieve_at_or_below_15(self):
        assert tx._achieve_pitch_wobble({"f0_jitter_cents": 12.0}) is True
        assert tx._achieve_pitch_wobble({"f0_jitter_cents": 20.0}) is False


class TestBreathyClosure:
    def test_diag_h1h2_high(self):
        assert tx._diag_breathy_closure({"h1h2_db": 12.0}, None) is True
        assert tx._diag_breathy_closure({"h1h2_db": 5.0}, None) is False

    def test_diag_uses_compare_verdict(self):
        c = {"voice_compare": {"closure": {"verdict": "breathier"}}}
        # 比較があれば H1-H2 単体ではなく verdict を優先
        assert tx._diag_breathy_closure({"h1h2_db": 2.0}, c) is True

    def test_achieve_below_8(self):
        assert tx._achieve_breathy_closure({"h1h2_db": 5.0}) is True
        assert tx._achieve_breathy_closure({"h1h2_db": 9.0}) is False


class TestWeakResonance:
    def test_diag_low_singers_formant(self):
        assert tx._diag_weak_resonance({"singers_formant_ratio": 0.001}, None) is True
        assert tx._diag_weak_resonance({"singers_formant_ratio": 0.01}, None) is False

    def test_achieve_at_or_above_0004(self):
        assert tx._achieve_weak_resonance({"singers_formant_ratio": 0.004}) is True


class TestRefHasVibrato:
    def test_true_when_ref_vibrato_clear(self):
        assert tx._ref_has_vibrato({"ref_vibrato_rate_hz": 5.5, "ref_vibrato_depth_cents": 40}) is True

    def test_false_without_compare(self):
        assert tx._ref_has_vibrato(None) is False
        assert tx._ref_has_vibrato({"ref_vibrato_rate_hz": 2.0, "ref_vibrato_depth_cents": 40}) is False


# --- get_task / diagnose_task / list_weaknesses ---

class TestTaskSelection:
    def test_get_task_known_and_unknown(self):
        assert tx.get_task("pitch_wobble")["id"] == "pitch_wobble"
        assert tx.get_task("does_not_exist") is None

    def test_diagnose_task_picks_matching(self):
        # ジッターだけ高い → pitch_wobble が選ばれる（他は材料が無く発火しない）
        task = tx.diagnose_task({"f0_jitter_cents": 30.0}, None)
        assert task is not None and task["id"] == "pitch_wobble"

    def test_diagnose_task_respects_exclude(self):
        task = tx.diagnose_task({"f0_jitter_cents": 30.0}, None, exclude=["pitch_wobble"])
        assert task is None or task["id"] != "pitch_wobble"

    def test_diagnose_task_none_when_clean(self):
        assert tx.diagnose_task({"f0_jitter_cents": 5.0}, None) is None

    def test_list_weaknesses_multiple_with_axis(self):
        a = {"f0_jitter_cents": 30.0, "h1h2_db": 12.0}
        out = tx.list_weaknesses(a, None, limit=3)
        ids = {w["id"] for w in out}
        assert "pitch_wobble" in ids and "breathy_closure" in ids
        assert all("axis" in w and "reason" in w for w in out)

    def test_list_weaknesses_limit(self):
        a = {"f0_jitter_cents": 30.0, "h1h2_db": 12.0, "singers_formant_ratio": 0.001}
        assert len(tx.list_weaknesses(a, None, limit=1)) == 1


# --- _note_label ---

class TestNoteLabel:
    def test_a4(self):
        assert tx._note_label(440.0) == "A4"

    def test_none(self):
        assert tx._note_label(None) == "—"


# --- projection_point（張りどころ判定） ---

class TestProjectionPoint:
    def _analysis(self, vt="chest", f0_std=30.0):
        return {
            "timeline": {
                "sustained_segments": [
                    {"start_sec": 2.0, "end_sec": 3.0, "mean_f0_hz": 330.0,
                     "duration_sec": 1.0, "f0_std_cents": f0_std, "voice_type_estimate": vt},
                ],
                "per_window": [
                    {"t_sec": 0.0, "rms_db": -20.0, "voiced_ratio": 0.9},
                    {"t_sec": 1.0, "rms_db": -20.0, "voiced_ratio": 0.9},
                    {"t_sec": 2.0, "rms_db": -12.0, "voiced_ratio": 0.9},
                    {"t_sec": 3.0, "rms_db": -12.0, "voiced_ratio": 0.9},
                    {"t_sec": 4.0, "rms_db": -20.0, "voiced_ratio": 0.9},
                ],
            }
        }

    def test_projected_when_strong_stable_chest(self):
        pp = tx.projection_point(self._analysis())
        assert pp is not None and pp["projected"] is True

    def test_not_projected_when_head_voice(self):
        # 裏声に逃げている → projected False
        pp = tx.projection_point(self._analysis(vt="head"))
        assert pp is not None and pp["projected"] is False

    def test_none_without_high_segments(self):
        assert tx.projection_point({"timeline": {"sustained_segments": [], "per_window": []}}) is None


# --- passaggio_estimate（換声点推定） ---

class TestPassaggio:
    def test_detects_chest_to_head_boundary(self):
        a = {"timeline": {"sustained_segments": [
            {"mean_f0_hz": 200.0, "voice_type_estimate": "chest"},
            {"mean_f0_hz": 300.0, "voice_type_estimate": "chest"},
            {"mean_f0_hz": 420.0, "voice_type_estimate": "head"},
        ]}}
        pg = tx.passaggio_estimate(a)
        assert pg is not None and pg["from_hz"] == 300.0 and pg["to_hz"] == 420.0

    def test_none_with_too_few_segments(self):
        a = {"timeline": {"sustained_segments": [
            {"mean_f0_hz": 200.0, "voice_type_estimate": "chest"},
        ]}}
        assert tx.passaggio_estimate(a) is None
