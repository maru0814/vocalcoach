"""
Reference (original song) acquisition via yt-dlp.
解析目的の一時取得。許可ドメインのみ。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from app.audio.convert import ffmpeg_exe

ALLOWED_HOSTS = {
    "www.youtube.com", "youtube.com", "youtu.be", "m.youtube.com", "music.youtube.com",
}


class ReferenceFetchError(Exception):
    pass


def is_allowed_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    return host in ALLOWED_HOSTS


def fetch_reference_wav(url: str, out_dir: str | Path, name: str) -> str:
    """Download audio from a YouTube URL and return the path to a wav file.

    Raises ReferenceFetchError on failure or disallowed URL.
    """
    if not is_allowed_url(url):
        raise ReferenceFetchError("対応していないURLです（YouTubeのURLをご利用ください）")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(out_dir / f"{name}.%(ext)s")
    wav_path = out_dir / f"{name}.wav"
    if wav_path.exists():
        return str(wav_path)

    ffmpeg = ffmpeg_exe()
    # 現在のPython（venv）の yt_dlp モジュールを直接呼ぶ（PATH非依存）
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--ffmpeg-location", ffmpeg,
        "-x", "--audio-format", "wav", "--audio-quality", "0",
        "--no-playlist",
        "-o", out_tmpl,
        url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as e:
        raise ReferenceFetchError("原曲の取得がタイムアウトしました") from e

    if proc.returncode != 0 or not wav_path.exists():
        raise ReferenceFetchError(f"原曲音源の取得に失敗しました: {proc.stderr.strip()[:200]}")
    return str(wav_path)
