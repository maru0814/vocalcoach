"""動画生成後の確認通知を送る。LINE Messaging API（主）→ Discord Webhook（副）の順で試みる。

通知の内容:
  - 動画ファイル（LINE: 0x0.st経由の一時URL / Discord: 直接添付）
  - 台本テキスト

LINE Messaging API（公式LINEアカウント経由。無料枠200通/月）:
  TIKTOK_LINE_CHANNEL_TOKEN=<チャンネルアクセストークン（長期）>
  TIKTOK_LINE_USER_ID=<あなたのLINEユーザーID（Uで始まる文字列）>

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
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path],
            capture_output=True, text=True, timeout=10)
        dur = 5.0
        if r.returncode == 0:
            for s in (json.loads(r.stdout).get("streams") or []):
                if s.get("codec_type") == "video":
                    dur = float(s.get("duration", 5.0))
                    break
        ts = dur * 0.3
        tmp = tempfile.mktemp(suffix=".jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(ts), "-i", video_path, "-vframes", "1",
             "-vf", "scale=390:-1", "-q:v", "3", tmp],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=20)
        return tmp if os.path.exists(tmp) else None
    except Exception:
        return None


def _upload_temp(path: str) -> str | None:
    """ファイルを litterbox.catbox.moe（24h）にアップロードして公開HTTPS URLを返す。失敗時 None。
    動画・サムネイルを一時公開してLINEのビデオメッセージに使う。"""
    if not path or not os.path.exists(path):
        return None
    try:
        import requests
        with open(path, "rb") as f:
            r = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "24h"},
                files={"fileToUpload": f},
                timeout=120,
            )
        if r.status_code == 200:
            url = r.text.strip()
            if url.startswith("https://"):
                return url
        print(f"[warn] litterbox アップロード失敗 HTTP {r.status_code}: {r.text[:100]}", file=sys.stderr)
    except Exception as e:
        print(f"[warn] 一時アップロード失敗: {e}", file=sys.stderr)
    return None


def _script_text(storyboard: dict, pillar: str) -> str:
    lines = [
        "🎬 TikTok動画 生成完了",
        f"型: {pillar}  / {storyboard.get('duration', '?')}秒",
        "",
        "▼ キャプション",
        storyboard.get("caption", ""),
        "",
        "▼ 台本",
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


def _send_line(text: str, video_path: str | None, thumb_path: str | None) -> bool:
    """LINE Messaging APIで通知を送る。動画があれば0x0.stにアップロードして動画メッセージで送る。

    TIKTOK_LINE_USER_ID があれば push（指定ユーザー宛）、無ければ broadcast（友だち全員宛）。
    自分1人だけが友だちなら broadcast でユーザーID不要。
    """
    token = os.getenv("TIKTOK_LINE_CHANNEL_TOKEN")
    user_id = os.getenv("TIKTOK_LINE_USER_ID")  # 任意。無ければ broadcast を使う
    if not token:
        return False
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        messages = []

        if video_path and os.path.exists(video_path):
            print("動画をアップロード中...", end=" ", flush=True)
            video_url = _upload_temp(video_path)
            thumb_url = _upload_temp(thumb_path) if thumb_path else None
            if video_url:
                print("完了")
                messages.append({
                    "type": "video",
                    "originalContentUrl": video_url,
                    "previewImageUrl": thumb_url if thumb_url else video_url,
                })
            else:
                print("失敗（テキストのみ送信）")

        messages.append({"type": "text", "text": text[:5000]})

        if user_id:
            endpoint = "https://api.line.me/v2/bot/message/push"
            body = {"to": user_id, "messages": messages}
        else:
            endpoint = "https://api.line.me/v2/bot/message/broadcast"
            body = {"messages": messages}

        r = requests.post(endpoint, headers=headers, json=body, timeout=20)
        if r.status_code == 200:
            return True
        print(f"[warn] LINE送信失敗 HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[warn] LINE通知失敗: {e}", file=sys.stderr)
        return False


def _send_discord(text: str, video_path: str | None, thumb_path: str | None) -> bool:
    """Discord Webhookで通知を送る。動画ファイルを直接添付する。"""
    url = os.getenv("TIKTOK_DISCORD_WEBHOOK_URL")
    if not url:
        return False
    try:
        import requests
        payload = {"content": text[:2000]}

        # 動画ファイルを直接添付（Discordは25MBまでファイル添付可）
        if video_path and os.path.exists(video_path):
            with open(video_path, "rb") as vf:
                files = {"file": (os.path.basename(video_path), vf, "video/mp4")}
                r = requests.post(url, data={"payload_json": json.dumps(payload)},
                                  files=files, timeout=60)
        else:
            r = requests.post(url, json=payload, timeout=20)
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"[warn] Discord通知失敗: {e}", file=sys.stderr)
        return False


def notify(storyboard: dict, video_path: str | None, pillar: str) -> bool:
    """通知を送る。LINE → Discord の順。どちらもキー未設定なら標準出力に出す。"""
    text = _script_text(storyboard, pillar)
    thumb = _thumbnail(video_path) if video_path else None

    try:
        if _send_line(text, video_path, thumb):
            print("📱 LINE通知を送信しました。")
            return True
        if _send_discord(text, video_path, thumb):
            print("💬 Discord通知を送信しました。")
            return True

        print("=" * 52)
        print("【通知キー未設定】以下の内容を確認して承認してください:")
        print(text)
        print("=" * 52)
        return False
    finally:
        if thumb and os.path.exists(thumb):
            os.remove(thumb)


def send_report(text: str) -> bool:
    """週次分析レポートをLINE → Discord の順で送信する（動画なし）。"""
    if _send_line(text, None, None):
        print("📱 週次レポートをLINEに送信しました。")
        return True
    if _send_discord(text, None, None):
        print("💬 週次レポートをDiscordに送信しました。")
        return True
    return False
