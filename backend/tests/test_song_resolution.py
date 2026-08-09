"""曲名からの原曲解決（docs/72）の単体テスト。

- search_youtube: yt-dlp 出力のパース（subprocess はモック。ネットワークに出ない）
- confirmed_song_url: 確認質問への肯定/否定の決定論検出（FR-03・AC-02/03/06）
- handle_text: 承諾で song_ref_url が確定し、決定論メッセージが返る（AC-02/05）
- _scrub_foreign_urls: ツールが返した候補URLは許可、それ以外の捏造URLは除去
- session_opener_context: 開始挨拶は宿題に言及しない（同日は短い出迎えのみ・docs/53 FR-06改定）
"""
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from app.audio import reference
from app.coaching import llm, rule_engine, tools
from app.services import karte_service

CAND_URL = "https://www.youtube.com/watch?v=abc123DEF45"
CONFIRM_MSG = (
    "原曲は『ツキミソウ』（Novelbright）でしょうか？"
    f"この曲で合っていますか？ → {CAND_URL}"
)


def _proc(stdout: str, returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr="", returncode=returncode)


# ---------- search_youtube（FR-01） ----------

def test_search_youtube_parses_flat_json_lines():
    lines = "\n".join([
        json.dumps({"id": "abc123DEF45", "title": "ツキミソウ", "channel": "Novelbright", "duration": 261}),
        "not-json",  # 混入行は無視
        json.dumps({"id": "xyz", "title": "ツキミソウ (cover)", "uploader": "someone"}),
        json.dumps({"title": "idなし→無視"}),
    ])
    with patch.object(reference.subprocess, "run", return_value=_proc(lines)):
        out = reference.search_youtube("ツキミソウ", limit=3)
    assert out[0] == {
        "title": "ツキミソウ",
        "url": "https://www.youtube.com/watch?v=abc123DEF45",
        "channel": "Novelbright",
        "duration_sec": 261,
    }
    assert len(out) == 2  # id無しは落ちる
    assert out[1]["channel"] == "someone"  # channel 無ければ uploader
    assert out[1]["duration_sec"] is None


def test_search_youtube_failure_and_empty_are_safe():
    with patch.object(reference.subprocess, "run", side_effect=OSError("boom")):
        assert reference.search_youtube("x") == []
    assert reference.search_youtube("") == []  # 空クエリはコマンドすら打たない
    with patch.object(reference.subprocess, "run", return_value=_proc("", returncode=1)):
        assert reference.search_youtube("x") == []


def test_search_original_song_tool_wraps_candidates():
    with patch.object(reference, "search_youtube", return_value=[{"title": "t", "url": CAND_URL, "channel": "", "duration_sec": None}]):
        res = tools.dispatch("search_original_song", {"query": "ツキミソウ"})
    assert res["found"] is True and res["candidates"][0]["url"] == CAND_URL
    assert tools.search_original_song("") == {"found": False, "candidates": []}


# ---------- confirmed_song_url（FR-03） ----------

def _hist(last_coach: str):
    return [
        {"role": "user", "content": "原曲 ツキミソウ"},
        {"role": "assistant", "content": last_coach},
    ]


def test_confirmed_song_url_accepts_short_yes():
    for yes in ("はい", "うん", "合ってる", "それです", "はい、お願いします！"):
        assert rule_engine.confirmed_song_url(yes, _hist(CONFIRM_MSG)) == CAND_URL


def test_confirmed_song_url_rejects_decline_and_offtopic():
    assert rule_engine.confirmed_song_url("違う", _hist(CONFIRM_MSG)) is None
    assert rule_engine.confirmed_song_url("いや、別の曲", _hist(CONFIRM_MSG)) is None
    # 長文は肯定語を含んでも発火しない（「はい」を含む雑談の誤爆防止）
    assert rule_engine.confirmed_song_url(
        "はいというかその曲も好きなんですけど今日は別の相談があって", _hist(CONFIRM_MSG)
    ) is None


def test_confirmed_song_url_requires_anchor_and_single_url():
    # アンカー無し（AC-06: ただの雑談への「はい」で発火しない）
    assert rule_engine.confirmed_song_url("はい", _hist("いい調子ですね！")) is None
    # URL 2件は誤発火防止で無効
    two = CONFIRM_MSG + " 他の候補: https://www.youtube.com/watch?v=other000000"
    assert rule_engine.confirmed_song_url("はい", _hist(two)) is None
    # ユーザー自身が URL を貼ったターンは対象外（そのURLが原曲指定として優先）
    assert rule_engine.confirmed_song_url(f"はい {CAND_URL}", _hist(CONFIRM_MSG)) is None
    # 履歴なし
    assert rule_engine.confirmed_song_url("はい", None) is None


def test_handle_text_confirmation_sets_song_ref_url():
    # docs/94: 確定（state更新）は決定論のまま。返答は定型でなくLLM生成
    # （hermetic環境ではLLM不可→正直フォールバック文になる。定型「原曲を受け取りました」には戻さない）。
    state = {"phase": rule_engine.LESSON, "song_ref_url": None}
    msgs, updates = rule_engine.handle_text(state, "はい", history=_hist(CONFIRM_MSG))
    assert updates.get("song_ref_url") == CAND_URL
    assert len(msgs) == 1 and msgs[0]["type"] == "text"


