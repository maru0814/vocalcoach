#!/usr/bin/env python3
"""ソラ先生 SNS自動投稿（X / 旧Twitter）。

1日2回（昼=slot1 / 夜=slot2）cron で実行する想定。
  1) 曜日とスロットに応じて投稿の柱（診断誘導 / Tips / 声タイプ紹介 / 会話）を選ぶ
  2) Gemini で投稿文を生成（失敗・未設定ならテンプレートを使用）
     tip/contrarian は2部構成: 本投稿=好奇心フックで寸止め / リプ(自己返信)=手順・本体。
     リプを開かせてエンゲージを伸ばす設計（診断導線型は単発）。
  3) X API v2 に投稿: 本投稿→リプ本体→(任意)URL の順でスレッド化。
     キー未設定 or DRY_RUN=1 なら本文を表示して終了。

環境変数（.env または環境に設定。.env.example 参照）:
  DRY_RUN=1                 … 投稿せず本文だけ表示（既定の安全側）
  APPROVAL_MODE=1           … 1=生成後LINEで承認を取る（既定）/0=従来どおり即投稿
  APP_URL=https://...       … 誘導先（未設定なら本番URL）
  GEMINI_API_KEY=...        … あれば文面をAI生成（無くてもテンプレで動く）
  X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET … X投稿用（OAuth1.0a）
  POST_LINK=0               … 1で自己リプにURLを付与。URL投稿は$0.20と高い＆reach減のため既定OFF
  POST_SLOT=1               … 1=昼枠/2=夜枠。1日2投稿で別の型を出すため（--slot でも指定可）
  MAX_POSTS_PER_DAY=2       … 1日の投稿上限（予算ガード）
  MONTHLY_COST_CAP_USD=12   … 月間概算コスト上限（超えたら投稿停止）

コスト方針(docs/29): 本文/リプにURLを入れない（$0.20回避＆reach優先）。リンクはプロフィール固定で誘導。
投稿IDは posts_log.jsonl に記録し、fetch_metrics.py でインプレを取得して改善に回す。

使い方:
  python generate_and_post.py                    # 今日の昼枠(slot1)の型を生成→LINEで承認待ちに送る
  python generate_and_post.py --slot 2           # 今日の夜枠(slot2)の型で1件
  python generate_and_post.py --pillar self_type # 型を指定（self_type/tip/voice_type/empathy/contrarian/question/visual）
  python generate_and_post.py --dry-run          # 生成して本文を表示するだけ（キューにもLINEにも送らない）
  python generate_and_post.py --post-now --force # 承認を挟まず即投稿（手動・緊急用。日次上限は無視）

承認フロー（既定）:
  生成 → pending_queue.jsonl に保存 → LINEに本文＋[承認][却下]ボタンをpush。
  あなたがLINEで承認したものだけ webhook.py が X に投稿する。
  APPROVAL_MODE=0 にすると従来どおり生成して即投稿する。
"""
import argparse
import datetime
import json
import os
import re
import sys
import uuid

import images
import infographic
import themes

try:
    from dotenv import load_dotenv  # 任意。無ければ環境変数だけ使う
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

_DIR = os.path.dirname(os.path.abspath(__file__))
# 実行時データの保存先。本番は永続volume（/data等）を SNS_DATA_DIR で指定する。
_DATA_DIR = os.getenv("SNS_DATA_DIR", _DIR)
os.makedirs(_DATA_DIR, exist_ok=True)
POSTS_LOG = os.path.join(_DATA_DIR, "posts_log.jsonl")  # 投稿ID・型の記録（計測/予算用）
IMG_DIR = os.path.join(_DATA_DIR, "images")              # 添付画像の保存先

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


