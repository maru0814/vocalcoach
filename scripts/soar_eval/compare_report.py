"""before/after 比較レポート（プロンプト修正の効果測定）。Claude不要。

- before: judge_out/_merged.json（旧プロンプトの151件コーパス審査・サフィックス無しID）
- after : judge_out/cmp_batch*.json のうち @after（新プロンプトの169件）
- 多ターン: cmp_batch*.json の @before / @after ペア（同一審査ラン内なので直接比較可）

品質スコアは審査ラン間でスケールが揺れるため、ラン間比較は fully/dodged/brushed/deflection の
バイナリ指標を主とする（品質は同一ラン内の参考値）。
"""
from __future__ import annotations

import argparse
import glob
import json
import re
from collections import Counter, defaultdict

DIM_NORM = {"過剰拒否・逃げ": "過剰拒否", "具体性・次の一歩": "具体性",
            "文脈整合・自然さ": "文脈整合", "冗長/長すぎ": "冗長", "萎え・失望": "萎え"}


def typ(cid: str) -> str:
    base = cid.split("@")[0]
    if "-multiturn-" in base:
        return "multiturn"
    if "-goodfaith-" in base:
        return "goodfaith"
    if re.match(r"^(AC\d|H7-|P3-)", base):
        return "planted"
    return "freeform"


def load_judged(paths: list[str]) -> dict[str, dict]:
    out = {}
    for p in paths:
        try:
            data = json.load(open(p))
        except Exception:
            continue
        rows = data if isinstance(data, list) else data.get("results", [])
        for r in rows:
            cid = r.get("case_id")
            if cid and cid not in out:
                out[cid] = r
    return out


def stats(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0}
    ans = Counter(r.get("answered") for r in rows)
    return {
        "n": n,
        "fully": ans.get("fully", 0), "partial": ans.get("partial", 0), "dodged": ans.get("dodged", 0),
        "brushed": sum(1 for r in rows if r.get("user_would_feel_brushed_off")),
        "deflection": sum(1 for r in rows if r.get("deflection_without_value")),
        "findings": sum(len(r.get("findings") or []) for r in rows),
    }


def pct(x, n):
    return f"{x}/{n}（{round(100*x/n)}%）" if n else "-"


def row(label, s):
    if not s.get("n"):
        return f"| {label} | - | - | - | - | - |"
    n = s["n"]
    return (f"| {label} | {n} | {pct(s['fully'],n)} | {pct(s['dodged'],n)} | "
            f"{pct(s['brushed'],n)} | {pct(s['deflection'],n)} |")


