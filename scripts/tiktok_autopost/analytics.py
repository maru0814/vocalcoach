#!/usr/bin/env python3
"""投稿パフォーマンス分析。posts_log.jsonl + metrics_log.jsonl を結合して傾向を出す。

使い方:
  python analytics.py              # レポートをターミナルに表示
  python analytics.py --weeks 4    # 直近4週分（既定2週）
  python analytics.py --notify     # レポートをLINE/Discordに送信
"""
import argparse
import datetime
import json
import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_LOG = os.path.join(_DIR, "posts_log.jsonl")
METRICS_LOG = os.path.join(_DIR, "metrics_log.jsonl")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_DIR, ".env"))
except Exception:
    pass


def _read_jsonl(path: str) -> list:
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
    return rows


def _week_label(ts_str: str) -> str:
    """ISO timestampから'W26'形式の週ラベルを返す。"""
    try:
        dt = datetime.datetime.fromisoformat(ts_str)
        return dt.strftime("W%W")
    except Exception:
        return "W??"


def build_report(weeks: int = 2) -> str:
    """分析レポートのテキストを返す（日本語、LINE送信想定）。"""
    posts = {p["publish_id"]: p for p in _read_jsonl(POSTS_LOG) if p.get("publish_id")}
    metrics_raw = _read_jsonl(METRICS_LOG)

    # publish_id ごとに最新のメトリクスを取る（複数回取得した場合は最新）
    metrics: dict[str, dict] = {}
    for m in metrics_raw:
        pid = m.get("publish_id")
        if not pid:
            continue
        if pid not in metrics or m.get("ts", "") > metrics[pid].get("ts", ""):
            metrics[pid] = m

    # 週フィルタ
    cutoff = (datetime.datetime.now() - datetime.timedelta(weeks=weeks)).isoformat()

    # posts_log + metrics を結合
    joined = []
    for pid, post in posts.items():
        if post.get("ts", "") < cutoff:
            continue
        m = metrics.get(pid, {})
        joined.append({
            "publish_id": pid,
            "hook": post.get("hook", ""),
            "pillar": post.get("pillar", "tip"),
            "ts": post.get("ts", ""),
            "week": _week_label(post.get("ts", "")),
            "views": m.get("views"),
            "completion": m.get("completion"),
            "comments": m.get("comments"),
            "has_metrics": pid in metrics,
        })

    total_posts = len(joined)
    measured = [r for r in joined if r["has_metrics"]]

    lines = [
        "📊 TikTokパフォーマンスレポート",
        f"集計期間: 直近{weeks}週間 / {datetime.date.today().isoformat()}",
        f"投稿数: {total_posts}本（指標あり: {len(measured)}本）",
        "",
    ]

    if not measured:
        lines.append("まだ指標データがありません。")
        lines.append("fetch_metrics.py --manual で数値を入力してください。")
        return "\n".join(lines)

    # ─── フック別ランキング ───────────────────────────────
    hook_stats: dict[str, dict] = {}
    for r in measured:
        hook = r["hook"] or "(フックなし)"
        s = hook_stats.setdefault(hook, {"views": [], "completion": [], "comments": [], "n": 0})
        s["n"] += 1
        if r["views"] is not None:
            s["views"].append(r["views"])
        if r["completion"] is not None:
            s["completion"].append(r["completion"])
        if r["comments"] is not None:
            s["comments"].append(r["comments"])

    def _avg(lst):
        return sum(lst) / len(lst) if lst else None

    ranked = sorted(
        hook_stats.items(),
        key=lambda kv: _avg(kv[1]["views"]) or 0,
        reverse=True,
    )

    lines.append("▼ フック別ランキング（再生数順）")
    for i, (hook, s) in enumerate(ranked[:5], 1):
        avg_v = _avg(s["views"])
        avg_cr = _avg(s["completion"])
        avg_c = _avg(s["comments"])
        cr_str = f"完了率{avg_cr*100:.0f}%" if avg_cr is not None else "完了率-"
        c_str = f"コメ{avg_c:.1f}" if avg_c is not None else ""
        v_str = f"{avg_v:,.0f}再生" if avg_v is not None else "-再生"
        display_hook = hook[:18] + "…" if len(hook) > 18 else hook
        lines.append(f"  {i}. 「{display_hook}」")
        lines.append(f"     {v_str}  {cr_str}  {c_str}  ({s['n']}本)")
    lines.append("")

    # ─── 週次トレンド ─────────────────────────────────────
    week_stats: dict[str, dict] = {}
    for r in measured:
        w = r["week"]
        s = week_stats.setdefault(w, {"views": [], "completion": []})
        if r["views"] is not None:
            s["views"].append(r["views"])
        if r["completion"] is not None:
            s["completion"].append(r["completion"])

    sorted_weeks = sorted(week_stats.keys())
    if len(sorted_weeks) >= 2:
        lines.append("▼ 週次トレンド（再生数平均）")
        prev_avg = None
        for w in sorted_weeks[-4:]:
            s = week_stats[w]
            avg_v = _avg(s["views"])
            avg_cr = _avg(s["completion"])
            v_str = f"{avg_v:,.0f}" if avg_v is not None else "-"
            cr_str = f"({avg_cr*100:.0f}%)" if avg_cr is not None else ""
            if prev_avg is not None and avg_v is not None and prev_avg > 0:
                delta = (avg_v - prev_avg) / prev_avg * 100
                arrow = "↑" if delta >= 0 else "↓"
                trend = f" {arrow}{abs(delta):.0f}%"
            else:
                trend = ""
            lines.append(f"  {w}: {v_str}再生 {cr_str}{trend}")
            if avg_v is not None:
                prev_avg = avg_v
        lines.append("")

    # ─── 全体平均 ─────────────────────────────────────────
    all_v = [r["views"] for r in measured if r["views"] is not None]
    all_cr = [r["completion"] for r in measured if r["completion"] is not None]
    all_c = [r["comments"] for r in measured if r["comments"] is not None]
    lines.append("▼ 全体平均")
    if all_v:
        lines.append(f"  再生数: {_avg(all_v):,.0f}")
    if all_cr:
        lines.append(f"  視聴完了率: {_avg(all_cr)*100:.1f}%")
    if all_c:
        lines.append(f"  コメント数: {_avg(all_c):.1f}")
    lines.append("")

    # ─── フックパターン分析 ────────────────────────────────
    def _hook_pattern(hook: str) -> str:
        """フックを文体パターンに分類する。"""
        h = hook
        if any(c in h for c in ("?", "？")):
            return "疑問形"
        if any(w in h for w in ("は嘘", "じゃない", "間違い", "ではない", "変わらない", "NG", "必要ない")):
            return "常識否定"
        if any(w in h for w in ("人だけ", "人だけ見て", "てる人", "人、", "だけ見て")):
            return "限定ターゲット"
        if any(c.isdigit() for c in h):
            return "数字入り"
        if any(w in h for w in ("して", "しよう", "やって", "試して")):
            return "行動促し"
        return "断定"

    pattern_stats: dict[str, dict] = {}
    for hook, s in hook_stats.items():
        ptn = _hook_pattern(hook)
        ps = pattern_stats.setdefault(ptn, {"views": [], "completion": [], "n": 0})
        ps["n"] += s["n"]
        ps["views"].extend(s["views"])
        ps["completion"].extend(s["completion"])

    ranked_patterns = sorted(
        pattern_stats.items(),
        key=lambda kv: _avg(kv[1]["views"]) or 0,
        reverse=True,
    )

    lines.append("▼ フックパターン別 傾向考察")
    if ranked_patterns:
        best_ptn, best_ps = ranked_patterns[0]
        best_avg_v = _avg(best_ps["views"])
        best_avg_cr = _avg(best_ps["completion"])
        lines.append(f"  最も伸びたパターン: 【{best_ptn}】")
        if best_avg_v is not None:
            lines.append(f"  → 平均{best_avg_v:,.0f}再生（{best_ps['n']}本）")

        for ptn, ps in ranked_patterns:
            avg_v = _avg(ps["views"])
            avg_cr = _avg(ps["completion"])
            v_str = f"{avg_v:,.0f}再生" if avg_v is not None else "-"
            cr_str = f" 完了率{avg_cr*100:.0f}%" if avg_cr is not None else ""
            lines.append(f"  {ptn}: {v_str}{cr_str}  ({ps['n']}本)")
        lines.append("")

        # 考察コメント: 再生は高いが完了率が低いパターンを検出
        high_v_low_cr = [
            (ptn, ps) for ptn, ps in ranked_patterns
            if (_avg(ps["views"]) or 0) > (_avg(all_v) if all_v else 0)
            and (_avg(ps["completion"]) or 1) < (_avg(all_cr) if all_cr else 1)
            and ps["completion"]
        ]
        high_v_high_cr = [
            (ptn, ps) for ptn, ps in ranked_patterns
            if (_avg(ps["views"]) or 0) > (_avg(all_v) if all_v else 0)
            and (_avg(ps["completion"]) or 0) >= (_avg(all_cr) if all_cr else 0)
            and ps["completion"]
        ]

        lines.append("▼ 考察")
        if high_v_high_cr:
            ptns = "・".join(p for p, _ in high_v_high_cr[:2])
            lines.append(f"  【伸びやすい型】{ptns}")
            lines.append("  → 再生も完了率も高い。フック+内容の両方が刺さっている。優先的に量産。")
        if high_v_low_cr:
            ptns = "・".join(p for p, _ in high_v_low_cr[:2])
            lines.append(f"  【フックは強いが完走されにくい型】{ptns}")
            lines.append("  → 指は止まるが最後まで見られていない。本文の密度を上げるか尺を短くする。")

        # 週次トレンドの考察
        if len(sorted_weeks) >= 2:
            last_w = sorted_weeks[-1]
            prev_w = sorted_weeks[-2]
            last_v = _avg(week_stats[last_w]["views"])
            prev_v = _avg(week_stats[prev_w]["views"])
            if last_v is not None and prev_v is not None and prev_v > 0:
                delta_pct = (last_v - prev_v) / prev_v * 100
                if delta_pct >= 20:
                    lines.append(f"  【週次伸び率 +{delta_pct:.0f}%】アルゴリズムに乗り始めている可能性。")
                    lines.append("  → 投稿頻度を週5〜7本に増やすタイミング。")
                elif delta_pct <= -20:
                    lines.append(f"  【週次落ち幅 {delta_pct:.0f}%】直近フックのテーマが飽和している可能性。")
                    lines.append(f"  → 「{best_ptn}」パターンの新テーマを仕込む（themes.py の TIPS を更新）。")
                else:
                    lines.append(f"  【週次横ばい ({delta_pct:+.0f}%)】安定期。フックのバリエーションを増やして突破口を探す。")
    else:
        lines.append("  （フックデータが不足しています）")
        lines.append("")

    # ─── アクション ───────────────────────────────────────
    lines.append("▼ 今週のアクション")
    avg_cr_all = _avg(all_cr)
    if ranked_patterns:
        best_ptn = ranked_patterns[0][0]
        lines.append(f"  1. 次回フックは【{best_ptn}】パターンで書く")
    if avg_cr_all is not None and avg_cr_all < 0.4:
        lines.append("  2. 完了率40%未満 → 尺を20秒以内に詰めるか冒頭2秒のフックを書き直す")
    elif avg_cr_all is not None and avg_cr_all >= 0.6:
        lines.append("  2. 完了率60%超 → 投稿頻度を上げて露出拡大するチャンス")
    else:
        lines.append("  2. 完了率50%前後 → フック強化と尺調整を同時に試す")
    lines.append("  3. python fetch_metrics.py --manual で最新値を入力")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=2, help="集計対象の週数（既定2）")
    ap.add_argument("--notify", action="store_true", help="レポートをLINE/Discordに送信")
    args = ap.parse_args()

    report = build_report(weeks=args.weeks)
    print(report)

    if args.notify:
        import notifier
        notifier.send_report(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
