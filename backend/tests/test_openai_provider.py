"""チャット経路の他社バックエンド（OpenAI）対応のテスト（docs/103 Stage 2a）。

実APIは叩かない。検証するのは以下の4点:
  1. プロバイダ判別がモデルIDだけで決まること
  2. 既定値のままなら従来どおり Gemini に行くこと（実装を入れただけで挙動が変わらない）
  3. ツール宣言が両社で同一の中身を共有すること（FB品質の分岐を作らない）
  4. Gemini 経路の事後保証（URL到達・原曲確認アンカー）が共通コードとして動くこと
"""
import unittest
from unittest import mock

from app.coaching import llm, tools as coach_tools
from app.core.config import settings


class ChatProviderRouting(unittest.TestCase):
    def test_openai_models_route_to_openai(self):
        for mid in ["gpt-5.6-terra", "gpt-5.6-sol", "GPT-5.6-LUNA", "o3-mini"]:
            self.assertEqual(llm._chat_provider(mid), "openai", mid)

    def test_gemini_and_unknown_models_route_to_gemini(self):
        # 既定・空・未知はすべて Gemini（安全側に倒す）
        for mid in ["gemini-3.5-flash", "gemini-2.5-flash", "", None, "claude-sonnet-5"]:
            self.assertEqual(llm._chat_provider(mid), "gemini", str(mid))

    def test_default_config_still_uses_gemini(self):
        """既定値のままなら他社に行かない（docs/103: 実装だけでは本番挙動が変わらない）。"""
        self.assertEqual(llm._chat_provider(settings.llm_chat_model), "gemini")
        self.assertEqual(llm._chat_provider(settings.llm_model), "gemini")

    def test_openai_path_without_key_falls_back(self):
        """キー未設定なら None を返して呼び出し側のフォールバックに落ちる。"""
        with mock.patch.object(settings, "openai_api_key", None):
            self.assertIsNone(llm._openai_client())
            self.assertIsNone(llm._complete_openai([], model="gpt-5.6-terra"))


class ToolDeclSharing(unittest.TestCase):
    def test_openai_wrapper_preserves_declaration(self):
        """包み方だけ変わり、名前・説明・スキーマは1文字も変えない。"""
        decl = coach_tools.SEARCH_ORIGINAL_SONG_DECL
        wrapped = coach_tools.to_openai_tool(decl)
        self.assertEqual(wrapped["type"], "function")
        self.assertEqual(wrapped["name"], decl["name"])
        self.assertEqual(wrapped["description"], decl["description"])
        self.assertEqual(wrapped["parameters"], decl["parameters"])

    def test_shape_is_flat_not_nested(self):
        """Responses API は平坦形（入れ子だと 400 でツールが全滅する。実測）。"""
        w = coach_tools.to_openai_tool(coach_tools.FIND_REFERENCE_VIDEO_DECL)
        self.assertNotIn("function", w)
        self.assertIn("name", w)

    def test_wrapper_does_not_mutate_source(self):
        decl = dict(coach_tools.FIND_REFERENCE_VIDEO_DECL)
        coach_tools.to_openai_tool(coach_tools.FIND_REFERENCE_VIDEO_DECL)["name"] = "x"
        self.assertEqual(coach_tools.FIND_REFERENCE_VIDEO_DECL, decl)

    def test_all_context_tools_convertible(self):
        for name, decl in coach_tools.CONTEXT_TOOL_DECLS.items():
            self.assertEqual(coach_tools.to_openai_tool(decl)["name"], decl["name"], name)


class MessageConversion(unittest.TestCase):
    class _P:
        def __init__(self, text): self.text = text

    class _C:
        def __init__(self, role, text):
            self.role = role
            self.parts = [MessageConversion._P(text)]

    def test_roles_are_mapped(self):
        """model→assistant に写り、順序が保たれる。人格は input ではなく instructions で渡す。"""
        contents = [self._C("user", "こんにちは"), self._C("model", "こんにちは！"),
                    self._C("user", "高い声のコツは？")]
        msgs = llm._contents_to_openai(contents)
        self.assertEqual([m["role"] for m in msgs], ["user", "assistant", "user"])
        self.assertEqual(msgs[-1]["content"], "高い声のコツは？")

    def test_empty_parts_are_skipped(self):
        self.assertEqual(llm._contents_to_openai([self._C("user", "   ")]), [])


class SharedToolPostProcessing(unittest.TestCase):
    """事後保証は共通コード。プロバイダを問わず同じ結果になること。"""

    def test_video_url_appended_when_missing(self):
        acc = llm._new_tool_acc()
        acc["found_video_url"] = "https://youtu.be/abc"
        out = llm._finalize_tool_reply("リップロールをやってみましょう。", acc)
        self.assertIn("https://youtu.be/abc", out)

    def test_video_url_not_duplicated(self):
        acc = llm._new_tool_acc()
        acc["found_video_url"] = "https://youtu.be/abc"
        out = llm._finalize_tool_reply("こちらです https://youtu.be/abc", acc)
        self.assertEqual(out.count("https://youtu.be/abc"), 1)

    def test_song_confirm_anchor_appended(self):
        acc = llm._new_tool_acc()
        acc["song_candidate"] = {"title": "ツキミソウ", "url": "https://youtu.be/xyz",
                                 "channel": "Novelbright"}
        out = llm._finalize_tool_reply("原曲を探しました。", acc)
        self.assertIn(llm.SONG_CONFIRM_ANCHOR, out)
        self.assertIn("https://youtu.be/xyz", out)

    def test_exec_tool_collects_urls_and_facts(self):
        acc = llm._new_tool_acc()
        sink = []
        ctx = {"listen_register": lambda a: {"found": True, "video_url": "https://youtu.be/v"}}
        result = llm._exec_tool("listen_register", {}, ctx, sink, acc)
        self.assertTrue(result["found"])
        self.assertIn("https://youtu.be/v", acc["tool_urls"])
        self.assertEqual(acc["found_video_url"], "https://youtu.be/v")
        self.assertEqual(len(sink), 1)

    def test_exec_tool_reports_failure_honestly(self):
        """文脈ツールが例外を投げても落とさず、正直に伝える指示を返す（docs/95 FR-05）。"""
        acc = llm._new_tool_acc()

        def _boom(_args):
            raise RuntimeError("boom")

        result = llm._exec_tool("listen_register", {}, {"listen_register": _boom}, None, acc)
        self.assertFalse(result["ok"])
        self.assertIn("正直", result["error"])


if __name__ == "__main__":
    unittest.main()
