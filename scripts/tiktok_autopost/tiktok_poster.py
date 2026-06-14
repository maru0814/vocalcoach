"""TikTok Content Posting API へのアップロード。キー未設定 or DRY_RUN なら投稿せず情報表示。

TikTok仕様の注意（docs/34 §5）:
- 動画・キャプションに踏めるリンクは貼れない。CTAは「プロフィールから」。bioのリンクが唯一の導線。
- Content Posting API は Business/承認アプリ枠が必要（申請に数日〜2週間）。承認までは手動投稿で並行。
- 直アップは FILE_UPLOAD（チャンク送信）。ここでは最小実装（1チャンク）＋ステータス確認。
"""
import os
import sys
import time


def _token() -> str | None:
    """ユーザーアクセストークン（OAuthで取得済みの想定。更新は別途cron）。"""
    return os.getenv("TIKTOK_ACCESS_TOKEN")


def post_video(video_path: str, caption: str, hashtags: list[str]) -> tuple[bool, str, str]:
    """動画を投稿。returns (ok, publish_id, info)。"""
    token = _token()
    if not token:
        return False, "", "TIKTOK_TOKEN_MISSING"
    if not (video_path and os.path.exists(video_path)):
        return False, "", f"VIDEO_NOT_FOUND: {video_path}"
    try:
        import requests
        size = os.path.getsize(video_path)
        title = (caption + " " + " ".join(hashtags)).strip()[:2200]
        privacy = os.getenv("TIKTOK_PRIVACY", "SELF_ONLY")  # 既定は自分のみ＝事故防止
        headers = {"Authorization": f"Bearer {token}",
                   "Content-Type": "application/json; charset=UTF-8"}

        # 1) 投稿セッションを初期化（FILE_UPLOAD・1チャンク）
        init = requests.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers=headers,
            json={"post_info": {"title": title, "privacy_level": privacy,
                                "disable_comment": False},
                  "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                  "chunk_size": size, "total_chunk_count": 1}},
            timeout=30,
        )
        if init.status_code != 200:
            return False, "", f"INIT HTTP {init.status_code}: {init.text[:200]}"
        data = init.json().get("data", {})
        publish_id = data.get("publish_id", "")
        upload_url = data.get("upload_url", "")
        if not upload_url:
            return False, "", f"NO_UPLOAD_URL: {init.text[:200]}"

        # 2) 動画バイト列をPUTでアップロード
        with open(video_path, "rb") as f:
            body = f.read()
        put = requests.put(
            upload_url, data=body,
            headers={"Content-Type": "video/mp4",
                     "Content-Range": f"bytes 0-{size - 1}/{size}"},
            timeout=300,
        )
        if put.status_code not in (200, 201, 206):
            return False, publish_id, f"UPLOAD HTTP {put.status_code}: {put.text[:160]}"

        # 3) 公開ステータスを軽くポーリング
        info = "uploaded"
        for _ in range(3):
            time.sleep(2)
            st = requests.post(
                "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
                headers=headers, json={"publish_id": publish_id}, timeout=20)
            if st.status_code == 200:
                status = (st.json().get("data") or {}).get("status", "")
                info = status or info
                if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
                    break
        return True, publish_id, info
    except Exception as e:
        return False, "", f"EXC: {e}"


if __name__ == "__main__":
    ok, pid, info = post_video(sys.argv[1] if len(sys.argv) > 1 else "", "テスト投稿", ["#テスト"])
    print(ok, pid, info)
