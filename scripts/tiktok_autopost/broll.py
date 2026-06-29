"""ネタに合う実写B-roll（縦型ストック動画）を Pexels API で取得し、9:16に正規化してキャッシュする。

紙芝居脱却の核。背景を「動くグラデ」から「実写（歌う人・マイク・スタジオ・波形）」に変え、
本文カットごとに切り替えることで“編集された動画”に見せる。

設計（sns_autopostの流儀: キーが無ければ安全に縮退）:
- PEXELS_API_KEY が無い / 取得失敗 / ffmpeg無し → None を返す。
  video_assembler 側が従来の背景（焼き込みモーション / 静止グラデ）にフォールバックする。
- 取得した素材は ffmpeg で 1080x1920 にカバークロップ＋軽い暗化して assets/broll_cache/ に焼く。
  本番の合成（moviepy）は「焼いたクリップを読んで切るだけ」＝リサイズ不要で軽く、PILにも触らない。

ライセンス: Pexels は無料・商用利用可・クレジット不要・改変可。市販曲/他者作品の転載はしない。
ユーザーがやること: https://www.pexels.com/api/ で無料登録 → APIキーを .env の PEXELS_API_KEY= に。
"""
import glob
import os
import re
import subprocess
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

# 解像度は環境変数で下げられる（video_assembler と揃える）。変えたら broll_cache を消して焼き直す。
W = int(os.getenv("TIKTOK_W", "1080"))
H = int(os.getenv("TIKTOK_H", "1920"))
_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(_DIR, "assets", "broll_cache")
RAW_DIR = os.path.join(CACHE_DIR, "raw")

# ネタ本文 → Pexels検索語（英語の方がヒット率が高い）。上から順にマッチを試す。
# フックには“顔・動き”の強い素材を優先で当てる（指を止める7割はここ）。
QUERY_MAP = [
    (r"高音",                 ["woman singing closeup", "singer microphone", "concert singing"]),
    (r"ミックス",             ["singer studio", "vocalist microphone", "singing closeup"]),
    (r"裏声",                 ["singing emotional", "female vocalist", "live singing"]),
    (r"声帯|喉|息",           ["throat closeup", "breathing calm", "person relaxing"]),
    (r"換声点",               ["vocal practice", "singing lesson", "music studio"]),
    (r"カラオケ",             ["karaoke night", "friends singing", "microphone neon"]),
    (r"録音",                 ["recording studio", "audio waveform", "studio microphone"]),
    (r"音痴",                 ["headphones listening", "music notes", "person headphones"]),
    (r"リップロール|ハミング", ["vocal warm up", "singing practice", "music class"]),
]
HOOK_QUERIES = ["woman singing closeup", "passionate singer", "singer microphone stage"]
DEFAULT_QUERIES = ["microphone stage", "music studio dark", "singer silhouette"]


def _api_key() -> str | None:
    return os.getenv("PEXELS_API_KEY") or None


def _has_ffmpeg() -> bool:
    import shutil
    return shutil.which("ffmpeg") is not None


def queries_for(text: str, is_hook: bool = False) -> list[str]:
    """シーンの字幕テキストから検索語の候補リストを引く。"""
    if is_hook:
        return HOOK_QUERIES + DEFAULT_QUERIES
    out = []
    for pat, qs in QUERY_MAP:
        if re.search(pat, text or ""):
            out += qs
    out += DEFAULT_QUERIES
    # 重複を除いて順序維持
    seen, uniq = set(), []
    for q in out:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


