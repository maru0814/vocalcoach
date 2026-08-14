"""聴いてから答えるフロー（docs/95, docs/99）のテスト。

①ブラインド聴取（listen_blind・第1段）と、②講評段への聴取事実注入
（blind / コメント申告）を LLM・ネットワーク非依存（hermetic）で検証する。

実行: cd backend && ./.venv/bin/python -m unittest tests.test_listen_first_flow -v
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402


def _fake_client(captured: dict, resp_text: str):
    """google.genai.Client のモック。渡ったテキストプロンプトを captured に記録する。"""

    class _Resp:
        text = resp_text

    class _Models:
        def generate_content(self, **kw):
            for content in kw.get("contents", []):
                for p in content.parts:
                    if getattr(p, "text", None):
                        captured["prompt"] = p.text
            captured["config"] = kw.get("config")
            return _Resp()

    class _Client:
        def __init__(self, **kw):
            self.models = _Models()

    return _Client


class BlindListen(unittest.TestCase):
    """FR-01: ブラインド聴取（第1段）。"""

    def _call(self, resp_text: str):
        from app.coaching import llm
        captured: dict = {}
        orig_key = settings.gemini_api_key
        settings.gemini_api_key = "TEST_DUMMY"
        try:
            with mock.patch("google.genai.Client", _fake_client(captured, resp_text)):
                result = llm.listen_blind(b"RIFFfake")
        finally:
            settings.gemini_api_key = orig_key
        return captured.get("prompt", ""), result

    def test_parses_wellformed_output(self):
        prompt, result = self._call(
            "KIND: practice\nPRACTICE: サイレン\nCONFIDENCE: high\n"
            "DESC: 低音から高音まで連続的に滑らかに上下している。"
        )
        self.assertEqual(result, {
            "kind": "practice", "practice": "サイレン", "confidence": "high",
            "desc": "低音から高音まで連続的に滑らかに上下している。",
        })

    def test_prompt_is_context_free(self):
        """AC-01: プロンプトに会話文脈（宿題・課題・履歴・コメント）が入らない。"""
        prompt, _ = self._call("KIND: song\nPRACTICE: 不明\nCONFIDENCE: mid\nDESC: 歌。")
        for banned in ("宿題", "課題", "勧めて", "レッスンでは"):
            self.assertNotIn(banned, prompt, f"ブラインド段に文脈語「{banned}」を入れない")
        self.assertIn("サイレン", prompt, "練習メニュー（語彙）は渡してよい")
        self.assertIn("先入観なし", prompt)

    def test_acoustic_facts_injected_as_ruler(self):
        """docs/104: 質感計測は「物差し」として注入され、文脈語は依然入らない。"""
        from app.coaching import llm
        captured: dict = {}
        orig_key = settings.gemini_api_key
        settings.gemini_api_key = "TEST_DUMMY"
        try:
            with mock.patch(
                "google.genai.Client",
                _fake_client(captured, "KIND: practice\nPRACTICE: サイレン\nCONFIDENCE: high\nDESC: 滑らか。"),
            ):
                llm.listen_blind(
                    b"RIFFfake",
                    acoustic_facts="規則的な振幅の震えは検出されない（なめらかな発声）",
                )
        finally:
            settings.gemini_api_key = orig_key
        prompt = captured.get("prompt", "")
        self.assertIn("この録音自体からの機械計測", prompt)
        self.assertIn("震えは検出されない", prompt)
        self.assertIn("名前を断定する材料ではなく", prompt)
        for banned in ("宿題", "課題", "勧めて", "レッスンでは"):
            self.assertNotIn(banned, prompt, "計測注入後もAC-01を維持")

    def test_song_maps_practice_none(self):
        _, result = self._call("KIND: song\nPRACTICE: 不明\nCONFIDENCE: mid\nDESC: 歌。")
        self.assertEqual(result["kind"], "song")
        self.assertIsNone(result["practice"])

    def test_malformed_output_returns_none(self):
        _, result = self._call("よく分かりませんでした。")
        self.assertIsNone(result, "KIND が取れなければ None（従来フローに退化＝AC-04）")

    def test_double_failure_returns_none_with_logs(self):
        """AC-04/10: 2回とも失敗なら None。失敗は無言にせず必ずログに残る。"""
        from app.coaching import llm

        calls = {"n": 0}

        class _Boom:
            def __init__(self, **kw):
                calls["n"] += 1
                raise RuntimeError("api down")

        orig_key = settings.gemini_api_key
        settings.gemini_api_key = "TEST_DUMMY"
        try:
            with mock.patch("google.genai.Client", _Boom):
                with self.assertLogs("app.coaching.llm", level="WARNING") as lg:
                    self.assertIsNone(llm.listen_blind(b"RIFFfake"))
        finally:
            settings.gemini_api_key = orig_key
        self.assertEqual(calls["n"], 2, "1回リトライして計2試行")
        self.assertTrue(any("2回とも失敗" in m for m in lg.output))

    def test_retry_succeeds_on_second_attempt(self):
        """AC-09: 1試行目が一時失敗しても、リトライで成功すれば判定が返る。"""
        from app.coaching import llm

        calls = {"n": 0}

        class _Models:
            def generate_content(self, **kw):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise RuntimeError("transient 503")

                class _R:
                    text = "KIND: practice\nPRACTICE: サイレン\nCONFIDENCE: high\nDESC: 滑らかな上下。"
                return _R()

        class _Client:
            def __init__(self, **kw):
                self.models = _Models()

        orig_key = settings.gemini_api_key
        settings.gemini_api_key = "TEST_DUMMY"
        try:
            with mock.patch("google.genai.Client", _Client):
                with self.assertLogs("app.coaching.llm", level="INFO") as lg:
                    r = llm.listen_blind(b"RIFFfake")
        finally:
            settings.gemini_api_key = orig_key
        self.assertIsNotNone(r)
        self.assertEqual(r["practice"], "サイレン")
        self.assertEqual(calls["n"], 2)
        self.assertTrue(any("リトライ" in m for m in lg.output), "失敗→リトライがログに残る")
        self.assertTrue(any("判定=practice" in m for m in lg.output), "成功時の判定内容もログに残る")

    def test_success_logs_result(self):
        """AC-10: 成功時も判定内容がログに残る（効いた回を後から確認できる）。"""
        from app.coaching import llm
        captured: dict = {}
        orig_key = settings.gemini_api_key
        settings.gemini_api_key = "TEST_DUMMY"
        try:
            with mock.patch(
                "google.genai.Client",
                _fake_client(captured, "KIND: song\nPRACTICE: 不明\nCONFIDENCE: mid\nDESC: 歌。"),
            ):
                with self.assertLogs("app.coaching.llm", level="INFO") as lg:
                    llm.listen_blind(b"RIFFfake")
        finally:
            settings.gemini_api_key = orig_key
        self.assertTrue(any("判定=song" in m for m in lg.output))

    def test_flag_off_skips_call(self):
        """AC-08: ENABLE_BLIND_LISTEN=false で第1段が完全に無効化される。"""
        from app.coaching import llm

        class _MustNotConstruct:
            def __init__(self, **kw):
                raise AssertionError("フラグOFF時にクライアントを作ってはいけない")

        orig_flag, orig_key = settings.enable_blind_listen, settings.gemini_api_key
        settings.enable_blind_listen, settings.gemini_api_key = False, "TEST_DUMMY"
        try:
            with mock.patch("google.genai.Client", _MustNotConstruct):
                self.assertIsNone(llm.listen_blind(b"RIFFfake"))
        finally:
            settings.enable_blind_listen, settings.gemini_api_key = orig_flag, orig_key


class ReconcileBlind(unittest.TestCase):
    """合意ゲート（docs/105 改訂・docs/106 §4）: 一致した時だけ名前を断定する。"""

    def _r(self, kind="practice", practice=None, conf="high", desc="d"):
        return {"kind": kind, "practice": practice, "confidence": conf, "desc": desc}

    def test_agreement_asserts_name(self):
        from app.coaching import llm
        out = llm.reconcile_blind(self._r(practice="リップロール"),
                                  self._r(practice="リップロール"))
        self.assertEqual(out["practice"], "リップロール")
        self.assertEqual(out["confidence"], "high")

    def test_disagreement_keeps_candidates_without_assertion(self):
        """実録音第2号の型: 耳=リップロール vs 事実=サイレン → 断定せず候補を残す。"""
        from app.coaching import llm
        out = llm.reconcile_blind(self._r(practice="リップロール", desc="唇を震わせている"),
                                  self._r(practice="サイレン", desc="連続的に移動"))
        self.assertIsNone(out["practice"])
        self.assertEqual(out["confidence"], "mid")
        self.assertIn("リップロール", out["desc"])
        self.assertIn("サイレン", out["desc"])
        self.assertIn("候補", out["desc"])

    def test_agreement_with_low_confidence_is_mid(self):
        from app.coaching import llm
        out = llm.reconcile_blind(self._r(practice="ハミング", conf="mid"),
                                  self._r(practice="ハミング"))
        self.assertEqual(out["practice"], "ハミング")
        self.assertEqual(out["confidence"], "mid")

    def test_kind_disagreement_takes_ear_kind_low_confidence(self):
        from app.coaching import llm
        out = llm.reconcile_blind(self._r(kind="song"), self._r(practice="サイレン"))
        self.assertEqual(out["kind"], "song")
        self.assertEqual(out["confidence"], "low")
        self.assertIsNone(out["practice"])

    def test_single_channel_passthrough(self):
        from app.coaching import llm
        ear = self._r(practice="サイレン")
        self.assertEqual(llm.reconcile_blind(ear, None), ear)
        self.assertEqual(llm.reconcile_blind(None, ear), ear)

    def test_both_none_is_none(self):
        from app.coaching import llm
        self.assertIsNone(llm.reconcile_blind(None, None))

    def test_song_agreement(self):
        from app.coaching import llm
        out = llm.reconcile_blind(self._r(kind="song"), self._r(kind="song"))
        self.assertEqual(out["kind"], "song")
        self.assertIsNone(out["practice"])
        self.assertEqual(out["confidence"], "high")


class IdentityBlock(unittest.TestCase):
    """docs/105: 識別コントラクトの注入と「再判定させない」プロンプト構造。"""

    def _generate(self, ictx: dict, user_comment=None,
                  model_reply="サイレン、いい滑らかさです。"):
        from app.coaching import llm
        captured: dict = {}
        state = {"phase": "practice", "current_task": "weak_resonance",
                 "last_analysis": {"duration_sec": 5.0}, "baseline_analysis": None,
                 "song_ref_url": None, "song_ref_path": None}
        orig_flag, orig_key = settings.enable_zero_base_fb, settings.gemini_api_key
        settings.enable_zero_base_fb, settings.gemini_api_key = True, "TEST_DUMMY"
        try:
            with mock.patch(
                "google.genai.Client", _fake_client(captured, model_reply),
            ):
                reply = llm.generate_feedback(
                    state, user_wav=b"RIFFfake", intent_ctx=ictx, user_comment=user_comment,
                )
        finally:
            settings.enable_zero_base_fb, settings.gemini_api_key = orig_flag, orig_key
        return captured.get("prompt", ""), reply

    def _ictx(self, identity=None):
        d = {"task_label": "響きを前に集める（芯・通り）",
             "practice_name": "ハミング → 母音（マスクに集める）"}
        if identity:
            d["identity"] = identity
        return d

    @staticmethod
    def _pr(name=None, conf="high", desc="低音から高音まで連続的に上下している。"):
        return {"kind": "practice", "name": name, "confidence": conf,
                "description": desc, "source": "blind"}

    def test_named_practice_block(self):
        """名前確定: 識別ブロックに名前が入り、宿題名での講評を一般則で禁止。

        （旧docs/52 AC-09・旧FR-07 の回帰を単一ルールで担保: 宿題=ハミングでも
        識別=サイレンなら、サイレンとして講評しハミング名を使わせない）
        """
        prompt, reply = self._generate(self._ictx(self._pr(name="サイレン")))
        self.assertIn("識別済み・ここは再判定しない", prompt)
        self.assertIn("聴こえた内容: サイレン", prompt)
        self.assertIn("識別と異なる名前（勧奨中の基礎練名を含む）でこの録音を講評しない", prompt)
        self.assertIn("歌としての講評", prompt)
        self.assertNotIn("(a)曲・歌の録音", prompt, "二択の再判定をさせない")
        self.assertNotIn("INTENT:", prompt, "旧タグプロトコルの指示を出さない")
        self.assertIsNotNone(reply)

    def test_unnamed_practice_block_describes_and_confirms(self):
        """名前未確定: 描写で講評し、一言確認してよい。宿題名は使わせない。"""
        prompt, _ = self._generate(self._ictx(self._pr(name=None, conf="mid")))
        self.assertIn("練習名は特定できていない", prompt)
        self.assertIn("名前を断定しない", prompt)
        self.assertIn("の練習で合っていますか？", prompt)
        self.assertIn("勧奨中の基礎練名をこの録音の名前として使わない", prompt)

    def test_song_block(self):
        """歌識別: 通常の歌講評。練習系ルールは出ない。"""
        prompt, _ = self._generate(self._ictx(
            {"kind": "song", "name": None, "confidence": "mid",
             "description": None, "source": "blind"}))
        self.assertIn("種類: 歌", prompt)
        self.assertIn("通常どおり歌として講評する", prompt)
        self.assertNotIn("名前を断定しない", prompt)
        self.assertNotIn("INTENT:", prompt)

    def test_stray_intent_tag_is_stripped_not_used(self):
        """旧癖で INTENT タグが出ても本文から剥がすだけ（heard 書き戻しは廃止）。"""
        ictx = self._ictx(self._pr(name="サイレン"))
        _, reply = self._generate(ictx, model_reply="INTENT: song\n\n本文です。")
        self.assertEqual(reply, "本文です。")
        self.assertNotIn("heard", ictx, "書き戻しはもう行わない")

    def test_comment_declaration_is_top_fact(self):
        """(A)案: コメントでの申告を最優先の事実として扱う指示が入る。"""
        prompt, _ = self._generate(self._ictx(self._pr(name="サイレン")),
                                   user_comment="サイレンやってみた")
        self.assertIn("「サイレンやってみた」", prompt)
        self.assertIn("最優先の事実として講評する", prompt)
        self.assertIn("決めつけずに正直に一言確認する", prompt)

    def test_no_comment_no_declaration_instruction(self):
        """コメントが無ければ申告優先の指示も出ない（不要な指示を増やさない）。"""
        prompt, _ = self._generate(self._ictx(self._pr(name="サイレン")))
        self.assertNotIn("最優先の事実として講評する", prompt)

    def test_heuristic_identity_low_confidence(self):
        """フラグOFF等のヒューリスティック識別（低確信・名前なし）でも描写・確認の型になる。"""
        prompt, _ = self._generate(self._ictx(
            {"kind": "practice", "name": None, "confidence": "low",
             "description": None, "source": "heuristic"}))
        self.assertIn("確信度 low", prompt)
        self.assertIn("名前を断定しない", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
