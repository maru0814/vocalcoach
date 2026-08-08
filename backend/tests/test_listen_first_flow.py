"""聴いてから答えるフロー（docs/95, docs/97）のテスト。

①ブラインド聴取（listen_blind・第1段）と、②講評段への聴取事実注入
（blind / コメント申告）を LLM・ネットワーク非依存（hermetic）で検証する。

実行: cd backend && ./.venv/bin/python -m unittest tests.test_listen_first_flow -v
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402


def _fake_client(captured: dict, resp_text: str):
    """google.genai.Client のモック。渡ったテキストプロンプトを captured に記録する。"""

    class _Resp:
        text = resp_text

    class _Models:
        def generate_content(self, **kw):
            for content in kw.get("contents", []):
                for p in content.parts:
                    if getattr(p, "text", None):
                        captured["prompt"] = p.text
            captured["config"] = kw.get("config")
            return _Resp()

    class _Client:
        def __init__(self, **kw):
            self.models = _Models()

    return _Client


class BlindListen(unittest.TestCase):
    """FR-01: ブラインド聴取（第1段）。"""

    def _call(self, resp_text: str):
        from app.coaching import llm
        captured: dict = {}
        orig_key = settings.gemini_api_key
        settings.gemini_api_key = "TEST_DUMMY"
        try:
            with mock.patch("google.genai.Client", _fake_client(captured, resp_text)):
                result = llm.listen_blind(b"RIFFfake")
        finally:
            settings.gemini_api_key = orig_key
        return captured.get("prompt", ""), result

    def test_parses_wellformed_output(self):
        prompt, result = self._call(
            "KIND: practice\nPRACTICE: サイレン\nCONFIDENCE: high\n"
            "DESC: 低音から高音まで連続的に滑らかに上下している。"
        )
        self.assertEqual(result, {
            "kind": "practice", "practice": "サイレン", "confidence": "high",
            "desc": "低音から高音まで連続的に滑らかに上下している。",
        })

    def test_prompt_is_context_free(self):
        """AC-01: プロンプトに会話文脈（宿題・課題・履歴・コメント）が入らない。"""
        prompt, _ = self._call("KIND: song\nPRACTICE: 不明\nCONFIDENCE: mid\nDESC: 歌。")
        for banned in ("宿題", "課題", "勧めて", "レッスンでは"):
            self.assertNotIn(banned, prompt, f"ブラインド段に文脈語「{banned}」を入れない")
        self.assertIn("サイレン", prompt, "練習メニュー（語彙）は渡してよい")
        self.assertIn("先入観なし", prompt)

    def test_song_maps_practice_none(self):
        _, result = self._call("KIND: song\nPRACTICE: 不明\nCONFIDENCE: mid\nDESC: 歌。")
        self.assertEqual(result["kind"], "song")
        self.assertIsNone(result["practice"])

    def test_malformed_output_returns_none(self):
        _, result = self._call("よく分かりませんでした。")
        self.assertIsNone(result, "KIND が取れなければ None（従来フローに退化＝AC-04）")

    def test_client_error_returns_none(self):
        from app.coaching import llm

        class _Boom:
            def __init__(self, **kw):
                raise RuntimeError("api down")

        orig_key = settings.gemini_api_key
        settings.gemini_api_key = "TEST_DUMMY"
        try:
            with mock.patch("google.genai.Client", _Boom):
                self.assertIsNone(llm.listen_blind(b"RIFFfake"), "例外は None（AC-04）")
        finally:
            settings.gemini_api_key = orig_key

    def test_flag_off_skips_call(self):
        """AC-08: ENABLE_BLIND_LISTEN=false で第1段が完全に無効化される。"""
        from app.coaching import llm

        class _MustNotConstruct:
            def __init__(self, **kw):
                raise AssertionError("フラグOFF時にクライアントを作ってはいけない")

        orig_flag, orig_key = settings.enable_blind_listen, settings.gemini_api_key
        settings.enable_blind_listen, settings.gemini_api_key = False, "TEST_DUMMY"
        try:
            with mock.patch("google.genai.Client", _MustNotConstruct):
                self.assertIsNone(llm.listen_blind(b"RIFFfake"))
        finally:
            settings.enable_blind_listen, settings.gemini_api_key = orig_flag, orig_key


class FactsInjection(unittest.TestCase):
    """FR-02/03: 講評段（第2段）への聴取事実の注入。"""

    def _generate(self, ictx: dict, user_comment=None):
        from app.coaching import llm
        captured: dict = {}
        state = {"phase": "practice", "current_task": "weak_resonance",
                 "last_analysis": {"duration_sec": 5.0}, "baseline_analysis": None,
                 "song_ref_url": None, "song_ref_path": None}
        orig_flag, orig_key = settings.enable_zero_base_fb, settings.gemini_api_key
        settings.enable_zero_base_fb, settings.gemini_api_key = True, "TEST_DUMMY"
        try:
            with mock.patch(
                "google.genai.Client",
                _fake_client(captured, "INTENT: practice\n\nサイレン、いい滑らかさです。"),
            ):
                reply = llm.generate_feedback(
                    state, user_wav=b"RIFFfake", intent_ctx=ictx, user_comment=user_comment,
                )
        finally:
            settings.enable_zero_base_fb, settings.gemini_api_key = orig_flag, orig_key
        return captured.get("prompt", ""), reply

    def _base_ictx(self, **extra):
        return {"kind_hint": "song", "task_label": "響きを前に集める（芯・通り）",
                "practice_name": "ハミング → 母音（マスクに集める）", **extra}

    def test_blind_result_injected(self):
        """AC-02: ブラインド判定が講評プロンプトに注入される。"""
        prompt, reply = self._generate(self._base_ictx(blind={
            "kind": "practice", "practice": "サイレン", "confidence": "high",
            "desc": "低音から高音まで連続的に上下している。",
        }))
        self.assertIn("ブラインド聴取の判定", prompt)
        self.assertIn("サイレン（確信度 high）", prompt)
        self.assertIn("宿題・レッスン文脈からの想像より優先する", prompt)
        self.assertIsNotNone(reply)

    def test_comment_declaration_is_top_fact(self):
        """AC-03（(A)案）: コメントでの申告を最優先の事実として扱う指示が入る。"""
        prompt, _ = self._generate(self._base_ictx(), user_comment="サイレンやってみた")
        self.assertIn("「サイレンやってみた」", prompt)
        self.assertIn("最優先の事実として講評する", prompt)
        self.assertIn("決めつけずに正直に一言確認する", prompt)

    def test_no_comment_no_declaration_instruction(self):
        """コメントが無ければ申告優先の指示も出ない（不要な指示を増やさない）。"""
        prompt, _ = self._generate(self._base_ictx())
        self.assertNotIn("最優先の事実として講評する", prompt)

    def test_no_facts_keeps_docs52_flow(self):
        """AC-07: 申告・ブラインドが無ければ docs/52 のプロンプトのまま（回帰）。"""
        prompt, _ = self._generate(self._base_ictx())
        self.assertNotIn("ブラインド聴取の判定", prompt)
        self.assertIn("実演が勧めた基礎練と一致するとは限らない", prompt, "docs/52 AC-09 の第三分岐は維持")


if __name__ == "__main__":
    unittest.main(verbosity=2)
