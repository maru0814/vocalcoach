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
    # 原曲（お手本）があり、メロディとの一致(in-tune)を実測できた場合はそれを主成分にする。
    # ジッターは「安定度」、in-tuneは「音を外していないか」の実測なので、後者を優先(7:3)。
    align = (c or {}).get("alignment")
    if align and align.get("in_tune_score") is not None:
        return _clamp(round(align["in_tune_score"] * 0.7 + base * 0.3))
    # 原曲との半音差が大きいと減点（オクターブ違い等は除外: 11-13は無視）
    if c and c.get("f0_median_diff_semitones") is not None:
        st = abs(c["f0_median_diff_semitones"])
        if not (10.5 <= st <= 13.5) and st > 1.0:
            base -= min(15, (st - 1.0) * 5)
    return _clamp(base)


def rhythm_score(a: dict, c: Optional[dict]) -> int:
    # 原曲(お手本)が無いと「走り/モタり」は正確に測れない。確信を持って低く出さず、
    # 中立(概算)に置く（毎回リズムだけ最下位に見える問題を回避。根拠はFBで明示する）。
    base = 80
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


def yokuyou_level(rng: Optional[float], c: Optional[dict]) -> str:
    """抑揚(強弱)の良し悪し◎○△×。原曲があれば原曲基準で評価する。

    原曲が抑揚をつけていない（平坦）なら、ユーザーも抑揚控えめでOK（不問）。
    原曲が抑揚をつけている所でつけられていない時だけ △/× で反応する。
    原曲が無いときは断定しすぎず、極端に平坦な時だけ控えめに指摘。
    """
    if rng is None:
        return "ok"
    if c and c.get("ref_rms_db_range") is not None:
        ref = c["ref_rms_db_range"]
        if ref < 12:                       # 原曲が平坦 → 抑揚控えめでも問題なし
            return "good" if rng >= ref - 2 else "ok"
        gap = ref - rng                    # 原曲よりどれだけ平坦か
        if gap <= 2:
            return "good"                  # 原曲と同等以上に抑揚をつけられている
        if gap <= 6:
            return "ok"
        if gap <= 12:
            return "weak"                  # 原曲は抑揚があるのに、つけられていない
        return "bad"
    # 原曲なし: 断定しすぎない
    return "good" if rng >= 18 else ("ok" if rng >= 8 else "weak")


def expression_score(a: dict, c: Optional[dict]) -> int:
    """表現力(DAM風)= 抑揚(強弱) を主軸に、ビブラート・しゃくり/フォール等の技法を加味。

    抑揚は原曲基準（原曲が平坦なら平坦でも減点しない）。技法は適度に入っていれば加点。
    """
    rng = a.get("rms_db_range")
    base = {"good": 84, "ok": 73, "weak": 60, "bad": 48}[yokuyou_level(rng, c)]
    vr = a.get("vibrato_rate_hz")
    vd = a.get("vibrato_depth_cents") or 0
    if vr is not None and 4.0 <= vr <= 7.5 and vd >= 20:
        base += 8          # 整ったビブラート
    orn = a.get("expression_ornaments") or {}
    tech = orn.get("scoop_count", 0) + orn.get("fall_count", 0)
    if 1 <= tech <= 12:
        base += 5          # しゃくり/フォール等を適度に使えている
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
