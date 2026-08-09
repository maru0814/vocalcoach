"""台本の予算チェック（docs/97 柱1・docs/99）。

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
