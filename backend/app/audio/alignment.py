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


def _chroma(y: np.ndarray, sr: int) -> np.ndarray:
    return librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP_LENGTH)


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
    return {"mean_lag_sec": round(mean_lag, 2), "worst_segments": worst}
