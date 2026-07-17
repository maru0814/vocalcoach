"""ソラ先生（LLM）が呼べるツール群（docs/44）。

会話の主導権は LLM に渡しつつ、"事実"（動画リンク・練習手順）は
ここが**カタログの実データだけ**を返す。ツールが URL を生成することはない
＝ 実在しない YouTube リンクの捏造を構造的に防ぐ。
"""
from typing import Optional

from app.coaching import rule_engine
from app.coaching.taxonomy import TASKS, get_task


def _catalog_video_urls() -> set[str]:
    """taxonomy に載っている実在動画URLの許可リスト（応答スクラブにも使う）。"""
    urls: set[str] = set()
    for t in TASKS:
        for p in t.get("practices", []):
            v = p.get("video") or {}
            if v.get("url"):
                urls.add(v["url"])
    return urls


CATALOG_VIDEO_URLS = _catalog_video_urls()


def find_reference_video(topic: str) -> dict:
    """練習トピック→対応課題の★練習と実在動画を返す。

    topic は日本語自由文（例: "エッジボイス" "高音" "ビブラート" "声帯の閉じ"）。
    見つからなければ {"found": False}。current_task へのフォールバックはしない
    （見当違いを避けるため。曖昧なら LLM 側が話題を1つ確認する）。
    """
    task_id = rule_engine.detect_topic_task(topic or "", history=None, fallback=None)
    task = get_task(task_id) if task_id else None
    if not task:
        return {"found": False}
    prac = (task.get("practices") or [None])[0]
    video = (prac or {}).get("video") or {}
    if not prac or not video.get("url"):
        return {"found": False}
    return {
        "found": True,
        "task_label": task["label"],
        "practice_name": prac["name"],
        "steps": list(prac.get("steps", []))[:3],
        "video_title": video["title"],
        "video_url": video["url"],
    }


# Gemini function calling 宣言（生の dict。llm.py で types.FunctionDeclaration へ変換）
FIND_REFERENCE_VIDEO_DECL = {
    "name": "find_reference_video",
    "description": (
        "歌の練習トピックに対応する、実在する参考練習動画とやり方を取得する。"
        "ユーザーが動画・お手本・見本・実演・良い例を求めた時に呼ぶ。"
        "topic は日本語の自由文でよい（例: エッジボイス, ボーカルフライ, 高音, ミックスボイス, "
        "ビブラート, 声帯の閉じ, リズム, 音程, ロングトーン, 強弱, 喉の力み）。"
        "直前の会話でコーチ自身が出した話題を指して『お手本ない？』と聞かれた時は、"
        "その話題を topic に補って呼ぶこと。"
        "found=false が返ったら、実在する動画が手元に無いということなので、"
        "でっち上げず正直に伝えるか、どのテーマの動画がいいか1つ確認する。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "動画を探したい練習トピック（日本語自由文）",
            }
        },
        "required": ["topic"],
    },
}


def search_original_song(query: str) -> dict:
    """曲名（＋歌手名）から原曲候補を YouTube 検索して返す（docs/72 FR-01）。

    読み取り専用。セッション状態は変更しない（確定は FR-03 の承諾検出が行う）。
    見つからなければ {"found": False, "candidates": []} — でっち上げは返さない。
    """
    from app.audio.reference import search_youtube

    q = (query or "").strip()
    if not q:
        return {"found": False, "candidates": []}
    try:
        candidates = search_youtube(q, limit=3)
    except Exception:
        candidates = []
    return {"found": bool(candidates), "candidates": candidates}


SEARCH_ORIGINAL_SONG_DECL = {
    "name": "search_original_song",
    "description": (
        "ユーザーが原曲（お手本にしたい曲）を曲名・歌手名だけで伝えてきた時に、"
        "YouTube から原曲候補を検索する。URLが貼られた時は呼ばない（そのURLが原曲になる）。"
        "query には曲名と、分かれば歌手名を含める（例: 『ツキミソウ Novelbright』）。"
        "返ってきた candidates の先頭候補を1つだけ、タイトル・チャンネル名と実URL付きで提示し、"
        "必ず「この曲で合っていますか？」と確認して返答を終える。確認前に原曲が決まった"
        "扱いをしない・比較したと言わない。found=false なら候補をでっち上げず、"
        "YouTubeのリンクを貼ってもらうよう正直に案内する。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "検索クエリ（曲名＋分かれば歌手名）",
            }
        },
        "required": ["query"],
    },
}


def dispatch(name: str, args: Optional[dict]) -> dict:
    """ツール名と引数を受けて実行結果（JSON化可能な dict）を返す。"""
    args = args or {}
    if name == "find_reference_video":
        return find_reference_video(args.get("topic") or "")
    if name == "search_original_song":
        return search_original_song(args.get("query") or "")
    return {"error": f"unknown tool: {name}"}
