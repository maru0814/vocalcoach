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


def _practice_payload(task: dict, prac: dict) -> dict:
    video = prac.get("video") or {}
    return {
        "task_label": task["label"],
        "practice_name": prac["name"],
        "steps": list(prac.get("steps", []))[:3],
        "video_title": video.get("title"),
        "video_url": video.get("url"),
    }


def find_reference_video(topic: str) -> dict:
    """練習トピックに対応する実在動画を、練習単位で正直にマッチして返す（docs/93 §4.4）。

    ① 練習そのものの一致（practice の name / aliases が topic に含まれる）→ found=true。
       返る動画はその練習自体の実演であることが保証される。
    ② 課題レベルの一致のみ（例: topic「エッジボイス」→ 課題「声帯の閉じ」）→ found=false ＋
       alternative（同課題の★練習と実在動画）。topic そのものの実演は無い、という事実を保つ。
       旧実装はここを found=true で返し、エッジボイスの実演としてリップロール動画が
       提示される事故を起こした（2026-08-07 スクショ・docs/93 §0）。
    ③ どちらも無し → found=false・alternative 無し。current_task へのフォールバックはしない。
    """
    topic_s = (topic or "").strip()
    if not topic_s:
        return {"found": False, "alternative": None}
    # ① 練習単位の一致（TASKS の定義順。同名練習は先勝ち）
    for task in TASKS:
        for prac in task.get("practices") or []:
            if not (prac.get("video") or {}).get("url"):
                continue
            names = [prac.get("name") or ""] + list(prac.get("aliases") or [])
            if any(n and n in topic_s for n in names):
                return {"found": True, "match": "practice", **_practice_payload(task, prac)}
    # ② 課題単位の一致 → 代替（別練習と明示して提案する材料）
    task_id = rule_engine.detect_topic_task(topic_s, history=None, fallback=None)
    task = get_task(task_id) if task_id else None
    prac = (task.get("practices") or [None])[0] if task else None
    if prac and (prac.get("video") or {}).get("url"):
        return {
            "found": False,
            "note": f"「{topic_s}」そのものを名指しした実演動画はカタログに無い",
            "alternative": _practice_payload(task, prac),
        }
    return {"found": False, "alternative": None}


# Gemini function calling 宣言（生の dict。llm.py で types.FunctionDeclaration へ変換）
FIND_REFERENCE_VIDEO_DECL = {
    "name": "find_reference_video",
    "description": (
        "歌の練習トピックに対応する、実在する参考練習動画とやり方を取得する。"
        "ユーザーが動画・お手本・見本・実演・良い例を求めた時、または動画を出すと約束した時に呼ぶ。"
        "topic は日本語の自由文でよい（例: リップロール, ストロー発声, エッジボイス, 高音, "
        "ミックスボイス, ビブラート, 声帯の閉じ, リズム, ロングトーン, 強弱, 喉の力み）。"
        "直前の会話でコーチ自身が出した話題・練習名を指して『お手本ない？』『よろ』等と"
        "応じられた時は、その練習名を topic に補って呼ぶこと。"
        "found=true のとき、動画はその練習そのものの実演である。"
        "found=false で alternative がある時は、topic そのものの動画は手元に無い。"
        "その場合は『topicそのものの実演動画は無い』と正直に伝えた上で、alternative を"
        "別の練習だと明示して提案してよい（alternative を topic の実演だと偽るのは禁止）。"
        "topic そのものの動画が欲しいのに found=false だった時は、search_practice_video で"
        "YouTube から実在の動画をその場で検索して提案できる（そこで会話を止めない）。"
        "動画について語ってよいのはタイトルと練習名だけ。動画の中身の構成"
        "（「後半で〜を実演」「何分あたりで〜」等）はデータに無いので断定しない。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "動画を探したい練習トピック・練習名（日本語自由文）",
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
        "呼ぶのは『実在する曲の名前を伝えられた』と確信できる時だけ。相槌（『やったー』"
        "『もっかいやってみる』）・練習の報告・質問・雑談を query に入れて検索しない。"
        "曲名かどうか確信が持てなければ、検索せずに曲名を教えてほしいと聞き返す。"
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


def search_practice_video(query: str) -> dict:
    """練習・ボイトレ動画を YouTube から実検索して返す（docs/93 §4.6）。

    カタログ（taxonomy）に該当練習の動画が無い時、「無い」で会話を止めずに
    その場で探すためのツール。search_original_song と同じ yt-dlp 検索を使うので
    返る URL は実在保証つき（捏造防止の不変条件はカタログ方式と同じ）。
    返却キーは "videos"（"candidates" は原曲確認アンカーの決定論が拾うため使わない）。
    """
    from app.audio.reference import search_youtube

    q = (query or "").strip()
    if not q:
        return {"found": False, "videos": []}
    try:
        videos = search_youtube(q, limit=3)
    except Exception:
        videos = []
    return {"found": bool(videos), "videos": videos}


SEARCH_PRACTICE_VIDEO_DECL = {
    "name": "search_practice_video",
    "description": (
        "ボイトレの練習・実演動画を YouTube から検索する。find_reference_video が"
        "found=false（カタログに無い）だった時や、カタログの動画をユーザーが不満とした時に呼ぶ。"
        "query は「練習名・話題＋ボイトレ/やり方」など日本語でよい（例: 『エッジボイス やり方』）。"
        "返ってきた videos から1件を選び、タイトル・チャンネル名と実URLを添えて提案する。"
        "カタログ外の動画なので内容の質は保証できない。タイトルとチャンネル名だけを根拠に語り、"
        "動画の中身は断定しない。found=false なら検索でも見つからなかったということなので、"
        "でっち上げず正直に伝えて文章でやり方を説明する。"
        "提示済みの動画に『違う』『これじゃない』と不満を伝えられた時は、同じURLを"
        "再提示しない。前回と別の検索語で探し直すか、無ければ正直に伝える。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "検索クエリ（練習名・話題＋『やり方』『ボイトレ』等）",
            }
        },
        "required": ["query"],
    },
}


