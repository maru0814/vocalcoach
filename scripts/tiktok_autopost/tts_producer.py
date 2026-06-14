"""ナレーション音声の生成。ElevenLabs（声クローン）優先、無ければ無音で尺を確保して縮退。

sns_autopost の流儀に合わせ「キーが無ければ安全に動く」。キー未設定でも動画は字幕だけで成立する。
ElevenLabs 1キーで日本語ナレーションを生成（docs/34 のコスト試算: 月$11程度）。
"""
import os
import shutil
import subprocess
import sys


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _estimate_sec(text: str) -> float:
    """日本語の読み上げ尺をざっくり推定（約7文字/秒）。最低3秒。"""
    n = len([c for c in text if not c.isspace()])
    return max(round(n / 7.0, 1), 3.0)


def _silence(out_path: str, seconds: float) -> bool:
    """無音WAVを生成（ffmpeg）。TTSキーが無い時のフォールバック。"""
    if not _has_ffmpeg():
        return False
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
           "-t", str(seconds), "-q:a", "9", out_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _elevenlabs(text: str, out_path: str) -> bool:
    key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    if not (key and voice_id):
        return False
    try:
        import requests
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        model = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
        r = requests.post(
            url,
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text, "model_id": model,
                  "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
            timeout=60,
        )
        if r.status_code != 200:
            print(f"[warn] ElevenLabs HTTP {r.status_code}: {r.text[:160]}", file=sys.stderr)
            return False
        with open(out_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"[warn] ElevenLabs失敗 → 無音にフォールバック: {e}", file=sys.stderr)
        return False


def produce(text: str, out_path: str, target_sec: float | None = None) -> dict:
    """ナレーション音声を out_path に生成。
    returns {ok, voiced(声入りか), seconds, path}。
    """
    seconds = float(target_sec or _estimate_sec(text))
    if _elevenlabs(text, out_path):
        return {"ok": True, "voiced": True, "seconds": seconds, "path": out_path}
    if _silence(out_path, seconds):
        return {"ok": True, "voiced": False, "seconds": seconds, "path": out_path}
    return {"ok": False, "voiced": False, "seconds": seconds, "path": None}


if __name__ == "__main__":
    txt = " ".join(sys.argv[1:]) or "テスト。これはナレーションの確認です。"
    res = produce(txt, os.path.join(os.path.dirname(__file__), "narration_test.mp3"))
    print(res)
