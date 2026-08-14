"""台本の予算チェック（docs/97 柱1・docs/102）。

会話用 SYSTEM_PROMPT は3,000字以内。追記は one-in-one-out（1行足すなら1行削る）。
このテストが落ちたら、行を足すのではなく docs/97 に従って削る・原則へ集約する。
字数は「形式」の決定論チェックなので会話憲法（docs/94）の許容範囲。
"""
from app.coaching import llm

BUDGET_CHARS = 3000  # docs/97 柱1


def test_system_prompt_within_budget():
    n = len(llm.SYSTEM_PROMPT)
    assert n <= BUDGET_CHARS, (
        f"SYSTEM_PROMPT が予算超過: {n}字 > {BUDGET_CHARS}字。"
        "docs/97（プロンプトダイエット方針）に従い、追記した分だけ削ること"
    )


def test_raw_units_rule_is_present():
    """docs/42 §6「生の数値を口に出さない」が台本に実装されているか。

    このルールは 2026-08-08 に運用者FBで docs/42 に入ったが、
    プロンプト側へ一度も反映されず、生の cents/dB がそのまま生徒に届いていた
    （2026-08-14 実測: 現行Gemini 11件/72会話・GPT 6件/72会話）。
    SSOT だけに書いて実装が抜ける事故を、このテストで塞ぐ。
    """
    p = llm.SYSTEM_PROMPT
    assert "cents" in p and "dB" in p, "生の単位を出さない原則が台本に無い"
    assert "体感" in p, "体感の言葉へ翻訳する指示が台本に無い"


def test_facts_carry_the_translation_reminder():
    """数値のすぐ隣にも念押しが載る（台本冒頭の原則だけでは引用事故が起きたため）。"""
    ctx = llm.build_session_context({"phase": "feedback",
                                     "last_analysis": {"duration_sec": 25.0}})
    assert "体感の言葉に翻訳" in ctx
