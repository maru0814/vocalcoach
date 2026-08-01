#!/usr/bin/env python3
"""ソラ先生 TikTok自動生成＆投稿（Tips型＋検証型）。docs/34 に準拠。

1日1回 cron で実行する想定。歌デモなしで全自動化できる2型に絞っている。
  1) trends.py … 伸びてるフォーマットに寄せる型プロファイル（尺・音源）を取得
  2) themes.py … 曜日から型(tip/demo)を選び絵コンテ(storyboard)を生成。Claudeがあれば口語化
  3) tts_producer … ナレーション音声（ElevenLabs。無ければ無音で尺確保）
  4) video_assembler … 縦9:16のMP4を描画（moviepy無ければ絵コンテJSONを出力）
  5) tiktok_poster … Content Posting APIで投稿（キー無 or DRY_RUN なら作るだけ）

「キーが無ければ作る所まで・投稿はしない」が安全既定（sns_autopostと同じ思想）。

環境変数（.env / 環境。.env.example 参照）:
  DRY_RUN=1                  … 投稿しない（既定。動画は生成する）
  APP_URL=https://...        … 誘導先（bioに置く想定。動画内には貼れない）
  ANTHROPIC_API_KEY=...      … あれば台本を口語リライト（無くてもテンプレで動く）
  ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID … ナレーション（無ければ無音）
  TIKTOK_ACCESS_TOKEN        … 投稿用（無ければ生成のみ）
  TIKTOK_RESEARCH_TOKEN      … トレンド検出（無ければ seed/既定にフォールバック）
  MAX_POSTS_PER_DAY=1        … 1日の投稿上限（事故ガード）
  TIKTOK_PRIVACY=SELF_ONLY   … 既定は自分のみ公開（検証後に PUBLIC_TO_EVERYONE）

使い方:
  python generate_and_render.py                 # 今日の曜日の型で1本 生成（DRY_RUN）
  python generate_and_render.py --pillar tip    # 型を指定（tip/demo）
  python generate_and_render.py --refresh-trends # Research APIでトレンド更新してから生成
  DRY_RUN=0 python generate_and_render.py        # 生成して実投稿
"""
import argparse
import datetime
import json
import os
import sys

import themes
import trends
import tts_producer
import video_assembler
import tiktok_poster
import notifier

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_DIR, "out")
PENDING_DIR = os.path.join(_DIR, "out", "pending")
POSTS_LOG = os.path.join(_DIR, "posts_log.jsonl")


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


