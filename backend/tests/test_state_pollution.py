"""雑談がレッスン状態を汚さないことの検査（docs/94 会話憲法）。

2026-08-07 の監査で、雑談・質問・否定文が focus_task / ref_range を黙って
書き換える事故を実証した（「昨日カラオケで90〜95点出た！」→ ref_range=90〜95、
「息継ぎのコツってあります？」→ focus_task=long_tone_decay 等）。
状態の書き換えは「誤読しようがない形式」（URL・時刻区間・秒明示区間）と
モデルの文脈判断（set_lesson_focus ツール）だけに限る。その回帰ガード。
"""
from app.coaching import llm, rule_engine, tools


class TestParsePhaseAPollution:
    """parse_phase_a は形式が一意なものだけ拾う。"""

    def test_casual_chat_does_not_mutate_state(self):
        for t in [
            "昨日カラオケで90〜95点出た！",          # 数字レンジの雑談（旧: ref_range汚染）
            "息継ぎのコツってあります？",             # ただの質問（旧: focus_task汚染）
            "喉が痛いわけじゃないんだけど",            # 否定文（旧: focus_task汚染）
            "リズムは得意なんだけど、高音がなあ",       # 得意分野の言及（旧: focus_task汚染）
            "3〜4回くらい練習した",                  # 回数の雑談
            "10〜20代に人気の曲らしい",              # 年代の雑談
        ]:
            assert rule_engine.parse_phase_a(t, {}) == {}, t

    def test_unambiguous_forms_are_still_parsed(self):
        # 時刻形式の区間
        u = rule_engine.parse_phase_a("サビは1:05〜1:20あたりです", {})
        assert u.get("ref_range") == "1:05〜1:20"
        # 秒明示の区間
        u = rule_engine.parse_phase_a("30〜45秒のところを歌いました", {})
        assert u.get("ref_range") == "30〜45"
        # URL
        u = rule_engine.parse_phase_a("https://www.youtube.com/watch?v=abc123 です", {})
        assert "song_ref_url" in u

    def test_focus_keyword_extraction_is_removed(self):
        """主訴のキーワード抽出（旧FOCUS_KEYWORDS）は撤去済み。復活させない。

        主訴の記録はモデルの文脈判断（set_lesson_focus ツール）が行う。
        """
        assert not hasattr(rule_engine, "FOCUS_KEYWORDS")


class TestSpecialPathRoutingRemoved:
    """正規表現ルーティング（声区・発音）は撤去済み。復活させない（docs/94）。

    「母音って何？」が発音分析へ、「裏声好きなんですけど変ですか？」が
    声区判定へ飛ぶ誤爆を実証したため。録音を聴くかはモデルが判断する。
    """

    def test_register_and_pronunciation_detectors_removed(self):
        for name in ("is_register_question", "is_pronunciation_request",
                     "PRONUNCIATION_KW", "_REGISTER_TERMS"):
            assert not hasattr(rule_engine, name), f"{name} は docs/94 で撤去済み"

    def test_context_tool_declarations_exist(self):
        # 置換先のセッション文脈ツール宣言が揃っている
        assert set(tools.CONTEXT_TOOL_DECLS) == {
            "listen_register", "listen_pronunciation",
            "rediagnose_with_reference", "set_lesson_focus",
        }
        for name, decl in tools.CONTEXT_TOOL_DECLS.items():
            assert decl["name"] == name


class TestContextToolWiring:
    """tool_ctx が generate_reply → _complete_with_tools に配線されている。"""

    def test_handle_text_accepts_tool_ctx(self):
        import inspect
        assert "tool_ctx" in inspect.signature(rule_engine.handle_text).parameters
        assert "tool_ctx" in inspect.signature(llm.generate_reply).parameters
        params = inspect.signature(llm._complete_with_tools).parameters
        assert "tool_ctx" in params and "facts_sink" in params

    def test_tool_facts_extend_allowed_seconds(self):
        """ツール所見の秒数が捏造スクラブで消えない（許可リストに入る）。"""
        allowed = llm._allowed_seconds("状況テキスト", "ユーザー発言",
                                       '{"verdict": "10秒あたりは裏声です"}')
        assert 10 in allowed
