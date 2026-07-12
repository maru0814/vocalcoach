"""状態バンク（事実の地面 = state）と、各 state の「許可された事実」の算出。

各 state は本物の `build_session_context(state)` にそのまま渡せる解析JSON。
決定論チェックの基準になる「許可事実」（言及可能な秒数・音名・in_tune可否）は、
コード側の真実（build_session_context の出力）から導出する。＝基準を二重管理しない。
"""
from __future__ import annotations

import re
from typing import Any

# --- 状態バンク（多様性: 原曲有無 / 録音長 / 声区 / 数値 / 空） ---

STATES: dict[str, dict[str, Any]] = {
    # 原曲なし・25秒・地声中心。F#5罠(AC-01)・30秒罠(AC-04)・数値罠(AC-06)の主舞台。
    "st_noref_25s_chest": {
        "phase": "feedback",
        "current_task": None,
        "last_analysis": {
            "duration_sec": 25.0,
            "f0_median_hz": 220.0,  # ≒A3
            "f0_jitter_cents": 12.0,
            "rms_db_range": 8.0,
            "long_tone_stability": 22.0,
            "h1h2_db": 9.0,
            "timeline": {
                "sustained_segments": [
                    {"start_sec": 8.0, "end_sec": 10.5, "mean_f0_hz": 330.0,
                     "register": "chest", "f0_std_cents": 40, "spectral_centroid_hz": 2800},
                    {"start_sec": 18.0, "end_sec": 20.0, "mean_f0_hz": 392.0,
                     "voice_type_estimate": "mix", "f0_std_cents": 55},
                ]
            },
        },
    },
    # 原曲あり・30秒・ミックス。in_tune照合あり(78点)。秒数罠(AC-07)・正確さ質問の舞台。
    "st_ref_30s_mix": {
        "phase": "feedback",
        "song_ref_path": "/x/ref.wav",
        "current_task": None,
        "last_analysis": {
            "duration_sec": 30.0,
            "f0_median_hz": 261.6,  # ≒C4
            "f0_jitter_cents": 7.0,
            "rms_db_range": 16.0,
            "long_tone_stability": 18.0,
            "timeline": {
                "sustained_segments": [
                    {"start_sec": 12.0, "end_sec": 14.5, "mean_f0_hz": 440.0,
                     "register": "chest", "f0_std_cents": 62, "spectral_centroid_hz": 2900},
                    {"start_sec": 21.0, "end_sec": 23.0, "mean_f0_hz": 330.0,
                     "voice_type_estimate": "head", "f0_std_cents": 18},
                ]
            },
            "_compare": {
                "alignment": {
                    "in_tune_score": 78, "pitch_error_cents": 20, "mean_lag_sec": 0.18,
                    "worst_segments": [{"user_sec": 12.0}, {"user_sec": 21.0}],
                    "pitch_off_spots": [{"user_sec": 12.0, "cents": 35, "direction": "flat"}],
                    "low_confidence": False,
                }
            },
        },
    },
    # 原曲リンクあるが照合が対応づかない（low_confidence）。正確さ断定罠(H7)の舞台。
    "st_lowconf_20s": {
        "phase": "feedback",
        "song_ref_url": "https://youtu.be/example",
        "user_range": "サビ",
        "current_task": None,
        "last_analysis": {
            "duration_sec": 20.0,
            "f0_median_hz": 293.7,  # ≒D4
            "f0_jitter_cents": 15.0,
            "rms_db_range": 10.0,
            "_compare": {"alignment": {"low_confidence": True}},
        },
    },
    # 録音前の雑談フェーズ。last_analysis がほぼ空。数値質問は「今は無い」が正解(AC-06)。
    "st_empty_chat": {
        "phase": "practice",
        "current_task": None,
        "last_analysis": {},
    },
    # 長尺60秒・裏声中心・原曲あり。長い録音での秒数・声区の扱い。
    "st_ref_60s_head": {
        "phase": "feedback",
        "song_ref_path": "/x/ref2.wav",
        "current_task": None,
        "last_analysis": {
            "duration_sec": 60.0,
            "f0_median_hz": 349.2,  # ≒F4
            "f0_jitter_cents": 9.0,
            "rms_db_range": 14.0,
            "timeline": {
                "sustained_segments": [
                    {"start_sec": 40.0, "end_sec": 44.0, "mean_f0_hz": 587.3,
                     "voice_type_estimate": "head", "f0_std_cents": 30},
                ]
            },
            "_compare": {
                "alignment": {"in_tune_score": 85, "pitch_error_cents": 14,
                              "mean_lag_sec": -0.1, "low_confidence": False}
            },
        },
    },
}

# 音名トークン（英語式）。例 A4, F#5, Bb3, C♯4。
NOTE_RE = re.compile(r"\b([A-G])(#|♯|b|♭|＃|♭)?(\d)\b")


def in_tune_available(state: dict) -> bool:
    """原曲照合による音程の“正確さ”が語れる state か（H7の基準）。"""
    analysis = state.get("last_analysis") or state.get("baseline_analysis") or {}
    align = ((analysis.get("_compare") or {}).get("alignment")) or {}
    if align.get("low_confidence"):
        return False
    return align.get("in_tune_score") is not None


def allowed_note_names(context: str) -> set[str]:
    """「現在のレッスン状況」テキストに現れる音名の集合（H3の許可集合）。

    build_session_context は f0 を音名（例 A3）に変換して載せる。ここに無い音名を
    コーチが新しく出したら創作＝H3。
    """
    return {f"{m.group(1)}{('#' if m.group(2) in ('#', '♯', '＃') else '')}{m.group(3)}"
            for m in NOTE_RE.finditer(context or "")}


def normalize_note(token_match: re.Match) -> str:
    sharp = "#" if token_match.group(2) in ("#", "♯", "＃") else ""
    return f"{token_match.group(1)}{sharp}{token_match.group(3)}"
