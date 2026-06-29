"""ゼロベース個人最適FB（docs/43）と月次コスト上限/通知の回帰テスト。

実際の Gemini API は叩かず、google.genai.Client をモックして
- build_evidence_pack が実測の証拠（タイムライン＋参照KB＋接地facts）を組むこと
- generate_feedback が接地ガード（証拠に無い秒の捏造を除去）を効かせること
- 月次コスト上限で停止し、上限到達時に通知が当月1回だけ飛ぶこと
を検証する。
"""

from __future__ import annotations

import pytest

from app.core.config import settings


SAMPLE_STATE = {
    "phase": "feedback",
    "song_ref_path": "/x/ref.wav",
    "current_task": None,
    "last_analysis": {
        "duration_sec": 30.0,
        "f0_median_hz": 220.0,
        "f0_jitter_cents": 12.0,
        "rms_db_range": 6.0,
        "long_tone_stability": 25.0,
        "timeline": {
            "sustained_segments": [
                {"start_sec": 12.0, "end_sec": 14.5, "mean_f0_hz": 440.0,
                 "register": "chest", "f0_std_cents": 62, "spectral_centroid_hz": 2900},
                {"start_sec": 21.0, "end_sec": 23.0, "mean_f0_hz": 330.0,
                 "voice_type_estimate": "head", "f0_std_cents": 18},
            ]
        },
        "_compare": {"alignment": {
            "in_tune_score": 78, "pitch_error_cents": 20, "mean_lag_sec": 0.18,
            "worst_segments": [{"user_sec": 12.0}, {"user_sec": 21.0}],
        }},
    },
}


@pytest.fixture
def zbfb_settings(tmp_path, monkeypatch):
    """テスト用の設定（一時台帳・フラグON・ダミーキー）。"""
    monkeypatch.setattr(settings, "llm_cost_ledger_path", str(tmp_path / "ledger.json"))
    monkeypatch.setattr(settings, "enable_zero_base_fb", True)
    monkeypatch.setattr(settings, "gemini_api_key", "TEST_DUMMY_KEY")
    return settings


def test_build_evidence_pack_has_timeline_and_kb(zbfb_settings):
    from app.coaching import llm
    pack = llm.build_evidence_pack(SAMPLE_STATE)
    assert "区間ごとの実測" in pack          # 全区間タイムライン
    assert "参考エクササイズ知識" in pack      # 参照KB（カタログを選択肢でなく知識として）
    assert "12〜14秒" in pack and "21〜23秒" in pack


def test_generate_feedback_grounds_seconds(zbfb_settings, monkeypatch):
    """証拠にある秒は残し、証拠に無い捏造の秒（99秒付近）は接地ガードで消す。"""
    from app.coaching import llm
    from google import genai

    fake = ("サビの高音いいですね。12〜14秒の伸ばしは少し力みが見えます。"
            "あと99秒付近の音も気になります。ネイネイで軽く当ててみましょう。録音送ってね。")

    class _Resp:
        text = fake

    class _Models:
        def generate_content(self, **kw):
            assert kw["model"] == settings.llm_analysis_model   # 分析用モデルで呼ばれる
            return _Resp()

    class _Client:
        def __init__(self, **kw):
            self.models = _Models()

    monkeypatch.setattr(genai, "Client", _Client)
    reply = llm.generate_feedback(SAMPLE_STATE, user_wav=b"RIFFfake", ref_wav=None)
    assert reply is not None
    assert "12〜14秒" in reply               # 実測の秒は残る
    assert "99秒付近" not in reply           # 捏造の秒は除去される


def test_generate_feedback_disabled_returns_none(tmp_path, monkeypatch):
    """フラグOFFなら呼ばない（None＝ルールベースFBにフォールバック）。"""
    from app.coaching import llm
    monkeypatch.setattr(settings, "enable_zero_base_fb", False)
    monkeypatch.setattr(settings, "gemini_api_key", "TEST_DUMMY_KEY")
    assert llm.generate_feedback(SAMPLE_STATE, user_wav=b"x") is None


def test_monthly_cap_stops_and_notifies_once(tmp_path, monkeypatch):
    """¥100上限・1回¥30 → 3回で停止、通知は当月ちょうど1回。"""
    from app.core import llm_budget
    monkeypatch.setattr(settings, "llm_cost_ledger_path", str(tmp_path / "ledger.json"))
    monkeypatch.setattr(settings, "llm_monthly_budget_jpy", 100)
    monkeypatch.setattr(settings, "llm_analysis_est_jpy_per_call", 30.0)

    sent = []
    monkeypatch.setattr(llm_budget, "_notify", lambda t: sent.append(t))

    done = 0
    for _ in range(6):
        est = settings.llm_analysis_est_jpy_per_call
        if llm_budget.would_exceed(est):
            llm_budget.notify_budget_reached_once()
        else:
            llm_budget.record(est)
            done += 1

    assert done == 3                          # 30×3=90、4回目(120>100)で停止
    assert llm_budget.month_spend_jpy() == 90.0
    assert len(sent) == 1                      # 通知は当月1回だけ


def test_unlimited_when_cap_zero(tmp_path, monkeypatch):
    """上限0なら無制限（would_exceed は常に False）。"""
    from app.core import llm_budget
    monkeypatch.setattr(settings, "llm_cost_ledger_path", str(tmp_path / "ledger.json"))
    monkeypatch.setattr(settings, "llm_monthly_budget_jpy", 0)
    assert llm_budget.would_exceed(999999) is False
