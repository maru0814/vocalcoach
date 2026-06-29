"""FB組み立て（app/coaching/feedback_builder.py）の純粋ロジックテスト。

音名変換・ビブラートラベル・◎○△×レベル・採点表・リズム所見・音程ミス・
進捗(改善)判定・達成判定を、解析dictから決定的に検証する。
"""
from app.coaching import feedback_builder as fb


# --- _note_name / vibrato_label ---

class TestLabels:
    def test_note_name_a4(self):
        assert fb._note_name(440.0) == "A4"

    def test_note_name_none(self):
        assert fb._note_name(None) == "—"

    def test_vibrato_natural_range(self):
        assert "自然なビブラート" in fb.vibrato_label(5.5, 50.0)

    def test_vibrato_too_slow(self):
        assert "遅め" in fb.vibrato_label(2.0)

    def test_vibrato_none(self):
        assert fb.vibrato_label(None) == "検出なし"


# --- レベル判定 ---

class TestLevels:
    def test_lvl4(self):
        assert fb._lvl4(True, True, True) == "good"
        assert fb._lvl4(False, True, True) == "ok"
        assert fb._lvl4(False, False, True) == "weak"
        assert fb._lvl4(False, False, False) == "bad"

    def test_axis_level_bands(self):
        assert fb._axis_level(95) == "good"
        assert fb._axis_level(80) == "ok"
        assert fb._axis_level(65) == "weak"
        assert fb._axis_level(50) == "bad"


# --- build_analysis_table（◎○△×が付く） ---

class TestAnalysisTable:
    def test_pitch_stability_row_level(self):
        rows = fb.build_analysis_table({"f0_jitter_cents": 4.0}, None)
        pitch = next(r for r in rows if r["label"] == "音程の安定度")
        assert pitch["level"] == "good"   # <=6

    def test_missing_metric_is_ok(self):
        rows = fb.build_analysis_table({}, None)
        pitch = next(r for r in rows if r["label"] == "音程の安定度")
        assert pitch["value"] == "—" and pitch["level"] == "ok"

    def test_alignment_adds_intune_row(self):
        c = {"alignment": {"in_tune_score": 92, "pitch_error_cents": 15, "mean_lag_sec": 0.0}}
        rows = fb.build_analysis_table({"f0_jitter_cents": 4.0}, c)
        labels = {r["label"] for r in rows}
        assert "原曲との一致（音程）" in labels


# --- build_rhythm_note ---

class TestRhythmNote:
    def test_none_without_alignment(self):
        assert fb.build_rhythm_note(None) is None
        assert fb.build_rhythm_note({}) is None

    def test_lag_described_as_motari(self):
        note = fb.build_rhythm_note({"alignment": {"mean_lag_sec": 0.3}})
        assert "モタり" in note

    def test_lag_described_as_hashiri(self):
        note = fb.build_rhythm_note({"alignment": {"mean_lag_sec": -0.3}})
        assert "走り" in note


# --- build_pitch_mistakes ---

class TestPitchMistakes:
    def test_empty_without_alignment(self):
        assert fb.build_pitch_mistakes(None) == []

    def test_maps_spots_with_direction(self):
        c = {"alignment": {"pitch_off_spots": [
            {"user_sec": 3.0, "cents": 80, "direction": "sharp"},
            {"user_sec": 5.0, "cents": 70, "direction": "flat"},
        ]}}
        out = fb.build_pitch_mistakes(c)
        assert out[0]["dir_jp"] == "高め"
        assert out[1]["dir_jp"] == "低め"


# --- build_progress_payload（改善検出） ---

class TestProgressPayload:
    def test_improvement_detected(self):
        baseline = {"f0_jitter_cents": 30.0, "long_tone_stability": 50.0, "rms_db_range": 8.0}
        current = {"f0_jitter_cents": 10.0, "long_tone_stability": 20.0, "rms_db_range": 16.0}
        out = fb.build_progress_payload(baseline, current, None)
        assert out["improved"] is True
        assert out["praise"] is not None

    def test_no_improvement(self):
        baseline = {"f0_jitter_cents": 10.0, "long_tone_stability": 20.0, "rms_db_range": 16.0}
        current = {"f0_jitter_cents": 30.0, "long_tone_stability": 50.0, "rms_db_range": 8.0}
        out = fb.build_progress_payload(baseline, current, None)
        assert out["improved"] is False
        assert out["praise"] is None

    def test_next_task_label_passthrough(self):
        out = fb.build_progress_payload({}, {}, {"label": "ミックス"})
        assert out["next_task_label"] == "ミックス"


# --- build_judge_payload（達成判定） ---

class TestJudgePayload:
    def _task(self, achieved: bool):
        return {
            "id": "long_tone_decay", "label": "ロングトーン",
            "achieve_label": "5秒安定", "achieve": lambda a: achieved,
        }

    def test_pass(self):
        out = fb.build_judge_payload(self._task(True), {"f0_jitter_cents": 4.0})
        assert out["result"] == "pass"

    def test_retry(self):
        out = fb.build_judge_payload(self._task(False), {"f0_jitter_cents": 4.0})
        assert out["result"] == "retry"

    def test_achieve_exception_is_retry(self):
        bad = {"id": "x", "label": "y", "achieve_label": "z",
               "achieve": lambda a: 1 / 0}
        out = fb.build_judge_payload(bad, {})
        assert out["result"] == "retry"


# --- build_good_points（弱い録音でも必ず1つ返す） ---

class TestGoodPoints:
    def test_always_returns_something(self):
        assert len(fb.build_good_points({})) >= 1

    def test_stable_pitch_praised(self):
        pts = fb.build_good_points({"f0_jitter_cents": 8.0})
        assert any("音程" in p for p in pts)
