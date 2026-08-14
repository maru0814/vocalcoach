#!/usr/bin/env python3
"""ブラインド聴取（llm.listen_blind）の聞き分け正答率 eval（docs/104 §4・docs/106 実施手順）。

正解付き録音のマニフェストCSVを読み、実APIで練習種別の判定精度を測る。
「どの練習名なら断定してよいか」の線引き（docs/95 FR-06）はこの実測で決める。

使い方:
    cd backend
    GEMINI_API_KEY=... の環境で
    python ../scripts/blind_listen_eval.py manifest.csv --runs 3 --out report.json
    # モデル横断比較＋DSPあり/なし比較:
    python ../scripts/blind_listen_eval.py manifest.csv \
        --models gemini-2.5-flash,gemini-3.5-flash --dsp both --out report.json

マニフェストCSV（ヘッダ必須。path はCSVからの相対パス可）:
    path,label
    recordings/siren1.wav,サイレン
    recordings/song1.wav,歌

- label は正解の練習名（llm.PRACTICE_KEYWORDS の語彙推奨）または「歌」。
- --dsp both で質感計測（texture＋音程移動幅）の有無を同条件で比較できる。
  事実の組み立ては本番（coach.py）と同じ app.audio.facts を使う＝評価と本番のドリフト無し。
- レポートには texture の窓ごとの生値（windows）も記録する。STRENGTH_THRESHOLD の
  較正（docs/106 §3）はこの分布から追加APIコストなしで行う。
- コスト目安: 1呼び出し ≒ ¥0.5。実行前に予定呼び出し数と概算を表示する。

注意: 実API・実音源依存のため CI では実行しない（手動運用）。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app.audio import facts as blind_facts  # noqa: E402
from app.audio import texture  # noqa: E402
from app.coaching import llm  # noqa: E402


def _load_manifest(path: str) -> list[dict]:
    base = os.path.dirname(os.path.abspath(path))
    rows = []
    for row in csv.DictReader(open(path, encoding="utf-8")):
        p = row["path"].strip()
        if not os.path.isabs(p):
            p = os.path.join(base, p)
        if not os.path.exists(p):
            print(f"skip（ファイルなし）: {p}", file=sys.stderr)
            continue
        rows.append({"path": p, "label": row["label"].strip()})
    return rows


def _analysis_for_facts(path: str):
    """本番と同じ音程移動幅の材料（analyzer の timeline）。失敗時は None＝texture のみ。"""
    try:
        from app.audio import analyzer
        return analyzer.analyze_file(path)
    except Exception as e:  # noqa: BLE001
        print(f"analyze_file 失敗（textureのみで続行）: {os.path.basename(path)}: {e}",
              file=sys.stderr)
        return None


def _pct(x: list[float], q: float) -> float:
    if not x:
        return 0.0
    s = sorted(x)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", help="path,label のCSV")
    ap.add_argument("--runs", type=int, default=3, help="1ファイル×1条件あたりの試行回数（既定3）")
    ap.add_argument("--models", default=None,
                    help="カンマ区切りのモデルID（既定: 現行の llm_analysis_model のみ）")
    ap.add_argument("--dsp", choices=("on", "off", "both"), default="on",
                    help="測定事実の注入 on/off/both（既定 on＝本番と同条件）")
    ap.add_argument("--no-dsp", action="store_true", help="（互換）--dsp off と同じ")
    ap.add_argument("--out", default=None, help="JSONレポートの出力先")
    args = ap.parse_args()

    rows = _load_manifest(args.manifest)
    if not rows:
        print("マニフェストが空です", file=sys.stderr)
        return 1

    default_model = llm.settings.llm_analysis_model
    models = [m.strip() for m in (args.models or default_model).split(",") if m.strip()]
    dsp_modes = [True] if args.dsp == "on" else [False] if (args.dsp == "off" or args.no_dsp) \
        else [True, False]

    n_calls = len(rows) * args.runs * len(models) * len(dsp_modes)
    print(f"計画: {len(rows)}ファイル × {args.runs}回 × {len(models)}モデル × "
          f"DSP{len(dsp_modes)}条件 = {n_calls}呼び出し（概算 ¥{n_calls * 0.5:.0f}）\n")

    # ファイルごとに一度だけ: 音源読み・質感プロファイル・測定事実（DSPあり用）
    prepared = []
    for row in rows:
        path = row["path"]
        profile = texture.modulation_profile(path)
        facts = blind_facts.assemble(path, _analysis_for_facts(path))
        prepared.append({**row, "wav": open(path, "rb").read(),
                         "profile": profile, "facts": facts})

    results = []
    try:
        for model in models:
            llm.settings.llm_analysis_model = model
            for use_dsp in dsp_modes:
                tag = f"[{model} / DSP{'あり' if use_dsp else 'なし'}]"
                for item in prepared:
                    label = item["label"]
                    facts = item["facts"] if use_dsp else None
                    for i in range(args.runs):
                        t0 = time.monotonic()
                        r = llm.listen_blind(item["wav"], acoustic_facts=facts)
                        dt = time.monotonic() - t0
                        ok_kind = bool(r) and r["kind"] == ("song" if label == "歌" else "practice")
                        ok_name = bool(r) and (
                            (label == "歌" and r["kind"] == "song")
                            or (label != "歌" and (r.get("practice") or "") == label)
                        )
                        results.append({
                            "model": model, "dsp": use_dsp,
                            "path": item["path"], "label": label, "run": i + 1,
                            "facts": facts, "got": r, "latency_sec": round(dt, 2),
                            "kind_ok": ok_kind, "name_ok": ok_name, "failed": r is None,
                        })
                        got = (r or {}).get("practice") or (r or {}).get("kind") or "失敗"
                        print(f"{tag} {os.path.basename(item['path'])} [{label}] run{i + 1}: "
                              f"→ {got} (kind {'○' if ok_kind else '×'} / "
                              f"name {'○' if ok_name else '×'} / {dt:.1f}s)")
    finally:
        llm.settings.llm_analysis_model = default_model

    # 集計1: (モデル×DSP×label) の正答率と、名指しラインの判定材料（docs/95 FR-06）
    agg: dict = defaultdict(lambda: {"n": 0, "kind_ok": 0, "name_ok": 0, "failed": 0})
    lat: dict = defaultdict(list)
    for r in results:
        key = (r["model"], r["dsp"], r["label"])
        a = agg[key]
        a["n"] += 1
        a["kind_ok"] += r["kind_ok"]
        a["name_ok"] += r["name_ok"]
        a["failed"] += r["failed"]
        lat[(r["model"], r["dsp"])].append(r["latency_sec"])

    print("\n=== 正答率（docs/95 FR-06 の断定ライン判断材料。名指しの線引きは運用者が決める）===")
    print(f"{'model':<22}{'DSP':<6}{'label':<14}{'n':>4}{'kind':>7}{'name':>7}{'失敗':>5}  名指し目安(≥90%)")
    for (model, dsp, label), a in sorted(agg.items()):
        name_rate = a["name_ok"] / a["n"]
        verdict = "名指し可" if (label != "歌" and name_rate >= 0.9) else \
            ("—" if label == "歌" else "描写どまり")
        print(f"{model:<22}{'あり' if dsp else 'なし':<5}{label:<14}{a['n']:>4}"
              f"{a['kind_ok'] / a['n']:>7.0%}{name_rate:>7.0%}{a['failed']:>5}  {verdict}")

    print("\n=== レイテンシ（モデル×DSP。listen_blind はリトライ込み）===")
    print(f"{'model':<22}{'DSP':<6}{'中央値':>8}{'p90':>8}{'最大':>8}")
    for (model, dsp), xs in sorted(lat.items()):
        print(f"{model:<22}{'あり' if dsp else 'なし':<5}"
              f"{statistics.median(xs):>7.1f}s{_pct(xs, 0.9):>7.1f}s{max(xs):>7.1f}s")

    # 集計2: しきい値較正の材料（labelごとの窓strength分布。API不要の再計算は docs/106 §3）
    strength_by_label: dict = defaultdict(list)
    for item in prepared:
        for w in (item["profile"] or {}).get("windows", []):
            strength_by_label[item["label"]].append(w["strength"])
    print(f"\n=== 質感strength分布（STRENGTH_THRESHOLD={texture.STRENGTH_THRESHOLD} の較正材料）===")
    print(f"{'label':<14}{'窓数':>5}{'min':>7}{'中央値':>8}{'max':>7}")
    for label, xs in sorted(strength_by_label.items()):
        print(f"{label:<14}{len(xs):>5}{min(xs):>7.2f}{statistics.median(xs):>8.2f}{max(xs):>7.2f}")

    if args.out:
        json.dump({
            "results": results,
            "aggregate": {f"{m}|{'dsp' if d else 'nodsp'}|{l}": dict(a)
                          for (m, d, l), a in agg.items()},
            "latency": {f"{m}|{'dsp' if d else 'nodsp'}":
                        {"median": statistics.median(xs), "p90": _pct(xs, 0.9), "max": max(xs)}
                        for (m, d), xs in lat.items()},
            "profiles": [{"path": p["path"], "label": p["label"],
                          "facts": p["facts"], "profile": p["profile"]} for p in prepared],
            "models": models, "runs": args.runs, "dsp_modes": args.dsp,
            "strength_threshold": texture.STRENGTH_THRESHOLD,
        }, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\nレポート: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
