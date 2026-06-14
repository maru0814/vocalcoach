#!/usr/bin/env python3
"""Playwright でアプリ画面を自動録画し demo_clips/ に保存する。

「一度だけの準備」を自動化する層（docs/34）。
流れ:
  1. assets/audio_samples/ にある歌声サンプル（WAV/MP3）を読み込む
  2. Playwright がブラウザを起動 → /voice-type を開く
  3. 「音源をアップロードして診断」でサンプルを送信（マイク不要）
  4. 診断結果が表示されるまで録画 → demo_clips/{tag}_{idx:02d}.mp4 に保存
  5. タグ(diagnose/register/pitch/similar)はサンプルのファイル名接頭辞で指定

事前準備:
  1. pip install playwright && playwright install chromium
  2. python setup_auth.py  … 一度だけログインしてセッションを保存
  3. assets/audio_samples/ に .wav/.mp3 を配置（naming → assets/audio_samples/README.md）

使い方:
  python clip_recorder.py                  # 全サンプルを録画
  python clip_recorder.py --sample assets/audio_samples/diagnose_01.wav  # 1ファイルだけ
  python clip_recorder.py --dry-run        # ブラウザを開くだけ（録画しない / 動作確認用）
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import time

_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.join(_DIR, "assets", "audio_samples")
CLIPS_DIR = os.path.join(_DIR, "assets", "demo_clips")
AUTH_STATE = os.path.join(_DIR, "assets", "auth_state.json")
TMP_VIDEO_DIR = os.path.join(_DIR, "out", "clip_tmp")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_DIR, ".env"))
except Exception:
    pass

APP_URL = os.getenv("APP_URL", "https://sora-vocal-ai.duckdns.org").rstrip("/")
VOICE_TYPE_URL = f"{APP_URL}/voice-type"

# 録画の画面サイズ（縦長スマホ相当）
VIEWPORT = {"width": 390, "height": 844}
RESULT_TIMEOUT_MS = 40_000   # 診断は最大40秒待つ
RECORD_TAIL_SEC = 3.0        # 結果表示後、この秒数だけ追加録画


def _tag_from_filename(path: str) -> str:
    """assets/audio_samples/diagnose_01.wav → 'diagnose'"""
    base = os.path.splitext(os.path.basename(path))[0]
    return base.split("_")[0] if "_" in base else "diagnose"


def _next_clip_path(tag: str) -> str:
    existing = sorted(glob.glob(os.path.join(CLIPS_DIR, f"{tag}_*.mp4")))
    idx = len(existing) + 1
    return os.path.join(CLIPS_DIR, f"{tag}_{idx:02d}.mp4")


def record_one(sample_path: str, dry_run: bool = False) -> dict:
    """1サンプルを録画して demo_clips に保存。returns {ok, path, note}。"""
    tag = _tag_from_filename(sample_path)
    dest = _next_clip_path(tag)
    print(f"  → tag={tag}  sample={os.path.basename(sample_path)}")

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        return {"ok": False, "path": None, "note": "playwright未導入（pip install playwright && playwright install chromium）"}

    os.makedirs(TMP_VIDEO_DIR, exist_ok=True)
    os.makedirs(CLIPS_DIR, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=not dry_run,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        ctx_kwargs: dict = {
            "viewport": VIEWPORT,
            "locale": "ja-JP",
            "user_agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                           "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"),
        }
        if not dry_run:
            ctx_kwargs["record_video_dir"] = TMP_VIDEO_DIR
            ctx_kwargs["record_video_size"] = VIEWPORT
        if os.path.exists(AUTH_STATE):
            ctx_kwargs["storage_state"] = AUTH_STATE

        ctx = browser.new_context(**ctx_kwargs)
        page = ctx.new_page()

        try:
            page.goto(VOICE_TYPE_URL, wait_until="networkidle", timeout=20_000)
            # ログインチェックが終わるまで待つ（スピナーが消えるまで）
            page.wait_for_selector("button:has-text('録音'), button:has-text('アップロード'), a:has-text('登録')",
                                   timeout=10_000)

            if dry_run:
                print("  [dry-run] ページを開いたのみ。Ctrl+C で終了。")
                time.sleep(5)
                ctx.close(); browser.close()
                return {"ok": True, "path": None, "note": "dry-run"}

            # アップロードボタン経由で音声ファイルを送る（マイク不要）
            upload_btn = page.get_by_text("音源をアップロードして診断")
            file_input = page.locator("input[type='file'][accept*='audio']")
            upload_btn.click()
            file_input.set_input_files(sample_path)

            # ローディング中（「声を解析しています」or 「録音中」の消滅）を待つ
            try:
                page.wait_for_selector("text=声を解析しています", timeout=8_000)
            except PWTimeout:
                pass  # 解析開始前に結果が出ることもある
            # 結果カードが出るまで待つ
            page.wait_for_selector("[class*='voice-type'], [class*='VoiceType'], text=総合", timeout=RESULT_TIMEOUT_MS)
            time.sleep(RECORD_TAIL_SEC)
        except PWTimeout as e:
            ctx.close(); browser.close()
            return {"ok": False, "path": None, "note": f"タイムアウト: {e}"}
        except Exception as e:
            ctx.close(); browser.close()
            return {"ok": False, "path": None, "note": f"操作エラー: {e}"}

        # ctx.close() で動画ファイルが確定する
        video_path = page.video.path() if page.video else None
        ctx.close()
        browser.close()

    if not video_path or not os.path.exists(video_path):
        return {"ok": False, "path": None, "note": "動画ファイルが生成されませんでした"}

    # WebM → MP4 に変換（ffmpeg）
    if shutil.which("ffmpeg"):
        cmd = ["ffmpeg", "-y", "-i", video_path,
               "-vf", f"scale={VIEWPORT['width']}:{VIEWPORT['height']}",
               "-c:v", "libx264", "-preset", "medium", "-crf", "23", dest]
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(video_path)
        if r.returncode != 0:
            return {"ok": False, "path": None, "note": "ffmpeg変換失敗"}
    else:
        shutil.move(video_path, dest.replace(".mp4", ".webm"))
        dest = dest.replace(".mp4", ".webm")

    print(f"  ✅ 保存: {os.path.basename(dest)}")
    return {"ok": True, "path": dest, "note": "ok"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", help="1ファイルだけ録画（未指定なら全サンプル）")
    ap.add_argument("--dry-run", action="store_true", help="ブラウザを開くだけ（録画しない）")
    args = ap.parse_args()

    if args.sample:
        samples = [args.sample]
    else:
        samples = sorted(glob.glob(os.path.join(SAMPLES_DIR, "*.wav")) +
                         glob.glob(os.path.join(SAMPLES_DIR, "*.mp3")))
        if not samples:
            print(f"サンプルが見つかりません: {SAMPLES_DIR}\nassets/audio_samples/README.md を参照してください。")
            return 1

    ok_count, fail_count = 0, 0
    for path in samples:
        print(f"[{samples.index(path) + 1}/{len(samples)}] {os.path.basename(path)}")
        res = record_one(path, dry_run=args.dry_run)
        if res["ok"]:
            ok_count += 1
        else:
            fail_count += 1
            print(f"  ❌ {res['note']}")

    print(f"\n完了: {ok_count}本成功 / {fail_count}本失敗")
    if fail_count:
        print("ヒント: python setup_auth.py でログインセッションを保存してから再実行してください。")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
