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
        # 代わりに正直な判定の指示がある
        assert "聴こえたとおりに判定" in p
        assert "無難な答えとして『ミックス』を使わない" in p

    def test_uncertainty_instruction_is_honest(self, captured):
        llm.classify_register_audio(b"RIFFfake")
        assert "確信が持てない場合は無理に断定せず" in captured["prompt"]


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