def test_handle_text_confirmation_phase_a():
    state = {"phase": rule_engine.PHASE_A, "song_ref_url": None}
    msgs, updates = rule_engine.handle_text(state, "はい", history=_hist(CONFIRM_MSG))
    assert updates.get("song_ref_url") == CAND_URL
    assert len(msgs) == 1 and msgs[0]["type"] == "text"


def test_url_received_fact_injected_not_canned():
    """原曲URLターンは定型即リターンでなく、事実注入つきでLLM会話に流れる（docs/94）。"""
    state = {"phase": rule_engine.PHASE_A, "song_ref_url": None}
    merged = {**state, "song_ref_url": CAND_URL, "_song_ref_just_received": True}
    _, system_text = llm._build_contents(merged, f"{CAND_URL} この曲のサビが苦しくて", [])
    assert "原曲（お手本）のURLを受け取り" in system_text
    assert "質問・相談が添えられていれば" in system_text


# ---------- URLスクラブの許可リスト（FR-02の候補URLを消さない） ----------

def test_scrub_keeps_tool_urls_and_drops_foreign():
    text = f"候補です {CAND_URL} 偽物 https://www.youtube.com/watch?v=fakefakefake"
    out = llm._scrub_foreign_urls(text, extra_allowed={CAND_URL})
    assert CAND_URL in out
    assert "fakefakefake" not in out


def test_song_confirm_anchor_constant():
    # rule_engine の決定論検出と llm の確定付与が同じアンカーを共有していること
    assert llm.SONG_CONFIRM_ANCHOR == "この曲で合っていますか"
    assert llm.SONG_CONFIRM_ANCHOR in CONFIRM_MSG


# ---------- 開始挨拶は宿題に言及しない（docs/53 FR-06 改定 2026-08-06） ----------

def _karte(hours_ago: float, practice: str = "リップロール"):
    return SimpleNamespace(
        last_session_at=datetime.utcnow() - timedelta(hours=hours_ago),
        homework={"practice_name": practice, "task_id": "t", "assigned_at": ""},
        last_summary="『TSUNAMI』を練習",
    )


def test_opener_same_day_is_short_welcome():
    op = karte_service.session_opener_context(_karte(hours_ago=0.1))
    assert op["mode"] == "continue_recent"
    first = rule_engine.initial_messages(op)[0]["text"]
    assert "リップロール" not in first  # 宿題を蒸し返さない
    assert "さっき" not in first        # 実在しない会話の記憶主張をしない
    assert "前回" not in first          # 同日は要約も読み上げない


def test_opener_next_day_falls_to_continue():
    op = karte_service.session_opener_context(_karte(hours_ago=30))
    assert op["mode"] == "continue"
    first = rule_engine.initial_messages(op)[0]["text"]
    assert "リップロール" not in first  # 宿題があっても挨拶では言及しない
    assert "TSUNAMI" in first           # 前回サマリには軽く触れる


# ---------- 曲名提示の決定論検出（_names_song_title・FR-01の後押し） ----------

def _ask_hist():
    return [
        {"role": "user", "content": "録音送りました"},
        {"role": "assistant", "content": "素敵な歌声ですね！もしよろしければ、原曲を教えていただけますか？"},
    ]


def test_names_song_title_prefix_forms():
    # 「原曲 ◯◯」形式は文脈不要で検索クエリになる
    assert llm._names_song_title("原曲　ツキミソウ", None) == "ツキミソウ"
    assert llm._names_song_title("原曲はTSUNAMI", None) == "TSUNAMI"
    assert llm._names_song_title("曲名 ツキミソウ Novelbright", None) == "ツキミソウ Novelbright"


def test_names_song_title_bare_reply_after_ask_removed():
    # 撤去ガード（docs/96 §4.1・docs/94 憲法 1.2）: 「尋ねた直後の短い返答＝曲名」の
    # 形状ベース推定はベースライン測定で相槌・練習報告を曲名検索する誤爆を多発させたため撤去。
    # 裸の曲名の理解は LLM の文脈判断（ツール宣言）に任せる。
    assert llm._names_song_title("ツキミソウ", _ask_hist()) is None
    assert llm._names_song_title("もっかいやってみる", _ask_hist()) is None
    assert llm._names_song_title("ひとつずつ確認してるところ", _ask_hist()) is None
    assert llm._names_song_title("やったー", _ask_hist()) is None
    # 尋ねられていない文脈の裸の曲名も従来どおり強制しない
    assert llm._names_song_title("ツキミソウ", None) is None
    # 明示形式は文脈の有無に関わらず生きている
    assert llm._names_song_title("原曲 ツキミソウ", _ask_hist()) == "ツキミソウ"


def test_names_song_title_guards():
    # 定型返事・質問文・否定文・URL言及は曲名扱いしない
    assert llm._names_song_title("はい", _ask_hist()) is None
    assert llm._names_song_title("わからない", _ask_hist()) is None
    assert llm._names_song_title("原曲がないと比較できないの？", None) is None
    assert llm._names_song_title("原曲がないんだよね", None) is None
    assert llm._names_song_title("原曲のURLってどこで見つけるの", None) is None
    # 「原曲の◯秒から…」は再診断の依頼であって曲名提示ではない（docs/94 スモークで誤爆実測）
    assert llm._names_song_title("原曲の45秒あたりから重ねてもう一度診断して", None) is None
    assert llm._names_song_title(f"原曲 {CAND_URL}", None) is None  # URLは既存経路が拾う
    # 長文はただの会話
    assert llm._names_song_title(
        "ツキミソウという曲なんですけど昔からずっと好きでカラオケでも毎回歌っていて", _ask_hist()
    ) is None
