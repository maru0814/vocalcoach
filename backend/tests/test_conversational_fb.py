"""会話型FBの契約テスト（docs/36-38, docs/39）。

DB・ネットワーク不要。LLM(_complete)を無効化し、ルールベースの確定的な
フォールバック文だけで「会話チャット契約」を検証する（hermetic）。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_conversational_fb -v
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coaching import llm, rule_engine  # noqa: E402

# 点数(NN/100, NN点) と ◎○△× が出力に現れたら NG。
BAD_SCORE = re.compile(r"\d+\s*/\s*100|\d+\s*点|[◎○△×]")
CARD_TYPES = {"feedback", "practice", "judge", "progress", "diagnosis"}


_ORIG_COMPLETE = None
_ORIG_COMPLETE_TOOLS = None


def setUpModule():
    # LLMを無効化 → _llm_or / generate_reply は確定的なテンプレ文へフォールバック。
    # _complete だけでなく tools 経路（_complete_with_tools）も遮断すること。
    # 実キー（GEMINI_API_KEY）がある環境では generate_reply が tools 経路を通り、
    # スタブを素通りして本物の API を叩いてしまう（課金・不安定・偽の失敗の原因）。
    global _ORIG_COMPLETE, _ORIG_COMPLETE_TOOLS
    _ORIG_COMPLETE = llm._complete
    _ORIG_COMPLETE_TOOLS = llm._complete_with_tools
    llm._complete = lambda *a, **k: None  # type: ignore
    # _complete_with_tools は (テキスト, ツールURL集合) のタプル契約（docs/72）
    llm._complete_with_tools = lambda *a, **k: (None, set())  # type: ignore


def tearDownModule():
    # 差し替えたスタブを元に戻す（他テストへリークさせない。pytest でのテスト間汚染防止）。
    if _ORIG_COMPLETE is not None:
        llm._complete = _ORIG_COMPLETE  # type: ignore
    if _ORIG_COMPLETE_TOOLS is not None:
        llm._complete_with_tools = _ORIG_COMPLETE_TOOLS  # type: ignore


def _state(**over):
    s = {
        "phase": "A", "song_ref_url": None, "song_ref_path": None,
        "user_range": None, "ref_range": None, "current_task": None,
        "focus_task": None, "avoid_task": None,
        "baseline_analysis": None, "last_analysis": None, "d_retry_count": 0,
    }
    s.update(over)
    return s


# 明確な課題あり（伸ばしが大きく揺れる＋音程ジッター大＋息漏れ）
ANALYSIS_ISSUE = {
    "duration_sec": 20.0, "rms_mean": 0.03, "voiced_ratio": 0.9,
    "f0_median_hz": 220.0, "f0_jitter_cents": 40.0, "long_tone_stability": 90.0,
    "rms_db_range": 6.0, "h1h2_db": 9.0, "cpp_db": 5.0, "hnr_db": 10.0,
    "harmonic_ratio": 0.4, "singers_formant_ratio": 0.001,
    "vibrato_rate_hz": None, "vibrato_depth_cents": None,
    "timeline": {"sustained_segments": [
        {"start_sec": 10.0, "end_sec": 14.0, "duration_sec": 4.0, "mean_f0_hz": 330.0,
         "register": "chest", "register_confidence": "high", "spectral_centroid_hz": 2900.0},
    ], "per_window": [{"f0_mean_hz": 220.0}, {"f0_mean_hz": 330.0}]},
}

# 大きな課題なし（安定・効率的・良い響き）
ANALYSIS_GOOD = {
    "duration_sec": 20.0, "rms_mean": 0.03, "voiced_ratio": 0.95,
    "f0_median_hz": 220.0, "f0_jitter_cents": 5.0, "long_tone_stability": 15.0,
    "rms_db_range": 16.0, "h1h2_db": 4.0, "cpp_db": 12.0, "hnr_db": 18.0,
    "harmonic_ratio": 0.6, "singers_formant_ratio": 0.009,
    "vibrato_rate_hz": 5.5, "vibrato_depth_cents": 50.0,
    "timeline": {"sustained_segments": [
        {"start_sec": 10.0, "end_sec": 14.0, "duration_sec": 4.0, "mean_f0_hz": 300.0,
         "register": "mix", "register_confidence": "high", "spectral_centroid_hz": 2400.0},
    ], "per_window": [{"f0_mean_hz": 220.0}, {"f0_mean_hz": 300.0}]},
}


class ConversationalFBContract(unittest.TestCase):
    def _assert_text_only_no_score(self, msgs):
        for m in msgs:
            self.assertEqual(m["type"], "text", f"カード型が混入: {m['type']}")
            self.assertNotIn(m["type"], CARD_TYPES)
            hit = BAD_SCORE.search(m.get("text") or "")
            self.assertIsNone(hit, f"点数/記号が出力に: {hit.group(0) if hit else ''}")

    # AC-01/02/03: 課題あり録音 → text 2吹き出し・点数なし・課題確定
    def test_diagnose_issue_two_text_bubbles(self):
        msgs, updates = rule_engine.handle_audio(_state(), ANALYSIS_ISSUE, None, "song")
        self._assert_text_only_no_score(msgs)
        self.assertEqual(len(msgs), 2, "課題ありは①感想②練習の2吹き出し")
        self.assertIsNotNone(updates.get("current_task"), "課題が確定するはず")

    # AC-01/02/03: 良い録音 → text 1吹き出し・練習を出さない
    def test_diagnose_good_single_bubble(self):
        msgs, updates = rule_engine.handle_audio(_state(), ANALYSIS_GOOD, None, "song")
        self._assert_text_only_no_score(msgs)
        self.assertEqual(len(msgs), 1, "良い録音は褒めのみ1吹き出し")
        self.assertIsNone(updates.get("current_task"), "練習(課題)を出さない")

    # AC-02: 基礎練の達成判定はカード/点数なしの会話文
    def test_practice_check_text_only(self):
        st = _state(current_task="long_tone_decay")
        msgs, _ = rule_engine.handle_audio(st, ANALYSIS_GOOD, None, "practice")
        self._assert_text_only_no_score(msgs)
        self.assertTrue(1 <= len(msgs) <= 2)

    # AC-02: 歌い直しの改善判定はカード/点数なしの会話文
    def test_recheck_text_only(self):
        st = _state(current_task="long_tone_decay", baseline_analysis=ANALYSIS_ISSUE)
        msgs, _ = rule_engine.handle_audio(st, ANALYSIS_GOOD, None, "song")
        self._assert_text_only_no_score(msgs)
        self.assertTrue(1 <= len(msgs) <= 2)

    # FR-04: 点数質問もチャット経路(LLM)に統一。点数(数字)を返さない。
    # （実LLMでの「点数はつけていない」方針は HTTP e2e TC-12 で確認済み。
    #   ここは LLM不可時に正直フォールバックへ落ち、点数を返さないことを担保する）
    def test_score_question_no_points(self):
        msgs, _ = rule_engine.handle_text(
            _state(phase="practice", current_task="pitch_wobble", baseline_analysis=ANALYSIS_ISSUE),
            "これ何点ですか？",
        )
        text = " ".join(m.get("text") or "" for m in msgs if m["role"] == "coach")
        self.assertIsNone(BAD_SCORE.search(text), "点数を返してはいけない")

    # FR-03: 動画依頼はカードでなく会話文＋リンク
    def test_video_request_inline_no_card(self):
        msgs = rule_engine.handle_video_request(_state(), "ミックスボイスの動画ある？")
        for m in msgs:
            self.assertEqual(m["type"], "text")
        self.assertEqual(len(msgs), 1)

    # 定型文廃止: ルールベースの answer_question は削除済み
    def test_rule_based_qa_removed(self):
        self.assertFalse(hasattr(rule_engine, "answer_question"),
                         "ルールベース定型Q&A(answer_question)は廃止されているべき")

    # 定型文廃止: LLM失敗時、はぐらかし定型でなく“正直な短いメッセージ”が返る
    def test_chat_llm_down_honest_not_hedge(self):
        # setUpModule で _complete→None（LLM不可）。LESSON中に質問する。
        st = _state(phase="practice", current_task="pitch_wobble",
                    baseline_analysis=ANALYSIS_ISSUE, last_analysis=ANALYSIS_ISSUE)
        msgs, _ = rule_engine.handle_text(st, "音程の揺れって具体的にどのあたり？")
        text = " ".join(m.get("text") or "" for m in msgs if m["role"] == "coach")
        # 旧・はぐらかし定型は出ない
        self.assertNotIn("なるほど😊", text)
        self.assertNotIn("準備ができたら", text)
        # 正直フォールバックである
        self.assertIn("うまく言葉が出せませんでした", text)


class TextReplyPromptFraming(unittest.TestCase):
    """テキスト質問のプロンプト構築（_build_contents）の契約。

    フォローアップの質問が「録音を解析したFB」テンプレで返る不具合の回帰ガード。
    LLM自体は叩かず、Gemini へ渡す contents の組み立てだけを検証する（hermetic）。
    """

    def _last_text(self, contents):
        return contents[-1].parts[0].text

    def test_followup_turn_marked_not_new_recording(self):
        # 録音解析済み(last_analysis あり)の状態でテキスト質問が来た場面。
        st = _state(phase="practice", current_task="pitch_wobble",
                    last_analysis=ANALYSIS_ISSUE, baseline_analysis=ANALYSIS_ISSUE)
        contents = llm._build_contents(st, "具体的にどう練習すればいいの？", [])
        last = self._last_text(contents)
        # 今回は新しい録音が来ていない、と明示している
        self.assertIn("新しく届いた録音ではない", last)
        # 講評の書き出しで始めない、という指示が入っている
        self.assertIn("録音を送ってくれてありがとう", last)
        self.assertIn("始めないこと", last)
        # ユーザーの発言はちゃんと載っている
        self.assertIn("具体的にどう練習すればいいの？", last)

    def test_history_preserved_before_question(self):
        st = _state(phase="practice", current_task="pitch_wobble",
                    last_analysis=ANALYSIS_ISSUE, baseline_analysis=ANALYSIS_ISSUE)
        history = [
            {"role": "user", "content": "ボーカルフライって何ですか？"},
            {"role": "assistant", "content": "ガラガラ声を作る練習です。"},
        ]
        contents = llm._build_contents(st, "次はどうする？", history)
        # 履歴が会話ターンとして渡る（user 始まりが保証される）
        joined = "\n".join(c.parts[0].text for c in contents)
        self.assertIn("ボーカルフライって何ですか？", joined)
        self.assertIn("ガラガラ声を作る練習です。", joined)
        self.assertEqual(contents[0].role, "user")


class VideoTopicRouting(unittest.TestCase):
    """「（エッジボイスの）お手本ない？」が今の課題の動画に化ける不具合の回帰ガード。

    エッジボイス／ボーカルフライは声帯の閉じ（breathy_closure）の話題。
    話題語がTOPIC_KEYWORDSに無いと current_task にフォールバックし、
    見当違いの動画（例: 喉の力み）を返してしまう。
    """

    def test_edge_voice_maps_to_closure_not_current_task(self):
        # 今の課題は喉の力み。エッジボイスの手本を尋ねる。
        for text in ["エッジボイスの良いお手本ない？", "ボーカルフライのお手本が聴きたい",
                     "エッジボイスの見本ある？"]:
            self.assertTrue(rule_engine.is_video_request(text), f"動画要求と判定されるべき: {text}")
            topic = rule_engine.detect_topic_task(text, [], fallback="throat_tension")
            self.assertEqual(topic, "breathy_closure",
                             f"エッジ/フライは声帯の閉じに写像すべき（現状: {topic}）: {text}")

    def test_edge_voice_video_reply_is_on_topic(self):
        st = _state(phase="practice", current_task="throat_tension",
                    last_analysis=ANALYSIS_ISSUE, baseline_analysis=ANALYSIS_ISSUE)
        msgs = rule_engine.handle_video_request(st, "エッジボイスの良いお手本ない？", history=[])
        text = " ".join(m.get("text") or "" for m in msgs)
        # 声帯の閉じ（＝エッジ/フライの話題）が返り、喉の力みには化けない
        self.assertIn("声帯の閉じ", text)
        self.assertNotIn("喉の力み", text)
        # 参考動画リンクが1行添えられている（FR-03）
        self.assertIn("http", text)


class CoachToolsAndScrub(unittest.TestCase):
    """ソラ先生ツール化（docs/44）の決定論部分の契約（LLM非依存）。"""

    def test_find_reference_video_maps_edge_to_closure(self):
        from app.coaching import tools
        for topic in ["エッジボイス", "ボーカルフライ", "声帯の閉じ"]:
            r = tools.find_reference_video(topic)
            self.assertTrue(r["found"], topic)
            self.assertIn("声帯の閉じ", r["task_label"])
            self.assertTrue(r["video_url"].startswith("http"))
            self.assertIn(r["video_url"], tools.CATALOG_VIDEO_URLS)

    def test_find_reference_video_unmapped_is_found_false(self):
        from app.coaching import tools
        self.assertEqual(tools.find_reference_video("宇宙人の言語xyz"), {"found": False})

    def test_scrub_foreign_urls_keeps_catalog_removes_fake(self):
        from app.coaching import tools
        real = next(iter(tools.CATALOG_VIDEO_URLS))
        text = f"本物 {real} と 偽物 https://youtu.be/FAKE99999 です"
        out = llm._scrub_foreign_urls(text)
        self.assertIn(real, out)
        self.assertNotIn("FAKE99999", out)

    def test_wants_reference_detection(self):
        # 参考例を求める言い回しは True
        for t in ["良いお手本ない？", "良い例ある？", "参考になる動画は？", "見本が欲しい"]:
            self.assertTrue(llm._wants_reference(t), t)
        # 普通の質問・原曲URLは False
        for t in ["具体的にどう練習すればいいの？", "https://youtu.be/abc これが原曲です"]:
            self.assertFalse(llm._wants_reference(t), t)


class VideoOfferAcceptance(unittest.TestCase):
    """動画オファーを承諾したのにURLが一度も出ない事故（docs/71）の回帰ガード。

    「実演動画を出しましょうか？」→「お願いします」がキーワード判定
    （_wants_reference）に引っかからず、ツールが強制されなかった。
    """

    OFFER = [
        {"role": "user", "content": "喉の力みを直したい"},
        {"role": "assistant",
         "content": "リップロールから始めましょう。参考になる実演動画を出しましょうか？"},
    ]
    BROKEN_PROMISE = [
        {"role": "user", "content": "お願いします"},
        {"role": "assistant",
         "content": "それでは、こちらが参考になるリップロールの練習動画です。"},
    ]

    def test_accept_after_offer_forces_tool(self):
        for t in ["お願いします", "はい", "ぜひ！", "見たいです"]:
            self.assertTrue(llm._accepts_video_offer(t, self.OFFER), t)

    def test_prompt_after_broken_promise_recovers(self):
        # URL無しの「こちらが〜動画です」の後の催促でも復帰できる
        for t in ["どれ？", "リンクないよ", "見えないです"]:
            self.assertTrue(llm._accepts_video_offer(t, self.BROKEN_PROMISE), t)

    def test_no_offer_decline_or_delivered_do_not_force(self):
        # オファーが無い会話では強制しない
        self.assertFalse(llm._accepts_video_offer("お願いします", []))
        # 辞退は強制しない
        for t in ["今は大丈夫です", "いらないです", "また今度で"]:
            self.assertFalse(llm._accepts_video_offer(t, self.OFFER), t)
        # 直前ターンで実URLを渡せているなら対象外（「どれ？」は別の話題）
        delivered = [{"role": "assistant",
                      "content": "こちらです。\n（参考動画 → https://www.youtube.com/watch?v=TakKKIdIGgQ）"}]
        self.assertFalse(llm._accepts_video_offer("どれ？", delivered))

    def test_practice_name_topics_map_to_real_videos(self):
        # 練習名そのもの（コーチが名指しで提案する語彙）で実在動画が引ける
        from app.coaching import tools
        for topic in ["リップロール", "ストロー", "あくび", "ハミング"]:
            r = tools.find_reference_video(topic)
            self.assertTrue(r.get("found"), topic)
            self.assertIn(r["video_url"], tools.CATALOG_VIDEO_URLS)
        # 事故になった実会話の話題: リップロールにはリップロールの実演動画が返る
        r = tools.find_reference_video("リップロール")
        self.assertIn("リップロール", r["video_title"])


class RecordingIntentRouting(unittest.TestCase):
    """勧めた基礎練の実演が「曲の歌い直し」と誤認される不具合の回帰ガード。

    5秒のボーカルフライ実演を送ったのに『音程が8.6cents改善』と講評された事象。
    録音の中身＋文脈から practice と判定し、_audio_recheck(歌い直し)へ流さない。
    """

    # 5秒・狭い音域＝基礎練らしい実演
    FRY_LIKE = {
        "duration_sec": 5.0, "rms_mean": 0.03, "voiced_ratio": 0.8,
        "f0_median_hz": 130.0, "f0_jitter_cents": 20.0, "h1h2_db": 6.0,
        "timeline": {"sustained_segments": [], "per_window": [
            {"f0_mean_hz": 130.0}, {"f0_mean_hz": 135.0}, {"f0_mean_hz": 130.0}]},
    }

    def test_resolve_kind_overrides_default_song_to_practice(self):
        st = _state(phase="practice", current_task="breathy_closure",
                    baseline_analysis=ANALYSIS_ISSUE)
        # クライアントが既定の "song" を送っても、課題練習中の短い基礎練実演は practice
        self.assertEqual(rule_engine.resolve_kind(st, self.FRY_LIKE, "song"), "practice")

    def test_resolve_kind_respects_explicit_practice(self):
        st = _state(current_task="breathy_closure")
        self.assertEqual(rule_engine.resolve_kind(st, ANALYSIS_GOOD, "practice"), "practice")

    def test_resolve_kind_song_stays_song_without_task(self):
        # 課題が無い初回は上書きしない（song は song のまま＝診断へ）
        st = _state(current_task=None)
        self.assertEqual(rule_engine.resolve_kind(st, self.FRY_LIKE, "song"), "song")

    # 境界値(TC-33): レッスン中でも、メロディのある歌い直しは practice に化けない
    MELODIC_RESING = {
        "duration_sec": 9.0, "f0_median_hz": 260.0,
        "timeline": {"sustained_segments": [], "per_window": [
            {"f0_mean_hz": 220.0}, {"f0_mean_hz": 262.0}, {"f0_mean_hz": 294.0},
            {"f0_mean_hz": 330.0}, {"f0_mean_hz": 294.0}, {"f0_mean_hz": 247.0}]},
    }

    def test_resolve_kind_melodic_resing_stays_song_in_lesson(self):
        st = _state(phase="practice", current_task="breathy_closure",
                    baseline_analysis=ANALYSIS_ISSUE)
        # 音域が広くメロディがある＝classify_kind は song。課題中でも song のまま歌い直し判定へ。
        self.assertEqual(rule_engine.classify_kind(self.MELODIC_RESING), "song")
        self.assertEqual(rule_engine.resolve_kind(st, self.MELODIC_RESING, "song"), "song")

    def test_fry_during_lesson_not_routed_to_recheck(self):
        # 既定 "song" で送っても、_audio_recheck（歌い直し改善判定）に化けない
        st = _state(phase="practice", current_task="breathy_closure",
                    baseline_analysis=ANALYSIS_ISSUE, last_analysis=self.FRY_LIKE)
        kind = rule_engine.resolve_kind(st, self.FRY_LIKE, "song")
        msgs, _ = rule_engine.handle_audio(st, self.FRY_LIKE, None, kind)
        text = " ".join(m.get("text") or "" for m in msgs if m["role"] == "coach")
        self._no_score = BAD_SCORE.search(text)
        self.assertIsNone(self._no_score, "点数/記号は出さない")
        self.assertNotIn("歌い直しの結果", text, "曲の歌い直し講評に化けてはいけない")


if __name__ == "__main__":
    unittest.main(verbosity=2)
