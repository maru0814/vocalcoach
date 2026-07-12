"""既存の実行結果(results_all.json)のtranscriptに、決定論チェックを再適用する。

Gemini を再実行せず（transcript は保存済み）、checkers.py の改良だけを反映して
deterministic_findings を作り直す。チェッカのチューニング反復を高速に回すための入口。
使い方:
  python -m scripts.soar_eval.recheck --in <results_all.json> --out <results_rechecked.json>
"""
from __future__ import annotations

import argparse
import json

from app.coaching.llm import _allowed_seconds

from . import checkers
from .states import STATES


def recheck_result(r: dict) -> dict:
    state = STATES.get(r["state_id"]) or r.get("state") or {}
    context = r["facts_snapshot"]
    transcript = r["transcript"]
    findings = []
    for i, e in enumerate(transcript):
        if e["role"] != "coach":
            continue
        prev_user = transcript[i - 1]["text"] if i > 0 and transcript[i - 1]["role"] == "user" else ""
        allowed = _allowed_seconds(context, prev_user)
        for k, det in enumerate(checkers.check_reply(e["text"], context, state, allowed)):
            det.update({
                "finding_id": f"{r['case_id']}-t{e['turn']}-{k}",
                "case_id": r["case_id"], "seed": r.get("seed", 0),
                "channel": "generate_reply", "state_id": r["state_id"],
                "case_type": r.get("case_type"), "turn_index": e["turn"],
                "user_turn_verbatim": prev_user, "coach_reply_full": e["text"],
                "expected_behavior": r.get("expected_behavior"),
                "facts_snapshot": context, "conversation_transcript": transcript,
            })
            findings.append(det)
    out = dict(r)
    out["deterministic_findings"] = findings
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = json.load(open(args.inp))
    results = [recheck_result(r) for r in (data["results"] if isinstance(data, dict) else data)]

    from collections import Counter
    cat = Counter(f["category"] for r in results for f in r["deterministic_findings"])
    ver = Counter(f["category"] for r in results for f in r["deterministic_findings"] if f["verified"])
    json.dump({"results": results,
               "summary": {"cases": len(results),
                           "total_findings": sum(len(r["deterministic_findings"]) for r in results),
                           "by_category": dict(cat)}},
              open(args.out, "w"), ensure_ascii=False, indent=2)
    print("all:", dict(cat))
    print("verified:", dict(ver))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
