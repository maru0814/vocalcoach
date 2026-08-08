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

    def test_followup_turn_marked_not_new_recording(self):
        # 録音解析済み(last_analysis あり)の状態でテキスト質問が来た場面。
        # docs/93: 「新しい録音ではない」の明示は system 側テキストに移った。
        st = _state(phase="practice", current_task="pitch_wobble",
                    last_analysis=ANALYSIS_ISSUE, baseline_analysis=ANALYSIS_ISSUE)
        contents, system_text = llm._build_contents(st, "具体的にどう練習すればいいの？", [])
        self.assertIn("録音なしのテキスト会話", system_text)
        self.assertIn("過去に送られた録音の再掲", system_text)
        # 講評の書き出しで始めない、という指示が入っている
        self.assertIn("解析したかのような書き出し", system_text)
        # ユーザーの発言は素のまま最終ターンに載っている（ラッパーで包まない）
        self.assertEqual(contents[-1].parts[0].text, "具体的にどう練習すればいいの？")

    def test_history_preserved_before_question(self):
        st = _state(phase="practice", current_task="pitch_wobble",
                    last_analysis=ANALYSIS_ISSUE, baseline_analysis=ANALYSIS_ISSUE)
        history = [
            {"role": "user", "content": "ボーカルフライって何ですか？"},
            {"role": "assistant", "content": "ガラガラ声を作る練習です。"},
        ]
        contents, _ = llm._build_contents(st, "次はどうする？", history)
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

    def test_find_reference_video_edge_voice_is_honest(self):
        """エッジボイスの実演動画はカタログに無い → found=false ＋ 代替を別練習と明示（docs/93 §4.4）。

        旧実装は found=true で別練習（ストロー/リップロール）の動画を返し、
        「エッジボイスの実演」としてリップロール動画が提示される事故を起こした
        （2026-08-07 スクショ「リップロールやん」）。
        """
        from app.coaching import tools
        for topic in ["エッジボイス", "ボーカルフライ", "声帯の閉じ"]:
            r = tools.find_reference_video(topic)
            self.assertFalse(r["found"], topic)
            alt = r.get("alternative")
            self.assertIsNotNone(alt, topic)
            self.assertIn("声帯の閉じ", alt["task_label"])
            self.assertTrue(alt["video_url"].startswith("http"))
            self.assertIn(alt["video_url"], tools.CATALOG_VIDEO_URLS)
            # 代替はエッジボイスと偽らない（練習名が返り、noteで「無い」と明示）
            self.assertNotIn("エッジ", alt["practice_name"])
            self.assertIn("実演動画はカタログに無い", r.get("note", ""))

    def test_find_reference_video_practice_match_is_exact(self):
        """練習単位マッチ（found=true）は、その練習そのものの動画が返る。"""
        from app.coaching import tools
        r = tools.find_reference_video("リップロール")
        self.assertTrue(r["found"])
        self.assertEqual(r.get("match"), "practice")
        self.assertIn("リップロール", r["practice_name"])
        self.assertIn("リップロール", r["video_title"])

    def test_find_reference_video_unmapped_is_found_false(self):
        from app.coaching import tools
        r = tools.find_reference_video("宇宙人の言語xyz")
        self.assertFalse(r["found"])
        self.assertIsNone(r.get("alternative"))

    def test_scrub_foreign_urls_keeps_catalog_removes_fake(self):
        from app.coaching import tools
        real = next(iter(tools.CATALOG_VIDEO_URLS))
        text = f"本物 {real} と 偽物 https://youtu.be/FAKE99999 です"
        out = llm._scrub_foreign_urls(text)
        self.assertIn(real, out)
        self.assertNotIn("FAKE99999", out)

    def test_wants_reference_detection(self):
        # 動画・お手本を明示的に指す語だけ強制（docs/94 で絞り込み）
        for t in ["良いお手本ない？", "参考になる動画は？", "見本が欲しい", "実演見せて"]:
            self.assertTrue(llm._wants_reference(t), t)
        # 普通の質問・原曲URL・曖昧語（参考/聞きたい/良い例）は強制しない
        # （モデルの AUTO 判断＋約束不履行の事後検知に任せる）
        for t in ["具体的にどう練習すればいいの？", "https://youtu.be/abc これが原曲です",
                  "参考までに、腹式呼吸って必要？", "ちょっと聞きたいんだけど毎日何分練習すべき？",
                  "良い例ある？"]:
            self.assertFalse(llm._wants_reference(t), t)


