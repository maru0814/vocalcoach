"""
Mic recorder for vocal-trainer skill.

macOS の AVFoundation 経由でマイクから wav を録音する小道具。
ffmpeg は backend/.venv 経由の imageio-ffmpeg をそのまま利用する。

初回実行時、ターミナル（または Claude Code）にマイク許可ダイアログが出る。
許可が取れないと録音は空ファイル/エラーになる。

使い方:
    python tools/record_audio.py --duration 30 --out tmp/audio/take1.wav
    python tools/record_audio.py --list                # マイクデバイス一覧
    python tools/record_audio.py --device 1 --duration 30 --out take.wav
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg


SR = 44100         # 録音は 44.1kHz で取り、解析側で 22050 にダウンサンプル
CHANNELS = 1       # モノラル
DEFAULT_DEVICE = 1  # macOS 内蔵マイクが大抵 index 1（MacBook Air のマイク等）


def ffmpeg_path() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def list_audio_devices() -> list[tuple[int, str]]:
    """Return [(index, name)] of avfoundation audio devices on macOS."""
    proc = subprocess.run(
        [ffmpeg_path(), "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True,
        text=True,
    )
    text = proc.stderr  # ffmpeg lists devices on stderr
    devices: list[tuple[int, str]] = []
    in_audio_section = False
    for line in text.splitlines():
        if "AVFoundation audio devices" in line:
            in_audio_section = True
            continue
        if in_audio_section:
            m = re.search(r"\[(\d+)\] (.+)$", line)
            if m:
                devices.append((int(m.group(1)), m.group(2).strip()))
            else:
                # End of section on first non-matching line
                if devices:
                    break
    return devices


def record(device: int, duration_sec: float, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    cmd = [
        ffmpeg_path(),
        "-hide_banner",
        "-loglevel", "warning",
        "-f", "avfoundation",
        "-i", f":{device}",
        "-t", str(duration_sec),
        "-ar", str(SR),
        "-ac", str(CHANNELS),
        "-y",
        str(out_path),
    ]
    print(f"[recording] device={device}, duration={duration_sec}s → {out_path}", file=sys.stderr)
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print("[error] ffmpeg failed. macOS のマイク許可を確認してください "
              "(System Settings → Privacy & Security → Microphone)", file=sys.stderr)
        return proc.returncode
    if not out_path.exists() or out_path.stat().st_size < 1024:
        print("[error] 録音ファイルが空または極小です。マイク許可未付与の可能性大", file=sys.stderr)
        return 2
    size_kb = out_path.stat().st_size / 1024
    print(f"[done] {out_path} ({size_kb:.1f} KB)", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Record audio from macOS mic via ffmpeg avfoundation.")
    parser.add_argument("--list", action="store_true", help="List audio devices and exit")
    parser.add_argument("--device", type=int, default=DEFAULT_DEVICE,
                        help=f"AVFoundation audio device index (default: {DEFAULT_DEVICE})")
    parser.add_argument("--duration", type=float, help="Recording duration in seconds")
    parser.add_argument("--out", type=str, help="Output wav path")
    args = parser.parse_args()

    if args.list:
        devices = list_audio_devices()
        if not devices:
            print("(no audio devices found)", file=sys.stderr)
            return 1
        for idx, name in devices:
            print(f"  [{idx}] {name}")
        return 0

    if args.duration is None or args.out is None:
        parser.error("--duration and --out are required (or pass --list)")

    return record(args.device, args.duration, Path(args.out))


if __name__ == "__main__":
    sys.exit(main())
