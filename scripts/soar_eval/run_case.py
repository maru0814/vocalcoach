"""CLI: 1ケース（state + user_turns）を本物の generate_reply で実行し、
transcript と決定論チェック所見を docs/64 §6.1 スキーマの JSON で emit する。

使い方:
  # 仕掛け型ケースを1件（backend/ を cwd にして venv python で）
  python -m scripts.soar_eval.run_case --planted AC01-F#5-noref
  # 仕掛け型を全件
  python -m scripts.soar_eval.run_case --planted-all --out reports/planted.json
  # 任意ケース（自由型など）を stdin JSON で
  echo '{"case_id":"free-1","state_id":"st_noref_25s_chest","case_type":"freeform",
         "user_turns":["高い声が苦しいです"]}' | python -m scripts.soar_eval.run_case --stdin
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.coaching.llm import _allowed_seconds

from . import checkers, driver
from .cases_planted import PLANTED_CASES
from .states import STATES


def _findings_for_case(case: dict) -> dict[str, Any]:
    state_id = case["state_id"]
    # state はバンク参照が基本。case に "state" があればインライン（自由型が独自 state を作る場合）
    state = case.get("state") or STATES[state_id]
    seed = case.get("seed", 0)
    case_type = case.get("case_type", "planted" if case in PLANTED_CASES else "freeform")
    user_turns = case["user_turns"]

    transcript = driver.run_conversation(state, user_turns, case.get("history_seed"))
    context = driver.facts_snapshot(state)

    findings: list[dict[str, Any]] = []
    # transcript は [user, coach, user, coach, ...]（history_seed があれば前置きあり）
    for i, entry in enumerate(transcript):
        if entry["role"] != "coach":
            continue
        # 直前の user 発言（このコーチ返答が答えている相手）
        prev_user = transcript[i - 1]["text"] if i > 0 and transcript[i - 1]["role"] == "user" else ""
        reply = entry["text"]
        allowed = _allowed_seconds(context, prev_user)  # 本物の generate_reply と同じ許可集合
        for k, det in enumerate(checkers.check_reply(reply, context, state, allowed)):
            det.update({
                "finding_id": f"{case['case_id']}-t{entry['turn']}-{k}",
                "case_id": case["case_id"],
                "seed": seed,
                "channel": "generate_reply",
                "state_id": state_id,
                "case_type": case_type,
                "turn_index": entry["turn"],
                "user_turn_verbatim": prev_user,
                "coach_reply_full": reply,
                "expected_behavior": case.get("expected_behavior"),
                "facts_snapshot": context,
                "conversation_transcript": transcript,
            })
            findings.append(det)

    return {
        "case_id": case["case_id"],
        "state_id": state_id,
        "case_type": case_type,
        "seed": seed,
        "ac": case.get("ac"),
        "target_categories": case.get("target_categories"),
        "expected_behavior": case.get("expected_behavior"),
        "facts_snapshot": context,
        "transcript": transcript,
        "deterministic_findings": findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--planted", help="仕掛け型ケースID（cases_planted.py）")
    ap.add_argument("--planted-all", action="store_true", help="仕掛け型ケースを全件")
    ap.add_argument("--stdin", action="store_true", help="任意ケースJSONを stdin から")
    ap.add_argument("--batch-file", help="ケースの配列（または{'cases':[...]}）JSONファイルを一括実行")
    ap.add_argument("--out", help="出力ファイル（省略時 stdout）")
    ap.add_argument("--checkpoint", help="ケースごとに追記するJSONLパス。既存分はスキップ（中断再開用）")
    args = ap.parse_args()

    cases: list[dict] = []
    if args.planted_all:
        cases = PLANTED_CASES
    elif args.planted:
        cases = [c for c in PLANTED_CASES if c["case_id"] == args.planted]
        if not cases:
            print(f"no such planted case: {args.planted}", file=sys.stderr)
            return 2
    elif args.batch_file:
        with open(args.batch_file) as f:
            data = json.load(f)
        cases = data.get("cases", data) if isinstance(data, dict) else data
    elif args.stdin:
        cases = [json.loads(sys.stdin.read())]
    else:
        print("one of --planted / --planted-all / --batch-file / --stdin required", file=sys.stderr)
        return 2

    # チェックポイント: 完了済み case_id をスキップし、1ケースごとに追記（ネットワーク断・中断からの再開用）
    done: dict[str, dict] = {}
    if args.checkpoint:
        import os
        if os.path.exists(args.checkpoint):
            with open(args.checkpoint) as f:
                for line in f:
                    try:
                        r = json.loads(line)
                        done[r["case_id"]] = r
                    except Exception:
                        continue
            if done:
                print(f"checkpoint: {len(done)} cases already done, skipping",
                      file=sys.stderr)

    results = []
    for c in cases:
        if c["case_id"] in done:
            results.append(done[c["case_id"]])
            continue
        r = _findings_for_case(c)
        results.append(r)
        if args.checkpoint:
            with open(args.checkpoint, "a") as f:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    payload = {"results": results,
               "summary": _summary(results)}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        import os
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            f.write(text)
        print(f"wrote {args.out} ({len(results)} cases, "
              f"{payload['summary']['total_findings']} findings)", file=sys.stderr)
    else:
        print(text)
    return 0


def _summary(results: list[dict]) -> dict[str, Any]:
    by_cat: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    total = 0
    for r in results:
        for f in r["deterministic_findings"]:
            total += 1
            by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
            by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1
    return {"cases": len(results), "total_findings": total,
            "by_category": by_cat, "by_severity": by_sev}


if __name__ == "__main__":
    raise SystemExit(main())
