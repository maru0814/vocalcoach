"""決定論チェックだけの中間レポート生成（Claude不要）。

results_all.json（run_case の出力）を読み、verified==true の確定所見を深刻度順に、
証拠（会話原文・該当箇所）つきで Markdown 化する。LLM審査の確定分は別途 merge する。
使い方:
  python -m scripts.soar_eval.report --in <results.json> --out-md <REPORT.md> --out-jsonl <findings.jsonl>
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

SEV_ORDER = {"S1": 0, "S2": 1, "S3": 2}


def load_findings(results: list[dict]):
    verified, pending = [], []
    for r in results:
        for f in r.get("deterministic_findings", []):
            (verified if f.get("verified") else pending).append(f)
    return verified, pending


def _turn_text(f, role_at):
    for e in f.get("conversation_transcript", []):
        if e["turn"] == role_at:
            return e["text"]
    return ""


def render_md(results: list[dict], verified: list[dict], pending: list[dict]) -> str:
    n_cases = len(results)
    n_coach = sum(1 for r in results for e in r["transcript"] if e["role"] == "coach")
    n_empty = sum(1 for r in results for e in r["transcript"]
                  if e["role"] == "coach" and e.get("empty_after_retry"))
    by_cat = Counter(f["category"] for f in verified)
    by_sev = Counter(f["severity"] for f in verified)

    L = []
    L.append("# ソラ先生 ハルシネーション/不自然日本語 検査レポート（決定論チェック・中間版）\n")
    L.append("> 本レポートは**機械的に確定できる違反のみ**（verified=true）。意味的な違反"
             "（追従・過去発言捏造・練習コロコロ変え・日本語の不自然さ等）はLLM審査フェーズで追補する。\n")
    L.append("## 1. サマリ")
    L.append(f"- 実行会話数: {n_cases} / コーチ返答ターン数: {n_coach}")
    L.append(f"- 空返答（リトライ後も空・実行失敗の疑い）: {n_empty}")
    L.append(f"- 確定所見（verified）: **{len(verified)}件** / 要LLM確認の候補（pending）: {len(pending)}件")
    L.append(f"- 深刻度別（確定）: " + ", ".join(f"{k}={by_sev.get(k,0)}" for k in ("S1", "S2", "S3")))
    L.append(f"- カテゴリ別（確定）: " + (", ".join(f"{k}={v}" for k, v in by_cat.most_common()) or "なし"))
    L.append("")

    L.append("## 2. 確定所見（深刻度順・証拠つき）")
    if not verified:
        L.append("_確定所見なし（決定論で捉える範囲では違反ゼロ。意味的違反はLLM審査で確認する）。_\n")
    vs = sorted(verified, key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["category"]))
    for i, f in enumerate(vs, 1):
        L.append(f"### {i}. [{f['severity']}/{f['category']} {f['category_label']}] {f['case_id']}")
        L.append(f"- **ユーザー発言**: {f.get('user_turn_verbatim','') or '（冒頭ターン）'}")
        L.append(f"- **問題の箇所（コーチ原文）**: 「{f['coach_span_verbatim']}」")
        L.append(f"- **コーチ返答全文**: {f.get('coach_reply_full','')}")
        L.append(f"- **なぜ変か**: {f['why']}")
        L.append(f"- **矛盾する事実**: {f.get('contradicting_fact','')}")
        if f.get("expected_behavior"):
            L.append(f"- **期待挙動**: {f['expected_behavior']}")
        L.append(f"- **違反ルール**: {', '.join(f.get('violated_rule', []))}")
        L.append(f"- **再現**: state_id={f['state_id']} / case_id={f['case_id']}")
        L.append("")

    if pending:
        L.append("## 3. 要LLM確認の候補（決定論では確定できず・誤検出の可能性あり）")
        pc = Counter(f["category"] for f in pending)
        L.append(f"- 候補カテゴリ: " + ", ".join(f"{k}={v}" for k, v in pc.most_common()))
        for f in sorted(pending, key=lambda f: SEV_ORDER.get(f["severity"], 9))[:40]:
            L.append(f"  - [{f['category']}] {f['case_id']}: 「{f['coach_span_verbatim']}」 — {f['why'][:80]}")
        L.append("")

    L.append("## 4. 再現方法")
    L.append("```bash")
    L.append("# 単体（仕掛け型）")
    L.append("bash scripts/soar_eval/run.sh --planted AC01-F#5-noref")
    L.append("# バッチ（自由型含む全バンク）")
    L.append("bash scripts/soar_eval/run.sh --batch-file <bank.json> --out <results.json>")
    L.append("```")
    return "\n".join(L)


def split_cases(results: list[dict], out_dir: str) -> int:
    """各ケースを小さな個別JSONに分割（LLM審査エージェントが小ファイルを読めるように）。"""
    import os
    os.makedirs(out_dir, exist_ok=True)
    idx = []
    for r in results:
        slim = {
            "case_id": r["case_id"], "state_id": r["state_id"],
            "case_type": r.get("case_type"), "ac": r.get("ac"),
            "expected_behavior": r.get("expected_behavior"),
            "target_categories": r.get("target_categories"),
            "facts_snapshot": r["facts_snapshot"],
            "transcript": r["transcript"],
            "deterministic_findings": [
                {k: v for k, v in f.items() if k != "conversation_transcript"}
                for f in r.get("deterministic_findings", [])
            ],
        }
        path = os.path.join(out_dir, f"{r['case_id']}.json")
        json.dump(slim, open(path, "w"), ensure_ascii=False, indent=2)
        idx.append({"case_id": r["case_id"], "path": path,
                    "n_coach": sum(1 for e in r["transcript"] if e["role"] == "coach")})
    json.dump({"cases": idx}, open(os.path.join(out_dir, "_index.json"), "w"), ensure_ascii=False, indent=2)
    return len(idx)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-jsonl", required=True)
    ap.add_argument("--split-dir", help="指定すると各ケースを個別JSONに分割")
    args = ap.parse_args()

    data = json.load(open(args.inp))
    results = data["results"] if isinstance(data, dict) else data
    verified, pending = load_findings(results)

    if args.split_dir:
        n = split_cases(results, args.split_dir)
        print(f"split {n} cases -> {args.split_dir}")

    with open(args.out_md, "w") as f:
        f.write(render_md(results, verified, pending))
    with open(args.out_jsonl, "w") as f:
        for x in verified + pending:
            slim = {k: v for k, v in x.items() if k != "conversation_transcript"}
            f.write(json.dumps(slim, ensure_ascii=False) + "\n")

    print(f"verified={len(verified)} pending={len(pending)} -> {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
