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


def test_injection_line_present_in_contents():
    """_build_contents の最終ユーザーメッセージに、提案済み練習の事実行が入る。"""
    state = {"phase": "practice", "last_analysis": {}}
    history = [{"role": "assistant", "content": "ストロー発声をやってみましょう"}]
    contents = llm._build_contents(state, "さっき別の練習勧めましたよね？", history)
    final = contents[-1].parts[0].text
    assert "提案した練習: ストロー発声" in final
    assert "これ以外の練習を「以前すすめた」ことにしない" in final


def test_injection_line_when_no_practice_proposed():
    state = {"phase": "practice", "last_analysis": {}}
    contents = llm._build_contents(state, "さっきの練習なんでしたっけ？", [])
    final = contents[-1].parts[0].text
    assert "まだ練習を提案していない" in final


def test_already_offered_video_detection():
    assert llm._already_offered_video(
        [{"role": "assistant", "content": "やってみて。参考になる実演動画を出しましょうか？"}]
    )
    # ユーザー発言は数えない
    assert not llm._already_offered_video(
        [{"role": "user", "content": "動画出してよ"}]
    )
    assert not llm._already_offered_video(
        [{"role": "assistant", "content": "リップロールをやってみましょう"}]
    )
    assert not llm._already_offered_video(None)


def test_video_offer_line_injected_after_prior_offer():
    state = {"phase": "practice", "last_analysis": {}}
    history = [
        {"role": "assistant", "content": "ストロー発声をやってみましょう。参考になる実演動画を出しましょうか？"},
        {"role": "user", "content": "うーん、で、どれくらいで上達する？"},
    ]
    final = llm._build_contents(state, "結局何すればいい？", history)[-1].parts[0].text
    assert "動画オファーを繰り返さない" in final


def test_no_video_offer_line_when_not_offered():
    state = {"phase": "practice", "last_analysis": {}}
    final = llm._build_contents(state, "高い声出したい", [])[-1].parts[0].text
    assert "動画オファーを繰り返さない" not in final


# === 会話モード検出＋対話モデル格上げ（docs/66） ===

def test_conversation_mode_aizuchi():
    for w in ["うん", "へー", "なるほどね", "そうなんだ", "やった", "ふーん"]:
        assert llm._detect_conversation_mode(w) == "casual", w


def test_conversation_mode_emotion():
    for w in ["全然上達しなくて落ち込む…もうやめようかな", "本番で緊張して最悪だった", "才能ないですよね"]:
        assert llm._detect_conversation_mode(w) == "emotion", w


def test_conversation_mode_short_smalltalk():
    assert llm._detect_conversation_mode("こんにちは！") == "casual"
    assert llm._detect_conversation_mode("いい天気ですね") == "casual"


def test_conversation_mode_excludes_explicit_requests():
    # 短くても明示的なコーチング依頼は会話モードにしない（ちゃんと答える）
    for w in ["練習教えて", "どうすれば直る？", "高い声出したい", "今の見て"]:
        assert llm._detect_conversation_mode(w) is None, w


def test_conversation_mode_none_for_long_question():
    assert llm._detect_conversation_mode("改善点を秒数つきで具体的に教えてください") is None


def test_conversation_mode_line_injected():
    state = {"phase": "feedback", "last_analysis": {"duration_sec": 25.0}}
    final = llm._build_contents(state, "うん", [])[-1].parts[0].text
    assert "会話モード" in final and "1〜2文で自然に短く" in final
    # 感情はさらに共感の指示
    final_e = llm._build_contents(state, "もうやめようかな…落ち込む", [])[-1].parts[0].text
    assert "まず気持ちに共感" in final_e


def test_conversation_mode_line_absent_for_request():
    state = {"phase": "feedback", "last_analysis": {"duration_sec": 25.0}}
    final = llm._build_contents(state, "改善点を秒数つきで教えて", [])[-1].parts[0].text
    assert "会話モード" not in final


def test_chat_model_configurable():
    from app.core.config import settings
    # 対話モデルは設定として存在し env で差し替え可能（既定は flash-lite。2.5-flash 格上げは
    # 多ターン悪化＋コスト増のため既定では採らない・docs/66）。
    assert settings.llm_chat_model


def test_complete_accepts_model_param():
    import inspect
    assert "model" in inspect.signature(llm._complete).parameters
    assert "model" in inspect.signature(llm._complete_with_tools).parameters


def test_conversation_mode_excludes_feedback_questions():
    # 「今の歌どうでしたか」等の評価質問は会話モードにせず、ちゃんとFBする
    for w in ["今の歌、どうでしたか？", "今の、良かった？", "どこが良かった？", "何点だった？"]:
        assert llm._detect_conversation_mode(w) is None, w
