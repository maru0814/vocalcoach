"""LLM モデル設定の回帰テスト（docs/91）。

守るもの（過去に本番を落とした3つ）:
  原因1 "-latest" エイリアス: 世代が切り替わり thinking_budget=0 が 400 になって会話が全滅した。
  原因2 thinking_budget の誤指定: 3系に thinking_budget=0 を送ると 400。2.5系に送らないと
        thinking が出力枠(400トークン)を食い潰し finish=MAX_TOKENS で本文が空になる。
  原因3 固定IDの退役: gemini-2.5-flash-lite が 404 "no longer available" になり、
        チャットが黙ってルールベースに落ち続けた。warning に埋もれて誰も気付けなかった。

ネットワーク不要（生存確認だけは RUN_LLM_LIVE=1 のときに実際に叩く）。
実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_llm_model_config -v
    RUN_LLM_LIVE=1 ./.venv/bin/python -m unittest tests.test_llm_model_config -v
"""
import logging
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coaching import llm  # noqa: E402
from app.core.config import Settings  # noqa: E402

# env による上書きを排除した「コードの既定値」を検査対象にする
# （実行環境の .env に LLM_MODEL があってもテストの意味が変わらないように）
DEFAULTS = Settings.model_fields
MODEL_FIELDS = ["llm_model", "llm_chat_model", "llm_audio_model", "llm_analysis_model"]


def default_of(field: str) -> str:
    return DEFAULTS[field].default


class TestNoLatestAlias(unittest.TestCase):
    """原因1: "-latest" エイリアスを既定値に置かない。"""

    def test_defaults_are_pinned_versions(self):
        for f in MODEL_FIELDS:
            with self.subTest(field=f):
                self.assertNotIn(
                    "-latest", default_of(f),
                    f"{f} が '-latest' エイリアス。世代切替で壊れる（docs/91 原因1）。"
                    "バージョン固定IDを使うこと",
                )

    def test_defaults_are_not_retired_models(self):
        """原因3: 退役が確認済みのモデルIDを既定に戻さない。"""
        retired = {"gemini-2.5-flash-lite"}  # 2026-08-06 に 404 を実測
        for f in MODEL_FIELDS:
            with self.subTest(field=f):
                self.assertNotIn(
                    default_of(f), retired,
                    f"{f} が退役済みモデル。全リクエストが 404 でフォールバックする",
                )


class TestThinkingConfig(unittest.TestCase):
    """原因2: thinking_budget を受け付けるモデルにだけ渡す。"""

    def test_supports_only_gemini_25(self):
        for model, expected in [
            ("gemini-2.5-flash", True),
            ("gemini-2.5-flash-lite", True),
            ("gemini-3.5-flash-lite", False),   # 実測: thinking_budget=0 は 400
            ("gemini-3.6-flash", False),
            ("gemini-3.1-flash-lite", False),
            ("gemini-flash-lite-latest", False),
            (None, False),
        ]:
            with self.subTest(model=model):
                self.assertEqual(llm._supports_thinking_budget(model), expected)

    def test_version_is_matched_not_substring(self):
        """"2.5" の部分文字列一致で誤判定しないこと（例: gemini-3.5 は 2.5 ではない）。"""
        self.assertFalse(llm._supports_thinking_budget("gemini-3.5-flash-lite"))
        self.assertFalse(llm._supports_thinking_budget("gemini-12.5-flash"))

    def test_thinking_off_returns_none_for_non_25(self):
        self.assertIsNone(llm._thinking_off("gemini-3.5-flash-lite"))
        cfg = llm._thinking_off("gemini-2.5-flash")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.thinking_budget, 0)

    def test_configured_chat_model_gets_no_thinking_budget(self):
        """既定のチャットモデルに thinking_config を送らない（送ると 400 で全滅する）。"""
        self.assertIsNone(llm._thinking_off(default_of("llm_chat_model")))


class TestFailureIsLoud(unittest.TestCase):
    """原因3の再発防止: 設定不備の失敗は warning に埋もれさせず ERROR で鳴らす。"""

    def test_retired_model_logs_error_with_marker(self):
        exc = Exception(
            "404 NOT_FOUND. {'error': {'message': 'This model models/gemini-2.5-flash-lite "
            "is no longer available.'}}"
        )
        with self.assertLogs(llm.logger, level=logging.ERROR) as cm:
            llm._log_llm_failure("テスト", "gemini-2.5-flash-lite", exc)
        self.assertIn(llm.LLM_CONFIG_FAULT_MARKER, "\n".join(cm.output))

    def test_invalid_argument_logs_error(self):
        exc = Exception("400 INVALID_ARGUMENT. Request contains an invalid argument.")
        with self.assertLogs(llm.logger, level=logging.ERROR) as cm:
            llm._log_llm_failure("テスト", "gemini-3.6-flash", exc)
        self.assertIn(llm.LLM_CONFIG_FAULT_MARKER, "\n".join(cm.output))

    def test_transient_failure_stays_warning(self):
        """一過性（503・タイムアウト）は ERROR に昇格させない（アラート疲れ防止）。"""
        exc = Exception("503 UNAVAILABLE. The model is overloaded.")
        with self.assertLogs(llm.logger, level=logging.WARNING) as cm:
            llm._log_llm_failure("テスト", "gemini-2.5-flash", exc)
        joined = "\n".join(cm.output)
        self.assertNotIn(llm.LLM_CONFIG_FAULT_MARKER, joined)
        self.assertNotIn("ERROR", joined)


@unittest.skipUnless(
    os.getenv("RUN_LLM_LIVE") == "1" and os.getenv("GEMINI_API_KEY"),
    "実 API を叩くため既定でスキップ（RUN_LLM_LIVE=1 かつ GEMINI_API_KEY で有効化）",
)
class TestModelsAreAlive(unittest.TestCase):
    """設定中のモデルが今も実在するか。退役を検出できる唯一のテスト。

    モックでは絶対に落ちないので、デプロイ前・定期実行で回す想定
    （同等の確認は scripts/ops/check_llm_models.py）。
    """

    def test_all_configured_models_respond(self):
        from app.core.config import settings
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        for f in MODEL_FIELDS:
            model = getattr(settings, f)
            with self.subTest(field=f, model=model):
                resp = client.models.generate_content(
                    model=model, contents="「OK」とだけ返して。",
                    config=types.GenerateContentConfig(
                        max_output_tokens=settings.llm_max_tokens,
                        thinking_config=llm._thinking_off(model),
                    ),
                )
                self.assertTrue(
                    (resp.text or "").strip(),
                    f"{f}={model} が本文を返さない（退役 or 出力枠不足）",
                )


if __name__ == "__main__":
    unittest.main()
