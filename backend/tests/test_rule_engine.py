"""ルールエンジン（app/coaching/rule_engine.py）の意図検出・パース・分岐テスト。

LLMに依存しない確定的な部分（URL/区間/着目点の抽出、各種リクエスト判定、
録音種別の推定、アクションチップのディスパッチ）を検証する。
"""
from app.coaching import rule_engine as re_


# --- parse_phase_a（URL / 区間 / 着目点の抽出） ---

class TestParsePhaseA:
    def test_extracts_youtube_url(self):
        out = re_.parse_phase_a("これです https://youtu.be/abc123 サビ", {})
        assert out["song_ref_url"] == "https://youtu.be/abc123"

    def test_single_range_is_reference(self):
        out = re_.parse_phase_a("0:48-1:13 を練習したい", {})
        assert out["ref_range"] == "0:48-1:13"
        assert out["user_range"] is None

    def test_two_ranges_user_then_ref(self):
        out = re_.parse_phase_a("自分は 0:10-0:30、原曲は 1:00-1:20", {})
        assert out["user_range"] == "0:10-0:30"
        assert out["ref_range"] == "1:00-1:20"

    def test_focus_keyword_detected(self):
        out = re_.parse_phase_a("高音のミックスがうまくいかない", {})
        assert out["focus_task"] == "mixed_voice"

    def test_no_signal_returns_empty(self):
        assert re_.parse_phase_a("こんにちは", {}) == {}


# --- 各種リクエスト判定 ---

class TestIntentDetection:
    def test_pronunciation_request(self):
        assert re_.is_pronunciation_request("滑舌を見てほしい") is True
        assert re_.is_pronunciation_request("音程どうでした？") is False

    def test_video_request(self):
        assert re_.is_video_request("ミックスの動画ある？") is True
        # URL を含むのは原曲指定なので動画リクエストではない
        assert re_.is_video_request("見本 https://youtu.be/x") is False

    def test_rediagnose_request(self):
        assert re_.is_rediagnose_request("もう一度診断して") is True
        assert re_.is_rediagnose_request("原曲の45秒から重ねて採点して") is True
        assert re_.is_rediagnose_request("いい天気ですね") is False

    def test_register_question_specific(self):
        # 地声/裏声を並べて「どっち？」＝この録音の声区判定
        assert re_.is_register_question("ここは地声？それとも裏声？") is True

    def test_register_question_excludes_general(self):
        # 一般的な定義・やり方の質問は通常チャットへ（False）
        assert re_.is_register_question("ミックスボイスとは何ですか？") is False
        assert re_.is_register_question("裏声の出し方を教えて") is False


# --- detect_topic_task（話題→課題ID、履歴引き継ぎ） ---

class TestDetectTopicTask:
    def test_keyword_in_text(self):
        assert re_.detect_topic_task("ビブラートのコツは？") == "no_vibrato"

    def test_inherits_from_user_history(self):
        hist = [{"role": "user", "content": "高音がつらい"},
                {"role": "coach", "content": "なるほど"}]
        # 今回の発話に話題語が無い → ユーザー履歴から引き継ぐ
        assert re_.detect_topic_task("動画ある？", hist) == "mixed_voice"

    def test_ignores_coach_history(self):
        hist = [{"role": "coach", "content": "ミックスボイスの練習もありますよ"}]
        assert re_.detect_topic_task("動画ある？", hist, fallback="x") == "x"


# --- classify_kind（曲 or 基礎練の推定） ---

class TestClassifyKind:
    def _analysis(self, f0s):
        return {"timeline": {"per_window": [{"f0_mean_hz": f} for f in f0s]}}

    def test_simple_is_practice(self):
        # 音数が少なく音域が狭い（単音中心）→ 基礎練
        assert re_.classify_kind(self._analysis([220.0, 220.0, 233.0])) == "practice"

    def test_melodic_is_song(self):
        # 音数・音域が広い → 曲
        assert re_.classify_kind(self._analysis([220, 277, 330, 392, 440, 494])) == "song"

    def test_no_pitch_defaults_to_song(self):
        assert re_.classify_kind(self._analysis([])) == "song"


# --- handle_action（チップ押下のディスパッチ） ---

class TestHandleAction:
    def test_finish_sets_done(self):
        msgs, updates = re_.handle_action({}, "finish")
        assert updates["phase"] == "done"
        assert msgs and msgs[0]["type"] == "text"

    def test_change_task_clears_and_avoids(self):
        msgs, updates = re_.handle_action({"current_task": "pitch_wobble"}, "change_task")
        assert updates["avoid_task"] == "pitch_wobble"
        assert updates["current_task"] is None

    def test_more_practice_without_task_routes_to_phase_a(self):
        msgs, updates = re_.handle_action({}, "more_practice")
        assert updates["phase"] == "A"

    def test_unknown_action_is_noop(self):
        msgs, updates = re_.handle_action({}, "???")
        assert updates == {}
        assert msgs[0]["type"] == "text"


# --- handle_text の確定的経路（LLM不要） ---

class TestHandleTextDeterministic:
    def test_phase_a_with_url_and_range_no_llm(self):
        state = {"phase": "A"}
        msgs, updates = re_.handle_text(state, "https://youtu.be/abc サビ 0:48-1:13")
        assert updates["song_ref_url"] == "https://youtu.be/abc"
        assert len(msgs) == 1 and msgs[0]["type"] == "text"
        assert "0:48-1:13" in msgs[0]["text"]

    def test_phase_b_new_url_acknowledged(self):
        state = {"phase": "practice"}
        msgs, updates = re_.handle_text(state, "原曲です https://youtu.be/xyz")
        assert updates["song_ref_url"] == "https://youtu.be/xyz"
        assert "受け取りました" in msgs[0]["text"]


# --- handle_video_request（話題不明なら聞き返す／既知なら練習を返す） ---

class TestHandleVideoRequest:
    def test_unknown_topic_asks_back(self):
        msgs = re_.handle_video_request({}, "動画ある？")
        assert len(msgs) == 1 and msgs[0]["type"] == "text"

    def test_known_topic_returns_practice_text(self):
        msgs = re_.handle_video_request({}, "ビブラートの動画ある？")
        assert len(msgs) == 1 and msgs[0]["type"] == "text"
        assert len(msgs[0]["text"]) > 0
