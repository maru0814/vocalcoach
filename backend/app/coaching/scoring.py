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
    tech = orn.get("scoop_count", 0) + orn.get("fall_count", 0) + orn.get("kobushi_count", 0)
    if 1 <= tech <= 14:
        base += 5          # しゃくり/フォール/こぶし等を適度に使えている
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


# ============================================================================
# 発声特化スコア（docs/21）。原曲(お手本)との比較を主成分にし、単体時は控えめに。
# ============================================================================

def pitch_accuracy_score(a: dict, c: Optional[dict]) -> int:
    """音程の正確さ。原曲とのin-tune実測があればそれを主に、無ければ安定度(ジッター)で近似。"""
    align = (c or {}).get("alignment") if c else None
    if align and align.get("in_tune_score") is not None:
        return _clamp(align["in_tune_score"])
    j = a.get("f0_jitter_cents")
    if j is None:
        return 62
    return _clamp(94 if j <= 6 else (84 if j <= 12 else (72 if j <= 20 else 58)))


def phonation_score(a: dict, c: Optional[dict]) -> int:
    """声の鳴り・効率（声帯の閉じ＝flow phonation＋響き/シンガーズフォルマント）。

    原曲があれば「原曲の閉じ・響きへの近さ」を主成分にする（H1-H2の絶対値はドメイン依存のため）。
    """
    sf = a.get("singers_formant_ratio") or 0.0
    h = a.get("h1h2_db")
    vc = (c or {}).get("voice_compare") if c else None
    if vc:
        base = 84
        clo = vc.get("closure")
        if clo and clo.get("verdict") != "match":
            base -= 12        # 原曲と声帯の閉じ方が乖離（息漏れ/締めすぎ）
        ring = vc.get("ring")
        if ring and ring.get("verdict") == "weaker":
            base -= 12        # 原曲より響きが弱い
        elif ring and ring.get("verdict") == "richer":
            base += 2
        return _clamp(base)
    # 原曲なし: 内転バランス＋響きの絶対評価（控えめ）
    if h is None:
        base = 70
    elif 2.0 <= h <= 6.0:
        base = 84             # バランスの良い閉じ
    elif 1.0 <= h <= 8.0:
        base = 77
    elif h > 12.0 or h < -2.0:
        base = 60             # 顕著な息漏れ/締めすぎ
    else:
        base = 70
    if sf >= 0.008:
        base += 8
    elif sf >= 0.003:
        base += 3
    return _clamp(base)


def registration_score(a: dict, c: Optional[dict]) -> int:
    """声区の運び。高音を原曲と同じように（多くはミックスで）運べているか＋換声点の段差。"""
    vc = (c or {}).get("voice_compare") if c else None
    rh = (vc or {}).get("register_high")
    if rh:
        if rh.get("verdict") == "match":
            base = 86
        elif rh.get("user") == "chest" and rh.get("ref") in ("mix", "head"):
            base = 62         # 原曲はミックス/裏声なのに地声で引っぱっている
        elif rh.get("user") == "head" and rh.get("ref") in ("mix", "chest"):
            base = 70         # 原曲より薄い裏声に逃げ気味
        else:
            base = 74
        return _clamp(base)
    # 原曲なし: 高音側の声区が出せていれば中立よりやや上
    v = (a.get("voice") or {}).get("register_high") or {}
    reg = v.get("register")
    if reg == "mix":
        return 80
    if reg in ("chest", "head"):
        return 74
    return 70


def support_score(a: dict, c: Optional[dict]) -> int:
    """支え・安定（appoggio）。伸ばした音の安定度で近似。"""
    lts = a.get("long_tone_stability")
    if lts is None:
        return 70
    return _clamp(90 if lts <= 20 else (82 if lts <= 30 else (72 if lts <= 45 else 58)))


def voice_scores(a: dict, c: Optional[dict]) -> dict:
    """発声4軸＋総合。音程・鳴り/効率・声区・支え。"""
    pitch = pitch_accuracy_score(a, c)
    phon = phonation_score(a, c)
    reg = registration_score(a, c)
    sup = support_score(a, c)
    total = _clamp(pitch * 0.30 + phon * 0.34 + reg * 0.22 + sup * 0.14)
    return {
        "pitch_score": pitch,
        "phonation_score": phon,
        "registration_score": reg,
        "support_score": sup,
        "total_score": total,
    }
