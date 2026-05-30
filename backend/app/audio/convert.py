"""
Audio format conversion via the ffmpeg binary bundled with imageio-ffmpeg.
ブラウザ録音(webm/opus)やアップロード(mp3/m4a)を解析用 wav に正規化する。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import imageio_ffmpeg


def ffmpeg_exe() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def to_wav(src_path: str | Path, dst_path: str | Path, sr: int = 22050) -> str:
    """Convert any audio file to mono wav at the given sample rate."""
    src, dst = str(src_path), str(dst_path)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_exe(),
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", src,
        "-ac", "1",
        "-ar", str(sr),
        dst,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {proc.stderr.strip()}")
    return dst