def _log_post(publish_id: str, pillar: str, video: str, info: str, hook: str = "") -> None:
    rec = {"publish_id": publish_id, "pillar": pillar, "hook": hook,
           "video": os.path.basename(video or ""),
           "info": info, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    with open(POSTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _daily_guard() -> tuple[bool, str]:
    posts = [p for p in _read_jsonl(POSTS_LOG) if p.get("publish_id")]
    today = datetime.date.today().isoformat()
    todays = [p for p in posts if str(p.get("ts", "")).startswith(today)]
    cap = int(os.getenv("MAX_POSTS_PER_DAY", "1"))
    if len(todays) >= cap:
        return False, f"本日の投稿上限({cap}件)に到達"
    return True, f"本日{len(todays)}件（上限{cap}）"


def _rewrite_with_claude(sb: dict) -> dict:
    """ANTHROPIC_API_KEY があれば絵コンテのtext/narrationを口語リライト。失敗時は元のまま。"""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return sb
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        model = os.getenv("TIKTOK_LLM_MODEL", "claude-sonnet-4-6")
        msg = client.messages.create(
            model=model, max_tokens=1500,
            messages=[{"role": "user", "content": themes.claude_prompt(sb)}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[-1]
        new = json.loads(text)
        # スキーマ健全性: scenes数・durationが保たれていれば採用。
        if isinstance(new, dict) and len(new.get("scenes", [])) == len(sb["scenes"]):
            for k in ("scenes", "narration", "caption", "hashtags"):
                if k in new:
                    sb[k] = new[k]
        return sb
    except Exception as e:
        print(f"[warn] Claudeリライト失敗 → テンプレ使用: {e}", file=sys.stderr)
        return sb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pillar", choices=["tip", "demo"], help="型を指定（既定は曜日ローテ）")
    ap.add_argument("--refresh-trends", action="store_true",
                    help="Research APIでトレンドを更新してから生成")
    ap.add_argument("--dry-run", action="store_true", help="投稿せず生成のみ")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    today = datetime.date.today()
    day_index = today.toordinal()
    pillar = args.pillar or themes.pillar_for(today.weekday())

    profile = trends.current_profile(refresh=args.refresh_trends)
    try:
        import autotune
        print(autotune.explain())
    except Exception:
        pass
    sb = themes.storyboard(pillar, day_index, profile)
    sb = _rewrite_with_claude(sb)

    stamp = today.isoformat()
    narr_path = os.path.join(OUT_DIR, f"{stamp}_{pillar}_narration.mp3")
    video_path = os.path.join(OUT_DIR, f"{stamp}_{pillar}.mp4")

    narr = tts_producer.produce(sb["narration"], narr_path, target_sec=sb["duration"])
    audio = narr["path"] if narr["ok"] else None

    print("─" * 52)
    print(f"[{stamp}] pillar={pillar}  trend={profile['source']} "
          f"target={profile['target_duration_sec']}s")
    print(f"ナレーション: {'声入り' if narr['voiced'] else '無音(キー未設定)'}  {sb['duration']}秒")

    result = video_assembler.render(sb, audio, video_path)
    if result["mode"] == "mp4":
        print(f"🎬 動画: {result['path']}")
    else:
        print(f"📝 絵コンテ出力（{result['note']}）: {result['path']}")
        if result.get("script"):
            print(f"   台本: {result['script']}")
    print(f"キャプション: {sb['caption']}")
    print(f"ハッシュタグ: {' '.join(sb['hashtags'])}")
    print("─" * 52)

    dry = args.dry_run or _truthy(os.getenv("DRY_RUN", "1"))
    if dry:
        print("DRY_RUN: 投稿していません（DRY_RUN=0 とTikTokトークンで実投稿）。")
        return 0
    if result["mode"] != "mp4":
        print("⏸ MP4が生成できていないため投稿しません（moviepy/ffmpeg/フォントを確認）。")
        return 0

    ok_guard, why = _daily_guard()
    if not ok_guard:
        print(f"⏸ ガードで停止: {why}")
        return 0

    # NOTIFY_BEFORE_POST=1 の時は pending に置いて通知だけ送る（承認は approve.py）
    if _truthy(os.getenv("NOTIFY_BEFORE_POST", "0")):
        os.makedirs(PENDING_DIR, exist_ok=True)
        pending_video = os.path.join(PENDING_DIR, os.path.basename(video_path))
        pending_sb = os.path.splitext(pending_video)[0] + ".storyboard.json"
        import shutil
        shutil.copy2(video_path, pending_video)
        with open(pending_sb, "w", encoding="utf-8") as f:
            import json as _json
            _json.dump({"storyboard": sb}, f, ensure_ascii=False, indent=2)
        print(f"📥 pending に保存: {os.path.basename(pending_video)}")
        notifier.notify(sb, pending_video, pillar)
        print("確認後: python approve.py  /  スキップ: python approve.py --skip")
        return 0

    ok, publish_id, info = tiktok_poster.post_video(video_path, sb["caption"], sb["hashtags"])
    if ok:
        hook = next((sc["text"] for sc in sb.get("scenes", []) if sc.get("kind") == "hook"), "")
        _log_post(publish_id, pillar, video_path, info, hook=hook)
        print(f"✅ 投稿しました: publish_id={publish_id} ({info})  [{why}]")
        print("※ 投稿後はプロフィール固定コメントで『診断はプロフィールから』を忘れずに（docs/34 §5）。")
        return 0
    print(f"❌ 投稿に失敗: {info}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
