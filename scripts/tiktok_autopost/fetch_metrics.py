#!/usr/bin/env python3
"""投稿後の動画指標を取得して改善に回す（docs/34 §6）。

posts_log.jsonl の publish_id から TikTok Display/Video API で再生数・視聴完了率・コメント数を取得し、
metrics_log.jsonl に追記。型(tip/demo)別サマリを表示 → 伸びた型に themes.PILLARS を寄せる。

キー未設定なら手動入力モード（--manual）で、TikTokアプリのインサイト値を貼って記録できる。

使い方:
  python fetch_metrics.py                # API取得（TIKTOK_ACCESS_TOKEN 必要）
  python fetch_metrics.py --manual       # 手動でインサイト値を入力して記録
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


def _fetch_api(video_ids: list[str]) -> dict:
    """video_id → メトリクス。Display API の video.list（fields=view_count等）。失敗時 {}。"""
    token = os.getenv("TIKTOK_ACCESS_TOKEN")
    if not token or not video_ids:
        return {}
    try:
        import requests
        r = requests.post(
            "https://open.tiktokapis.com/v2/video/query/",
            params={"fields": "id,view_count,like_count,comment_count,share_count"},
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={"filters": {"video_ids": video_ids}}, timeout=30)
        if r.status_code != 200:
            print(f"[warn] 取得失敗 HTTP {r.status_code}: {r.text[:160]}", file=sys.stderr)
            return {}
        out = {}
        for v in (r.json().get("data") or {}).get("videos", []):
            out[str(v.get("id"))] = v
        return out
    except Exception as e:
        print(f"[warn] API例外: {e}", file=sys.stderr)
        return {}


def _summary(rows: list[dict]) -> None:
    by_pillar: dict[str, list] = {}
    for r in rows:
        by_pillar.setdefault(r.get("pillar", "?"), []).append(r)
    print("=" * 56)
    print(f"TikTok指標サマリ（{len(rows)}件）")
    print(f"{'型':<6}{'件':>3}{'平均再生':>10}{'平均完了率':>10}{'平均コメ':>9}")
    for pillar, rs in sorted(by_pillar.items(),
                             key=lambda kv: -sum(x.get("views", 0) for x in kv[1]) / max(len(kv[1]), 1)):
        n = len(rs)
        av = sum(x.get("views", 0) for x in rs) / n
        cr = [x["completion"] for x in rs if x.get("completion") is not None]
        acr = sum(cr) / len(cr) if cr else 0
        ac = sum(x.get("comments", 0) for x in rs) / n
        print(f"{pillar:<6}{n:>3}{av:>10,.0f}{acr*100:>9.1f}%{ac:>9.1f}")
    print("=" * 56)
    print("→ 平均再生・完了率が高い型を themes.PILLARS で増やす（docs/34 §3 週次レビュー）。")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual", action="store_true", help="インサイト値を手入力して記録")
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()

    posts = [p for p in _read_jsonl(POSTS_LOG) if p.get("publish_id")][-args.limit:]
    if not posts:
        print("posts_log.jsonl に投稿がありません（まず generate_and_render.py で投稿）。")
        return 0

    now = datetime.datetime.now().isoformat(timespec="seconds")
    rows = []

    if args.manual:
        print("各投稿のインサイト値を入力（空Enterでスキップ）。完了率は0〜100の数値。")
        for p in posts:
            pid = p["publish_id"]
            print(f"\n[{p.get('ts','?')}] {p.get('pillar')} publish_id={pid}")
            try:
                views = int(input("  再生数: ") or 0)
                completion = float(input("  視聴完了率%(0-100): ") or 0) / 100
                comments = int(input("  コメント数: ") or 0)
            except (ValueError, EOFError):
                continue
            rows.append({"publish_id": pid, "pillar": p.get("pillar"), "views": views,
                         "completion": completion, "comments": comments, "ts": now})
    else:
        # publish_id と video_id は別物。投稿時に紐付けできていれば video_id を使う。
        ids = [p.get("video_id") or p.get("publish_id") for p in posts]
        data = _fetch_api([i for i in ids if i])
        if not data:
            print("API取得不可（トークン未設定 or video_id未紐付け）。--manual を使ってください。")
            return 1
        for p in posts:
            vid = str(p.get("video_id") or p.get("publish_id"))
            v = data.get(vid)
            if not v:
                continue
            rows.append({"publish_id": p["publish_id"], "pillar": p.get("pillar"),
                         "views": int(v.get("view_count", 0)),
                         "completion": None,  # 完了率はResearch/Insights枠が必要。手動補完推奨
                         "comments": int(v.get("comment_count", 0)), "ts": now})

    if not rows:
        print("記録対象がありませんでした。")
        return 0
    with open(METRICS_LOG, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    _summary(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
