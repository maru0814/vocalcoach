"""
Reference (original song) acquisition via yt-dlp.
解析目的の一時取得。許可ドメインのみ。
"""

from __future__ import annotations

import json
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse

from app.audio.convert import ffmpeg_exe


def _ssl_context() -> ssl.SSLContext | None:
    """certifi があればそれで検証。無ければ既定（環境のCA）。"""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None

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


def fetch_youtube_title(url: str, timeout: float = 5.0) -> str | None:
    """oEmbed で YouTube 動画のタイトルを取得（ダウンロード不要・無料）。失敗時 None。"""
    if not is_allowed_url(url):
        return None
    oembed = f"https://www.youtube.com/oembed?url={quote(url, safe='')}&format=json"
    try:
        req = urllib.request.Request(
            oembed, headers={"User-Agent": "Mozilla/5.0 (compatible; VocalCoach/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            title = data.get("title")
            return title.strip() if isinstance(title, str) and title.strip() else None
    except Exception:
        return None


def search_youtube(query: str, limit: int = 3, timeout: float = 20.0) -> list[dict]:
    """曲名（＋歌手名）から YouTube の原曲候補を探す（docs/72 FR-01）。

    yt-dlp の ytsearch をフラットモードで叩き、メタデータだけ取得する
    （動画・音声のダウンロードは一切しない）。失敗・0件時は空リスト。
    返却: [{"title", "url", "channel", "duration_sec"}]（最大 limit 件）
    """
    q = (query or "").strip()
    if not q:
        return []
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist", "-j", "--no-warnings",
        f"ytsearch{int(limit)}:{q}",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return []
    out: list[dict] = []
    for line in (proc.stdout or "").splitlines():
        try:
            e = json.loads(line)
        except (ValueError, TypeError):
            continue
        vid, title = e.get("id"), e.get("title")
        if not vid or not title:
            continue
        out.append({
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "channel": e.get("channel") or e.get("uploader") or "",
            "duration_sec": int(e["duration"]) if e.get("duration") else None,
        })
        if len(out) >= limit:
            break
    return out


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
