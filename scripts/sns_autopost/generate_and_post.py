#!/usr/bin/env python3
"""ソラ先生 SNS自動投稿（X / 旧Twitter）。

毎日1回 cron で実行する想定。
  1) 曜日に応じて投稿の柱（診断誘導 / Tips / 声タイプ紹介）を選ぶ
  2) Gemini で投稿文を生成（失敗・未設定ならテンプレートを使用）
  3) X API v2 に投稿（キー未設定 or DRY_RUN=1 なら本文を表示して終了）

環境変数（.env または環境に設定。.env.example 参照）:
  DRY_RUN=1                 … 投稿せず本文だけ表示（既定の安全側）
  APP_URL=https://...       … 誘導先（未設定なら本番URL）
  GEMINI_API_KEY=...        … あれば文面をAI生成（無くてもテンプレで動く）
  X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET … X投稿用（OAuth1.0a）
  POST_LINK=0               … 1で自己リプにURLを付与。URL投稿は$0.20と高い＆reach減のため既定OFF
  MAX_POSTS_PER_DAY=1       … 1日の投稿上限（予算ガード）
  MONTHLY_COST_CAP_USD=12   … 月間概算コスト上限（超えたら投稿停止）

コスト方針(docs/29): 本文/リプにURLを入れない（$0.20回避＆reach優先）。リンクはプロフィール固定で誘導。
投稿IDは posts_log.jsonl に記録し、fetch_metrics.py でインプレを取得して改善に回す。

使い方:
  python generate_and_post.py                    # 今日の型で1件
  python generate_and_post.py --pillar self_type # 型を指定（self_type/tip/voice_type/empathy/contrarian/question/visual）
  python generate_and_post.py --dry-run          # 強制ドライラン
"""
import argparse
import datetime
import json
import os
import sys

import themes

try:
    from dotenv import load_dotenv  # 任意。無ければ環境変数だけ使う
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_LOG = os.path.join(_DIR, "posts_log.jsonl")  # 投稿ID・型の記録（計測/予算用）

# X API 概算単価（2026。URL投稿は高い→既定で避ける）
COST_POST = 0.015      # URLなし投稿 $/件
COST_POST_URL = 0.20   # URLあり投稿 $/件（自己リプにリンクを貼る場合も該当）


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


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


def _log_post(tweet_id: str, pillar: str, had_link: bool) -> None:
    rec = {"tweet_id": tweet_id, "pillar": pillar, "link": bool(had_link),
           "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    with open(POSTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _budget_check(post_has_link: bool) -> tuple[bool, str]:
    """1日の投稿上限・月間概算コスト上限を超えていないか。超過なら投稿しない。"""
    posts = _read_jsonl(POSTS_LOG)
    today = datetime.date.today().isoformat()
    month = today[:7]
    todays = [p for p in posts if str(p.get("ts", "")).startswith(today)]
    months = [p for p in posts if str(p.get("ts", "")).startswith(month)]
    max_per_day = int(os.getenv("MAX_POSTS_PER_DAY", "1"))
    if len(todays) >= max_per_day:
        return False, f"本日の投稿上限({max_per_day}件)に到達"
    spent = sum(COST_POST_URL if p.get("link") else COST_POST for p in months)
    after = spent + (COST_POST_URL if post_has_link else COST_POST)
    cap = float(os.getenv("MONTHLY_COST_CAP_USD", "12"))
    if after > cap:
        return False, f"月間概算コスト上限(${cap})に到達（今月概算${spent:.2f}）"
    return True, f"今月{len(months)}件/概算${spent:.2f}→投稿後${after:.2f}（上限${cap}）"


def generate_post(pillar: str, day_index: int, app_url: str) -> dict:
    """{text, link} を返す。Geminiがあれば本文を生成、無ければテンプレ。リンクはテンプレ側で決定。"""
    post = themes.template_post(pillar, day_index, app_url)  # {text, link}
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return post
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("SNS_LLM_MODEL", "gemini-flash-lite-latest")
        resp = client.models.generate_content(
            model=model,
            contents=themes.gemini_prompt(pillar, day_index, app_url),
        )
        text = (resp.text or "").strip()
        # 健全性チェック: 短すぎ or 誤って本文にURLを入れたらテンプレへ
        if len(text) < 20 or "http" in text:
            return post
        return {"text": text, "link": post.get("link")}
    except Exception as e:
        print(f"[warn] Gemini生成に失敗 → テンプレ使用: {e}", file=sys.stderr)
        return post


def _x_session():
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


def post_to_x(text: str, link: str | None, post_link: bool) -> tuple[bool, str, str]:
    """本文を投稿。post_link=True かつ link がある時だけ自己リプにURLを貼る（$0.20課金なので既定OFF）。
    returns (ok, tweet_id, info)。"""
    oauth = _x_session()
    if oauth is None:
        return False, "", "X_KEYS_MISSING"
    try:
        r = oauth.post("https://api.twitter.com/2/tweets", json={"text": text}, timeout=20)
        if r.status_code not in (200, 201):
            return False, "", f"HTTP {r.status_code}: {r.text[:200]}"
        tweet_id = str(r.json().get("data", {}).get("id", ""))
        info = "ok"
        if post_link and link and tweet_id:
            reply = {"text": f"▼ ここから無料で診断できます🎤\n{link}",
                     "reply": {"in_reply_to_tweet_id": tweet_id}}
            rr = oauth.post("https://api.twitter.com/2/tweets", json=reply, timeout=20)
            info = "link付" if rr.status_code in (200, 201) else f"本文OK/リプ失敗 {rr.status_code}"
        return True, tweet_id or "ok", info
    except Exception as e:
        return False, "", f"EXC: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pillar",
                    choices=["self_type", "tip", "voice_type", "empathy", "contrarian", "question", "visual"],
                    help="投稿の型を指定")
    ap.add_argument("--dry-run", action="store_true", help="投稿せず本文だけ表示")
    args = ap.parse_args()

    app_url = os.getenv("APP_URL", themes.APP_URL_DEFAULT).rstrip("/")
    today = datetime.date.today()
    day_index = today.toordinal()
    pillar = args.pillar or themes.PILLARS[today.weekday()]

    post = generate_post(pillar, day_index, app_url)
    text, link = post["text"], post.get("link")
    # URL投稿は $0.20 と高くリーチも落ちるため既定OFF。POST_LINK=1 の時だけリプにリンク。
    post_link = _truthy(os.getenv("POST_LINK", "0")) and bool(link)

    print("─" * 48)
    print(f"[{today}] pillar={pillar}")
    print(text)
    if link:
        print(f"\n[リンク] {link}  (POST_LINK={'ON→リプに付与' if post_link else 'OFF→プロフィール固定で誘導'})")
    print("─" * 48)

    dry = args.dry_run or _truthy(os.getenv("DRY_RUN", "1"))  # 既定は安全側でドライラン
    if dry:
        print("DRY_RUN: 投稿はしていません（DRY_RUN=0 とXキー設定で実投稿）。")
        return 0

    ok_budget, why = _budget_check(post_has_link=post_link)
    if not ok_budget:
        print(f"⏸ 予算/上限ガードで停止: {why}")
        return 0

    ok, tweet_id, info = post_to_x(text, link, post_link)
    if ok:
        _log_post(tweet_id, pillar, post_link)
        print(f"✅ 投稿しました: id={tweet_id} ({info})  [{why}]")
        return 0
    print(f"❌ 投稿に失敗: {info}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
