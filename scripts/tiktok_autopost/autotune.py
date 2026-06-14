#!/usr/bin/env python3
"""実績フィードバック — 投稿ログから「伸びるフックパターン」を学習し、次に作るネタを自動で寄せる。

改善ループを人手なしで閉じる層:
  generate_and_render → themes._tip_storyboard が pick_tip_index() を呼ぶ
  → posts_log + metrics_log を読み、フックのパターン別スコアを算出
  → 直近で使ったネタ(クールダウン)を避けつつ、勝ちパターンのネタを優先選択
  → 実績データが無ければ None を返し、themes 側が曜日ローテにフォールバック

スコア = 正規化再生数 × 0.6 + 視聴完了率 × 0.4（完了率が取れていない時は再生のみ）。
視聴完了率はTikTokアルゴリズムの最重要シグナルなので、取れているなら重く効かせる。

使い方:
  python autotune.py            # 現在の学習状況（パターン別スコア）を表示
"""
import json
import os

import themes

_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_LOG = os.path.join(_DIR, "posts_log.jsonl")
METRICS_LOG = os.path.join(_DIR, "metrics_log.jsonl")

COOLDOWN = 4  # 直近この本数で使ったフックは再選択しない（マンネリ防止）


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


def _joined() -> list[dict]:
    """投稿(hook付き) × 最新メトリクスを結合した行を返す。"""
    posts = {p["publish_id"]: p for p in _read_jsonl(POSTS_LOG) if p.get("publish_id")}
    metrics: dict[str, dict] = {}
    for m in _read_jsonl(METRICS_LOG):
        pid = m.get("publish_id")
        if not pid:
            continue
        if pid not in metrics or m.get("ts", "") > metrics[pid].get("ts", ""):
            metrics[pid] = m
    rows = []
    for pid, p in posts.items():
        m = metrics.get(pid)
        if not m:
            continue
        rows.append({"hook": p.get("hook", ""),
                     "views": m.get("views"), "completion": m.get("completion")})
    return rows


def pattern_scores() -> dict[str, float]:
    """フックパターン → スコア(0〜1目安)。実績が無ければ空dict。"""
    rows = _joined()
    if not rows:
        return {}
    vmax = max((r["views"] or 0) for r in rows) or 1
    agg: dict[str, dict] = {}
    for r in rows:
        ptn = themes.hook_pattern(r["hook"])
        a = agg.setdefault(ptn, {"v": [], "c": []})
        if r["views"] is not None:
            a["v"].append(r["views"] / vmax)
        if r["completion"] is not None:
            a["c"].append(r["completion"])
    scores: dict[str, float] = {}
    for ptn, a in agg.items():
        v = sum(a["v"]) / len(a["v"]) if a["v"] else 0.0
        c = sum(a["c"]) / len(a["c"]) if a["c"] else None
        scores[ptn] = (v * 0.6 + c * 0.4) if c is not None else v
    return scores


def _recent_hooks(n: int) -> set[str]:
    posts = [p for p in _read_jsonl(POSTS_LOG) if p.get("publish_id") and p.get("hook")]
    return {p["hook"] for p in posts[-n:]}


def pick_tip_index(day_index: int) -> int | None:
    """次に作るネタの index を返す。実績が無ければ None（themes側がローテにフォールバック）。"""
    n = len(themes.TIPS)
    recent = _recent_hooks(COOLDOWN)
    candidates = [i for i, t in enumerate(themes.TIPS) if t["hook"] not in recent]
    if not candidates:
        candidates = list(range(n))

    scores = pattern_scores()
    if not scores:
        return None  # データ無し → ローテにフォールバック

    def keyf(i: int):
        ptn = themes.hook_pattern(themes.TIPS[i]["hook"])
        # 第1キー: パターンスコア / 第2キー: 曜日からの距離（同点なら巡回で変化をつける）
        return (scores.get(ptn, 0.0), -((i - day_index) % n))

    return max(candidates, key=keyf)


def explain() -> str:
    """生成ログに出す一行サマリ。"""
    scores = pattern_scores()
    rows = _joined()
    if not scores:
        return "autotune: 実績データ無し → 曜日ローテで選択（指標が溜まると勝ちパターンへ自動で寄せます）"
    best = max(scores, key=scores.get)
    return f"autotune: 実績{len(rows)}本から学習 → 勝ちパターン【{best}】のネタを優先選択"


def main() -> int:
    scores = pattern_scores()
    print("=" * 48)
    print("autotune 学習状況")
    if not scores:
        print("  実績データなし（曜日ローテで動作中）。")
        print("  fetch_metrics.py で指標を溜めると自動でチューニングされます。")
        return 0
    for ptn, sc in sorted(scores.items(), key=lambda kv: -kv[1]):
        print(f"  {ptn:<8} スコア {sc:.3f}")
    best = max(scores, key=scores.get)
    print(f"→ 次回は【{best}】パターンのネタを優先します。")
    print("=" * 48)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
