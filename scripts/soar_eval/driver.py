"""会話ドライバ: 1つの会話スクリプトを本物の generate_reply で逐次実行する。"""
from __future__ import annotations

import os
import time
from typing import Any

from app.coaching.llm import generate_reply, build_session_context

# 大量実行時のレート制限対策。ターン間スリープ（秒）と空返答リトライ回数。
_SLEEP = float(os.environ.get("SOAR_EVAL_SLEEP", "0.8"))
_RETRY = int(os.environ.get("SOAR_EVAL_RETRY", "3"))


def run_conversation(state: dict, user_turns: list[str],
                     history_seed: list[dict] | None = None) -> list[dict[str, Any]]:
    """user_turns を順に generate_reply へ渡し、transcript を返す。

    transcript: [{"turn": i, "role": "user"|"coach", "text": str}, ...]
    history 形式は llm._build_contents に合わせて {"role": "user"|"assistant", "content": str}。
    """
    history: list[dict] = list(history_seed or [])
    transcript: list[dict[str, Any]] = []
    turn = 0
    for msg in history:  # 前置き履歴も transcript に残す（再現性）
        transcript.append({"turn": turn, "role": "coach" if msg["role"] == "assistant" else "user",
                           "text": msg["content"]})
        turn += 1

    for user_text in user_turns:
        transcript.append({"turn": turn, "role": "user", "text": user_text})
        turn += 1
        # 空返答（レート制限/一過性失敗）はバックオフして数回リトライ。
        # elapsed_sec は成功した最後の呼び出し1回分の所要秒（docs/96 §4 レイテンシ測定用。
        # リトライの待ち時間は含めない＝モデル応答時間だけを測る）。
        reply = ""
        elapsed = None
        for attempt in range(_RETRY):
            t0 = time.monotonic()
            reply = generate_reply(state, user_text, history) or ""
            elapsed = time.monotonic() - t0
            if reply:
                break
            time.sleep(1.5 * (attempt + 1))
        transcript.append({"turn": turn, "role": "coach", "text": reply,
                           **({"elapsed_sec": round(elapsed, 2)} if elapsed is not None else {}),
                           **({"empty_after_retry": True} if not reply else {})})
        turn += 1
        if _SLEEP:
            time.sleep(_SLEEP)
        # 次ターンの文脈に積む
        history = history + [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": reply},
        ]
    return transcript


def facts_snapshot(state: dict) -> str:
    """所見に添える『許可事実』のダイジェスト（build_session_context の生出力）。"""
    return build_session_context(state)
