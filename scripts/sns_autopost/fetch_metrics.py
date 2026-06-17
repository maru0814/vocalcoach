#!/usr/bin/env python3
"""投稿のインプレッション/エンゲージメントを取得して改善に回す（docs/29）。

posts_log.jsonl の直近投稿IDのメトリクスを X API で取得し（自分の投稿の読取＝$0.001/件と激安）、
metrics_log.jsonl に追記。最後に「型(pillar)別の平均インプレ・エンゲージ率」を表示する。
→ 週次でこれを見て、伸びた型を増やし、伸びない型を削る（themes.py の PILLARS を寄せる）。

使い方:
  python fetch_metrics.py            # 直近25件のメトリクス取得＋型別サマリ
  python fetch_metrics.py --limit 50
環境変数: X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET（投稿と同じ）
"""
import argparse
import datetime
import json
import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
# 実行時データの保存先。本番は永続volume（/data等）を SNS_DATA_DIR で指定する。
_DATA_DIR = os.getenv("SNS_DATA_DIR", _DIR)
POSTS_LOG = os.path.join(_DATA_DIR, "posts_log.jsonl")
METRICS_LOG = os.path.join(_DATA_DIR, "metrics_log.jsonl")

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


def _session():
    keys = {k: os.getenv(k) for k in
            ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
    if not all(keys.values()):
        return None
    from requests_oauthlib import OAuth1Session
    return OAuth1Session(
        keys["X_API_KEY"], client_secret=keys["X_API_SECRET"],
        resource_owner_key=keys["X_ACCESS_TOKEN"],
        resource_owner_secret=keys["X_ACCESS_SECRET"],
    )


def _impressions(t: dict):
    """public/non_public/organic のどこに入っていても impression_count を拾う。"""
    for bucket in ("non_public_metrics", "organic_metrics", "public_metrics"):
        v = (t.get(bucket) or {}).get("impression_count")
        if v is not None:
            return int(v)
    return None


def _engagement(t: dict) -> int:
    pm = t.get("public_metrics") or {}
    return sum(int(pm.get(k, 0)) for k in
               ("like_count", "retweet_count", "reply_count", "quote_count", "bookmark_count"))


def fetch(ids: list[str]) -> list[dict]:
    oauth = _session()
    if oauth is None:
        print("X_KEYS_MISSING（.env にXキーを設定してください）", file=sys.stderr)
        return []
    out = []
    # 100件ずつ。非公開メトリクスが弾かれたら public_metrics のみで再試行。
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        params = {"ids": ",".join(chunk),
                  "tweet.fields": "public_metrics,non_public_metrics,organic_metrics"}
        r = oauth.get("https://api.twitter.com/2/tweets", params=params, timeout=20)
        if r.status_code != 200:
            r = oauth.get("https://api.twitter.com/2/tweets",
                          params={"ids": ",".join(chunk), "tweet.fields": "public_metrics"},
                          timeout=20)
        if r.status_code != 200:
            print(f"[warn] 取得失敗 HTTP {r.status_code}: {r.text[:160]}", file=sys.stderr)
            continue
        out.extend((r.json().get("data") or []))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25, help="直近何件を集計するか")
    args = ap.parse_args()

    posts = _read_jsonl(POSTS_LOG)
    posts = [p for p in posts if p.get("tweet_id")][-args.limit:]
    if not posts:
        print("posts_log.jsonl に投稿がありません（まず generate_and_post.py で投稿）。")
        return 0
    pillar_by_id = {p["tweet_id"]: p.get("pillar", "?") for p in posts}

    tweets = fetch(list(pillar_by_id.keys()))
    if not tweets:
        return 1

    now = datetime.datetime.now().isoformat(timespec="seconds")
    rows = []
    with open(METRICS_LOG, "a", encoding="utf-8") as f:
        for t in tweets:
            tid = str(t.get("id"))
            imp = _impressions(t)
            eng = _engagement(t)
            rate = round(eng / imp, 4) if imp else None
            rec = {"tweet_id": tid, "pillar": pillar_by_id.get(tid, "?"),
                   "impressions": imp, "engagement": eng, "eng_rate": rate, "ts": now}
            rows.append(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 型別サマリ
    by_pillar: dict[str, list] = {}
    for r in rows:
        by_pillar.setdefault(r["pillar"], []).append(r)

    print("=" * 56)
    print(f"インプレ計測 {now}  （{len(rows)}件）")
    print(f"{'型(pillar)':<12}{'件':>3}{'平均imp':>9}{'平均eng':>8}{'eng率':>8}")
    summary = []
    for pillar, rs in by_pillar.items():
        imps = [r["impressions"] for r in rs if r["impressions"] is not None]
        avg_imp = sum(imps) / len(imps) if imps else 0
        avg_eng = sum(r["engagement"] for r in rs) / len(rs)
        rates = [r["eng_rate"] for r in rs if r["eng_rate"] is not None]
        avg_rate = sum(rates) / len(rates) if rates else 0
        summary.append((pillar, len(rs), avg_imp, avg_eng, avg_rate))
    # 平均インプレ降順
    for pillar, n, ai, ae, ar in sorted(summary, key=lambda x: x[2], reverse=True):
        imp_s = f"{ai:,.0f}" if ai else "—"
        print(f"{pillar:<12}{n:>3}{imp_s:>9}{ae:>8.1f}{ar*100:>7.1f}%")
    print("=" * 56)
    print("→ 平均インプレ・eng率が高い型を themes.py の PILLARS で増やす。低い型は減らす。")
    if all(r["impressions"] is None for r in rows):
        print("※ インプレ(impression_count)がAPIで取得できませんでした。"
              "公開メトリクス(eng)で代替中。インプレはX標準アナリティクスでも確認できます。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
