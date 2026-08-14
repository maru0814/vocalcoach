"""運用者アカウントの直近コーチ会話・解析データの読み取り専用ダンプ（SRE運用ツール）。

用途: 本番での講評内容の検証（例: 「音の高さ」指摘が測定に基づくかの確認）。
実行場所: 本番 backend コンテナ内（ops-query.yml が SSH 経由で stdin 実行）。
書き込みは一切しない。対象は OWNER_EMAIL のアカウントのみ（他ユーザーのデータは出さない）。
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, "/app")

from app.db.session import SessionLocal  # noqa: E402
from app.models.coaching import ChatMessage, ChatSession  # noqa: E402
from app.models.user import User  # noqa: E402

OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "yumaruyama0814@gmail.com")
N_MSGS = int(os.environ.get("N_MSGS", "12"))


def _f0_summary(analysis: dict | None) -> dict:
    """last_analysis から音の高さに関わる測定値だけを抜く（検証に必要な最小限）。"""
    if not isinstance(analysis, dict):
        return {}
    out = {k: v for k, v in analysis.items()
           if isinstance(v, (int, float, str)) and (
               "f0" in k or "range" in k or "note" in k or "pitch" in k
               or k in ("duration_sec", "rms_mean", "voiced_ratio"))}
    pw = (analysis.get("timeline") or {}).get("per_window") or []
    f0s = [w.get("f0_mean_hz") for w in pw if w.get("f0_mean_hz")]
    if f0s:
        out["timeline_f0_min_hz"] = round(min(f0s), 1)
        out["timeline_f0_max_hz"] = round(max(f0s), 1)
        out["timeline_windows"] = len(f0s)
    return out


def main() -> int:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == OWNER_EMAIL).first()
        if not user:
            print(f"user not found: {OWNER_EMAIL}")
            return 1
        s = (db.query(ChatSession).filter(ChatSession.user_id == user.id)
             .order_by(ChatSession.updated_at.desc()).first())
        if not s:
            print("no sessions")
            return 1
        print(f"=== session id={s.id} updated={s.updated_at} phase={s.phase} "
              f"current_task={s.current_task} ===")
        msgs = (db.query(ChatMessage).filter(ChatMessage.session_id == s.id)
                .order_by(ChatMessage.id.desc()).limit(N_MSGS).all())
        print(f"--- 直近{len(msgs)}メッセージ（新しい順）---")
        for m in msgs:
            body = (m.text or "").replace("\n", " ")
            extra = ""
            if m.type != "text" and isinstance(m.payload, dict):
                keep = {k: v for k, v in m.payload.items()
                        if isinstance(v, (str, int, float)) and len(str(v)) < 200}
                extra = f" payload={json.dumps(keep, ensure_ascii=False)}"
            print(f"[{m.id}] {m.created_at} {m.role}/{m.type}: {body}{extra}")
        print("--- last_analysis の音高関連測定値 ---")
        print(json.dumps(_f0_summary(s.last_analysis), ensure_ascii=False, indent=2))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