def _search_pexels(query: str, exclude_ids: set, key: str) -> tuple | None:
    """Pexels Videos を検索し (video_id, 直リンクmp4 URL) を1つ返す。失敗/該当なし None。"""
    try:
        import requests
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "orientation": "portrait",
                    "size": "medium", "per_page": 15},
            headers={"Authorization": key}, timeout=20)
        if r.status_code != 200:
            print(f"[warn] Pexels検索 HTTP {r.status_code}: {r.text[:120]}", file=sys.stderr)
            return None
        videos = r.json().get("videos") or []
        for v in videos:
            vid = v.get("id")
            if not vid or vid in exclude_ids:
                continue
            if float(v.get("duration", 0)) < 3:
                continue
            # 縦型で、解像度が大きすぎない(=DLが軽い)ファイルを選ぶ。
            files = [f for f in (v.get("video_files") or [])
                     if f.get("link") and (f.get("height") or 0) >= (f.get("width") or 0)]
            if not files:
                files = v.get("video_files") or []
            # height 1200〜2400 を優先、無ければ最小heightを選ぶ
            def score(f):
                h = f.get("height") or 0
                return (0 if 1200 <= h <= 2400 else 1, h)
            files = sorted([f for f in files if f.get("link")], key=score)
            if files:
                return (vid, files[0]["link"])
        return None
    except Exception as e:
        print(f"[warn] Pexels検索失敗: {e}", file=sys.stderr)
        return None


def _download(url: str, dest: str) -> bool:
    try:
        import requests
        with requests.get(url, stream=True, timeout=120) as r:
            if r.status_code != 200:
                return False
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    if chunk:
                        f.write(chunk)
        return os.path.getsize(dest) > 1024
    except Exception as e:
        print(f"[warn] B-rollダウンロード失敗: {e}", file=sys.stderr)
        return False


def _normalize(raw_path: str, out_path: str, max_sec: float = 10.0) -> bool:
    """ffmpegで 1080x1920 にカバークロップ＋軽い暗化＋yuv420p に焼く（最長 max_sec）。"""
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},eq=brightness=-0.10:saturation=1.05,format=yuv420p")
    cmd = ["ffmpeg", "-y", "-i", raw_path, "-t", str(max_sec), "-an",
           "-vf", vf, "-r", "30", "-preset", "veryfast", out_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=180)
        return os.path.exists(out_path) and os.path.getsize(out_path) > 1024
    except Exception as e:
        print(f"[warn] B-roll正規化失敗: {e}", file=sys.stderr)
        return False


def fetch_for(text: str, exclude_ids: set, is_hook: bool = False) -> str | None:
    """字幕テキストに合う正規化済みB-rollのパスを返す。無ければ None（背景フォールバック）。

    exclude_ids には使用済みの video_id を入れて渡すと、同一動画内でB-rollが被らない。
    """
    key = _api_key()
    if not key or not _has_ffmpeg():
        return None
    os.makedirs(RAW_DIR, exist_ok=True)
    for q in queries_for(text, is_hook):
        hit = _search_pexels(q, exclude_ids, key)
        if not hit:
            continue
        vid, url = hit
        cached = os.path.join(CACHE_DIR, f"{vid}.mp4")
        if os.path.exists(cached):
            exclude_ids.add(vid)
            return cached
        raw = os.path.join(RAW_DIR, f"{vid}_raw.mp4")
        if not os.path.exists(raw) and not _download(url, raw):
            continue
        if _normalize(raw, cached):
            try:
                os.remove(raw)  # 生ファイルは消してキャッシュだけ残す
            except Exception:
                pass
            exclude_ids.add(vid)
            return cached
    return None


def cached_clips() -> list[str]:
    """既に焼いてあるB-rollキャッシュ（オフライン時の使い回し用）。"""
    return sorted(glob.glob(os.path.join(CACHE_DIR, "*.mp4")))


if __name__ == "__main__":
    # 単体テスト: 検索語の確認と、キーがあれば1本取得してみる。
    print("queries(高音, hook):", queries_for("まだ喉で高音出そうとしてる?", is_hook=True)[:3])
    print("queries(ミックス):", queries_for("ミックスボイスが出ない本当の理由")[:3])
    if _api_key():
        ex = set()
        p = fetch_for("まだ喉で高音出そうとしてる?", ex, is_hook=True)
        print("取得:", p)
    else:
        print("PEXELS_API_KEY 未設定（取得テストはスキップ）")
