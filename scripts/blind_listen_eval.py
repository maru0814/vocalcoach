#!/usr/bin/env python3
"""ブラインド聴取（llm.listen_blind）の聞き分け正答率 eval（docs/104 §4）。

正解付き録音のマニフェストCSVを読み、実APIで練習種別の判定精度を測る。
「どの練習名なら断定してよいか」の線引き（docs/95 FR-06）はこの実測で決める。

使い方:
    cd backend
    GEMINI_API_KEY=... ../.venv 等の python で
    python ../scripts/blind_listen_eval.py manifest.csv --runs 3 --out report.json

マニフェストCSV（ヘッダ必須）:
    path,label
    /path/to/siren1.wav,サイレン
    /path/to/song1.wav,歌

- label は正解の練習名（llm.PRACTICE_KEYWORDS の語彙推奨）または「歌」。
- --no-dsp を付けると質感計測（texture）なしで測れる＝DSP有無の効果比較用。
- コスト目安: 1ファイル×1回 ≒ ¥0.5。

注意: 実API・実音源依存のため CI では実行しない（手動運用）。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app.audio import texture  # noqa: E402
from app.coaching import llm  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", help="path,label のCSV")
    ap.add_argument("--runs", type=int, default=3, help="1ファイルあたりの試行回数（既定3）")
    ap.add_argument("--no-dsp", action="store_true", help="質感計測を注入しない（比較用）")
    ap.add_argument("--out", default=None, help="JSONレポートの出力先")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))
    if not rows:
        print("マニフェストが空です", file=sys.stderr)
        return 1

    results = []
    for row in rows:
        path, label = row["path"].strip(), row["label"].strip()
        if not os.path.exists(path):
            print(f"skip（ファイルなし）: {path}", file=sys.stderr)
            continue
        wav = open(path, "rb").read()
        facts = None
        if not args.no_dsp:
            facts = texture.describe(texture.modulation_profile(path))
        for i in range(args.runs):
            r = llm.listen_blind(wav, acoustic_facts=facts)
            ok_kind = bool(r) and r["kind"] == ("song" if label == "歌" else "practice")
            ok_name = bool(r) and (
                (label == "歌" and r["kind"] == "song")
                or (label != "歌" and (r.get("practice") or "") == label)
            )
            results.append({
                "path": path, "label": label, "run": i + 1, "facts": facts,
                "got": r, "kind_ok": ok_kind, "name_ok": ok_name,
            })
            got = (r or {}).get("practice") or (r or {}).get("kind") or "失敗"
            print(f"{os.path.basename(path)} [{label}] run{i+1}: → {got} "
                  f"(kind {'○' if ok_kind else '×'} / name {'○' if ok_name else '×'})")

    # 集計（練習名ごと）
    agg: dict = defaultdict(lambda: {"n": 0, "kind_ok": 0, "name_ok": 0})
    for r in results:
        a = agg[r["label"]]
        a["n"] += 1
        a["kind_ok"] += r["kind_ok"]
        a["name_ok"] += r["name_ok"]

    print("\n=== 集計（docs/95 FR-06 の断定ライン判断材料）===")
    print(f"{'label':<16}{'n':>4}{'kind正答':>10}{'name正答':>10}")
    for label, a in sorted(agg.items()):
        print(f"{label:<16}{a['n']:>4}{a['kind_ok']/a['n']:>9.0%}{a['name_ok']/a['n']:>9.0%}")

    if args.out:
        json.dump({"results": results,
                   "aggregate": {k: dict(v) for k, v in agg.items()},
                   "dsp": not args.no_dsp},
                  open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\nレポート: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
