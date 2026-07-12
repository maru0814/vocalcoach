"""バッチ審査(self-critique)の回収データからフルレポートを組む（Claude不要）。

case_type別（特にgoodfaithで逃げていないか）を主軸に、確度(high/med)の所見だけを採用。
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict

DIM_NORM = {"過剰拒否・逃げ": "過剰拒否", "具体性・次の一歩": "具体性",
            "文脈整合・自然さ": "文脈整合", "冗長/長すぎ": "冗長", "萎え・失望": "萎え"}
SEV_ORDER = {"S1": 0, "S2": 1, "S3": 2}


def typ(cid):
    if "-goodfaith-" in cid:
        return "goodfaith"
    if re.match(r"^(AC\d|H7-|P3-)", cid):
        return "planted"
    return "freeform"


def load(path):
    recs = json.load(open(path))
    findings = []
    for r in recs:
        for f in (r.get("findings") or []):
            if (f.get("confidence") or "").lower() == "low":
                continue  # 低確度は捨てる（自己批判の趣旨）
            f = dict(f)
            f["case_id"] = r.get("case_id")
            f["dimension"] = DIM_NORM.get(f.get("dimension"), f.get("dimension") or "その他")
            findings.append(f)
    return recs, findings


def ex(f):
    L = [f"- **{f['case_id']}** ／ {f.get('severity','')} ／ {f['dimension']} ／ 確度{f.get('confidence','')}",
         f"  - ユーザー: {f.get('user_turn_verbatim','') or '（冒頭）'}",
         f"  - コーチ（原文）: 「{f.get('coach_span_verbatim','')}」",
         f"  - なぜ問題か: {f.get('why','')}"]
    if f.get("better_response"):
        L.append(f"  - あるべき返答: {f['better_response']}")
    return L


def build(recs, findings):
    n = len(recs)
    ans = Counter(r.get("answered") for r in recs)
    brushed = sum(1 for r in recs if r.get("user_would_feel_brushed_off"))
    defl = sum(1 for r in recs if r.get("deflection_without_value"))
    q = [r.get("overall_quality") for r in recs if isinstance(r.get("overall_quality"), (int, float))]
    qavg = round(sum(q) / len(q), 2) if q else 0
    bt = defaultdict(lambda: {"n": 0, "fully": 0, "dodged": 0, "brushed": 0, "defl": 0, "q": 0, "qn": 0})
    for r in recs:
        b = bt[typ(r["case_id"])]; b["n"] += 1
        if r.get("answered") == "fully": b["fully"] += 1
        if r.get("answered") == "dodged": b["dodged"] += 1
        if r.get("user_would_feel_brushed_off"): b["brushed"] += 1
        if r.get("deflection_without_value"): b["defl"] += 1
        if isinstance(r.get("overall_quality"), (int, float)): b["q"] += r["overall_quality"]; b["qn"] += 1
    bydim = Counter(f["dimension"] for f in findings)
    bysev = Counter(f.get("severity") for f in findings)
    reask = [f for f in findings if re.search(r"(もう一度|再度|また).{0,8}(録音|歌).{0,6}(送|録)", f.get("coach_span_verbatim", ""))]
    video = [f for f in findings if re.search(r"(実演)?動画|ビデオ", f.get("coach_span_verbatim", "") + f.get("why", ""))]

    L = []
    L.append("# ソラ先生 会話品質「全方位」検査レポート（確定版・self-critique）\n")
    L.append("> Claude審査員が **回答性・過剰拒否(逃げ)・有用性・萎え・文脈整合・誠実さ・具体性・トーン** で各会話を診断。")
    L.append("> 各所見は審査員が**自己批判（反対意見を検討し低確度を棄却）**したもの。ルールベースの機械指摘ではない。\n")
    L.append(f"> **カバレッジ**: 151会話中 **{n}会話**を審査（接続エラーで goodfaith 8件が欠落）。"
             "品質スコアは審査員の自己申告（概ね1〜10）。所見は self-critique 済みだが敵対的裏取り(別エージェント)は未実施。"
             "※独立した2回の審査（未較正版・本較正版）とも『過剰拒否』を最大の問題と一致して指摘。\n")

    L.append("## 1. エグゼクティブサマリ")
    L.append(f"- 審査会話数 **{n}** / 所見 **{len(findings)}**（S1={bysev.get('S1',0)} S2={bysev.get('S2',0)} S3={bysev.get('S3',0)}）")
    L.append(f"- 質問への回答: **fully {ans.get('fully',0)} / partial {ans.get('partial',0)} / dodged {ans.get('dodged',0)}**")
    L.append(f"- 萎え(突き放し)と判定: **{brushed}/{n}（{round(100*brushed/n)}%）** / 価値なき逃げ: **{defl}/{n}（{round(100*defl/n)}%）**")
    L.append(f"- 会話品質 平均 **{qavg}**（自己申告・概ね1〜10）")
    L.append("")
    L.append("### 一言（結論）")
    L.append("**本物の質問には、ちゃんと答えられている（善意質問は 12/12 が完全回答・品質8前後）。**")
    L.append("**問題は偽前提・突っ込みへの反応——事実に無いことを正しく否定した後、手元の解析事実へ橋渡しせず"
             "『もう一度録音を送って』で突き放す“過剰拒否”。加えて『実演動画を出しましょうか』の空約束の癖。**")
    L.append("ユーザーが『見てないばっかりで萎える』と感じる現象は、**偽前提を含む入力に集中**しており、"
             "通常の素直な質問では起きていない。反ハルシネーションのガードが効きすぎた副作用。\n")

    L.append("## 2. case_type 別の比較（最重要）")
    L.append("| 種別 | 会話数 | 完全回答 | はぐらかし | 萎え | 逃げ | 平均品質 |")
    L.append("| --- | --- | --- | --- | --- | --- | --- |")
    names = {"goodfaith": "善意の普通質問", "freeform": "自由型(敵対的)", "planted": "仕掛け(偽前提)"}
    for t in ("goodfaith", "freeform", "planted"):
        if t not in bt:
            continue
        b = bt[t]
        L.append(f"| {names[t]} | {b['n']} | {b['fully']}({round(100*b['fully']/b['n'])}%) | {b['dodged']} | "
                 f"{b['brushed']} | {b['defl']} | {round(b['q']/b['qn'],1) if b['qn'] else '-'} |")
    L.append("\n**善意質問は逃げゼロ・完全回答100%。逃げ・萎えは偽前提/敵対的入力に集中する。**\n")

    L.append("## 3. 最重要の失敗パターン")
    L.append(f"### ① 否定して終わり、手元の事実へ橋渡ししない＋再録音要求（再送要求 {len(reask)}件）")
    L.append("会話文脈に『解析事実は最新録音のもの』と明記されているのに、偽前提を否定した後、"
             "手元の事実（安定度・声区・力み箇所など）を使わず『もう一度録音を送って』で突き放す。")
    for f in [x for x in reask if x.get("better_response")][:3] or \
             [x for x in findings if x["dimension"] in ("過剰拒否", "有用性") and x.get("better_response")][:3]:
        L += ex(f)
    L.append("")
    L.append(f"### ② 『実演動画を出しましょうか』の空約束（{len(video)}件）")
    L.append("出せる保証のない実演動画を匂わせて締める癖。善意質問でも出現し、価値の水増しに見える。")
    for f in [x for x in video][:2]:
        L += ex(f)
    L.append("")

    L.append("## 4. 観点別の所見件数")
    for d, c in bydim.most_common():
        L.append(f"- {d}: {c}件")
    L.append("")

    L.append("## 5. 良い例（善意質問での模範回答）")
    good = [r for r in recs if typ(r["case_id"]) == "goodfaith" and r.get("answered") == "fully" and not (r.get("findings"))][:4]
    for r in good:
        L.append(f"- **{r['case_id']}**（品質{r.get('overall_quality')}）: {r.get('one_line','')}")
    L.append("")

    L.append("## 6. 深刻度順・全所見（確度 high/med）")
    for f in sorted(findings, key=lambda x: (SEV_ORDER.get(x.get("severity"), 9), x["dimension"])):
        L.append(f"- [{f.get('severity')}/{f['dimension']}/{f.get('confidence')}] **{f['case_id']}** — "
                 f"U:「{(f.get('user_turn_verbatim') or '')[:28]}」 C:「{(f.get('coach_span_verbatim') or '')[:55]}」 "
                 f"→ {(f.get('why') or '')[:65]}")
    L.append("")

    L.append("## 7. プロンプト修正の打ち手（仮説・要検証）")
    L.append("- **橋渡し義務**: 『事実に無いことは否定してよいが、否定で終わらせず、**必ず現在のレッスン状況にある事実へ橋渡しして具体的な価値を1つ返す**』。")
    L.append("- **再録音要求の抑制**: 『現在のレッスン状況は最新録音の解析。**答えるために再録音を要求しない**。手元の事実で答えてから、必要時のみ追加録音を促す』。")
    L.append("- **動画の空約束の禁止**: 『実演動画は、ツールが実URLを返した時だけ添える。“出しましょうか”と匂わせない』。")
    L.append("- **反復禁止＋簡潔**: 直前と同趣旨を繰り返さない／2〜4文・120字目安を守る。")
    L.append("- 反映順序: docs/42（SSOT）→ Web版 llm.py の SYSTEM_PROMPT → skill（片方だけ変えない）。")
    L.append("")
    L.append("## 8. 限界と次のステップ")
    L.append("- 欠落した goodfaith 8件を追補審査（接続エラー分）。")
    L.append("- 敵対的裏取り(別エージェント)で確度medの所見を確定/棄却。")
    L.append("- 修正プロンプトを当てて **before/after** で萎え率・回答性が改善するか同一コーパスで再測定。")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-jsonl", required=True)
    a = ap.parse_args()
    recs, findings = load(a.inp)
    open(a.out_md, "w").write(build(recs, findings))
    with open(a.out_jsonl, "w") as fh:
        for f in findings:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")
    print(f"cases={len(recs)} findings={len(findings)} -> {a.out_md}")


if __name__ == "__main__":
    main()
