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

    # ─── アドバイス ───────────────────────────────────────
    lines.append("▼ 改善ヒント")
    if ranked:
        top_hook = ranked[0][0][:18]
        lines.append(f"  ・「{top_hook}」型のフックを増やす")
    if all_cr:
        avg_cr_all = _avg(all_cr)
        if avg_cr_all is not None and avg_cr_all < 0.4:
            lines.append("  ・完了率40%未満 → 動画を20秒以内に短縮するか冒頭フックを強化")
        elif avg_cr_all is not None and avg_cr_all >= 0.6:
            lines.append("  ・完了率60%超 → 投稿頻度を週5〜7本に増やすチャンス")
    lines.append("  ・詳細: python fetch_metrics.py --manual で最新値を入力")

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
