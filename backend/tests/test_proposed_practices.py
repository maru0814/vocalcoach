"""提案済み練習の文脈注入（docs/65）の単体テスト。"""
from app.coaching import llm
from app.coaching.taxonomy import TASKS


def test_extract_practices_order_and_dedup():
    text = "まずネイネイ、それからリップロール。仕上げにまたネイネイをやりましょう"
    assert llm.extract_practices(text) == ["ネイネイ", "リップロール"]


def test_extract_practices_none_and_empty():
    assert llm.extract_practices(None) == []
    assert llm.extract_practices("") == []
    assert llm.extract_practices("今日はいい天気ですね") == []


def test_extract_practices_substring_subsumption():
    # 「スーッ呼吸」を含む文で、部分文字列の「スー呼吸」に二重ヒットしない
    assert llm.extract_practices("スーッ呼吸をやりましょう") == ["スーッ呼吸"]


def test_vocabulary_covers_taxonomy_practices():
    """taxonomy の全練習名が語彙のどれかで検出できる（新練習追加時の乖離検知）。"""
    missed = []
    for task in TASKS:
        for prac in task.get("practices") or []:
            name = prac.get("name") or ""
            if not llm.extract_practices(name):
                missed.append(name)
    assert not missed, f"語彙で検出できない練習名: {missed}（PRACTICE_KEYWORDS に追加する）"


def test_proposed_practices_from_history_assistant_only():
    history = [
        {"role": "user", "content": "リップロールって何ですか？"},  # ユーザー発言は数えない
        {"role": "assistant", "content": "まずはストロー発声から始めましょう"},
        {"role": "user", "content": "わかりました"},
        {"role": "assistant", "content": "ストロー発声に慣れたらネイネイもいいですよ"},
    ]
    assert llm.proposed_practices_from_history(history) == ["ストロー発声", "ネイネイ"]


def test_injection_line_present_in_system_text():
    """提案済み練習の事実行は system 側テキストに入り、ユーザー発言は素のまま渡る（docs/93）。"""
    state = {"phase": "practice", "last_analysis": {}}
    history = [{"role": "assistant", "content": "ストロー発声をやってみましょう"}]
    contents, system_text = llm._build_contents(state, "さっき別の練習勧めましたよね？", history)
    # docs/94: 「言及」と「提案」を決定論で区別できないため「名前を出した練習」として注入
    assert "名前を出した練習" in system_text and "ストロー発声" in system_text
    assert "これ以外の練習を「以前すすめた」ことにしない" in system_text
    # ユーザー発言は指示書で包まない（会話の連続性をモデルに渡す）
    assert contents[-1].parts[0].text == "さっき別の練習勧めましたよね？"


def test_injection_line_when_no_practice_proposed():
    state = {"phase": "practice", "last_analysis": {}}
    _, system_text = llm._build_contents(state, "さっきの練習なんでしたっけ？", [])
    assert "まだ練習の名前を出していない" in system_text


def test_video_offer_regex_detection_is_removed():
    """オファー済みの正規表現検出（旧docs/65）は docs/94 で撤去済み（復活防止ガード）。

    モデルの言い回しが自由になった今、定型文マッチは言い換えですり抜ける
    （「お手本の動画もあるので、見たかったら言ってくださいね」を検出できない実証あり）。
    繰り返し抑制は会話履歴＋SYSTEM_PROMPT の作法に任せる。
    """
    for name in ("_already_offered_video", "_video_offer_line", "_VIDEO_OFFER_RE"):
        assert not hasattr(llm, name), f"{name} は docs/94 で撤去済み。復活させない"


# === 会話レイヤー刷新（docs/93）: 意図理解はモデルへ・状況は system 側へ ===

def test_conversation_mode_gates_are_removed():
    """正規表現の会話モードゲート（旧docs/66）が撤去されている（docs/93 §2）。

    「12文字未満は相槌」等の決定論が「よろ」「リップロールやん」を雑談と誤断定し、
    会話が噛み合わなくなった（2026-08-07 スクショ）。復活させないための回帰ガード。
    """
    for name in ("_detect_conversation_mode", "_conversation_mode_line",
                 "_AIZUCHI", "_EMOTION_RE", "_EXPLICIT_REQUEST_RE",
                 "_VIDEO_ACCEPT_RE", "_VIDEO_DECLINE_RE", "_accepts_video_offer"):
        assert not hasattr(llm, name), f"{name} は docs/93 で撤去済み。復活させない"


def test_user_text_is_not_wrapped():
    """ユーザー発言は指示書ラッパーで包まず素のまま渡す（docs/93 §4.1）。"""
    state = {"phase": "feedback", "last_analysis": {"duration_sec": 25.0}}
    for text in ["うん", "よろ", "リップロールやん", "改善点を秒数つきで教えて"]:
        contents, system_text = llm._build_contents(state, text, [])
        assert contents[-1].parts[0].text == text
        assert "# ユーザーの発言" not in system_text


def test_system_text_contains_persona_and_context():
    """system 側に人格（SYSTEM_PROMPT）とレッスン状況（事実）が両方入る。"""
    state = {"phase": "feedback", "last_analysis": {"duration_sec": 25.0}}
    _, system_text = llm._build_contents(state, "高い声出したい", [])
    assert "ソラ先生" in system_text
    assert "# 現在のレッスン状況" in system_text
    assert "録音なしのテキスト会話" in system_text


def test_chat_model_is_pinned_upgrade():
    from app.core.config import settings
    # docs/93: 会話は gemini-3.5-flash（バージョン固定・エイリアス禁止）。
    assert settings.llm_chat_model == "gemini-3.5-flash"
    assert "latest" not in settings.llm_chat_model


def test_complete_accepts_model_and_system_params():
    import inspect
    for fn in (llm._complete, llm._complete_with_tools):
        params = inspect.signature(fn).parameters
        assert "model" in params
        assert "system_text" in params


def test_video_delivery_retry_detection():
    """「お出しします」と約束したのにURLが無い返答だけがリトライ対象（docs/93 §4.3）。"""
    promise_no_url = "いいですよ！リップロールの動画をお出ししますね。"
    assert llm._needs_video_delivery_retry(promise_no_url, set())
    # URLが本文にあれば不要
    with_url = "こちらが動画です → https://www.youtube.com/watch?v=TakKKIdIGgQ"
    assert not llm._needs_video_delivery_retry(with_url, set())
    # ツールが実URLを返していれば不要（本文には決定論で付与される）
    assert not llm._needs_video_delivery_retry(
        promise_no_url, {"https://www.youtube.com/watch?v=TakKKIdIGgQ"})
    # 約束していない普通の返答は対象外
    assert not llm._needs_video_delivery_retry("いいね、その調子！", set())
    assert not llm._needs_video_delivery_retry("", set())

