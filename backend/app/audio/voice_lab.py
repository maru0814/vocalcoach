"""音声医学指標（Praat / parselmouth）。資料2章・docs/21 準拠。

CPP(声の芯)・Jitter(周期ゆらぎ)・Shimmer(振幅ゆらぎ)・HNR(倍音対雑音)・フォルマント F1-F3。
parselmouth が無い環境では全て None を返す graceful fallback（本体は落とさない）。
"""

from __future__ import annotations

import numpy as np

# 正常域の目安（資料・音声医学の一般値）。診断ツリーのしきい値に使う。
CPP_NORMAL_DB = 12.0          # これ未満は息漏れ/芯の弱さ
HNR_LOW_DB = 10.0             # これ未満は雑音優位（息漏れ・嗄れ）
JITTER_HIGH_PCT = 1.04        # 臨床的に正常上限の目安(%)
SHIMMER_HIGH_PCT = 3.8        # 臨床的に正常上限の目安(%)


def available() -> bool:
    try:
        import parselmouth  # noqa: F401
        return True
    except Exception:
        return False


def _cpp_db(y: np.ndarray, sr: int, f0_hz: np.ndarray, voiced_flag: np.ndarray,
            hop: int = 512, frame: int = 2048, fmin: float = 60.0, fmax: float = 500.0,
            max_samples: int = 60) -> float | None:
    """CPP(ケプストラムピーク突出度, dB)を numpy で高速算出（Praat CPPS と同等の物理量）。

    各有声フレームで log power spectrum → 実ケプストラム を作り、基本周期(1/f0)付近の
    ケプストラムピークと、ケプストラム回帰直線(背景)の差(dB)を求めて中央値をとる。
    高い=芯のある(倍音が立つ)声／低い=息漏れ・嗄れ。parselmouthのCPPSは22sで約67秒
    かかるため、こちらを採用する（資料2.4 の「同等の機能」）。
    """
    vf = np.asarray(voiced_flag).astype(bool)
    idxs = np.flatnonzero(vf)
    if idxs.size < 4:
        return None
    if idxs.size > max_samples:
        idxs = idxs[np.linspace(0, idxs.size - 1, max_samples).astype(int)]
    win = np.hanning(frame)
    q_lo = int(sr / fmax)            # 最小ケフレンシ（最高f0）
    q_hi = int(sr / fmin)            # 最大ケフレンシ（最低f0）
    vals: list[float] = []
    for i in idxs:
        st = int(i) * hop
        seg = y[st:st + frame]
        if len(seg) < frame:
            continue
        w = seg.astype(np.float64) * win
        spec = np.fft.rfft(w)
        logp = 10.0 * np.log10(np.abs(spec) ** 2 + 1e-12)   # log power spectrum (dB)
        ceps = np.fft.irfft(logp)                            # 実ケプストラム
        n = len(ceps)
        hi = min(q_hi, n - 1)
        if hi - q_lo < 4:
            continue
        band = ceps[q_lo:hi]
        pk = int(np.argmax(band))
        pk_q = q_lo + pk
        pk_val = float(band[pk])
        # 背景の回帰直線（q_lo..hi の線形回帰）でピーク位置のベースラインを推定
        xs = np.arange(q_lo, hi)
        a, b = np.polyfit(xs, ceps[q_lo:hi], 1)
        base = a * pk_q + b
        vals.append(pk_val - base)
    if not vals:
        return None
    raw = float(np.median(vals))
    # おおよそ Praat CPPS の dB スケールへ線形近似（合成2点較正: clear≈10.8 / breathy≈0.9）。
    # 絶対値はマイク・声分離でドメイン依存のため目安。実ラベル音源が集まり次第較正する（docs/15方針）。
    return round(max(0.0, 14.0 * raw - 7.5), 1)


def analyze_voice_lab(y: np.ndarray, sr: int,
                      f0_hz: np.ndarray | None = None,
                      voiced_flag: np.ndarray | None = None) -> dict:
    """波形(モノ)から CPP/Jitter/Shimmer/HNR/フォルマント を算出して返す。

    戻り: {"cpp_db","jitter_pct","shimmer_pct","hnr_db","formants":{f1_hz..f3_hz},"engine"}
    CPPは numpy 高速版（_cpp_db, parselmouth不要）。Jitter/Shimmer/HNR/フォルマントは
    parselmouth（無い環境では None）。
    """
    out: dict = {"cpp_db": None, "jitter_pct": None, "shimmer_pct": None,
                 "hnr_db": None, "formants": None, "engine": "none"}
    # CPP は parselmouth 非依存で高速に算出（資料2.4 の「同等の機能」）
    if f0_hz is not None and voiced_flag is not None:
        try:
            out["cpp_db"] = _cpp_db(np.asarray(y), sr, np.asarray(f0_hz), np.asarray(voiced_flag))
        except Exception:
            pass
    try:
        import parselmouth
        from parselmouth.praat import call
    except Exception:
        return out
    try:
        snd = parselmouth.Sound(np.ascontiguousarray(np.asarray(y, dtype=np.float64)),
                                sampling_frequency=float(sr))
    except Exception:
        return out
    out["engine"] = "parselmouth"

    # --- Jitter / Shimmer（周期的ポイントプロセス経由）---
    try:
        pp = call(snd, "To PointProcess (periodic, cc)", 75, 500)
        npts = call(pp, "Get number of points")
        if npts and npts > 6:
            jit = call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
            shim = call([snd, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
            if jit == jit:                       # NaN チェック
                out["jitter_pct"] = round(float(jit) * 100.0, 3)
            if shim == shim:
                out["shimmer_pct"] = round(float(shim) * 100.0, 3)
    except Exception:
        pass

    # --- HNR ---
    try:
        harm = call(snd, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
        hnr = call(harm, "Get mean", 0, 0)
        if hnr == hnr and hnr > -200:
            out["hnr_db"] = round(float(hnr), 1)
    except Exception:
        pass

    # CPP は上で numpy 版を算出済み（parselmouth の CPPS は 22sで約67秒かかり不採用）。

    # --- フォルマント F1-F3（Burg法・中央値）---
    try:
        fm = call(snd, "To Formant (burg)", 0.01, 5, 5500.0, 0.025, 50)
        formants: dict = {}
        for k in (1, 2, 3):
            try:
                v = call(fm, "Get quantile", k, 0, 0, "Hertz", 0.5)
            except Exception:
                v = float("nan")
            formants[f"f{k}_hz"] = int(round(float(v))) if (v == v and 90 < v < 5000) else None
        out["formants"] = formants
    except Exception:
        pass

    return out
