"""機械計測メトリクス（Claude不要・決定論）。プロンプト修正のbefore/after効果を客観測定する。

指標（すべて正規表現/文字列類似度で決定論的に計測）:
- rerecord   : 「もう一度録音を送って」等の再録音要求を含むコーチターン数
- video_off  : 「実演動画を出しましょうか」等の動画オファーを含むコーチターン数（会話内2回以上=連発フラグ）
- apology    : 謝罪語（ごめんなさい/申し訳/すみません）を含むコーチターン数
- repeat     : 直前のコーチ返答との類似度(difflib)>0.60 のターン数（内容の反復）
- bare_denial: 否定語（残っていない/記録に無い/確認できない/算出されていない）を含むのに、
               数値つきの事実（dB/cents/Hz/秒/点/音名）を1つも添えないターン数（=橋渡しなしの突き放し）
- denial     : 否定語を含むターン総数（bare_denial / denial = 突き放し率）
"""
from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher

RERecord = re.compile(r"(もう一度|もう1度|また|再度|新しく)[^。]{0,14}(録音|歌声|歌)[^。]{0,10}(送|とど|届)")
VIDEO = re.compile(r"(実演)?動画[^。]{0,10}(出しましょうか|お出ししましょうか|見てみますか|ご覧になりますか)")
APOLOGY = re.compile(r"(ごめんなさい|申し訳|すみません)")
DENIAL = re.compile(r"(残って(?:い|お)?(?:ま?せん|ない)|記録に(?:は)?(?:無|な)い|確認でき(?:ま?せん|ない)|"
                    r"(?:算出|検出|検知|判定|特定)されて(?:い|お)?(?:ま?せん|ない)|分かり?ま?せん|わかりま?せん)")
FACT = re.compile(r"\d+(?:\.\d+)?\s*(dB|cents|セント|Hz|秒|点|回)|[A-G]#?[0-9]")


def coach_turns(tr):
    return [e["text"] for e in tr if e["role"] == "coach"]


def measure(results: list[dict]) -> dict:
    m = {"convs": 0, "turns": 0, "rerecord": 0, "video_off": 0, "video_spam_convs": 0,
         "apology": 0, "repeat": 0, "denial": 0, "bare_denial": 0}
    for r in results:
        turns = coach_turns(r["transcript"])
        if not turns:
            continue
        m["convs"] += 1
        m["turns"] += len(turns)
        vids = 0
        prev = None
        for t in turns:
            if RERecord.search(t):
                m["rerecord"] += 1
            if VIDEO.search(t):
                m["video_off"] += 1
                vids += 1
            if APOLOGY.search(t):
                m["apology"] += 1
            if DENIAL.search(t):
                m["denial"] += 1
                if not FACT.search(t):
                    m["bare_denial"] += 1
            if prev is not None and SequenceMatcher(None, prev, t).ratio() > 0.60:
                m["repeat"] += 1
            prev = t
        if vids >= 2:
            m["video_spam_convs"] += 1
    return m


def rate(m, key, base="turns"):
    n = m.get(base) or 1
    return f"{m[key]}/{m[base]}（{round(100*m[key]/n)}%）"


def load(path):
    d = json.load(open(path))
    return d["results"] if isinstance(d, dict) else d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", nargs="+", required=True, help="beforeのresults JSON（複数可）")
    ap.add_argument("--after", required=True)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()

    before = []
    for p in a.before:
        before += load(p)
    after = load(a.after)

    def split_mt(rs):
        mt = [r for r in rs if "-multiturn-" in r["case_id"]]
        rest = [r for r in rs if "-multiturn-" not in r["case_id"]]
        return rest, mt

    b_rest, b_mt = split_mt(before)
    a_rest, a_mt = split_mt(after)

    out = {
        "before_all": measure(before), "after_all": measure(after),
        "before_multiturn": measure(b_mt), "after_multiturn": measure(a_mt),
        "before_single": measure(b_rest), "after_single": measure(a_rest),
    }
    json.dump(out, open(a.out_json, "w"), ensure_ascii=False, indent=2)

    for name in ("all", "multiturn", "single"):
        b, af = out[f"before_{name}"], out[f"after_{name}"]
        print(f"\n== {name} (before {b['convs']}会話/{b['turns']}T → after {af['convs']}会話/{af['turns']}T) ==")
        for k, jp in (("rerecord", "再録音要求"), ("video_off", "動画オファー"), ("apology", "謝罪"),
                      ("repeat", "反復(類似>0.6)"), ("bare_denial", "橋渡しなし否定")):
            print(f"  {jp:14s}: {rate(b,k)}  →  {rate(af,k)}")
        if b["denial"] or af["denial"]:
            rb = round(100*b['bare_denial']/b['denial']) if b['denial'] else 0
            ra = round(100*af['bare_denial']/af['denial']) if af['denial'] else 0
            print(f"  否定時の突き放し率: {rb}%（{b['bare_denial']}/{b['denial']}） → {ra}%（{af['bare_denial']}/{af['denial']}）")
        print(f"  動画オファー連発会話: {b['video_spam_convs']} → {af['video_spam_convs']}")


if __name__ == "__main__":
    main()