# --- セッション文脈ツール（docs/94 会話憲法）---
# 実体は endpoint 側がクロージャ（tool_ctx）として提供する。ここは宣言だけを持つ。
# 「録音を聴く」「測り直す」「主訴を覚える」もモデルの文脈判断で呼ぶ＝正規表現ルーティングの置換。

LISTEN_REGISTER_DECL = {
    "name": "listen_register",
    "description": (
        "ユーザーの最新の録音を実際に聴いて、声区（地声/ミックス/裏声）や換声点のつながりを"
        "音色から判定した専門所見を得る。ユーザーが自分の録音の声の種類を尋ねた時"
        "（「ここ地声？裏声？」「ミックスになってた？」）や、判定への異議があった時に呼ぶ。"
        "一般的な定義・やり方の質問（「ミックスボイスとは？」）では呼ばない（普通に答える）。"
        "返ってきた所見(verdict)を根拠に、ユーザーの質問(question)に噛み合う形で答える。"
        "所見に無い箇所・秒数を作らない。処理に10秒前後かかるので、迷ったら呼ばずに聞き返す。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "ユーザーが知りたいこと（例: 『2番のサビは裏声になっていないか』）",
            }
        },
        "required": ["question"],
    },
}

LISTEN_PRONUNCIATION_DECL = {
    "name": "listen_pronunciation",
    "description": (
        "ユーザーの最新の録音を実際に聴いて、発音（母音の口の開き・子音・滑舌）の専門所見を得る。"
        "ユーザーが自分の録音の発音・滑舌の講評を求めた時に呼ぶ。"
        "用語の意味の質問（「母音って何？」）や雑談（「滑舌悪いんだよね〜」の自己開示）では"
        "呼ばず、普通に会話する（講評が欲しそうなら一言確認してから）。"
        "返ってきた所見(verdict)を根拠に、質問(question)に噛み合う形で答える。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "ユーザーが知りたいこと（例: 『言葉がはっきり聞こえるか』）",
            }
        },
        "required": ["question"],
    },
}

REDIAGNOSE_DECL = {
    "name": "rediagnose_with_reference",
    "description": (
        "直前の録音を、原曲（お手本）の指定区間と重ね直して再解析し、新しい診断結果を得る。"
        "ユーザーが「原曲の◯秒から重ねてもう一度診断/採点して」のように、"
        "比較のやり直しを明確に求めた時だけ呼ぶ。雑談での「また比べたい」（未来の意思）では呼ばない。"
        "ref_start_sec は原曲側の開始秒（『45秒あたりから』→45）。"
        "返ってきた診断結果(report)だけを根拠に話す。無い数値・秒数を作らない。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ref_start_sec": {"type": "number", "description": "原曲側の開始秒（不明なら省略）"},
            "ref_end_sec": {"type": "number", "description": "原曲側の終了秒（不明なら省略）"},
        },
    },
}

SET_LESSON_FOCUS_DECL = {
    "name": "set_lesson_focus",
    "description": (
        "ユーザーが『ここを直したい』という主訴（例: 高音が出ない、音程が不安、喉が疲れる）を"
        "明確に表明した時に、その主訴をレッスンの最優先課題として記録する。"
        "次の録音診断で解析結果よりも主訴が優先される。"
        "呼ぶのは本人の明確な意思表示がある時だけ。雑談での話題の言及（「リズムは得意」"
        "「友達が高音出なくて」）や質問（「息継ぎのコツは？」）では呼ばない。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "主訴の内容（日本語自由文。例: 高音がひっくり返る）",
            }
        },
        "required": ["topic"],
    },
}

# tool_ctx（endpoint 提供のクロージャ）で実装される宣言の一覧
CONTEXT_TOOL_DECLS = {
    "listen_register": LISTEN_REGISTER_DECL,
    "listen_pronunciation": LISTEN_PRONUNCIATION_DECL,
    "rediagnose_with_reference": REDIAGNOSE_DECL,
    "set_lesson_focus": SET_LESSON_FOCUS_DECL,
}


def to_openai_tool(decl: dict) -> dict:
    """Gemini の FunctionDeclaration 形式を OpenAI の tools 形式へ変換する（docs/103）。

    両社とも中身は同じ JSON Schema で、包み方だけが違う:
      Gemini: {name, description, parameters}
      OpenAI: {"type": "function", "function": {name, description, parameters}}
    宣言そのもの（＝ツールをいつ呼ぶかの判断基準）は1か所で管理し、
    プロバイダごとに文言が分岐しないようにする。
    """
    return {"type": "function", "function": dict(decl)}


def dispatch(name: str, args: Optional[dict]) -> dict:
    """ツール名と引数を受けて実行結果（JSON化可能な dict）を返す。"""
    args = args or {}
    if name == "find_reference_video":
        return find_reference_video(args.get("topic") or "")
    if name == "search_original_song":
        return search_original_song(args.get("query") or "")
    if name == "search_practice_video":
        return search_practice_video(args.get("query") or "")
    return {"error": f"unknown tool: {name}"}
