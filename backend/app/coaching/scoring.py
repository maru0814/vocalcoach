"""
解析値 → 4軸スコア（0-100）。docs/04 の 3.4.1 対応表に基づくルールベース算出。
"""

from __future__ import annotations

from typing import Optional


def _clamp(v: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, round(v))))


def pitch_score(a: dict, c: Optional[dict]) -> int:
    """f0ジッター中心。低いほど良い。key不一致やオクターブずれで減点。"""
    j = a.get("f0_jitter_cents")
    if j is None:
        base = 60
    elif j <= 5:
        base = 95
    elif j <= 15:
        base = 85
    elif j <= 30:
        base = 70
    else:
        base = 50
    # 原曲との半音差が大きいと減点（オクターブ違い等は除外: 11-13は無視）
    if c and c.get("f0_median_diff_semitones") is not None:
        st = abs(c["f0_median_diff_semitones"])
        if not (10.5 <= st <= 13.5) and st > 1.0:
            base -= min(15, (st - 1.0) * 5)
    return _clamp(base)


def rhythm_score(a: dict, c: Optional[dict]) -> int:
    base = 75
    if c and c.get("tempo_diff_bpm") is not None:
        td = abs(c["tempo_diff_bpm"])
        if td <= 2:
            base = 88
        elif td <= 6:
            base = 78
        elif td <= 15:
            base = 68
        else:
            base = 60
    # DTWアライメントの平均ラグも加味（フレーズの走り/モタり）
    align = (c or {}).get("alignment")
    if align and align.get("mean_lag_sec") is not None:
        lag = abs(align["mean_lag_sec"])
        if lag <= 0.1:
            base += 5
        elif lag >= 0.4:
            base -= 10
        elif lag >= 0.25:
            base -= 5
    return _clamp(base)


def expression_score(a: dict, c: Optional[dict]) -> int:
    rng = a.get("rms_db_range")
    if rng is None:
        base = 60
    elif rng >= 18:
        base = 88
    elif rng >= 12:
        base = 80
    elif rng >= 8:
        base = 70
    else:
        base = 60
    # ビブラートがあれば加点
    vr = a.get("vibrato_rate_hz")
    if vr is not None and 4.0 <= vr <= 7.5:
        base += 5
    return _clamp(base)


def compute_scores(a: dict, c: Optional[dict]) -> dict:
    p = pitch_score(a, c)
    r = rhythm_score(a, c)
    e = expression_score(a, c)
    total = _clamp(p * 0.35 + r * 0.30 + e * 0.35)
    return {
        "pitch_score": p,
        "rhythm_score": r,
        "expression_score": e,
        "total_score": total,
    }
