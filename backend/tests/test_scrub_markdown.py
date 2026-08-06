"""Markdown記法の除去（docs/42 §2）の回帰テスト。

フロントの吹き出しは素テキスト描画（Bubbles.tsx の whitespace-pre-wrap）なので、
`**リップロール**` と書かれると記号がそのまま画面に出る。プロンプトで禁じても漏れる
（実測: 現行モデルで6回中2回混入。docs/92 §4-1）ため、返す直前に機械的に落とす。
"""

from __future__ import annotations

import pytest

from app.coaching.llm import scrub_markdown


class TestStripsDecoration:
    def test_bold_keeps_inner_text(self):
        assert scrub_markdown("まずは**リップロール**を試してみましょう") \
            == "まずはリップロールを試してみましょう"

    def test_underscore_bold(self):
        assert scrub_markdown("__ネイネイ__で軽く当てる") == "ネイネイで軽く当てる"

    def test_italic(self):
        assert scrub_markdown("*やさしく*息を流す") == "やさしく息を流す"

    def test_heading_marker_removed(self):
        assert scrub_markdown("## 今日のポイント\n喉を開きましょう") \
            == "今日のポイント\n喉を開きましょう"

    def test_bullets_removed(self):
        assert scrub_markdown("- ひとつ目\n- ふたつ目") == "ひとつ目\nふたつ目"

    def test_multiple_bold_in_one_line(self):
        assert scrub_markdown("**支え**と**閉じ**の両方") == "支えと閉じの両方"


class TestLeavesNormalTextAlone:
    def test_plain_japanese_untouched(self):
        s = "高い音がとてもきれいに響いていますね。7秒あたりの伸ばしが特に良かったです。"
        assert scrub_markdown(s) == s

    def test_url_is_not_mangled(self):
        s = "参考はこちら https://www.youtube.com/watch?v=abc_def-123"
        assert scrub_markdown(s) == s

    def test_hyphen_inside_sentence_survives(self):
        """行頭でないハイフンは箇条書きではないので残す。"""
        s = "H1-H2 は声帯の閉じ具合の目安です"
        assert scrub_markdown(s) == s

    def test_lone_asterisk_survives(self):
        """対になっていない記号は消さない（誤爆で本文を壊さない）。"""
        s = "3*4 の練習を繰り返します"
        assert scrub_markdown(s) == s

    @pytest.mark.parametrize("value", [None, ""])
    def test_empty_passthrough(self, value):
        assert scrub_markdown(value) == value

    def test_bold_spanning_newline_is_not_matched(self):
        """改行をまたぐ誤マッチで本文を破壊しないこと。"""
        s = "ここが**大事\nです**ね"
        assert scrub_markdown(s) == s


class TestAppliedAtReturnPaths:
    """実際の返却経路で効いていること（プロンプト任せにしない）。"""

    def test_generate_feedback_strips_bold(self, monkeypatch, tmp_path):
        from app.core.config import settings
        from app.coaching import llm
        from google import genai

        monkeypatch.setattr(settings, "llm_cost_ledger_path", str(tmp_path / "l.json"))
        monkeypatch.setattr(settings, "enable_zero_base_fb", True)
        monkeypatch.setattr(settings, "gemini_api_key", "TEST_DUMMY_KEY")

        class _Resp:
            text = "いい響きですね。まずは**リップロール**を試しましょう。"

        class _Models:
            def generate_content(self, **kw):
                return _Resp()

        class _Client:
            def __init__(self, **kw):
                self.models = _Models()

        monkeypatch.setattr(genai, "Client", _Client)
        reply = llm.generate_feedback({"phase": "feedback"}, user_wav=b"RIFFfake")
        assert reply is not None
        assert "**" not in reply
        assert "リップロール" in reply
