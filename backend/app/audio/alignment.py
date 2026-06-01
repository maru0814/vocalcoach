"""
DTW アライメント（librosa.sequence.dtw）。

ユーザー録音と原曲(声分離後)のクロマ系列を対応付け、
時間的なずれ（走り/モタり）を秒数つきで抽出する。
"""

from __future__ import annotations

from typing import Optional

import librosa
import numpy as np

HOP_LENGTH = 512
FMIN_HZ = 65.0
FMAX_HZ = 1000.0
FRAME_LENGTH = 2048


def _chroma(y: np.ndarray, sr: int) -> np.ndarray:
    return librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP_LENGTH)


def _f0_cents(y: np.ndarray, sr: int) -> np.ndarray:
    f0, _, _ = librosa.pyin(y, fmin=FMIN_HZ, fmax=FMAX_HZ, sr=sr,
                            frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where((f0 is not None) & (f0 > 0), 1200.0 * np.log2(f0 / 440.0), np.nan)


def _intune_score(mad_cents: float, off_ratio: float) -> int:
    """音程の正確さスコア(0-100)。

    中央絶対偏差(MAD, ビブラート等の外れ値に強い)を主成分にし、
    「明らかに別の音(>80c)に外れている割合」でペナルティを加える。
    良い歌唱でもビブラート・自然なゆらぎで20〜40c程度は出るため、閾値はやや寛容。
    """
    if mad_cents <= 22:
        base = 92
    elif mad_cents <= 35:
        base = 82
    elif mad_cents <= 55:
        base = 70
    elif mad_cents <= 85:
        base = 56
    else:
        base = 42
    base -= int(min(30, off_ratio * 60))  # 別の音に外れている割合でさらに減点
    return max(20, min(98, base))


def _pitch_accuracy(user_y, ref_y, sr, wp, lo, hi) -> tuple[Optional[float], Optional[int], Optional[float]]:
    """ワーピングパスに沿って、原曲メロディと音を外していないか(in-tune)を実測。

    全体の移調（キー差）を中央値で除き、オクターブに畳んだ残差から
    中央絶対偏差(MAD)と「別の音に外れている割合(>80c)」を出す。
    戻り: (pitch_error_cents=MAD, in_tune_score, off_ratio) or (None, None, None)。
    """
    try:
        cu = _f0_cents(user_y, sr)
        cr = _f0_cents(ref_y, sr)
    except Exception:
        return None, None, None
    uf, rf = wp[:, 0], wp[:, 1]
    devs = []
    for i in range(lo, hi):
        ui, ri = int(uf[i]), int(rf[i])
        if ui < len(cu) and ri < len(cr):
            a, b = cu[ui], cr[ri]
            if not (np.isnan(a) or np.isnan(b)):
                devs.append(a - b)
    if len(devs) < 8:
        return None, None, None
    arr = np.array(devs, dtype=float)
    rel = arr - np.median(arr)              # 全体の移調(キー差)を除去
    rel = ((rel + 600.0) % 1200.0) - 600.0  # オクターブに畳む(±600c)
    absdev = np.abs(rel)
    mad = float(np.median(absdev))          # 中央絶対偏差(外れ値に強い)
    off_ratio = float(np.mean(absdev > 80))  # 明らかに別の音に外れている割合
    return round(mad, 1), _intune_score(mad, off_ratio), round(off_ratio, 3)


def align(user_y: np.ndarray, ref_y: np.ndarray, sr: int,
          lag_threshold_sec: float = 0.25, max_segments: int = 3) -> Optional[dict]:
    """ユーザーと原曲のDTW対応からフレーズずれを抽出。

    返り値:
      {
        "mean_lag_sec": float,   # +が遅れ(モタり)、-が走り
        "worst_segments": [{"user_sec", "ref_sec", "lag_sec"}, ...]
      }
    対応が取れない/長さが極端に違う場合は None。
    """
    hop_sec = HOP_LENGTH / sr
    u_dur = len(user_y) / sr
    r_dur = len(ref_y) / sr
    # 長さが極端に違う場合は誤対応しやすいのでスキップ
    if u_dur < 3 or r_dur < 3:
        return None
    ratio = u_dur / r_dur
    if ratio < 0.5 or ratio > 2.0:
        return None

    cu = _chroma(user_y, sr)
    cr = _chroma(ref_y, sr)
    if cu.shape[1] < 8 or cr.shape[1] < 8:
        return None

    # DTW: コスト行列 + ワーピングパス（D, wp）
    try:
        _, wp = librosa.sequence.dtw(X=cu, Y=cr, metric="cosine")
    except Exception:
        return None

    # wp は (user_frame, ref_frame) のペア列（逆順）。時間順に直す。
    wp = wp[::-1]
    user_t = wp[:, 0] * hop_sec
    ref_t = wp[:, 1] * hop_sec
    # DTW は端点で強制的に (0,0)/(末尾,末尾) に固定されるため、境界10%をトリム
    n = len(wp)
    if n < 10:
        return None
    lo, hi = int(n * 0.1), int(n * 0.9)
    # 原曲メロディとの音程の正確さ(in-tune)を実測（ワーピングパスに沿って）
    pitch_err, in_tune, off_ratio = _pitch_accuracy(user_y, ref_y, sr, wp, lo, hi)
    user_t = user_t[lo:hi]
    ref_t = ref_t[lo:hi]
    # 各対応点のラグ = ユーザー時刻 - 原曲時刻（の相対基準を引く）
    lag = user_t - ref_t
    # 全体オフセット（区間開始位置の差）を除くため中央値を基準化
    rel_lag = lag - np.median(lag)

    mean_lag = float(np.mean(rel_lag))

    # ずれの大きい点を間引いて抽出
    worst = []
    order = np.argsort(-np.abs(rel_lag))
    seen_user = set()
    for idx in order:
        l = float(rel_lag[idx])
        if abs(l) < lag_threshold_sec:
            break
        u_sec = round(float(user_t[idx]), 1)
        # 近接点をまとめる（1秒バケツ）
        bucket = int(u_sec)
        if bucket in seen_user:
            continue
        seen_user.add(bucket)
        worst.append({
            "user_sec": u_sec,
            "ref_sec": round(float(ref_t[idx]), 1),
            "lag_sec": round(l, 2),
        })
        if len(worst) >= max_segments:
            break

    worst.sort(key=lambda w: w["user_sec"])
    return {
        "mean_lag_sec": round(mean_lag, 2),
        "worst_segments": worst,
        "pitch_error_cents": pitch_err,
        "in_tune_score": in_tune,
        "off_pitch_ratio": off_ratio,
    }
