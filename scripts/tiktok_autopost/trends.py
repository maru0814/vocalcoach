"""トレンド検出 — 伸びてるフォーマットに“寄せる”ための型プロファイルを返す。

docs/34 §1 の「流行りのフォーマットをパクる」を実装する層。ただし“パクる”の対象は
**構造（尺・テロップ密度・フックの言い回し傾向・トレンド音源ID）**であって、他者の映像/音声そのものではない。
他人の動画を再アップロードしない（IP配慮）。やるのは「今どの構造が伸びてるか」を数値で掴み、
自前テンプレ(themes.storyboard)のパラメータに落とすこと。

データ源:
- TikTok Research API（学術/一部ビジネス枠。要申請）でニッチのトップ動画メタを取得 → 中央値の尺・
  トレンド音源を抽出。Commercial Sounds Library の楽曲なら投稿に合法的に使える。
- キー未設定なら同梱の trends_seed.json（手動更新OK）にフォールバック。
"""
import json
import os
import statistics

_DIR = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(_DIR, "trends_seed.json")
CACHE = os.path.join(_DIR, "trends_cache.json")

# ニッチを絞る検索語（docs/34）。Research API のクエリにもseed選定にも使う。
NICHE_HASHTAGS = ["ボイトレ", "歌ってみた", "カラオケ", "ミックスボイス", "声診断"]

DEFAULT_PROFILE = {
    "target_duration_sec": 22,   # 短尺＝高完了率（15秒なら13秒視聴で“完了”）。
    "caption_density": "high",   # テロップ密度。high=テンポ速め
    "trending_sound": None,      # 使える音源ID or ローカルBGMパス。None＝無音/自前BGM
    "source": "default",
}


def _research_api_token() -> str | None:
    return os.getenv("TIKTOK_RESEARCH_TOKEN")


def _from_research_api() -> dict | None:
    """TikTok Research API でニッチのトップ動画メタを取得し型プロファイル化。失敗時 None。"""
    token = _research_api_token()
    if not token:
        return None
    try:
        import requests
        url = "https://open.tiktokapis.com/v2/research/video/query/"
        # 直近のニッチ人気動画を取得（フィールドは尺と音源のみ＝メタ情報。本文/映像は取らない）。
        body = {
            "query": {"and": [{"operation": "IN", "field_name": "hashtag_name",
                               "field_values": NICHE_HASHTAGS}]},
            "max_count": 50,
            "fields": ["id", "duration", "music_id", "view_count"],
        }
        r = requests.post(url, params={"fields": "id,duration,music_id,view_count"},
                          headers={"Authorization": f"Bearer {token}",
                                   "Content-Type": "application/json"},
                          json=body, timeout=20)
        if r.status_code != 200:
            return None
        vids = (r.json().get("data") or {}).get("videos") or []
        if not vids:
            return None
        durs = [int(v["duration"]) for v in vids if v.get("duration")]
        # 再生数で重み付けして“伸びてる音源”を1つ拾う。
        top = sorted(vids, key=lambda v: int(v.get("view_count", 0)), reverse=True)
        sound = next((str(v["music_id"]) for v in top if v.get("music_id")), None)
        target = int(statistics.median(durs)) if durs else 22
        target = min(max(target, 12), 34)  # 12〜34秒に丸める（完了率優先）
        return {"target_duration_sec": target, "caption_density": "high",
                "trending_sound": sound, "source": "research_api"}
    except Exception:
        return None


def _from_seed() -> dict | None:
    for path in (CACHE, SEED):
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                prof = dict(DEFAULT_PROFILE)
                prof.update(data.get("profile", {}))
                prof["source"] = f"seed:{os.path.basename(path)}"
                return prof
            except Exception:
                continue
    return None


def current_profile(refresh: bool = False) -> dict:
    """今週寄せるべき型プロファイルを返す。Research API → seed → 既定の順でフォールバック。"""
    if refresh:
        prof = _from_research_api()
        if prof:
            try:
                with open(CACHE, "w", encoding="utf-8") as f:
                    json.dump({"profile": prof}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return prof
    return _from_seed() or dict(DEFAULT_PROFILE)


if __name__ == "__main__":
    import sys
    refresh = "--refresh" in sys.argv
    prof = current_profile(refresh=refresh)
    print(json.dumps(prof, ensure_ascii=False, indent=2))
