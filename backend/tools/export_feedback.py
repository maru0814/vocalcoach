"""
コーチFBへのユーザーフィードバックを書き出す（改善ループ用）。

👎を優先し、カテゴリ集計＋コメント＋その時の解析サマリを一覧化する。
運営はこれを見て SYSTEM_PROMPT・ルール・しきい値・較正データへ反映する（docs/19）。

使い方:
    python -m tools.export_feedback            # サマリを標準出力
    python -m tools.export_feedback --json out.json
    python -m tools.export_feedback --csv out.csv --only-down
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter

from app.db.session import SessionLocal
from app.models.coaching import ChatMessage, MessageFeedback


def collect(only_down: bool = False) -> list[dict]:
    db = SessionLocal()
    try:
        q = db.query(MessageFeedback).order_by(MessageFeedback.created_at.desc())
        if only_down:
            q = q.filter(MessageFeedback.rating == "down")
        rows = []
        for fb in q.all():
            msg = db.get(ChatMessage, fb.message_id)
            ctx = fb.context or {}
            rows.append({
                "id": fb.id,
                "created_at": fb.created_at.isoformat(),
                "rating": fb.rating,
                "reason": fb.reason or "",
                "comment": fb.comment or "",
                "session_id": fb.session_id,
                "message_id": fb.message_id,
                "message_excerpt": ctx.get("message_excerpt") or (msg.text if msg else "") or "",
                "analysis": ctx.get("analysis") or {},
            })
        return rows
    finally:
        db.close()


def print_summary(rows: list[dict]) -> None:
    total = len(rows)
    ratings = Counter(r["rating"] for r in rows)
    reasons = Counter(r["reason"] for r in rows if r["rating"] == "down")
    print(f"フィードバック総数: {total}  (👍 {ratings.get('up',0)} / 👎 {ratings.get('down',0)})")
    if reasons:
        print("👎の理由内訳:", dict(reasons))
    downs = [r for r in rows if r["rating"] == "down"]
    if downs:
        print("\n--- 👎（改善の優先候補） ---")
        for r in downs[:30]:
            print(f"[{r['created_at'][:16]}] reason={r['reason'] or '-'} "
                  f"sess={r['session_id']} msg={r['message_id']}")
            print(f"   コーチ: {r['message_excerpt'][:90]}")
            if r["comment"]:
                print(f"   指摘 : {r['comment']}")
    else:
        print("\n👎はまだありません。")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="JSONで書き出すパス")
    ap.add_argument("--csv", help="CSVで書き出すパス")
    ap.add_argument("--only-down", action="store_true", help="👎のみ")
    args = ap.parse_args()

    rows = collect(only_down=args.only_down)
    print_summary(rows)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f"\n→ JSON: {args.json}")
    if args.csv:
        with open(args.csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "created_at", "rating", "reason", "comment",
                        "session_id", "message_id", "message_excerpt", "analysis"])
            for r in rows:
                w.writerow([r["id"], r["created_at"], r["rating"], r["reason"], r["comment"],
                            r["session_id"], r["message_id"], r["message_excerpt"],
                            json.dumps(r["analysis"], ensure_ascii=False)])
        print(f"→ CSV: {args.csv}")


if __name__ == "__main__":
    main()