def _log_post(tweet_id: str, pillar: str, had_link: bool, had_reply: bool = False) -> None:
    rec = {"tweet_id": tweet_id, "pillar": pillar, "link": bool(had_link),
           "reply": bool(had_reply),
           "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    with open(POSTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _post_cost(has_link: bool, has_reply: bool) -> float:
    """1投稿セットの概算コスト。本投稿＋（リプ本体）＋（URLリプ）。"""
    return COST_POST + (COST_POST if has_reply else 0.0) + (COST_POST_URL if has_link else 0.0)


def _budget_check(post_has_link: bool, post_has_reply: bool = False,
                  force: bool = False) -> tuple[bool, str]:
    """1日の投稿上限・月間概算コスト上限を超えていないか。超過なら投稿しない。
    force=True（手動 --force）のときは日次上限のみ無視する。月間コスト上限は安全弁として常に有効。"""
    posts = _read_jsonl(POSTS_LOG)
    today = datetime.date.today().isoformat()
    month = today[:7]
    todays = [p for p in posts if str(p.get("ts", "")).startswith(today)]
    months = [p for p in posts if str(p.get("ts", "")).startswith(month)]
    max_per_day = int(os.getenv("MAX_POSTS_PER_DAY", "1"))
    if not force and len(todays) >= max_per_day:
        return False, f"本日の投稿上限({max_per_day}件)に到達"
    spent = sum(_post_cost(p.get("link"), p.get("reply")) for p in months)
    after = spent + _post_cost(post_has_link, post_has_reply)
    cap = float(os.getenv("MONTHLY_COST_CAP_USD", "12"))
    if after > cap:
        return False, f"月間概算コスト上限(${cap})に到達（今月概算${spent:.2f}）"
    return True, f"今月{len(months)}件/概算${spent:.2f}→投稿後${after:.2f}（上限${cap}）"


def generate_post(pillar: str, day_index: int, app_url: str) -> dict:
    """{text, reply, link} を返す。text=本投稿、reply=リプに置く本体 or None。
    reply を持つ型（tip/contrarian）は2部構成で生成。無ければテンプレ。"""
    post = themes.template_post(pillar, day_index, app_url)  # {text, reply, link}
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return post
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("SNS_LLM_MODEL", "gemini-flash-lite-latest")
        if post.get("reply"):  # 2部構成（本投稿フック＋リプ本体）
            resp = client.models.generate_content(
                model=model, contents=themes.gemini_twopart_prompt(pillar, day_index, app_url))
            m = re.search(r"\{.*\}", (resp.text or "").strip(), re.S)
            if m:
                data = json.loads(m.group(0))
                hook = (data.get("hook") or "").strip()
                body = (data.get("body") or "").strip()
                if len(hook) >= 10 and len(body) >= 20 and "http" not in hook and "http" not in body:
                    return {"text": hook, "reply": body, "link": post.get("link")}
            return post  # 解析失敗・不正ならテンプレ
        # 単発型（self_type / voice_type / visual）
        resp = client.models.generate_content(
            model=model, contents=themes.gemini_prompt(pillar, day_index, app_url))
        text = (resp.text or "").strip()
        if len(text) < 20 or "http" in text:
            return post
        return {"text": text, "reply": None, "link": post.get("link")}
    except Exception as e:
        print(f"[warn] Gemini生成に失敗 → テンプレ使用: {e}", file=sys.stderr)
        return post


def build_image(pillar: str, slot: int, day_index: int, app_url: str) -> str | None:
    """投稿に添付するブランド画像を生成してパスを返す（作れなければ None）。
    - tip / contrarian: 図解インフォグラフィック（Playwright）。失敗時はカードにフォールバック。
    - 診断導線（self_type/voice_type/visual）: 従来のカード（情報量が少なく図解に不向き）。"""
    if not _truthy(os.getenv("SNS_IMAGE", "1")):
        return None
    name = (f"{datetime.date.today().isoformat()}_s{slot}_{pillar}_"
            f"{uuid.uuid4().hex[:6]}.png")
    out = os.path.join(IMG_DIR, name)
    if pillar in ("tip", "contrarian"):
        p = infographic.generate(pillar, day_index, app_url, out)
        if p:
            return p
        # 図解レンダリング不可（playwright未導入等）→ カードにフォールバック
    base = themes.template_post(pillar, day_index, app_url)
    headline = images.build_headline(pillar, base.get("text", ""), base.get("reply"))
    return images.generate_image(pillar, headline, out)


def _upload_media(oauth, image_path: str) -> str | None:
    """画像を X にアップロードして media_id を返す（失敗なら None）。"""
    try:
        with open(image_path, "rb") as f:
            r = oauth.post("https://upload.twitter.com/1.1/media/upload.json",
                           files={"media": f}, timeout=60)
        if r.status_code in (200, 201):
            j = r.json()
            return str(j.get("media_id_string") or j.get("media_id") or "") or None
        print(f"[warn] 画像アップロード失敗 {r.status_code}: {r.text[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"[warn] 画像アップロード例外: {e}", file=sys.stderr)
    return None


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


def _reply(oauth, text: str, in_reply_to: str) -> tuple[bool, str, int]:
    """自己返信を1件投稿。(ok, new_id, status)。"""
    r = oauth.post("https://api.twitter.com/2/tweets",
                   json={"text": text, "reply": {"in_reply_to_tweet_id": in_reply_to}}, timeout=20)
    if r.status_code in (200, 201):
        return True, str(r.json().get("data", {}).get("id", "")), r.status_code
    return False, "", r.status_code


def post_to_x(text: str, reply: str | None, link: str | None,
              post_link: bool, image_path: str | None = None) -> tuple[bool, str, str]:
    """本投稿(text)→リプ本体(reply)→(任意)URL の順にスレッド投稿する。
    image_path があれば本投稿にブランド画像を添付する（アップロード失敗時は文字だけで続行）。
    reply に“大事な中身（手順）”を置いてリプを開かせる設計。link は POST_LINK=1 のときだけ。
    returns (ok, tweet_id, info)。"""
    oauth = _x_session()
    if oauth is None:
        return False, "", "X_KEYS_MISSING"
    try:
        payload: dict = {"text": text}
        img_info = ""
        if image_path and os.path.exists(image_path):
            mid = _upload_media(oauth, image_path)
            if mid:
                payload["media"] = {"media_ids": [mid]}
                img_info = "+画像"
            else:
                img_info = "/画像失敗"
        r = oauth.post("https://api.twitter.com/2/tweets", json=payload, timeout=30)
        if r.status_code not in (200, 201):
            return False, "", f"HTTP {r.status_code}: {r.text[:200]}"
        tweet_id = str(r.json().get("data", {}).get("id", ""))
        info, last_id = "本投稿OK" + img_info, tweet_id
        if reply and last_id:                       # 大事な中身を自己リプに
            ok, rid, st = _reply(oauth, reply, last_id)
            if ok:
                info, last_id = "本投稿+リプ本体", rid or last_id
            else:
                info = f"本投稿OK/リプ本体失敗{st}"
        if post_link and link and last_id:          # 任意でURLリプ（$0.20課金）
            ok, _, st = _reply(oauth, f"▼ ここから無料で診断できます🎤\n{link}", last_id)
            info += " +link" if ok else f" +link失敗{st}"
        return True, tweet_id or "ok", info
    except Exception as e:
        return False, "", f"EXC: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pillar",
                    choices=["self_type", "tip", "voice_type", "contrarian", "visual"],
                    help="投稿の型を指定")
    ap.add_argument("--slot", type=int, choices=[1, 2], default=None,
                    help="1=昼枠（既定）/2=夜枠。1日2投稿時に別の型を出すために使う")
    ap.add_argument("--force", action="store_true",
                    help="手動投稿用。1日の投稿上限を無視して追加投稿する（月間コスト上限は維持）")
    ap.add_argument("--dry-run", action="store_true",
                    help="生成して本文を表示するだけ（キューにもLINEにも送らない）")
    ap.add_argument("--post-now", action="store_true",
                    help="承認を挟まず即投稿する（APPROVAL_MODEを無視。手動・緊急用）")
    args = ap.parse_args()

    app_url = os.getenv("APP_URL", themes.APP_URL_DEFAULT).rstrip("/")
    today = datetime.date.today()
    day_index = today.toordinal()
    slot = args.slot or int(os.getenv("POST_SLOT", "1"))
    pillar = args.pillar or themes.pillar_for(today.weekday(), slot)

    post = generate_post(pillar, day_index, app_url)
    text, reply, link = post["text"], post.get("reply"), post.get("link")
    # URL投稿は $0.20 と高くリーチも落ちるため既定OFF。POST_LINK=1 の時だけリプにリンク。
    post_link = _truthy(os.getenv("POST_LINK", "0")) and bool(link)
    # 全投稿にブランド画像を添付（tip/contrarian=図解 / 診断導線=カード。SNS_IMAGE=0で無効）。
    image_path = build_image(pillar, slot, day_index, app_url)

    print("─" * 48)
    print(f"[{today}] slot={slot} pillar={pillar}")
    print("【本投稿】")
    print(text)
    if reply:
        print("\n【リプ（自己返信）＝大事な中身】")
        print(reply)
    if link:
        print(f"\n[リンク] {link}  (POST_LINK={'ON→リプに付与' if post_link else 'OFF→プロフィール固定で誘導'})")
    print(f"[画像] {image_path or '生成なし（SNS_IMAGE=0 or 失敗）'}")
    print("─" * 48)

    dry = args.dry_run or _truthy(os.getenv("DRY_RUN", "1"))  # 既定は安全側でドライラン
    if dry:
        print("DRY_RUN: 生成のみ。承認キュー・LINE・投稿はいずれもしていません。")
        return 0

    # 既定は承認フロー: 投稿せずキューに積み、LINEで承認を仰ぐ。
    approval = _truthy(os.getenv("APPROVAL_MODE", "1")) and not args.post_now
    if approval:
        import approval_queue as q
        import line_client
        draft = q.enqueue(pillar, slot, text, reply, link, post_link, image_path)
        ok_line, info = line_client.push_approval(draft)
        if ok_line:
            print(f"📨 承認待ちに送信しました（id={draft['id']}）。LINEで承認/却下してください。")
            return 0
        print(f"⚠ キューには保存しましたが、LINE送信に失敗: {info}", file=sys.stderr)
        print(f"   id={draft['id']} pillar={pillar}（承認できる経路を確認してください）",
              file=sys.stderr)
        return 1

    # --post-now / APPROVAL_MODE=0: 従来どおり生成して即投稿。
    ok_budget, why = _budget_check(post_has_link=post_link,
                                   post_has_reply=bool(reply), force=args.force)
    if args.force:
        print("⚠ --force: 本日の投稿上限を無視して投稿します（月間コスト上限は維持）。")
    if not ok_budget:
        print(f"⏸ 予算/上限ガードで停止: {why}")
        return 0

    ok, tweet_id, info = post_to_x(text, reply, link, post_link, image_path)
    if ok:
        _log_post(tweet_id, pillar, post_link, bool(reply))
        print(f"✅ 投稿しました: id={tweet_id} ({info})  [{why}]")
        return 0
    print(f"❌ 投稿に失敗: {info}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
