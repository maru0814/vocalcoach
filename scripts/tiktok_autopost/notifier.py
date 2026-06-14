"""動画生成後の確認通知を送る。LINE Notify（主）→ Discord Webhook（副）の順で試みる。

通知の内容:
  - 動画の絵コンテ（台本テキスト）
  - サムネイル画像（ffmpeg で動画から切り出し。ffmpeg無ければ省略）
  - 承認コマンド（SSH してから python approve.py）

LINE Notify: https://notify-bot.line.me/ でトークンを発行（無料）。
  TIKTOK_LINE_TOKEN=<your_token> を .env に追加するだけで動く。

Discord: TIKTOK_DISCORD_WEBHOOK_URL を .env に追加。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile


def _thumbnail(video_path: str) -> str | None:
    """ffmpeg で動画の中間フレームをJPEGに切り出す。失敗したら None。"""
    if not (video_path and os.path.exists(video_path) and shutil.which("ffmpeg")):
        return None
    try:
        import subprocess, tempfile
        # 動画の長さを取得
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path],
            capture_output=True, text=True, timeout=10)
        dur = 5.0
        if r.returncode == 0:
            for s in (json.loads(r.stdout).get("streams") or []):
                if s.get("codec_type") == "video":
                    dur = float(s.get("duration", 5.0))
                    break
        ts = dur * 0.3  # 動画の30%地点（フックテロップが大きく出ている）
        tmp = tempfile.mktemp(suffix=".jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(ts), "-i", video_path, "-vframes", "1",
             "-vf", "scale=390:-1", "-q:v", "3", tmp],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=20)
        return tmp if os.path.exists(tmp) else None
    except Exception:
        return None


def _script_text(storyboard: dict, pillar: str) -> str:
    """通知に貼るテキストを組み立てる。"""
    lines = [
        f"🎬 TikTok動画 生成完了",
        f"型: {pillar}  / {storyboard.get('duration', '?')}秒",
        "",
        f"▼ キャプション",
        storyboard.get("caption", ""),
        "",
        f"▼ 台本",
    ]
    for sc in storyboard.get("scenes", []):
        t = sc.get("text", "").replace("\n", " ")
        if sc["kind"] == "clip":
            t = f"<アプリ画面録画 tag={sc.get('clip_tag')}>"
        lines.append(f"[{sc['kind']}] {t}")
    lines += ["", "▼ ハッシュタグ", " ".join(storyboard.get("hashtags", []))]
    lines += ["", "✅ 承認して投稿: python approve.py",
              "🗑 スキップ: python approve.py --skip"]
    return "\n".join(lines)


def _send_line(text: str, image_path: str | None) -> bool:
    token = os.getenv("TIKTOK_LINE_TOKEN")
    if not token:
        return False
    try:
        import requests
        data = {"message": text[:1000]}  # LINE Notify は1000文字上限
        files = {}
        if image_path and os.path.exists(image_path):
            files = {"imageFile": open(image_path, "rb")}
        r = requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {token}"},
            data=data, files=files if files else None, timeout=20)
        return r.status_code == 200
    except Exception as e:
        print(f"[warn] LINE通知失敗: {e}", file=sys.stderr)
        return False


def _send_discord(text: str, image_path: str | None) -> bool:
    url = os.getenv("TIKTOK_DISCORD_WEBHOOK_URL")
    if not url:
        return False
    try:
        import requests
        payload = {"content": text[:2000]}
        files = {}
        if image_path and os.path.exists(image_path):
            files = {"file": ("thumbnail.jpg", open(image_path, "rb"), "image/jpeg")}
            r = requests.post(url, data={"payload_json": json.dumps(payload)},
                              files=files, timeout=20)
        else:
            r = requests.post(url, json=payload, timeout=20)
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"[warn] Discord通知失敗: {e}", file=sys.stderr)
        return False


def notify(storyboard: dict, video_path: str | None, pillar: str) -> bool:
    """通知を送る。LINE → Discord の順。どちらもキー未設定なら標準出力に出す。returns True if sent."""
    text = _script_text(storyboard, pillar)
    thumb = _thumbnail(video_path) if video_path else None

    if _send_line(text, thumb):
        print("📱 LINE通知を送信しました。")
        if thumb:
            os.remove(thumb)
        return True
    if _send_discord(text, thumb):
        print("💬 Discord通知を送信しました。")
        if thumb:
            os.remove(thumb)
        return True

    # どちらのキーもない → 標準出力に出してスキップ
    print("=" * 52)
    print("【通知キー未設定】以下の内容を確認して承認してください:")
    print(text)
    print("=" * 52)
    if thumb:
        os.remove(thumb)
    return False


def send_report(text: str) -> bool:
    """週次分析レポートをLINE → Discord の順で送信する。returns True if sent."""
    if _send_line(text, None):
        print("📱 週次レポートをLINEに送信しました。")
        return True
    if _send_discord(text, None):
        print("💬 週次レポートをDiscordに送信しました。")
        return True
    return False
