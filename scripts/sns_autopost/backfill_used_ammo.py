#!/usr/bin/env python3
"""過去に投稿・下書き化された弾を、ammo_key 導入後の世界へ焼却バックフィルする（docs/108）。

ammo_key の記録は導入後の下書きにしか付かないため、導入前に使われた弾は
そのままだと「未使用」に見え、もう一度だけ選ばれてしまう。このスクリプトは
pending_queue.jsonl の履歴と現行 themes.py の弾倉を突き合わせ、確実に一致した
弾を used_ammo.jsonl に焼却記録する。

一致ルール（保守的に。曖昧一致で未使用の良弾を焼かない）:
  1. 本文の完全一致（空白揺れのみ吸収）= テンプレ素のまま出た過去分
  2. リプ本体の完全一致 = tip 等でフックだけGeminiが書き換えた過去分
  3. 本文1行目の完全一致 = フック1行目を保ったリライト分
  4. artist_analysis のみ: 同型の過去下書き本文にそのアーティスト実名が含まれる
     （実名は弾ごとに一意で、docs/84 が他歌手名の追加を禁止しているため安全）

使い方（既定はdry-run。--apply で書き込み）:
  python backfill_used_ammo.py           # 何が焼却されるか表示のみ
  python backfill_used_ammo.py --apply   # used_ammo.jsonl に記録
"""
import argparse
import json
import os
import re
import sys

import dedup
import themes

_WS_RE = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS_RE.sub("", s or "")


def find_burned(rows: list[dict]) -> list[dict]:
    """キュー履歴 rows から、焼却すべき弾 [{ammo_key, pillar, reason, label}] を返す。"""
    app = os.getenv("APP_URL", themes.APP_URL_DEFAULT).rstrip("/")
    by_pillar: dict[str, list[dict]] = {}
    for r in rows:
        by_pillar.setdefault(r.get("pillar", ""), []).append(r)

    already = dedup.used_ammo_keys()
    out = []
    for pillar in ("tip", "contrarian", "voice_type", "self_type", "visual",
                   "artist_analysis"):
        hist = by_pillar.get(pillar, [])
        texts = [_norm(r.get("text") or "") for r in hist]
        replies = [_norm(r.get("reply") or "") for r in hist]
        firsts = {(r.get("text") or "").strip().splitlines()[0]
                  for r in hist if (r.get("text") or "").strip()}
        for i in range(themes.pool_size(pillar)):
            key = dedup.ammo_key(pillar, i, app)
            if key in already:
                continue  # すでに記録済み（enqueue時 or 過去のバックフィル）
            t = themes.template_post(pillar, i, app)
            t_text, t_reply = _norm(t["text"]), _norm(t.get("reply") or "")
            t_first = t["text"].strip().splitlines()[0]
            reason = None
            if t_text and t_text in texts:
                reason = "text_exact"
            elif (pillar not in themes.DIAGNOSIS_PILLARS
                  and t_reply and t_reply in replies):
                # リプ一致は、リプ本体が弾ごとに固有な型（tip等）だけに適用する。
                # 診断導線のリプは全弾共通の「8タイプ早見」なので、これで一致を取ると
                # 一度も出ていないフック変奏まで全弾焼却してしまう（2026-08-26 dry-runで検出）。
                reason = "reply_exact"
            elif t_first in firsts:
                reason = "first_line"
            elif pillar == "artist_analysis":
                artist = themes.ARTIST_ANALYSIS[i % len(themes.ARTIST_ANALYSIS)]["artist"]
                if any(artist in (r.get("text") or "") for r in hist):
                    reason = f"artist:{artist}"
            if reason:
                out.append({"ammo_key": key, "pillar": pillar,
                            "reason": f"backfill:{reason}",
                            "label": t["text"].strip().splitlines()[0][:40]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="実際に used_ammo.jsonl へ焼却を記録する（省略時は表示のみ）")
    args = ap.parse_args()

    qpath = os.path.join(os.getenv("SNS_DATA_DIR",
                                   os.path.dirname(os.path.abspath(__file__))),
                         "pending_queue.jsonl")
    rows = []
    if os.path.exists(qpath):
        with open(qpath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
    burned = find_burned(rows)
    print(f"キュー履歴 {len(rows)}件 → 焼却対象 {len(burned)}弾")
    for b in burned:
        print(f"  [{b['pillar']}] {b['label']}  ({b['reason']})")
    if not burned:
        return 0
    if not args.apply:
        print("（dry-run。書き込むには --apply を付けて再実行）")
        return 0
    n = dedup.record_used(burned)
    print(f"used_ammo.jsonl に {n}件 記録しました。以後これらの弾は二度と選ばれません。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
