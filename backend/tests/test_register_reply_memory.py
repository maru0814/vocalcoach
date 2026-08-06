"""声区判定の「逃げ道なしプロンプト」と前回判定メモリ（docs/92・運用者決定 2026-08-08）。

- プロンプトに「迷ったらミックスでOK」の逃げ道を書かない（無難な誤判定への収束を防ぐ）
- 毎回その場で実際に聴く（キャッシュしない）
- 前回の判定を覚えておき、変わる時は「変化」として触れる（黙って逆を言わない）
"""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.coaching import llm


@pytest.fixture
def captured(monkeypatch):
    """genai.Client をモックし、送られたプロンプト全文を捕まえる。"""
    from google import genai

    seen: dict = {}

    class _Resp:
        text = "高い音の箇所は裏声に聴こえます。息が多く混ざった軽い響きが特徴です。"

    class _Models:
        def generate_content(self, **kw):
            texts = []
            for c in kw["contents"]:
                for p in c.parts:
                    t = getattr(p, "text", None)
                    if t:
                        texts.append(t)
            seen["prompt"] = "\n".join(texts)
            return _Resp()

    class _Client:
        def __init__(self, **kw):
            self.models = _Models()

    monkeypatch.setattr(genai, "Client", _Client)
    monkeypatch.setattr(settings, "gemini_api_key", "TEST_DUMMY_KEY")
    return seen


class TestNoEscapeHatch:
    def test_prompt_does_not_offer_mix_as_default(self, captured):
        assert llm.classify_register_audio(b"RIFFfake") is not None
        p = captured["prompt"]
        # 逃げ道の文言が無い
        assert "断定しづらければ" not in p
        assert "と答えてOK" not in p
        # 迷った時の逃げ場としてのミックスも禁止のまま（docs/92 §5.5 の決定を維持）
        assert "無難な答えとして『ミックス』という言葉に逃げない" in p

    def test_prompt_defines_mix_as_muscular_coordination(self, captured):
        """ミックスの定義を「音色の混合」ではなく「TA→CTの滑らかな移行」として渡す。

        単一の音から声区を断定するのは機構的に不可能（つながりは音域移動時にしか
        現れない）。定義を誤ると、純ファルセットを「理想的なミックス」と褒める事故が起きる。
        docs/42 §4・docs/92 §5.7。
        """
        llm.classify_register_audio(b"RIFFfake")
        p = captured["prompt"]
        assert "「地声と裏声の音色を混ぜたもの」ではありません" in p
        assert "段差が出ない" in p
        assert "1つの音だけを切り取って" in p


class TestRangeHintGrounding:
    """音域移動の有無は DSP の実測を事実として渡す（耳では取り違えるため）。"""

    def test_moves_describes_transition_without_asserting(self, captured):
        """音域移動ありでも段差の有無は断定させない（docs/92 §5.8）。

        正解が「段差なし」と分かっているサイレンで、両モデルとも6回中2〜3回誤答した。
        誤断定は「できている人へのダメ出し」「つながっていない人への理想的です」の
        両方向に事故る。DSP検出が入るまでは観察の共有にとどめる。
        """
        llm.classify_register_audio(
            b"RIFFfake", range_hint={"moves": True, "text": "約2.5オクターブの移動を含む"})
        p = captured["prompt"]
        assert "音域移動が含まれます" in p
        assert "約2.5オクターブの移動を含む" in p  # 実測が本文に載る
        assert "断定しないでください" in p
        assert "『理想的な状態です』という褒めはしないこと" in p
        assert "この段差の判断を根拠にしては出さないでください" in p

    def test_single_register_refuses_to_judge_connection(self, captured):
        """単一音域では「つながっている＝理想的」と褒めさせない（純ファルセット誤認の防止）。"""
        llm.classify_register_audio(
            b"RIFFfake", range_hint={"moves": False, "text": "ほぼ単一の音域"})
        p = captured["prompt"]
        assert "この録音からは判定できません" in p
        assert "つながりを評価する言い方もしないこと" in p
        assert "サイレンのようにつなげた録音" in p

    def test_no_hint_is_conservative(self, captured):
        """実測が無い時は、つながりを断定させない安全側に倒す。"""
        llm.classify_register_audio(b"RIFFfake")
        p = captured["prompt"]
        assert "断定せず" in p


class TestBuildRangeHint:
    def test_detects_wide_movement(self):
        r = llm.build_range_hint({
            "f0_median_hz": 84.8,
            "timeline": {"sustained_segments": [{"mean_f0_hz": 486.4}, {"mean_f0_hz": 335.5}]}})
        assert r["moves"] is True
        assert r["octaves"] == pytest.approx(2.52, abs=0.05)
        assert "オクターブ" in r["text"]

    def test_single_register_is_not_movement(self):
        r = llm.build_range_hint({
            "f0_median_hz": 312.0,
            "timeline": {"sustained_segments": [{"mean_f0_hz": 330.0}]}})
        assert r["moves"] is False
        assert "含まない" in r["text"]

    def test_returns_none_without_enough_data(self):
        assert llm.build_range_hint(None) is None
        assert llm.build_range_hint({"f0_median_hz": 220.0}) is None  # 1点だけでは判定不能

    def test_siren_without_sustained_segments(self):
        """サイレンは伸ばし区間が0個。f0_low/high から音域移動を取れること（docs/92 §5.7）。

        つながり判定の本命入力がサイレンなので、ここで None になると機能が成立しない。
        """
        r = llm.build_range_hint({
            "f0_median_hz": 178.1, "f0_low_hz": 70.0, "f0_high_hz": 359.0,
            "timeline": {"sustained_segments": []}})
        assert r is not None
        assert r["moves"] is True
        assert r["octaves"] == pytest.approx(2.36, abs=0.05)

    def test_f0_range_takes_priority_over_segments(self):
        """f0_low/high があれば伸ばし区間より優先（区間は一部しか拾わないため）。"""
        r = llm.build_range_hint({
            "f0_median_hz": 200.0, "f0_low_hz": 100.0, "f0_high_hz": 400.0,
            "timeline": {"sustained_segments": [{"mean_f0_hz": 210.0}]}})
        assert r["low_hz"] == 100.0 and r["high_hz"] == 400.0


class TestPrevVerdictMemory:
    def test_no_prev_no_memory_block(self, captured):
        llm.classify_register_audio(b"RIFFfake")
        assert "前回" not in captured["prompt"]

    def test_same_recording_asks_to_relisten(self, captured):
        llm.classify_register_audio(
            b"RIFFfake",
            prev_verdict={"text": "高い音は裏声に聴こえます。", "same_recording": True})
        p = captured["prompt"]
        assert "同じ録音への再質問" in p
        assert "高い音は裏声に聴こえます。" in p
        # 聴き直しの指示があり、前回への追従は求めない
        assert "もう一度聴き直して" in p
        assert "前回に合わせる必要はありません" in p

    def test_different_take_mentions_change(self, captured):
        llm.classify_register_audio(
            b"RIFFfake",
            prev_verdict={"text": "前は地声でした。", "same_recording": False})
        p = captured["prompt"]
        assert "別テイク" in p
        assert "変化として自然に触れて" in p
        # 判定を曲げない安全弁
        assert "前回に引きずられて今回の判定を曲げない" in p

    def test_empty_prev_text_is_ignored(self, captured):
        llm.classify_register_audio(b"RIFFfake", prev_verdict={"text": "", "same_recording": True})
        assert "前回" not in captured["prompt"]
