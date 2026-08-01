#!/usr/bin/env python3
"""承認して pending 動画を TikTok に投稿する。

generate_and_render.py が NOTIFY_BEFORE_POST=1 の時に out/pending/ に動画を置く。
通知を確認したら、このスクリプトを実行するだけで投稿される。

使い方:
  python approve.py           # out/pending/ の最新ファイルを投稿
  python approve.py --skip    # pending ファイルを out/skipped/ に移してスキップ
  python approve.py --list    # pending 一覧を表示
  python approve.py out/pending/2026-06-14_demo.mp4  # ファイルを指定
"""
import argparse
import datetime
import glob
import json
import os
import shutil
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
PENDING_DIR = os.path.join(_DIR, "out", "pending")
POSTED_DIR = os.path.join(_DIR, "out", "posted")
SKIPPED_DIR = os.path.join(_DIR, "out", "skipped")
POSTS_LOG = os.path.join(_DIR, "posts_log.jsonl")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_DIR, ".env"))
except Exception:
    pass


def _find_pending() -> list[str]:
    return sorted(glob.glob(os.path.join(PENDING_DIR, "*.mp4")) +
                  glob.glob(os.path.join(PENDING_DIR, "*.webm")))


def _storyboard_for(video_path: str) -> dict:
    """動画と同名の .storyboard.json があれば読む。無ければ空。"""
    sb_path = os.path.splitext(video_path)[0] + ".storyboard.json"
    if os.path.exists(sb_path):
        try:
            with open(sb_path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("storyboard", data)
        except Exception:
            pass
    return {}


def _log_post(publish_id: str, pillar: str, video: str, info: str, hook: str = "") -> None:
    rec = {"publish_id": publish_id, "pillar": pillar, "hook": hook,
           "video": os.path.basename(video),
           "info": info, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    with open(POSTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?", help="投稿するファイルを指定（省略で最新）")
    ap.add_argument("--skip", action="store_true", help="投稿せずスキップ（out/skipped/ に移動）")
    ap.add_argument("--list", action="store_true", help="pending 一覧を表示")
    args = ap.parse_args()

    pending = _find_pending()

    if args.list:
        if not pending:
            print("pending 動画はありません。")
        for p in pending:
            sb = _storyboard_for(p)
            print(f"  {os.path.basename(p)}  [{sb.get('pillar', '?')}]  {sb.get('duration', '?')}秒")
            print(f"    {sb.get('caption', '')}")
        return 0

    # ファイルを決定
    if args.video:
        video = args.video
    elif pending:
        video = pending[-1]  # 最新
    else:
        print("pending 動画がありません。generate_and_render.py を NOTIFY_BEFORE_POST=1 で実行してください。")
        return 1

    if not os.path.exists(video):
        print(f"ファイルが見つかりません: {video}")
        return 1

    sb = _storyboard_for(video)
    pillar = sb.get("pillar", os.path.basename(video).split("_")[-1].split(".")[0])
    caption = sb.get("caption", "")
    hashtags = sb.get("hashtags", ["#ボイトレ"])

    print(f"動画: {os.path.basename(video)}")
    print(f"型: {pillar}  キャプション: {caption}")

    if args.skip:
        os.makedirs(SKIPPED_DIR, exist_ok=True)
        shutil.move(video, os.path.join(SKIPPED_DIR, os.path.basename(video)))
        sb_path = os.path.splitext(video)[0] + ".storyboard.json"
        if os.path.exists(sb_path):
            shutil.move(sb_path, os.path.join(SKIPPED_DIR, os.path.basename(sb_path)))
        print("⏭ スキップしました（out/skipped/ に移動）。")
        return 0

    import tiktok_poster
    ok, publish_id, info = tiktok_poster.post_video(video, caption, hashtags)
    if ok:
        hook = next((sc["text"] for sc in sb.get("scenes", []) if sc.get("kind") == "hook"), caption)
        _log_post(publish_id, pillar, video, info, hook=hook)
        os.makedirs(POSTED_DIR, exist_ok=True)
        shutil.move(video, os.path.join(POSTED_DIR, os.path.basename(video)))
        sb_path = os.path.splitext(video)[0] + ".storyboard.json"
        if os.path.exists(sb_path):
            shutil.move(sb_path, os.path.join(POSTED_DIR, os.path.basename(sb_path)))
        print(f"✅ 投稿完了: publish_id={publish_id} ({info})")
        print("💡 TikTokアプリで動画を確認し、コメント欄に『診断はプロフィールから🎤』を固定してください（docs/34 §5）。")
        return 0

    print(f"❌ 投稿失敗: {info}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
