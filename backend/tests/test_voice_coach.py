"""発声診断ツリー＋声タイプ判定（app/coaching/voice_coach.py）のテスト。

資料3章の6ケース診断・処方RAGの抽出・3軸→8タイプの声タイプ判定・
LLM注入ブロックの組み立てを、解析dictから決定的に検証する。
"""
from app.coaching import voice_coach as vc


# --- diagnose（6ケース） ---

class TestDiagnose:
    def test_breathy_high_severity(self):
        # H1-H2 高 + CPP 低(<6) → 息漏れ・重要度 high
        issues = vc.diagnose({"h1h2_db": 10.0, "cpp_db": 5.0})
        breathy = next(i for i in issues if i["id"] == "breathy")
        assert breathy["severity"] == "high"

    def test_breathy_needs_low_cpp_or_hnr(self):
        # H1-H2 高でも CPP/HNR が良ければ息漏れと断定しない
        assert not any(i["id"] == "breathy"
                       for i in vc.diagnose({"h1h2_db": 10.0, "cpp_db": 14.0, "hnr_db": 18.0}))

    def test_pulled_chest_requires_strain(self):
        base = {"f0_median_hz": 130.0,
                "timeline": {"sustained_segments": [
                    {"mean_f0_hz": 400.0, "register": "chest"}]}}
        # 力みのサイン(jitter/shimmer上昇)が無ければ張り上げと断定しない
        assert not any(i["id"] == "pulled_chest" for i in vc.diagnose(base))
        # jitter が高ければ張り上げと判定
        strained = dict(base, jitter_pct=2.0)
        assert any(i["id"] == "pulled_chest" for i in vc.diagnose(strained))

    def test_lack_resonance(self):
        issues = vc.diagnose({"singers_formant_ratio": 0.001, "hnr_db": 16.0})
        assert any(i["id"] == "lack_resonance" for i in issues)

    def test_artificial_vibrato_slow(self):
        issues = vc.diagnose({"vibrato_rate_hz": 3.0, "vibrato_depth_cents": 20})
        assert any(i["id"] == "artificial_vibrato" for i in issues)

    def test_unstable_support(self):
        issues = vc.diagnose({"long_tone_stability": 50.0})
        assert any(i["id"] == "unstable_support" for i in issues)

    def test_mix_incoordination(self):
        a = {"timeline": {"sustained_segments": [
            {"mean_f0_hz": 200.0, "register": "chest", "register_confidence": "high"},
            {"mean_f0_hz": 400.0, "register": "head", "register_confidence": "high"},
        ]}}
        assert any(i["id"] == "mix_incoordination" for i in vc.diagnose(a))

    def test_sorted_by_severity(self):
        # high(unstable_support) と low(artificial_vibrato) が混在 → high が先頭
        a = {"long_tone_stability": 50.0, "vibrato_rate_hz": 3.0, "vibrato_depth_cents": 20}
        issues = vc.diagnose(a)
        assert issues[0]["severity"] == "high"

    def test_clean_returns_empty(self):
        assert vc.diagnose({"h1h2_db": 4.0, "cpp_db": 14.0, "hnr_db": 18.0}) == []


# --- prescriptions_for / primary_issue ---

class TestPrescriptions:
    def test_maps_issue_to_exercises(self):
        rx = vc.prescriptions_for(["breathy"])
        ids = {x["id"] for x in rx}
        assert ids == {"D3", "B3", "A1"}

    def test_dedup_and_cap(self):
        rx = vc.prescriptions_for(["pulled_chest", "mix_incoordination"])
        ids = [x["id"] for x in rx]
        assert len(ids) == len(set(ids))   # 重複なし
        assert len(ids) <= 5

    def test_unknown_issue_ignored(self):
        assert vc.prescriptions_for(["nonexistent"]) == []

    def test_primary_issue(self):
        assert vc.primary_issue([{"id": "x"}, {"id": "y"}]) == {"id": "x"}
        assert vc.primary_issue([]) is None


# --- classify_voice_type（3軸→8タイプ） ---

class TestClassifyVoiceType:
    def test_rock_voice(self):
        # 地声・パワフル・クリア
        a = {"h1h2_db": 2.0, "voice": {"register_high": {"register": "chest"}},
             "cpp_db": 12.0, "hnr_db": 18.0, "singers_formant_ratio": 0.01,
             "spectral_tilt_db_oct": -5.0}
        out = vc.classify_voice_type(a)
        assert out["id"] == "rock"
        assert out["axes"] == {"register": "chest", "power": "power", "color": "clear"}

    def test_moody_voice(self):
        # 裏声・エアリー・ディープ
        a = {"h1h2_db": 10.0, "voice": {"register_high": {"register": "head"}},
             "cpp_db": 4.0, "hnr_db": 8.0, "singers_formant_ratio": 0.001,
             "spectral_tilt_db_oct": -13.0}
        out = vc.classify_voice_type(a)
        assert out["id"] == "moody"

    def test_none_without_metrics(self):
        assert vc.classify_voice_type({"voiced_ratio": 0.9}) is None

    def test_near_flag_on_boundary(self):
        # 各指標が境界付近 → near=True を返す
        a = {"h1h2_db": 4.0, "cpp_db": 8.0, "hnr_db": 14.0,
             "singers_formant_ratio": 0.004, "spectral_tilt_db_oct": -9.0}
        out = vc.classify_voice_type(a)
        assert out["near"]["register"] is True


# --- build_llm_block ---

class TestBuildLlmBlock:
    def test_includes_detected_issue_and_rx(self):
        block = vc.build_llm_block({"h1h2_db": 10.0, "cpp_db": 5.0})
        assert "検知された発声課題" in block
        assert "処方候補" in block

    def test_no_issue_branch(self):
        block = vc.build_llm_block({"cpp_db": 14.0, "h1h2_db": 4.0, "hnr_db": 18.0})
        assert "大きな課題は検知されていない" in block

    def test_lists_measured_metrics(self):
        block = vc.build_llm_block({"cpp_db": 11.0, "h1h2_db": 4.0})
        assert "発声指標(実測)" in block
