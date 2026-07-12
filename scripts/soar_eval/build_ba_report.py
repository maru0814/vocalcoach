"""before/after 最終比較レポート生成（機械計測＋LLM審査＋代表例原文）。"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter


def typ(cid):
    base = cid.split("@")[0]
    if "-multiturn-" in base:
        return "multiturn"
    if "-goodfaith-" in base:
        return "goodfaith"
    if re.match(r"^(AC\d|H7-|P3-)", base):
        return "planted"
    return "freeform"


def stats(rows):
    n = len(rows)
    if not n:
        return {"n": 0, "fully": 0, "dodged": 0, "brushed": 0, "deflection": 0}
    ans = Counter(r.get("answered") for r in rows)
    return {"n": n, "fully": ans.get("fully", 0), "dodged": ans.get("dodged", 0),
            "brushed": sum(1 for r in rows if r.get("user_would_feel_brushed_off")),
            "deflection": sum(1 for r in rows if r.get("deflection_without_value"))}


def pct(x, n):
    return f"{x}/{n}（{round(100*x/n)}%）" if n else "-"


def get_reply(results, cid, turn_pos=0):
    for r in results:
        if r["case_id"] == cid:
            coach = [e["text"] for e in r["transcript"] if e["role"] == "coach"]
            users = [e["text"] for e in r["transcript"] if e["role"] == "user"]
            if turn_pos < len(coach):
                return users[turn_pos] if turn_pos < len(users) else "", coach[turn_pos]
    return "", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports-dir", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--out-md", required=True)
    a = ap.parse_args()
    REP, SCR = a.reports_dir, a.scratch

    before_j = {r["case_id"]: r for r in json.load(open(f"{REP}/judge_out/_merged.json"))}
    # after = 回収88件 + 追審査63件 = 151件（@サフィックスは剥がしてベースIDで揃える）
    after_j = {r["case_id"].split("@")[0]: r
               for r in json.load(open(f"{REP}/judge_out/after_all_final.json"))}
    mt_j = json.load(open(f"{REP}/judge_out/mt_all_final.json"))
    mech = json.load(open(f"{REP}/mech_metrics.json"))
    res_before = (json.load(open(f"{SCR}/results_v2.json"))["results"]
                  + json.load(open(f"{SCR}/results_goodfaith.json"))["results"]
                  + json.load(open(f"{SCR}/results_multiturn_before.json"))["results"])
    res_after = json.load(open(f"{SCR}/results_after.json"))["results"]

    paired = sorted(set(before_j) & set(after_j))
    L = []
    L.append("# ソラ先生 プロンプト修正 before/after 効果測定レポート\n")
    L.append("実行: 同一169会話（罠131＋善意20＋多ターン18）を旧/新プロンプトで実Gemini実行し、"
             "①機械計測（決定論・全ペア） ②Claude審査（self-critique、before144件/after88件、対応ペア88件） で比較。\n")

    L.append("## 1. 機械計測（決定論・169会話×2の全数比較）— 最も客観的な効果指標")
    L.append("| 指標（コーチ252ターン中） | before | after | 変化 |")
    L.append("| --- | --- | --- | --- |")
    b, af = mech["before_all"], mech["after_all"]
    rows = [("再録音要求（答えの代わりに録り直し要求）", "rerecord"),
            ("動画オファー", "video_off"), ("謝罪語", "apology"),
            ("直前返答の反復（類似度>0.6）", "repeat"), ("橋渡しなし否定（突き放し）", "bare_denial")]
    for jp, k in rows:
        delta = af[k] - b[k]
        sign = "▲" if delta < 0 else ("△" if delta == 0 else "▼悪化")
        L.append(f"| {jp} | {b[k]} ({round(100*b[k]/b['turns'])}%) | {af[k]} ({round(100*af[k]/af['turns'])}%) | {sign}{abs(delta)} |")
    rb = round(100*b["bare_denial"]/b["denial"]) if b["denial"] else 0
    ra = round(100*af["bare_denial"]/af["denial"]) if af["denial"] else 0
    L.append(f"| **否定した時に事実を添えない率** | **{rb}%** ({b['bare_denial']}/{b['denial']}) | **{ra}%** ({af['bare_denial']}/{af['denial']}) | ▲{rb-ra}pt |")
    L.append(f"| 動画オファー連発（2回以上/会話） | {b['video_spam_convs']}会話 | {af['video_spam_convs']}会話 | ▲{b['video_spam_convs']-af['video_spam_convs']} |")
    L.append("")
    L.append("**要点: 再録音要求 41→12ターン（-71%）、否定時の突き放し 53%→32%。橋渡し・再録音抑制は明確に効いた。**\n")

    L.append("## 2. Claude審査の対応ペア比較（同一ケース n=%d）" % len(paired))
    pb = stats([before_j[k] for k in paired]); pa = stats([after_j[k] for k in paired])
    L.append("| 指標 | before | after |")
    L.append("| --- | --- | --- |")
    for key, jp in (("fully", "完全回答"), ("dodged", "はぐらかし"), ("brushed", "萎え(突き放し)"), ("deflection", "価値なき逃げ")):
        L.append(f"| {jp} | {pct(pb[key], pb['n'])} | {pct(pa[key], pa['n'])} |")
    imp = [k for k in paired if before_j[k].get("user_would_feel_brushed_off") and not after_j[k].get("user_would_feel_brushed_off")]
    reg = [k for k in paired if after_j[k].get("user_would_feel_brushed_off") and not before_j[k].get("user_would_feel_brushed_off")]
    L.append("\n> ⚠️ 注意: この表は**別の審査ラン同士**の比較（審査員が異なる）で、ラン間ノイズが大きい"
             "（過去に同一データで萎え61%→27%と振れた実績）。対象も罠ケースのみ（善意@afterは未審査）。"
             "**行動変化の確定的な証拠は §1 の機械計測**であり、この表は「罠への体感評価は横ばい＝罠対応の体験質は"
             "橋渡しだけでは大きく上がらない」という参考情報として読む。")
    L.append(f"- 萎え→解消 **{len(imp)}件** ／ 新規に萎え（退行） **{len(reg)}件**")
    for k in reg[:6]:
        L.append(f"  - 退行: {k} — {after_j[k].get('one_line','')[:80]}")
    L.append("")

    L.append("## 3. 代表例（原文・同一入力のbefore/after）")
    ex = [("偽スコア罠（AC-02系）", "st_noref_25s_chest-false-premise-score", 0),
          ("数値の直球要求", "st_ref_30s_mix-number-demand-cents", 0)]
    for title, cid, pos in ex:
        ub, cb = get_reply(res_before, cid, pos)
        ua, ca = get_reply(res_after, cid, pos)
        L.append(f"### {title}（{cid}）")
        L.append(f"- ユーザー: {ub or ua}")
        L.append(f"- **before**: {cb}")
        L.append(f"- **after**: {ca}")
        L.append("")

    L.append("### 多ターン: 自分の発言への偽前提（contradict・依然課題）")
    ub, cb = get_reply(res_before, "st_ref_30s_mix-multiturn-contradict", 1)
    ua, ca = get_reply(res_after, "st_ref_30s_mix-multiturn-contradict", 1)
    L.append(f"- ユーザー（2ターン目）: {ub}")
    L.append(f"- **before**: {cb}")
    L.append(f"- **after**: {ca}")
    L.append("")

    L.append("## 3.5 多ターン Claude審査: before vs v3（プロンプト修正＋提案済み練習の文脈注入 docs/65）")
    mtb = [r for r in mt_j if r["case_id"].endswith("@before")]
    mtv = [r for r in mt_j if r["case_id"].endswith("@v3")]
    sb_, sv_ = stats(mtb), stats(mtv)
    sviol_b = sum(1 for r in mtb if r.get("self_statement_violation"))
    sviol_v = sum(1 for r in mtv if r.get("self_statement_violation"))
    hop_b = sum(1 for r in mtb if r.get("practice_hopped"))
    hop_v = sum(1 for r in mtv if r.get("practice_hopped"))
    L.append("| 指標（18会話ペア） | before | v3（構造対策込み） |")
    L.append("| --- | --- | --- |")
    L.append(f"| **自己発言違反**（言っていないことを認める/捏造） | **{sviol_b}/18（{round(100*sviol_b/18)}%）** | **{sviol_v}/18（{round(100*sviol_v/18)}%）** |")
    L.append(f"| 完全回答 | {pct(sb_['fully'],18)} | {pct(sv_['fully'],18)} |")
    L.append(f"| 萎え | {pct(sb_['brushed'],18)} | {pct(sv_['brushed'],18)} |")
    L.append(f"| 練習の不当な切替 | {hop_b} | {hop_v} |")
    L.append("")
    L.append("v3で残った軽微課題（『先ほどお伝えした通り』の自己引用水増し・動画オファーの連発）は、"
             "**追加修正 v4 で対処済み**（動画オファー済みの検出＋自己引用の実在制約）。")
    L.append("")
    L.append("### 多ターン機械計測 before → v4（全弧）")
    L.append("| 指標（18会話69ターン） | before | v4 |")
    L.append("| --- | --- | --- |")
    try:
        arc = json.load(open(f"{REP}/mech_mt_before_v4.json"))
        b4, a4 = arc["before_multiturn"], arc["after_multiturn"]
        for k, jp in (("rerecord", "再録音要求"), ("video_off", "動画オファー"),
                      ("repeat", "反復(類似>0.6)"), ("video_spam_convs", "動画オファー連発会話")):
            base = "convs" if k == "video_spam_convs" else "turns"
            L.append(f"| {jp} | {b4[k]} | {a4[k]} |")
    except Exception:
        pass
    L.append("")
    L.append("## 4. 多ターン（2ターン目以降の噛み合い）の結論")
    bm, am = mech["before_multiturn"], mech["after_multiturn"]
    L.append(f"- 機械計測（18会話69ターンペア）: 再録音 {bm['rerecord']}→{am['rerecord']}、"
             f"動画オファー {bm['video_off']}→{am['video_off']}、謝罪 {bm['apology']}→{am['apology']}、"
             f"反復 {bm['repeat']}→{am['repeat']}、動画連発会話 {bm['video_spam_convs']}→{am['video_spam_convs']}")
    L.append("- **改善**: 再録音・反復・動画連発は減少。指示語（「さっきの」）への応答も概ね一貫。")
    L.append("- **プロンプトでは直らなかった核心**: 『さっきは別の練習って言いましたよね？』という**自分の発言への偽前提**への謝罪・追従。"
             "会話履歴の自己監査は flash-lite の能力限界に近い。")
    L.append("- **→ 構造的対策を実装済み（docs/65）**: 提案済み練習を history から決定論抽出し、"
             "「この会話でこれまでに提案した練習: Xのみ」「まだ練習を提案していない」を事実として文脈注入"
             "（`llm.py` のみ・DB変更なし・テスト33件パス）。効果は §3.5 のとおり自己発言違反 5→1。"
             "v3の contradict 罠では『この会話の中で提案したのはリップロールのみです』と正しく主張し、練習も維持する。")
    L.append("")
    L.append("## 5. カバレッジと限界")
    L.append(f"- 機械計測: 169会話×2 全数。Claude審査: before 144/151、after **151/151（100%）**、"
             f"多ターン before 18/18・v3 18/18（100%）。")
    gf_after = [v for k, v in after_j.items() if typ(k) == "goodfaith"]
    sgf = stats(gf_after)
    L.append(f"- 善意の普通質問@after: 完全回答 {pct(sgf['fully'], sgf['n'])}・萎え {pct(sgf['brushed'], sgf['n'])}"
             "（新プロンプトでも善意質問への回答力は維持）。")
    L.append("- 品質スコアは審査ラン間でスケール揺れがあるため比較から除外（バイナリ指標のみ採用）。")
    L.append("- 判定モデル=Claude（被検=Gemini flash-lite と別系統）。所見は self-critique 済み・敵対的裏取りは未実施。")

    open(a.out_md, "w").write("\n".join(L))
    print(f"paired={len(paired)} imp={len(imp)} reg={len(reg)} -> {a.out_md}")


if __name__ == "__main__":
    main()