def dim_counter(rows):
    c = Counter()
    for r in rows:
        for f in (r.get("findings") or []):
            if (f.get("confidence") or "").lower() == "low":
                continue
            c[DIM_NORM.get(f.get("dimension"), f.get("dimension") or "その他")] += 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports-dir", required=True)
    ap.add_argument("--out-md", required=True)
    a = ap.parse_args()
    REP = a.reports_dir

    before = load_judged([f"{REP}/judge_out/_merged.json"])
    cmp_all = load_judged(sorted(glob.glob(f"{REP}/judge_out/cmp_batch*.json")))
    after = {k.split("@")[0]: v for k, v in cmp_all.items() if k.endswith("@after")}
    mt_before = {k.split("@")[0]: v for k, v in cmp_all.items() if k.endswith("@before")}
    mt_after = {k: v for k, v in after.items() if typ(k) == "multiturn"}
    core_after = {k: v for k, v in after.items() if typ(k) != "multiturn"}

    # ペア比較（同一 case_id が before/after 両方に居るもの）
    paired = sorted(set(before) & set(core_after))

    L = []
    L.append("# ソラ先生 プロンプト修正 before/after 比較レポート\n")
    L.append("> 修正内容（docs/42 2026-07-10）: ①橋渡し義務（否定で終わらせない） ②答えるための再録音要求の禁止 "
             "③§8枠外の動画匂わせ禁止 ④反復禁止・指示語は自分の実発言を参照。\n"
             "> before=旧プロンプト / after=新プロンプト。審査は同一ルーブリック（自己批判つきバッチ審査）。"
             "ラン間の品質スコアはスケール揺れがあるためバイナリ指標（回答性・萎え・逃げ）で比較する。\n")

    L.append("## 1. 全体比較（罠＋善意コーパス）")
    L.append("| 指標 | 会話数 | 完全回答 | はぐらかし | 萎え | 価値なき逃げ |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    L.append(row("before（旧）", stats([before[k] for k in before if typ(k) != "multiturn"])))
    L.append(row("**after（新）**", stats(list(core_after.values()))))
    L.append("")

    L.append("### ペア比較（同一ケースのみ, n=%d）" % len(paired))
    L.append("| 指標 | before | after |")
    L.append("| --- | --- | --- |")
    pb = stats([before[k] for k in paired]); pa = stats([core_after[k] for k in paired])
    for key, jp in (("fully", "完全回答"), ("dodged", "はぐらかし"), ("brushed", "萎え"), ("deflection", "価値なき逃げ")):
        L.append(f"| {jp} | {pct(pb[key], pb['n'])} | {pct(pa[key], pa['n'])} |")
    L.append("")

    L.append("## 2. case_type 別（after）と before の対比")
    L.append("| 種別 | before 萎え | after 萎え | before 完全回答 | after 完全回答 |")
    L.append("| --- | --- | --- | --- | --- |")
    for t, name in (("planted", "仕掛け(偽前提)"), ("freeform", "自由型(敵対)"), ("goodfaith", "善意の普通質問")):
        sb = stats([v for k, v in before.items() if typ(k) == t])
        sa = stats([v for k, v in core_after.items() if typ(k) == t])
        L.append(f"| {name} | {pct(sb.get('brushed',0), sb.get('n',0))} | {pct(sa.get('brushed',0), sa.get('n',0))} | "
                 f"{pct(sb.get('fully',0), sb.get('n',0))} | {pct(sa.get('fully',0), sa.get('n',0))} |")
    L.append("")

    L.append("## 3. 多ターン（2ターン目以降の噛み合い）before/after")
    L.append("同一審査ラン内での直接比較（18会話ペア）。")
    L.append("| 指標 | before | after |")
    L.append("| --- | --- | --- |")
    sb = stats(list(mt_before.values())); sa = stats(list(mt_after.values()))
    for key, jp in (("fully", "完全回答"), ("dodged", "はぐらかし"), ("brushed", "萎え"),
                    ("deflection", "価値なき逃げ"), ("findings", "所見数(全)")):
        vb = sb.get(key, 0); va = sa.get(key, 0)
        if key == "findings":
            L.append(f"| {jp} | {vb} | {va} |")
        else:
            L.append(f"| {jp} | {pct(vb, sb.get('n',0))} | {pct(va, sa.get('n',0))} |")
    db = dim_counter(mt_before.values()); da = dim_counter(mt_after.values())
    dims = sorted(set(db) | set(da), key=lambda d: -(db.get(d, 0) + da.get(d, 0)))
    L.append("")
    L.append("| 観点別所見 | before | after |")
    L.append("| --- | --- | --- |")
    for d in dims:
        L.append(f"| {d} | {db.get(d,0)} | {da.get(d,0)} |")
    L.append("")

    L.append("## 4. 観点別所見（罠＋善意, before vs after）")
    db = dim_counter([before[k] for k in before if typ(k) != "multiturn"])
    da = dim_counter(core_after.values())
    L.append("| 観点 | before | after |")
    L.append("| --- | --- | --- |")
    for d in sorted(set(db) | set(da), key=lambda d: -(db.get(d, 0) + da.get(d, 0))):
        L.append(f"| {d} | {db.get(d,0)} | {da.get(d,0)} |")
    L.append("")

    # 5. 悪化ケース（after で萎え/dodged になったのに before はOKだった）
    regressed = [k for k in paired
                 if (core_after[k].get("user_would_feel_brushed_off") and not before[k].get("user_would_feel_brushed_off"))
                 or (core_after[k].get("answered") == "dodged" and before[k].get("answered") != "dodged")]
    improved = [k for k in paired
                if (before[k].get("user_would_feel_brushed_off") and not core_after[k].get("user_would_feel_brushed_off"))]
    L.append("## 5. 改善/悪化の個別ケース")
    L.append(f"- 萎え→解消: **{len(improved)}件** / 新規に萎え・はぐらかし化（退行）: **{len(regressed)}件**")
    if regressed:
        L.append("\n### 退行ケース（要確認）")
        for k in regressed[:10]:
            L.append(f"- {k}: after判定「{core_after[k].get('one_line','')[:90]}」")
    if improved:
        L.append("\n### 改善ケース（例）")
        for k in improved[:8]:
            L.append(f"- {k}: after判定「{core_after[k].get('one_line','')[:90]}」")
    L.append("")

    open(a.out_md, "w").write("\n".join(L))
    print(f"before={len(before)} after={len(core_after)} mt_before={len(mt_before)} mt_after={len(mt_after)}"
          f" paired={len(paired)} -> {a.out_md}")


if __name__ == "__main__":
    main()
