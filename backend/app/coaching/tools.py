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


def dispatch(name: str, args: Optional[dict]) -> dict:
    """ツール名と引数を受けて実行結果（JSON化可能な dict）を返す。"""
    args = args or {}
    if name == "find_reference_video":
        return find_reference_video(args.get("topic") or "")
    return {"error": f"unknown tool: {name}"}
