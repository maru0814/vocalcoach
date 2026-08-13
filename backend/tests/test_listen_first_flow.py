"""聴いてから答えるフロー（docs/95, docs/99）のテスト。

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

    def test_double_failure_returns_none_with_logs(self):
        """AC-04/10: 2回とも失敗なら None。失敗は無言にせず必ずログに残る。"""
        from app.coaching import llm

        calls = {"n": 0}

        class _Boom:
            def __init__(self, **kw):
                calls["n"] += 1
                raise RuntimeError("api down")

        orig_key = settings.gemini_api_key
        settings.gemini_api_key = "TEST_DUMMY"
        try:
            with mock.patch("google.genai.Client", _Boom):
                with self.assertLogs("app.coaching.llm", level="WARNING") as lg:
                    self.assertIsNone(llm.listen_blind(b"RIFFfake"))
        finally:
            settings.gemini_api_key = orig_key
        self.assertEqual(calls["n"], 2, "1回リトライして計2試行")
        self.assertTrue(any("2回とも失敗" in m for m in lg.output))

    def test_retry_succeeds_on_second_attempt(self):
        """AC-09: 1試行目が一時失敗しても、リトライで成功すれば判定が返る。"""
        from app.coaching import llm

        calls = {"n": 0}

        class _Models:
            def generate_content(self, **kw):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise RuntimeError("transient 503")

                class _R:
                    text = "KIND: practice\nPRACTICE: サイレン\nCONFIDENCE: high\nDESC: 滑らかな上下。"
                return _R()

        class _Client:
            def __init__(self, **kw):
                self.models = _Models()

        orig_key = settings.gemini_api_key
        settings.gemini_api_key = "TEST_DUMMY"
        try:
            with mock.patch("google.genai.Client", _Client):
                with self.assertLogs("app.coaching.llm", level="INFO") as lg:
                    r = llm.listen_blind(b"RIFFfake")
        finally:
            settings.gemini_api_key = orig_key
        self.assertIsNotNone(r)
        self.assertEqual(r["practice"], "サイレン")
        self.assertEqual(calls["n"], 2)
        self.assertTrue(any("リトライ" in m for m in lg.output), "失敗→リトライがログに残る")
        self.assertTrue(any("判定=practice" in m for m in lg.output), "成功時の判定内容もログに残る")

    def test_success_logs_result(self):
        """AC-10: 成功時も判定内容がログに残る（効いた回を後から確認できる）。"""
        from app.coaching import llm
        captured: dict = {}
        orig_key = settings.gemini_api_key
        settings.gemini_api_key = "TEST_DUMMY"
        try:
            with mock.patch(
                "google.genai.Client",
                _fake_client(captured, "KIND: song\nPRACTICE: 不明\nCONFIDENCE: mid\nDESC: 歌。"),
            ):
                with self.assertLogs("app.coaching.llm", level="INFO") as lg:
                    llm.listen_blind(b"RIFFfake")
        finally:
            settings.gemini_api_key = orig_key
        self.assertTrue(any("判定=song" in m for m in lg.output))

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

    def test_forced_practice_removes_song_branch(self):
        """AC-12: forced_intent=practice では歌/練習の二択を出さず、練習名断定禁止の注意が入る。"""
        prompt, _ = self._generate(self._base_ictx(
            forced_intent="practice",
            blind={"kind": "practice", "practice": "リップロール",
                   "confidence": "high", "desc": "音程が滑らかに上下している。"},
        ))
        self.assertIn("発声練習の実演（確定）", prompt)
        self.assertNotIn("(a)曲・歌の録音", prompt, "歌の選択肢を出さない")
        self.assertIn("練習名はあくまで推定", prompt)
        self.assertIn("聴こえた動きの描写で語るか、一言確認する", prompt)

    def test_forced_practice_pins_heard_even_if_model_says_song(self):
        """AC-13: モデルが INTENT: song を返しても heard は practice に固定される。"""
        from app.coaching import llm
        captured: dict = {}
        state = {"phase": "practice", "current_task": "weak_resonance",
                 "last_analysis": {"duration_sec": 5.0}, "baseline_analysis": None,
                 "song_ref_url": None, "song_ref_path": None}
        ictx = self._base_ictx(
            forced_intent="practice",
            blind={"kind": "practice", "practice": "サイレン", "confidence": "high", "desc": None},
        )
        orig_flag, orig_key = settings.enable_zero_base_fb, settings.gemini_api_key
        settings.enable_zero_base_fb, settings.gemini_api_key = True, "TEST_DUMMY"
        try:
            with mock.patch(
                "google.genai.Client",
                _fake_client(captured, "INTENT: song\n\n歌の講評です。"),
            ):
                with self.assertLogs("app.coaching.llm", level="WARNING") as lg:
                    reply = llm.generate_feedback(state, user_wav=b"RIFFfake", intent_ctx=ictx)
        finally:
            settings.enable_zero_base_fb, settings.gemini_api_key = orig_flag, orig_key
        self.assertIsNotNone(reply)
        self.assertEqual(ictx.get("heard"), "practice", "songタグは無視してpracticeに固定")
        self.assertTrue(any("INTENT: song を返した" in m for m in lg.output))

    def test_no_facts_keeps_docs52_flow(self):
        """AC-07: 申告・ブラインドが無ければ docs/52 のプロンプトのまま（回帰）。"""
        prompt, _ = self._generate(self._base_ictx())
        self.assertNotIn("ブラインド聴取の判定", prompt)
        self.assertIn("実演が勧めた基礎練と一致するとは限らない", prompt, "docs/52 AC-09 の第三分岐は維持")


if __name__ == "__main__":
    unittest.main(verbosity=2)