class VideoDeliveryGuarantee(unittest.TestCase):
    """動画URLの到達保証（docs/93 §4.3。旧docs/71 の承諾正規表現を置換）。

    承諾かどうかの理解はモデルの仕事。コードは「約束したのにURLが無い」という
    結果だけを事後検知し、generate_reply が1回だけツール強制で再生成する。
    """

    def test_promise_without_url_triggers_retry(self):
        for reply in ["いいですよ、リップロールの動画をお出ししますね。",
                      "それでは、こちらが参考になるリップロールの動画です。"]:
            self.assertTrue(llm._needs_video_delivery_retry(reply, set()), reply)

    def test_delivered_or_plain_reply_does_not_trigger(self):
        # 本文に実URLがあれば約束は果たされている
        delivered = "こちらです。\n（参考動画 → https://www.youtube.com/watch?v=TakKKIdIGgQ）"
        self.assertFalse(llm._needs_video_delivery_retry(delivered, set()))
        # ツールがURLを返していれば決定論付与が効くので不要
        self.assertTrue(llm._needs_video_delivery_retry("動画をお出ししますね。", set()))
        self.assertFalse(llm._needs_video_delivery_retry(
            "動画をお出ししますね。", {"https://www.youtube.com/watch?v=TakKKIdIGgQ"}))
        # 約束の無い普通の会話・オファー（〜出しましょうか？）は対象外
        for reply in ["いいね、その調子です！", "参考になる実演動画を出しましょうか？", ""]:
            self.assertFalse(llm._needs_video_delivery_retry(reply, set()), reply)

    def test_practice_name_topics_map_to_real_videos(self):
        # 練習名そのもの（コーチが名指しで提案する語彙）で実在動画が練習単位で引ける
        from app.coaching import tools
        for topic in ["リップロール", "ストロー", "あくび", "ハミング"]:
            r = tools.find_reference_video(topic)
            self.assertTrue(r.get("found"), topic)
            self.assertEqual(r.get("match"), "practice", topic)
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


class PracticeVideoSearch(unittest.TestCase):
    """カタログ外はYouTube実検索で探しに行く（docs/93 §4.6）。「無い」で会話を止めない。"""

    def test_search_returns_real_results_under_videos_key(self):
        from unittest.mock import patch
        from app.coaching import tools
        fake = [{"title": "エッジボイスのやり方", "url": "https://www.youtube.com/watch?v=abc123xyz",
                 "channel": "ボイトレch", "duration_sec": 300}]
        with patch("app.audio.reference.search_youtube", return_value=fake):
            r = tools.search_practice_video("エッジボイス やり方")
        self.assertTrue(r["found"])
        # 原曲確認アンカーの決定論（candidates キー）と衝突しない
        self.assertIn("videos", r)
        self.assertNotIn("candidates", r)
        self.assertEqual(r["videos"][0]["url"], "https://www.youtube.com/watch?v=abc123xyz")

    def test_search_failure_is_honest_empty(self):
        from unittest.mock import patch
        from app.coaching import tools
        with patch("app.audio.reference.search_youtube", side_effect=RuntimeError):
            r = tools.search_practice_video("エッジボイス")
        self.assertEqual(r, {"found": False, "videos": []})
        self.assertEqual(tools.search_practice_video(""), {"found": False, "videos": []})

    def test_dispatch_routes_search_practice_video(self):
        from unittest.mock import patch
        from app.coaching import tools
        with patch("app.audio.reference.search_youtube", return_value=[]) as m:
            tools.dispatch("search_practice_video", {"query": "リップロール やり方"})
        m.assert_called_once()

    def test_declaration_is_wired_and_honest(self):
        from app.coaching import tools
        d = tools.SEARCH_PRACTICE_VIDEO_DECL
        self.assertEqual(d["name"], "search_practice_video")
        self.assertIn("質は保証できない", d["description"])
        self.assertIn("でっち上げず", d["description"])
