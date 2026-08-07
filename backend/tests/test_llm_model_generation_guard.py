"""音声入力パスのモデル世代ガード（docs/92）の回帰テスト。

Gemini 3 系・`*-latest` エイリアスは `thinking_budget=0` を 400 INVALID_ARGUMENT で拒否し、
かつ thinking を切れないため思考トークンが `max_output_tokens` を食って本文が途切れる。
env の LLM_AUDIO_MODEL 差し替えだけで緊急復旧できるよう、危険な組み合わせを
コード側で安全側に寄せていることを検証する（実API は叩かない）。
"""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.coaching import llm


class TestSafeThinkingBudget:
    """thinking_budget=0 を許すのは Gemini 2.x 固定IDだけ。"""

    @pytest.mark.parametrize("model", ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"])
    def test_gemini25_keeps_thinking_off(self, model):
        """判定は _supports_thinking_budget（2.5 系のみ）に一本化している。"""
        assert llm._safe_thinking_budget(model, 0) == 0

    @pytest.mark.parametrize("model", [
        "gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest",
        "gemini-flash-lite-latest", "",
    ])
    def test_non_gemini2_is_bumped_to_minimum(self, model):
        """0 のまま投げると 400 になる世代は最小予算へ引き上げる。"""
        assert llm._safe_thinking_budget(model, 0) == llm._MIN_THINKING_BUDGET

    @pytest.mark.parametrize("model", ["gemini-2.5-flash", "gemini-3.6-flash"])
    def test_explicit_budget_is_never_overridden(self, model):
        """明示的に >0 を指定したらそのまま通す（分析ターンの 512 を壊さない）。"""
        assert llm._safe_thinking_budget(model, 512) == 512


class TestSafeMaxTokens:
    def test_thinking_off_keeps_requested_value(self):
        """2.5 系＋thinking無効なら、思考が枠を食わないので要求値のまま。"""
        assert llm._safe_max_tokens("gemini-2.5-flash", 0, 600) == 600

    def test_thinking_on_raises_floor(self):
        """思考が有効な世代では本文が切れないよう下限を確保する。"""
        assert llm._safe_max_tokens("gemini-3.6-flash", 128, 400) == llm._MIN_MAX_TOKENS_WITH_THINKING

    def test_larger_request_wins(self):
        """下限より大きい要求はそのまま尊重する。"""
        assert llm._safe_max_tokens("gemini-3.6-flash", 128, 2048) == 2048


class TestBlankEnvFallsBackToDefault:
    """docker-compose の `${VAR:-}` は未設定でも空文字を渡してくる（docs/92 §0）。

    空文字がそのまま入ると、文字列項目はコード既定を潰し、数値項目は
    ValidationError で起動そのものが失敗する。空文字＝未設定として扱うこと。
    """

    def test_blank_model_id_uses_code_default(self, monkeypatch):
        from app.core.config import Settings
        for var in ("LLM_MODEL", "LLM_CHAT_MODEL", "LLM_AUDIO_MODEL", "LLM_ANALYSIS_MODEL"):
            monkeypatch.setenv(var, "")
        s = Settings(_env_file=None)
        assert s.llm_model == "gemini-3.5-flash-lite"
        assert s.llm_chat_model == "gemini-3.5-flash"   # docs/93 で格上げ
        assert s.llm_audio_model == "gemini-2.5-flash"  # docs/92 §5.10 で差し戻し
        assert s.llm_analysis_model == "gemini-2.5-flash"

    def test_blank_numeric_does_not_crash_startup(self, monkeypatch):
        from app.core.config import Settings
        monkeypatch.setenv("LLM_AUDIO_THINKING_BUDGET", "")
        monkeypatch.setenv("LLM_AUDIO_MAX_TOKENS", "")
        s = Settings(_env_file=None)
        assert s.llm_audio_thinking_budget == 0
        assert s.llm_audio_max_tokens == 1024

    def test_real_value_still_wins(self, monkeypatch):
        """緊急時の env 差し替えが効くこと（これが効かないと載せ替え経路が死ぬ）。"""
        from app.core.config import Settings
        monkeypatch.setenv("LLM_AUDIO_MODEL", "gemini-3.6-flash")
        monkeypatch.setenv("LLM_AUDIO_THINKING_BUDGET", "128")
        s = Settings(_env_file=None)
        assert s.llm_audio_model == "gemini-3.6-flash"
        assert s.llm_audio_thinking_budget == 128


@pytest.fixture
def captured_config(monkeypatch):
    """genai.Client をモックし、generate_content に渡された config を捕まえる。"""
    from google import genai

    seen: dict = {}

    class _Resp:
        text = "高い音は裏声寄りのミックスに聞こえます。息の混じりがやわらかいですね。"

    class _Models:
        def generate_content(self, **kw):
            seen["model"] = kw["model"]
            seen["config"] = kw["config"]
            return _Resp()

    class _Client:
        def __init__(self, **kw):
            self.models = _Models()

    monkeypatch.setattr(genai, "Client", _Client)
    monkeypatch.setattr(settings, "gemini_api_key", "TEST_DUMMY_KEY")
    return seen


class TestAudioCallSitesRespectGuard:
    """実際の呼び出し2箇所が、モデル世代に応じた config を組むこと。"""

    @pytest.mark.parametrize("fn_name", ["classify_register_audio", "analyze_pronunciation"])
    def test_gemini3_gets_thinking_and_headroom(self, fn_name, captured_config, monkeypatch):
        monkeypatch.setattr(settings, "llm_audio_model", "gemini-3.6-flash")
        monkeypatch.setattr(settings, "llm_audio_thinking_budget", 0)

        assert getattr(llm, fn_name)(b"RIFFfake") is not None
        cfg = captured_config["config"]
        assert captured_config["model"] == "gemini-3.6-flash"
        # 0 のままだと本番で 400 になる
        assert cfg.thinking_config.thinking_budget == llm._MIN_THINKING_BUDGET
        # 思考が枠を食うので本文用の余白が要る
        assert cfg.max_output_tokens >= llm._MIN_MAX_TOKENS_WITH_THINKING

    @pytest.mark.parametrize("fn_name", ["classify_register_audio", "analyze_pronunciation"])
    def test_gemini25_keeps_thinking_disabled(self, fn_name, captured_config, monkeypatch):
        """既定の 2.5-flash では従来どおり thinking 無効のまま（挙動・コストを変えない）。"""
        monkeypatch.setattr(settings, "llm_audio_model", "gemini-2.5-flash")
        monkeypatch.setattr(settings, "llm_audio_thinking_budget", 0)

        assert getattr(llm, fn_name)(b"RIFFfake") is not None
        assert captured_config["config"].thinking_config.thinking_budget == 0


class TestChatThinkingOff:
    """会話パスの thinking 無効化（docs/93）。

    音声パスの _safe_thinking_budget（2.5 系のみ・docs/92 §5.6 の実測構成を維持）とは
    独立に、会話パスは tb=0 の受理を実測確認済みの固定IDだけ思考を切る（docs/92 §2-2）。
    """

    def test_chat_model_gemini35flash_disables_thinking(self):
        cfg = llm._thinking_off("gemini-3.5-flash")
        assert cfg is not None and cfg.thinking_budget == 0

    def test_gemini25_still_disables_thinking(self):
        cfg = llm._thinking_off("gemini-2.5-flash")
        assert cfg is not None and cfg.thinking_budget == 0

    @pytest.mark.parametrize("model", [
        "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-flash-latest", "", None,
    ])
    def test_unverified_models_leave_thinking_default(self, model):
        """tb=0 未実測のモデルには thinking_config を送らない（400 INVALID_ARGUMENT 回避）。"""
        assert llm._thinking_off(model) is None

    def test_audio_guard_unchanged_for_gemini35flash(self):
        """音声パスの実測済み構成（3.5-flash＋最小思考予算）を docs/93 が変えていないこと。"""
        assert llm._safe_thinking_budget("gemini-3.5-flash", 0) == llm._MIN_THINKING_BUDGET
