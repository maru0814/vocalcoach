#!/usr/bin/env python3
"""リード獲得の計測: クエリ別フォロバ率（docs/55 FR-06）。

engaged_log.jsonl の承認済みリードについて、そのユーザーが自アカウントを
フォローしているか（＝フォロバ）を自分のフォロワー一覧（owned read ≒$0.001/件）で
確認し、query_id 別のフォロバ率を出す。他人ツイートの検索APIは使わない。

使い方:
  python lead_metrics.py          # 未計測の承認リードを確認して集計表示
  python lead_metrics.py --all    # 計測済みも含めて再確認
週次バッチ（growth-operator の週次レポート）に載せる想定。
"""
import argparse
import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_DIR, ".env"))
except Exception:
    pass

import approval_queue as q
from lead_finder import ReadMeter, _session


def fetch_follower_handles(oauth, meter: ReadMeter) -> set[str] | None:
    """自分のフォロワーの username 集合（小文字）。取得不可なら None。"""
    try:
        me = oauth.get("https://api.twitter.com/2/users/me", timeout=20)
        if me.status_code != 200:
            print(f"[warn] users/me 失敗 HTTP {me.status_code}", file=sys.stderr)
            return None
        meter.add("owned_read", 1)
        my_id = me.json()["data"]["id"]
        handles: set[str] = set()
        token = None
        while True:
            params = {"max_results": 1000, "user.fields": "username"}
            if token:
                params["pagination_token"] = token
            r = oauth.get(f"https://api.twitter.com/2/users/{my_id}/followers",
                          params=params, timeout=30)
            if r.status_code != 200:
                print(f"[warn] followers 失敗 HTTP {r.status_code}: {r.text[:120]}",
                      file=sys.stderr)
                return handles if handles else None
            body = r.json()
            data = body.get("data") or []
            meter.add("owned_read", len(data))
            handles.update(u.get("username", "").lower() for u in data)
            token = (body.get("meta") or {}).get("next_token")
            if not token:
                return handles
    except Exception as e:
        print(f"[warn] フォロワー取得に失敗: {e}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="計測済み(followed_back記入済み)も再確認")
    args = ap.parse_args()

    rows = [r for r in q.read_engaged() if r.get("status") == "approved"]
    if not rows:
        print("engaged_log.jsonl に承認済みリードがありません（まず lead_finder.py から）。")
        return 0

    oauth = _session()
    if oauth is None:
        print("計測スキップ（Xキー未設定。探索・承認は動きます）。")
        return 0
    meter = ReadMeter()
    followers = fetch_follower_handles(oauth, meter)
    meter.persist()
    if followers is None:
        print("計測スキップ（フォロワー一覧を取得できませんでした）。")
        return 0

    # followed_back を記入（未計測 or --all）
    for r in rows:
        if r.get("followed_back") is not None and not args.all:
            continue
        fb = (r.get("handle") or "").lstrip("@").lower() in followers
        q.update_engaged(r["lead_id"], followed_back=fb)
        r["followed_back"] = fb

    # クエリ別サマリ
    by_q: dict[str, list] = {}
    for r in rows:
        by_q.setdefault(r.get("query_id", "?"), []).append(r)
    print("=" * 56)
    print(f"リード計測（承認 {len(rows)}件 / フォロワー {len(followers)}人 / "
          f"read概算 ${meter.usd():.3f}）")
    print(f"{'クエリ':<14}{'承認':>4}{'フォロバ':>6}{'率':>8}")
    summary = []
    for qid, rs in by_q.items():
        done = [r for r in rs if r.get("followed_back") is not None]
        fb = sum(1 for r in done if r["followed_back"])
        rate = fb / len(done) if done else 0.0
        summary.append((qid, len(rs), fb, rate))
    for qid, n, fb, rate in sorted(summary, key=lambda x: x[3], reverse=True):
        print(f"{qid:<14}{n:>4}{fb:>6}{rate * 100:>7.1f}%")
    print("=" * 56)
    print("→ 率が高いクエリを leads.LEAD_QUERIES で増やし、低いクエリを削る"
          "（growth-operator の週次レポートに載せる）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
