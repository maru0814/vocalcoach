"""回収した審査出力(salvaged_judge.json)から、全方位ホリスティックレポートを組む（Claude不要）。

judge単独（verify未実施）のため所見は unverified 扱いで正直に明記する。
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict

DIM_NORM = {
    "過剰拒否・逃げ": "過剰拒否", "具体性・次の一歩": "具体性", "文脈整合・自然さ": "文脈整合",
    "冗長/長すぎ": "冗長", "萎え・失望": "萎え",
}
SEV_ORDER = {"S1": 0, "S2": 1, "S3": 2}


def typ(cid: str) -> str:
    if cid and "-goodfaith-" in cid:
        return "goodfaith"
    if cid and re.match(r"^(AC\d|H7-|P3-)", cid):
        return "planted"
    return "freeform"


def norm_dim(d: str) -> str:
    return DIM_NORM.get(d, d or "その他")


def load(path: str):
    recs = json.load(open(path))
    findings = []
    for r in recs:
        for f in (r.get("findings") or []):
            f = dict(f)
            f["case_id"] = r.get("case_id")
            f["dimension"] = norm_dim(f.get("dimension"))
            findings.append(f)
    return recs, findings


def ex_block(f: dict) -> list[str]:
    L = [f"- **{f.get('case_id')}** ／ {f.get('severity','')} ／ 観点: {f.get('dimension','')}",
         f"  - ユーザー: {f.get('user_turn_verbatim','') or '（冒頭）'}",
         f"  - コーチ（原文）: 「{f.get('coach_span_verbatim','')}」",
         f"  - なぜ萎える/問題か: {f.get('why','')}"]
    if f.get("better_response"):
        L.append(f"  - あるべき返答: {f['better_response']}")
    return L


def build(recs, findings) -> str:
    n = len(recs)
    ans = Counter(r.get("answered") for r in recs)
    brushed = sum(1 for r in recs if r.get("user_would_feel_brushed_off"))
    defl = sum(1 for r in recs if r.get("deflection_without_value"))
    q = [r.get("overall_quality") for r in recs if isinstance(r.get("overall_quality"), (int, float))]
    qavg = round(sum(q) / len(q), 2) if q else 0
    bytype = defaultdict(lambda: {"n": 0, "brushed": 0, "dodged": 0})
    for r in recs:
        t = typ(r.get("case_id"))
        bytype[t]["n"] += 1
        if r.get("user_would_feel_brushed_off"):
            bytype[t]["brushed"] += 1
        if r.get("answered") == "dodged":
            bytype[t]["dodged"] += 1
    bydim = Counter(f["dimension"] for f in findings)
    bysev = Counter(f.get("severity") for f in findings)

    # 「録音済みなのに再送要求」検出（最重要パターンの定量化）
    reask = [f for f in findings if re.search(r"(もう一度|再度|また).{0,8}(録音|歌).{0,6}(送|録)", f.get("coach_span_verbatim", ""))]

    L = []
    L.append("# ソラ先生 会話品質「全方位」検査レポート（ホリスティック審査）\n")
    L.append("> 各会話を Claude 審査員が **回答性・過剰拒否(逃げ)・有用性・萎え・文脈整合・誠実さ・具体性・トーン** で診断。")
    L.append("> ルールベースの機械指摘ではなく、**ユーザー体験**を主軸に評価している。\n")
    L.append("> ⚠️ **カバレッジ注記**: セッション上限により、審査は 151会話中 **101会話（planted 11 + freeform 90）** まで完了。")
    L.append("> 善意の普通質問(goodfaith 20)と一部状態は未審査（次回リセット後に追補）。また敵対的裏取り(verify)も上限で未実施のため、")
    L.append("> 本レポートの所見は **審査員1名の判定（unverified）**。傾向は明確だが、個別の断定は裏取り後に確定する。\n")

    L.append("## 1. エグゼクティブサマリ")
    L.append(f"- 審査会話数: **{n}**（コーチ返答を全方位診断）")
    L.append(f"- 質問への回答: **fully {ans.get('fully',0)} / partial {ans.get('partial',0)} / dodged {ans.get('dodged',0)}** "
             f"（＝ちゃんと答えられたのは **{round(100*ans.get('fully',0)/n)}%** のみ）")
    L.append(f"- **ユーザーが萎える/突き放されたと感じる会話: {brushed}/{n}（{round(100*brushed/n)}%）**")
    L.append(f"- **価値を出さず逃げた会話: {defl}/{n}（{round(100*defl/n)}%）**")
    L.append(f"- 会話品質 平均 **{qavg}/5**（1〜2の低品質が {sum(1 for x in q if x<=2)}会話）")
    L.append(f"- 所見総数 {len(findings)}（S1={bysev.get('S1',0)} / S2={bysev.get('S2',0)} / S3={bysev.get('S3',0)}）")
    L.append("")
    L.append("### 一言")
    L.append("**ハルシネーションはよく抑えられている。問題はその裏側——「事実に無い」と正しく否定した後、"
             "手元にある解析事実へ橋渡しせず『もう一度録音を送って』と突き放す“過剰拒否”。"
             "結果、ユーザーは『大した回答をくれない』と感じ、真面目に話す気を失う。**\n")

    L.append("## 2. 最重要の失敗パターン")
    L.append(f"### ① 録音済みなのに「もう一度送って」と再送要求（{len(reask)}件で検出）")
    L.append("会話文脈には『解析事実はいちばん最後に送られた録音のもの（古い録音ではない）』と**明記されている**のに、"
             "コーチは手元の事実を使わず再録音を要求する。答えられるのに答えていない典型。反ハルシネーションの防御が過剰化した結果。")
    picked = [f for f in reask if f.get("better_response")][:4]
    for f in picked:
        L += ex_block(f)
    L.append("")
    L.append("### ② 偽前提を否定して終わり、価値へ橋渡ししない")
    L.append("「F#5だった/95点だった/30秒のところ」等の偽前提を**正しく否定**するが、"
             "『でも今の録音から言えることはこれ』という橋渡しが無く、否定だけで突き放す。")
    bridge = [f for f in findings if f["dimension"] in ("過剰拒否", "有用性")
              and f.get("severity") == "S1" and f.get("better_response")
              and f not in picked][:3]
    for f in bridge:
        L += ex_block(f)
    L.append("")
    L.append("### ③ 同じ返答の使い回し（2ターン目に前と同じことを言う）")
    rep = [f for f in findings if re.search(r"(繰り返|使い回|同一|同じ返答|スルー)", f.get("why", ""))][:2]
    for f in rep:
        L += ex_block(f)
    if not rep:
        L.append("_（このパターンは所見の why に散見。裏取り後に定量化）_")
    L.append("")

    L.append("## 3. 観点別の所見件数")
    for d, c in bydim.most_common():
        L.append(f"- {d}: {c}件")
    L.append("")

    L.append("## 4. 回答状況の内訳（case_type別）")
    for t, v in bytype.items():
        L.append(f"- {t}: {v['n']}会話中、萎え {v['brushed']}・はぐらかし {v['dodged']}")
    L.append("_※今回は罠中心のコーパス。善意質問(goodfaith)は未審査のため、"
             "『答えられる時にちゃんと答えているか』の公平な評価は次回追補。_\n")

    L.append("## 5. 深刻度順・全確定所見（S1→S2→S3）")
    for f in sorted(findings, key=lambda x: (SEV_ORDER.get(x.get("severity"), 9), x["dimension"])):
        L.append(f"- [{f.get('severity')}/{f['dimension']}] **{f.get('case_id')}** "
                 f"— U:「{(f.get('user_turn_verbatim') or '')[:30]}」 / "
                 f"C:「{(f.get('coach_span_verbatim') or '')[:60]}」 → {(f.get('why') or '')[:70]}")
    L.append("")

    L.append("## 6. プロンプト修正の打ち手（仮説・要検証）")
    L.append("- **「橋渡し義務」を明文化**: SYSTEM_PROMPT に『事実に無いことは否定してよいが、"
             "**否定で終わらせず、必ず現在のレッスン状況にある事実へ橋渡しして具体的な価値を1つ返す**』を追加。")
    L.append("- **再録音要求の抑制**: 『現在のレッスン状況は最新録音の解析。"
             "**答えるために再録音を要求しない**。手元の事実で答えてから、必要な時だけ追加録音を促す』。")
    L.append("- **反復の禁止**: 『直前の自分の返答と同じ趣旨を繰り返さない。2度目の訴えには一段深く応じる』（§6の運用強化）。")
    L.append("- 変更は docs/42（SSOT）→ Web版 llm.py の SYSTEM_PROMPT / skill の順で反映（片方だけ変えない）。")
    L.append("")
    L.append("## 7. 限界と次のステップ")
    L.append("- 未審査の goodfaith 20 + 未完了分 = 50会話を次回（上限リセット後）に審査し、"
             "『答えられる時に答えているか』を公平に測る。")
    L.append("- 敵対的裏取り(verify)を実施し、各所見の誤検出を棄却して確定版にする。")
    L.append("- 判定コストが高い（今回 380エージェント）ため、judge+self-critique を1エージェントに統合してコスト削減する。")
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
            f = dict(f); f["verified"] = False; f["verifier"] = "judge_only"
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")
    print(f"cases={len(recs)} findings={len(findings)} -> {a.out_md}")


if __name__ == "__main__":
    main()
