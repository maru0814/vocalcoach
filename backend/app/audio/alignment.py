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


def _pitch_accuracy(user_y, ref_y, sr, wp, lo, hi) -> tuple[Optional[float], Optional[int], Optional[float], list]:
    """ワーピングパスに沿って、原曲メロディと音を外していないか(in-tune)を実測。

    全体の移調（キー差）を中央値で除き、オクターブに畳んだ残差から
    中央絶対偏差(MAD)と「別の音に外れている割合(>80c)」を出す。
    戻り: (pitch_error_cents=MAD, in_tune_score, off_ratio) or (None, None, None)。
    """
    hop_sec = HOP_LENGTH / sr
    try:
        cu = _f0_cents(user_y, sr)
        cr = _f0_cents(ref_y, sr)
    except Exception:
        return None, None, None, []
    uf, rf = wp[:, 0], wp[:, 1]
    devs, times = [], []
    for i in range(lo, hi):
        ui, ri = int(uf[i]), int(rf[i])
        if ui < len(cu) and ri < len(cr):
            a, b = cu[ui], cr[ri]
            if not (np.isnan(a) or np.isnan(b)):
                devs.append(a - b)
                times.append(ui * hop_sec)
    if len(devs) < 8:
        return None, None, None, []
    arr = np.array(devs, dtype=float)
    rel = arr - np.median(arr)              # 全体の移調(キー差)を除去
    rel = ((rel + 600.0) % 1200.0) - 600.0  # オクターブに畳む(±600c)
    absdev = np.abs(rel)
    mad = float(np.median(absdev))          # 中央絶対偏差(外れ値に強い)
    off_ratio = float(np.mean(absdev > 80))  # 明らかに別の音に外れている割合
    spots = _pitch_off_spots(rel, np.array(times))
    return round(mad, 1), _intune_score(mad, off_ratio), round(off_ratio, 3), spots


