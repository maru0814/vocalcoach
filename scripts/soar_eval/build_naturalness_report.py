"""やり取りの自然さレポート（決定論計測＋Claude審査＋実例原文）。Claude審査結果は judge_out/nat_chunk*.json。"""
from __future__ import annotations

import argparse
import glob
import json
import re
from collections import Counter


def load_judge(rep):
    rows = []
    for f in sorted(glob.glob(f"{rep}/judge_out/nat_chunk*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        rows += d if isinstance(d, list) else d.get("results", [])
    return rows


def get_turn(results, cid, ti):
    for r in results:
        if r["case_id"] == cid:
            for e in r["transcript"]:
                if e["turn"] == ti:
                    return e["text"]
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports-dir", required=True)
    ap.add_argument("--metrics", required=True)      # naturalness_corpus.json
    ap.add_argument("--broad-metrics", required=True)  # naturalness_broad.json
    ap.add_argument("--results", required=True)       # results_naturalness.json
    ap.add_argument("--out-md", required=True)
    a = ap.parse_args()
    REP = a.reports_dir
    m = json.load(open(a.metrics))
    mb = json.load(open(a.broad_metrics))
    results = json.load(open(a.results))["results"]
    judge = load_judge(REP)

    sc = [r.get("naturalness_score") for r in judge if isinstance(r.get("naturalness_score"), (int, float))]
    avg = round(sum(sc) / len(sc), 1) if sc else 0
    tempo = sum(1 for r in judge if r.get("tempo_mismatch"))
    pushy = sum(1 for r in judge if r.get("pushy_redirect"))
    templ = sum(1 for r in judge if r.get("templated"))
    findings = [dict(f, case_id=r["case_id"]) for r in judge for f in (r.get("findings") or [])
                if (f.get("confidence") or "").lower() != "low"]
    bydim = Counter(f.get("dimension") for f in findings)

    L = []
    L.append("# ソラ先生 やり取りの自然さ 検査レポート\n")
    L.append("> 対象: マージ後の本番プロンプト（PR #160）。カジュアル/感情/短い相槌の48会話を実Geminiで実行し、"
             "①決定論のテンプレ臭さ計測（全数）②Claude自然さ審査（人間コーチなら何と返すか）で診断。"
             "ハルシネーション・事実誤りは対象外——**会話としての自然さだけ**を見る。\n")

    L.append("## 1. 結論")
    L.append(f"**自然さスコア 平均 {avg}/10（{len(judge)}会話）。テンポ不一致 {tempo}/{len(judge)}、"
             f"押し付け誘導 {pushy}/{len(judge)}、テンプレ音声 {templ}/{len(judge)}。**")
    L.append("正体は **テンポ不一致＋押し付け＋テンプレ音声**。「うん」「へー」「やった」のような一言や雑談・感情の吐露に、"
             "毎回100〜160字の講義で返し、必ず『録音を送って』『練習メニューを一緒に作りましょうか』へ引き戻す。"
             "**ソラ先生は雑談・共感ができず、常にレッスンへ引きずり込む。** これは人間のコーチではなくボットの応対に感じられる。\n")

    L.append("## 2. 決定論のテンプレ臭さ計測（Claude不要・全数）")
    L.append(f"### カジュアル48会話 / コーチ{m['coach_turns']}ターン")
    L.append(f"- 平均 **{m['avg_chars']}字** / **120字超 {m['over_120_chars'][1]}%**（短い相槌にも講義）"
             f" / 疑問で締める {m['question_end_rate'][1]}% / 絵文字 {m['emoji_turn_rate'][1]}%")
    L.append("- 常套句の出現ターン率（多いほどテンプレ臭い）:")
    for name, (h, r) in sorted(m["phrase_rate"].items(), key=lambda x: -x[1][1])[:6]:
        L.append(f"  - {name}: **{r}%**（{h}ターン）")
    L.append(f"- 締めの定型 TOP: " + " / ".join(f"「…{t}」×{c}" for t, c in m["top_tails"][:3]))
    L.append(f"\n（参考: 罠中心の広域169会話でも 120字超 {mb['over_120_chars'][1]}%・"
             f"「もしよろしければ」{mb['phrase_rate']['もしよろしければ'][1]}% と同傾向）\n")

    L.append("## 3. Claude審査の観点別所見")
    for d, c in bydim.most_common():
        L.append(f"- {d}: {c}件")
    L.append("")

    L.append("## 4. 代表例（実際のやり取り・原文と「人間ならこう返す」）")
    # tempo_mismatch と 押し付け を優先、スコア低い会話から
    key_dims = ("テンポ不一致", "押し付け", "感情応答", "蒸し返し")
    shown = 0
    seen_cases = set()
    for r in sorted(judge, key=lambda r: r.get("naturalness_score", 10)):
        for f in (r.get("findings") or []):
            if (f.get("confidence") or "").lower() == "low":
                continue
            if f.get("dimension") not in key_dims:
                continue
            if r["case_id"] in seen_cases:
                continue
            seen_cases.add(r["case_id"])
            L.append(f"### [{f.get('dimension')}] {r['case_id']}（自然さ{r.get('naturalness_score')}/10）")
            L.append(f"- ユーザー: 「{f.get('user_turn_verbatim','')}」")
            L.append(f"- **コーチ（実際）**: {f.get('coach_span_verbatim','')}")
            L.append(f"- **人間コーチなら**: {f.get('natural_version','')}")
            L.append(f"- なぜ不自然か: {f.get('why','')}")
            L.append("")
            shown += 1
            break
        if shown >= 8:
            break

    L.append("## 5. 推定原因と打ち手（仮説）")
    L.append("- **原因**: SYSTEM_PROMPT が「120字程度」と書いても守られない＋『問いかけ/オファーを1つ添える』が"
             "全ターンで発火し、雑談でも練習誘導になる。段階的エンゲージメント(§8)が“常に前進させる”方向に効きすぎ。")
    L.append("- **打ち手A（軽量・プロンプト）**: 「短い相槌・雑談・感情の吐露には、まず一言で受け止めて短く返す"
             "（練習誘導・録音依頼をしない）。長文の講義をしない」を会話ルールに追加。")
    L.append("- **打ち手B（構造・確実）**: 直前のユーザー発言が短い/雑談的（例: 10字未満、相槌語）なら、"
             "システム側で『今回は短く相槌だけ。練習・録音の誘導を付けない』を文脈注入（提案済み練習と同じ事実注入パターン）。")
    L.append("- **打ち手C**: 温かい雑談では絵文字0%が無機質。ペルソナの『絵文字0〜2個』を実際に出させる。")
    L.append("- before/after は本ハーネス（cases_naturalness.py＋naturalness_metrics.py）で同一コーパス再測定できる。")
    L.append("")
    L.append("## 6. 限界")
    L.append("- 被検 Gemini flash-lite。Claude審査は self-critique 済み・敵対的裏取り未実施。"
             "自然さスコアは審査員の主観だが、決定論計測（120字超76%・常套句率）が独立に同結論を支持する。")
    open(a.out_md, "w").write("\n".join(L))
    print(f"judge={len(judge)} avg={avg} findings={len(findings)} -> {a.out_md}")


if __name__ == "__main__":
    main()
