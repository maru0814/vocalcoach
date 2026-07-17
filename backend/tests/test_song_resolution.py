"""曲名からの原曲解決（docs/72）の単体テスト。

- search_youtube: yt-dlp 出力のパース（subprocess はモック。ネットワークに出ない）
- confirmed_song_url: 確認質問への肯定/否定の決定論検出（FR-03・AC-02/03/06）
- handle_text: 承諾で song_ref_url が確定し、決定論メッセージが返る（AC-02/05）
- _scrub_foreign_urls: ツールが返した候補URLは許可、それ以外の捏造URLは除去
- session_opener_context: 同日宿題は homework_recent（「おうちでやってみて」と聞かない）
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
    state = {"phase": rule_engine.LESSON, "song_ref_url": None}
    msgs, updates = rule_engine.handle_text(state, "はい", history=_hist(CONFIRM_MSG))
    assert updates.get("song_ref_url") == CAND_URL
    assert any("原曲を受け取りました" in (m.get("text") or "") for m in msgs)


def test_handle_text_confirmation_phase_a():
    state = {"phase": rule_engine.PHASE_A, "song_ref_url": None}
    msgs, updates = rule_engine.handle_text(state, "はい", history=_hist(CONFIRM_MSG))
    assert updates.get("song_ref_url") == CAND_URL
    assert any("原曲" in (m.get("text") or "") for m in msgs)


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


# ---------- 同日宿題の挨拶（homework_recent） ----------

def _karte(hours_ago: float, practice: str = "リップロール"):
    return SimpleNamespace(
        last_session_at=datetime.utcnow() - timedelta(hours=hours_ago),
        homework={"practice_name": practice, "task_id": "t", "assigned_at": ""},
        last_summary="『TSUNAMI』を練習",
    )


def test_opener_same_day_homework_is_recent():
    op = karte_service.session_opener_context(_karte(hours_ago=0.1))
    assert op["mode"] == "homework_recent"


def test_opener_next_day_homework_unchanged():
    op = karte_service.session_opener_context(_karte(hours_ago=30))
    assert op["mode"] == "homework"


def test_initial_messages_homework_recent_wording():
    msgs = rule_engine.initial_messages({"mode": "homework_recent", "practice_name": "リップロール"})
    first = msgs[0]["text"]
    assert "リップロール" in first
    assert "おうちでやってみて" not in first  # 数分前の提案を宿題扱いしない
    # 従来モードは従来文言のまま
    hw = rule_engine.initial_messages({"mode": "homework", "practice_name": "リップロール"})
    assert "おうちでやってみて" in hw[0]["text"]