def _pitch_off_spots(rel: np.ndarray, times: np.ndarray,
                     thr_cents: float = 40.0, max_cents: float = 150.0,
                     max_spots: int = 3) -> list[dict]:
    """音程が外れている箇所を、方向（高い/低い）と秒数つきで抽出する。

    rel>0 = ユーザーが原曲より高い(シャープ)、rel<0 = 低い(フラット)。
    近接点は1.5秒バケツでまとめ、ズレの大きい順に最大 max_spots 件。
    40〜150centの範囲だけ採用する（150c超は別の音/DTW誤対応の可能性が高く、
    「少し外した」の指摘としては不正確なので事実化しない）。
    """
    spots: list[dict] = []
    order = np.argsort(-np.abs(rel))
    seen: set[int] = set()
    for idx in order:
        c = float(rel[idx])
        if abs(c) > max_cents:
            continue  # 別の音/誤対応の可能性 → 採用しない
        if abs(c) < thr_cents:
            break
        t = float(times[idx])
        bucket = int(t // 1.5)
        if bucket in seen:
            continue
        seen.add(bucket)
        spots.append({
            "user_sec": round(t, 1),
            "cents": round(abs(c)),
            "direction": "sharp" if c > 0 else "flat",  # 高い / 低い
        })
        if len(spots) >= max_spots:
            break
    spots.sort(key=lambda s: s["user_sec"])
    return spots


# 同じ曲として照合できたとみなす最低の識別度（パス一致 − ランダム対応一致）。
# DTW はどんな信号でも貪欲にマッチさせるため、絶対的なコサイン類似では無関係音源も
# 高く出る。そこで「ランダム対応にしたときの一致度」を引いた差分で同一曲かを判定する。
# 実測: 実際の歌い直し ≥0.28 / 無関係・ノイズ ≤0.02 → 0.20 で安全に分離。
CONFIDENCE_MIN = 0.20
# リズムずれとして musically 妥当な上限（これを超えるのはDTWの誤対応アーティファクト）
MAX_PLAUSIBLE_LAG_SEC = 1.0


def _best_pc_shift(cu: np.ndarray, cr: np.ndarray) -> tuple[int, float]:
    """ユーザーと原曲の全体的なキー差（ピッチクラスの回転量, 半音）を推定。

    平均クロマベクトルの巡回相関が最大になる回転量を返す。
    戻り: (shift_semitones[-5..6], best_similarity[0..1])。
    """
    mu = cu.mean(axis=1)
    mr = cr.mean(axis=1)
    nu, nr = np.linalg.norm(mu), np.linalg.norm(mr)
    if nu <= 0 or nr <= 0:
        return 0, 0.0
    mu = mu / nu
    mr = mr / nr
    best_k, best = 0, -1.0
    for k in range(12):
        s = float(np.dot(np.roll(mu, k), mr))
        if s > best:
            best, best_k = s, k
    shift = best_k if best_k <= 6 else best_k - 12
    return shift, best


def _path_confidence(cu: np.ndarray, cr: np.ndarray, wp: np.ndarray, lo: int, hi: int) -> float:
    """同一曲としての識別度（パス対応の一致 − ランダム対応の一致）。

    DTW は無関係な音源でも貪欲に高コサイン類似のパスを作ってしまうため、絶対値では
    判定できない。そこで「実際のパス対応」と「参照フレームをシャッフルした対応」の
    一致度の差をとる。同じ曲なら大きく(>0.25)、無関係なら≈0。
    """
    def cos(a, b):
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        return float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0

    rng = np.random.default_rng(0)
    perm = rng.permutation(cr.shape[1])
    path_sims, base_sims = [], []
    for i in range(lo, hi):
        ui, ri = int(wp[i, 0]), int(wp[i, 1])
        path_sims.append(cos(cu[:, ui], cr[:, ri]))
        base_sims.append(cos(cu[:, ui], cr[:, perm[ri]]))
    if not path_sims:
        return 0.0
    return float(np.median(path_sims) - np.median(base_sims))


def align(user_y: np.ndarray, ref_y: np.ndarray, sr: int,
          lag_threshold_sec: float = 0.25, max_segments: int = 3) -> Optional[dict]:
    """ユーザーと原曲のDTW対応から、音程の正確さ(in-tune)とフレーズずれを抽出。

    返り値:
      {
        "mean_lag_sec": float,        # +が遅れ(モタり)、-が走り
        "worst_segments": [...],
        "pitch_error_cents": float,   # in-tune の中央絶対偏差
        "in_tune_score": int|None,    # 同一曲として照合できた時のみ
        "off_pitch_ratio": float|None,
        "key_shift_semitones": int,   # 原曲に対するキー差（同キーなら0）
        "confidence": float,          # 同一曲としての一致度
        "low_confidence": bool,       # Trueなら断定しない
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

    # ② キー差を推定し、ユーザークロマを回転させてキー不変に整列する
    #    （別キーで上手に歌った録音を「音痴」と誤判定しないため）
    key_shift, _ = _best_pc_shift(cu, cr)
    cu_aligned = np.roll(cu, key_shift, axis=0)

    # DTW: コスト行列 + ワーピングパス（D, wp）
    try:
        _, wp = librosa.sequence.dtw(X=cu_aligned, Y=cr, metric="cosine")
    except Exception:
        return None

    # wp は (user_frame, ref_frame) のペア列（逆順）。時間順に直す。
    wp = wp[::-1]
    n = len(wp)
    if n < 10:
        return None
    lo, hi = int(n * 0.1), int(n * 0.9)

    # ③ 同一曲としての信頼度。低ければ in-tune/リズムを断定しない
    confidence = _path_confidence(cu_aligned, cr, wp, lo, hi)
    low_conf = confidence < CONFIDENCE_MIN

    user_t = (wp[:, 0] * hop_sec)[lo:hi]
    ref_t = (wp[:, 1] * hop_sec)[lo:hi]

    if low_conf:
        # 同じ曲として照合できていない（誤った原曲/無関係音源など）。数値は出さない。
        return {
            "mean_lag_sec": None,
            "worst_segments": [],
            "pitch_error_cents": None,
            "in_tune_score": None,
            "off_pitch_ratio": None,
            "key_shift_semitones": int(key_shift),
            "confidence": round(confidence, 2),
            "low_confidence": True,
        }

    # 原曲メロディとの音程の正確さ(in-tune)を実測（ワーピングパスに沿って）
    pitch_err, in_tune, off_ratio, pitch_off_spots = _pitch_accuracy(user_y, ref_y, sr, wp, lo, hi)

    # 各対応点のラグ = ユーザー時刻 - 原曲時刻（の相対基準を引く）
    lag = user_t - ref_t
    rel_lag = lag - np.median(lag)  # 全体オフセット（区間開始差）を中央値で基準化
    mean_lag = float(np.mean(rel_lag))

    # ④ ずれの大きい点を抽出（巨大な外れ値=DTW誤対応は除外）
    worst = []
    order = np.argsort(-np.abs(rel_lag))
    seen_user = set()
    for idx in order:
        l = float(rel_lag[idx])
        if abs(l) < lag_threshold_sec:
            break
        if abs(l) > MAX_PLAUSIBLE_LAG_SEC:
            continue  # 1秒超のラグはアライメントのアーティファクト。事実として出さない
        u_sec = round(float(user_t[idx]), 1)
        bucket = int(u_sec)  # 近接点をまとめる（1秒バケツ）
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
        "pitch_off_spots": pitch_off_spots,
        "key_shift_semitones": int(key_shift),
        "confidence": round(confidence, 2),
        "low_confidence": False,
    }
