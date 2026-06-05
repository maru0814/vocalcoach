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

使い方:
  python generate_and_post.py            # 今日の柱で1件
  python generate_and_post.py --pillar diagnosis   # 柱を指定
  python generate_and_post.py --dry-run            # 強制ドライラン
"""
import argparse
import datetime
import os
import sys

import themes

try:
    from dotenv import load_dotenv  # 任意。無ければ環境変数だけ使う
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


def generate_text(pillar: str, day_index: int, app_url: str) -> str:
    """Geminiがあれば生成、無ければテンプレート。必ず文字列を返す。"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return themes.template_post(pillar, day_index, app_url)
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("SNS_LLM_MODEL", "gemini-flash-lite-latest")
        resp = client.models.generate_content(
            model=model,
            contents=themes.gemini_prompt(pillar, day_index, app_url),
        )
        text = (resp.text or "").strip()
        # 念のための健全性チェック（短すぎ/URL欠落ならテンプレへ）
        if len(text) < 20 or app_url not in text:
            return themes.template_post(pillar, day_index, app_url)
        return text
    except Exception as e:
        print(f"[warn] Gemini生成に失敗 → テンプレ使用: {e}", file=sys.stderr)
        return themes.template_post(pillar, day_index, app_url)


def post_to_x(text: str) -> tuple[bool, str]:
    """X API v2 にツイート。成功なら (True, tweet_id)。"""
    keys = {k: os.getenv(k) for k in
            ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
    if not all(keys.values()):
        return False, "X_KEYS_MISSING"
    try:
        from requests_oauthlib import OAuth1Session
        oauth = OAuth1Session(
            keys["X_API_KEY"], client_secret=keys["X_API_SECRET"],
            resource_owner_key=keys["X_ACCESS_TOKEN"],
            resource_owner_secret=keys["X_ACCESS_SECRET"],
        )
        r = oauth.post("https://api.twitter.com/2/tweets", json={"text": text}, timeout=20)
        if r.status_code in (200, 201):
            return True, str(r.json().get("data", {}).get("id", "ok"))
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"EXC: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pillar", choices=["diagnosis", "tip", "type"], help="投稿の柱を指定")
    ap.add_argument("--dry-run", action="store_true", help="投稿せず本文だけ表示")
    args = ap.parse_args()

    app_url = os.getenv("APP_URL", themes.APP_URL_DEFAULT).rstrip("/")
    today = datetime.date.today()
    day_index = today.toordinal()
    pillar = args.pillar or themes.PILLARS[today.weekday()]

    text = generate_text(pillar, day_index, app_url)

    print("─" * 48)
    print(f"[{today}] pillar={pillar}")
    print(text)
    print("─" * 48)

    dry = args.dry_run or _truthy(os.getenv("DRY_RUN", "1"))  # 既定は安全側でドライラン
    if dry:
        print("DRY_RUN: 投稿はしていません（DRY_RUN=0 とXキー設定で実投稿）。")
        return 0

    ok, info = post_to_x(text)
    if ok:
        print(f"✅ 投稿しました: tweet_id={info}")
        return 0
    print(f"❌ 投稿に失敗: {info}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
