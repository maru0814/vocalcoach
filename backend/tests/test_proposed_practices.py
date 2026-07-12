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
