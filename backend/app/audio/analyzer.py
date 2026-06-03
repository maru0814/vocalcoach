"""
Audio analysis service (librosa).

`tools/audio_analyzer.py` のコアを Web版バックエンドへ移植したもの。
Claude Code版と同一指標を返すことで、両チャネルのFB品質を統一する。

公開API:
    analyze_file(path, start_sec=None, end_sec=None) -> dict
    compare(user: dict, ref: dict) -> dict
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np


SR = 22050
# hop=1024（50%オーバーラップ）で pyin/chroma/DTW を約2倍高速化。f0_jitter だけは
# フレーム間隔に比例して増えるので JITTER_REF_HOP で正規化し従来スケールを保つ。
HOP_LENGTH = 1024
FRAME_LENGTH = 2048
FMIN_HZ = 65.0
FMAX_HZ = 1000.0
JITTER_REF_HOP = 512  # f0_jitter の基準ホップ（この値での値に正規化する）
# 解析する最大秒数（応答時間を10秒以内に抑える安全上限）。長尺は先頭この秒数だけ解析。
MAX_ANALYSIS_SEC = 30.0
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def hz_to_cents(hz: np.ndarray, ref_hz: float = 440.0) -> np.ndarray:
    pos = hz > 0
    out = np.full_like(hz, np.nan, dtype=float)
    out[pos] = 1200.0 * np.log2(hz[pos] / ref_hz)
    return out


def estimate_key(y: np.ndarray, sr: int) -> tuple[str, str]:
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP_LENGTH)
    mean_chroma = chroma.mean(axis=1)
    major_profile = np.array(
        [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    )
    minor_profile = np.array(
        [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    )
    best_score = -np.inf
    best_key, best_mode = "C", "major"
    for shift in range(12):
        s_major = np.corrcoef(mean_chroma, np.roll(major_profile, shift))[0, 1]
        s_minor = np.corrcoef(mean_chroma, np.roll(minor_profile, shift))[0, 1]
        if s_major > best_score:
            best_score, best_key, best_mode = s_major, PITCH_CLASSES[shift], "major"
        if s_minor > best_score:
            best_score, best_key, best_mode = s_minor, PITCH_CLASSES[shift], "minor"
    return best_key, best_mode


def detect_vibrato(f0_hz: np.ndarray, hop_sec: float) -> tuple[float | None, float | None]:
    voiced_mask = ~np.isnan(f0_hz) & (f0_hz > 0)
    if voiced_mask.sum() < 50:
        return None, None
    f0_cents = hz_to_cents(f0_hz)
    diffs = np.diff(voiced_mask.astype(int))
    starts = np.where(diffs == 1)[0] + 1
    ends = np.where(diffs == -1)[0] + 1
    if voiced_mask[0]:
        starts = np.insert(starts, 0, 0)
    if voiced_mask[-1]:
        ends = np.append(ends, len(voiced_mask))
    if len(starts) == 0 or len(ends) == 0:
        return None, None
    longest = int(np.argmax(ends - starts))
    seg = f0_cents[starts[longest]:ends[longest]]
    seg = seg[~np.isnan(seg)]
    if len(seg) < 50:
        return None, None
    win = max(3, int(0.5 / hop_sec))
    if win % 2 == 0:
        win += 1
    drift = np.array(
        [np.median(seg[max(0, i - win // 2): i + win // 2 + 1]) for i in range(len(seg))]
    )
    centered = seg - drift
    spectrum = np.abs(np.fft.rfft(centered - centered.mean()))
    freqs = np.fft.rfftfreq(len(centered), d=hop_sec)
    mask = (freqs >= 3.0) & (freqs <= 10.0)
    if not mask.any() or spectrum[mask].size == 0:
        return None, None
    peak_idx = int(np.argmax(spectrum[mask]))
    peak_freq = float(freqs[mask][peak_idx])
    peak_power = float(spectrum[mask][peak_idx])
    median_power = float(np.median(spectrum[mask]))
    if median_power == 0 or peak_power < median_power * 2.0:
        return None, None
    return peak_freq, float(np.std(centered))


def _voiced_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """連続して声が出ている区間 [s, e) のリスト。"""
    diffs = np.diff(mask.astype(int))
    starts = np.where(diffs == 1)[0] + 1
    ends = np.where(diffs == -1)[0] + 1
    if mask[0]:
        starts = np.insert(starts, 0, 0)
    if mask[-1]:
        ends = np.append(ends, len(mask))
    return list(zip(starts.tolist(), ends.tolist()))


def detect_ornaments(f0_hz: np.ndarray, voiced_flag: np.ndarray, hop_sec: float) -> dict:
    """歌い回しの装飾を f0 から検出: しゃくり(下から入る)・フォール(語尾で落とす)。

    各有声フレーズの「頭」が本体より低ければ しゃくり、「終わり」が下に落ちれば フォール。
    戻り: {"scoops":[秒...], "falls":[秒...], "scoop_count", "fall_count"}（目安）。
    """
    scoops: list[float] = []
    falls: list[float] = []
    edge = max(2, int(round(0.12 / hop_sec)))  # 頭/終わりを見る窓 ≒120ms
    for s, e in _voiced_runs(voiced_flag.astype(bool)):
        if (e - s) * hop_sec < 0.30:
            continue
        seg = f0_hz[s:e]
        core = seg[edge:len(seg) - edge] if len(seg) > 2 * edge else seg
        body = float(np.nanmedian(core))
        if not np.isfinite(body) or body <= 0:
            continue
        head = float(np.nanmedian(seg[:edge]))
        tail = float(np.nanmedian(seg[-edge:]))
        if np.isfinite(head) and head > 0:
            if 1200.0 * np.log2(head / body) <= -55:   # 頭が本体より55c以上低い＝下から入った
                scoops.append(round(s * hop_sec, 1))
        if np.isfinite(tail) and tail > 0:
            if 1200.0 * np.log2(tail / body) <= -80:   # 終わりが80c以上落ちる＝フォール
                falls.append(round(e * hop_sec, 1))
    return {
        "scoops": scoops[:5], "falls": falls[:5],
        "scoop_count": len(scoops), "fall_count": len(falls),
    }


def detect_kobushi(f0_hz: np.ndarray, voiced_flag: np.ndarray, hop_sec: float) -> dict:
    """こぶし: 伸ばした音の“途中”での一瞬のピッチの跳ね上げ／当て直し（演歌・J-POPの装飾）。

    各有声フレーズの中間部で、なめらかなベースライン(移動中央値)から短時間だけ大きく
    外れてすぐ戻る“単発の山/谷”を数える。区別:
      - しゃくり=フレーズの「入り」/ フォール=「終わり」→ 端を除外して中間部だけ見る
      - ビブラート=周期的な揺れ → イベント周辺の符号反転が多い区間は除外（単発のみ採用）
    戻り: {"kobushi":[秒...], "kobushi_count": n}（目安）。
    """
    try:
        from scipy.ndimage import median_filter
    except Exception:
        return {"kobushi": [], "kobushi_count": 0}
    f0c = hz_to_cents(f0_hz)
    vflag = voiced_flag.astype(bool)
    if len(vflag) == 0:
        return {"kobushi": [], "kobushi_count": 0}
    min_run = int(round(0.40 / hop_sec))            # こぶしは伸ばし気味の音に出やすい
    edge = max(2, int(round(0.12 / hop_sec)))        # 頭(しゃくり)/終わり(フォール)は除外
    base_win = max(3, (int(round(0.35 / hop_sec)) | 1))
    around_w = max(1, int(round(0.30 / hop_sec)))
    side_w = max(3, int(round(0.15 / hop_sec)))      # 突出の前後の「保持」を見る窓 ≒150ms
    dur_min = max(1, int(round(0.05 / hop_sec)))
    dur_max = max(dur_min + 1, int(round(0.30 / hop_sec)))
    thr = 45.0                                       # ベースラインからの突出量(cents)
    return_tol = 45.0                                # 前後の音高がこれ以内なら「同じ音に戻った」
    spots: list[float] = []
    for s, e in _voiced_runs(vflag):
        if (e - s) < min_run:
            continue
        seg = f0c[s:e].astype(float).copy()
        valid = np.isfinite(seg)
        if int(valid.sum()) < min_run:
            continue
        if not valid.all():
            seg = np.interp(np.arange(len(seg)), np.flatnonzero(valid), seg[valid])
        base = median_filter(seg, size=base_win, mode="nearest")
        res = seg - base
        lo, hi = edge, len(seg) - edge
        if hi - lo < dur_min:
            continue
        i = lo
        while i < hi:
            if abs(res[i]) >= thr:
                sign = res[i] > 0
                j = i
                while j < hi and abs(res[j]) >= thr * 0.5 and ((res[j] > 0) == sign):
                    j += 1
                dur = j - i
                peak = float(np.max(np.abs(res[i:j]))) if j > i else 0.0
                if dur_min <= dur <= dur_max and thr <= peak <= 400.0:
                    # ① 「同じ音を保持している途中での一瞬の跳ね」だけを こぶし とみなす。
                    #    突出の前後がともに安定（保持された音）で、かつ同じ音高に戻ること。
                    #    片側でも揺れていれば（＝メロディが動いている＝音の移り変わり）除外。
                    pre_seg = seg[max(0, i - side_w):i]
                    post_seg = seg[j:j + side_w]
                    if len(pre_seg) >= 2 and len(post_seg) >= 2:
                        pre, post = float(np.median(pre_seg)), float(np.median(post_seg))
                        held = float(np.std(pre_seg)) < 22.0 and float(np.std(post_seg)) < 22.0
                        returned = held and abs(pre - post) <= return_tol
                    else:
                        returned = False
                    # ② 周辺の符号反転が多い区間（周期的＝ビブラート）は除外し、単発のみ採用。
                    a, b = max(lo, i - around_w), min(hi, j + around_w)
                    sig = np.sign(res[a:b][np.abs(res[a:b]) >= thr * 0.5])
                    flips = int(np.sum(np.abs(np.diff(sig)) > 0)) if len(sig) > 1 else 0
                    if returned and flips <= 2:
                        spots.append(round((s + i) * hop_sec, 1))
                i = j + dur_min
            else:
                i += 1
    merged: list[float] = []
    for t in sorted(spots):
        if not merged or t - merged[-1] >= 0.2:
            merged.append(t)
    return {"kobushi": merged[:5], "kobushi_count": len(merged)}


def _stable_holds(
    f0_hz: np.ndarray, s: int, e: int, hop_sec: float, min_frames: int,
    tol_cents: float = 70.0, min_f0: float = 100.0,
) -> list[tuple[int, int]]:
    """連続発声 [s, e) を「音程が一定(±tol_cents)に保たれた区間」に分割する。

    これにより、メロディ（音程が動く一節）を1つの"伸ばし"と誤認しなくなる。
    各区間が min_frames 以上（＝本物のロングトーン）のものだけ返す。
    """
    holds: list[tuple[int, int]] = []
    cur_start: int | None = None
    cur_hz: list[float] = []

    def flush(end_idx: int) -> None:
        if cur_start is not None and cur_hz and (end_idx - cur_start) >= min_frames:
            holds.append((cur_start, end_idx))

    for fi in range(s, e):
        v = f0_hz[fi]
        if np.isnan(v) or v < min_f0:
            flush(fi)
            cur_start, cur_hz = None, []
            continue
        if cur_start is None:
            cur_start, cur_hz = fi, [float(v)]
            continue
        med = float(np.median(cur_hz))
        if med > 0 and abs(1200.0 * np.log2(v / med)) > tol_cents:
            flush(fi)
            cur_start, cur_hz = fi, [float(v)]
        else:
            cur_hz.append(float(v))
    flush(e)
    return holds


def long_tone_stability(f0_hz: np.ndarray, hop_sec: float, min_dur_sec: float = 0.6) -> float | None:
    """本物の伸ばし（音程が一定に保たれた区間）の f0 揺れ(cents)平均。なければ None。"""
    mask = ~np.isnan(f0_hz) & (f0_hz > 0)
    f0_cents = hz_to_cents(f0_hz)
    min_frames = int(min_dur_sec / hop_sec)
    stds = []
    for run_s, run_e in _voiced_runs(mask):
        for s, e in _stable_holds(f0_hz, run_s, run_e, hop_sec, min_frames):
            seg = f0_cents[s:e]
            seg = seg[~np.isnan(seg)]
            if len(seg) < min_frames:
                continue
            stds.append(float(np.std(seg - np.median(seg))))
    return float(np.mean(stds)) if stds else None


def harmonic_ratio(
    y: np.ndarray, sr: int, f0_hz: np.ndarray, voiced_flag: np.ndarray, max_harmonics: int = 15
) -> float | None:
    """整数次倍音の豊かさ(0..1)。各有声フレームで f0 の整数倍(k*f0)に乗るエネルギー比。

    高い＝整数次倍音リッチ（クリアで芯のある・通る声）。
    低い＝非整数次倍音リッチ（息まじり・かすれ・ささやき寄りの柔らかい声）。
    """
    S = np.abs(librosa.stft(y, n_fft=FRAME_LENGTH, hop_length=HOP_LENGTH))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=FRAME_LENGTH)
    nyq = sr / 2.0
    n = min(S.shape[1], len(f0_hz))
    vals = []
    for i in range(n):
        f0 = f0_hz[i]
        if np.isnan(f0) or f0 < 80 or (i < len(voiced_flag) and not voiced_flag[i]):
            continue
        spec = S[:, i]
        total = float(np.sum(spec ** 2)) + 1e-9
        harm = 0.0
        for k in range(1, max_harmonics + 1):
            fk = k * f0
            if fk >= nyq:
                break
            band = spec[(freqs >= fk * 0.96) & (freqs <= fk * 1.04)]
            if band.size:
                harm += float(np.max(band)) ** 2
        vals.append(min(1.0, harm / total))
    return float(np.mean(vals)) if vals else None


def _voice_type(rolloff_to_f0: float | None) -> str | None:
    if rolloff_to_f0 is None:
        return None
    if rolloff_to_f0 >= 6.0:
        return "chest"
    if rolloff_to_f0 >= 4.0:
        return "mix"
    return "head"


# ---- 声区推定の精度向上（フォルマント＋スペクトル傾斜＋H1-H2 の併用）----

def _spectral_tilt(seg: np.ndarray, sr: int, lo: float = 300.0, hi: float = 4000.0) -> float | None:
    """対数スペクトルの傾き(dB/oct)。地声=浅い／裏声=急。声区の主指標。"""
    if len(seg) < 256:
        return None
    w = seg * np.hanning(len(seg))
    nfft = 1 << (int(np.ceil(np.log2(len(w)))) + 1)
    S = np.abs(np.fft.rfft(w, nfft))
    fr = np.fft.rfftfreq(nfft, 1.0 / sr)
    m = (fr >= lo) & (fr <= hi) & (S > 0)
    if int(np.count_nonzero(m)) < 8:
        return None
    slope = np.polyfit(np.log2(fr[m]), 20.0 * np.log10(S[m] + 1e-9), 1)[0]
    return float(slope)


def _h1_h2(seg: np.ndarray, sr: int, f0: float) -> float | None:
    """第1倍音と第2倍音の振幅差(dB)。声門開放率の指標。大=裏声寄り／小=地声寄り。"""
    if len(seg) < 256 or not f0 or f0 <= 0:
        return None
    w = seg * np.hanning(len(seg))
    nfft = 1 << (int(np.ceil(np.log2(len(w)))) + 1)
    S = np.abs(np.fft.rfft(w, nfft))
    fr = np.fft.rfftfreq(nfft, 1.0 / sr)

    def amp(fk: float):
        band = S[(fr >= fk * 0.85) & (fr <= fk * 1.15)]
        return 20.0 * np.log10(float(np.max(band)) + 1e-9) if band.size else None

    a1, a2 = amp(f0), amp(2.0 * f0)
    return (a1 - a2) if (a1 is not None and a2 is not None) else None


def _lpc_formants(seg: np.ndarray, sr: int, max_formants: int = 3) -> list[int]:
    """LPC（自己相関法）の根から共鳴周波数（フォルマント）を推定。帯域幅で絞る。"""
    if len(seg) < 256:
        return []
    order = int(2 + sr / 1000)
    x = seg - float(np.mean(seg))
    x = np.append(x[0], x[1:] - 0.63 * x[:-1])  # プリエンファシス
    x = x * np.hamming(len(x))
    if not np.any(x):
        return []
    try:
        a = librosa.lpc(x.astype(float), order=order)
    except Exception:
        return []
    roots = np.roots(a)
    roots = roots[np.imag(roots) >= 0.01]
    if roots.size == 0:
        return []
    ang = np.arctan2(np.imag(roots), np.real(roots))
    freqs = ang * (sr / (2.0 * np.pi))
    bws = -0.5 * (sr / (2.0 * np.pi)) * np.log(np.abs(roots) + 1e-12)
    cand = sorted((float(f), float(b)) for f, b in zip(freqs, bws) if 90.0 < f < 4000.0 and b < 400.0)
    return [int(round(f)) for f, _ in cand[:max_formants]]


def _segment_voice_features(y: np.ndarray, sr: int, s_frame: int, e_frame: int,
                            f0_hz: np.ndarray, max_frames: int = 10) -> dict:
    """伸ばし区間の声区特徴（傾斜・H1-H2・フォルマント）。区間内を間引いて中央値。"""
    if e_frame <= s_frame:
        return {}
    if e_frame - s_frame > max_frames:
        idxs = np.linspace(s_frame, e_frame - 1, max_frames).astype(int)
    else:
        idxs = np.arange(s_frame, e_frame)
    tilts, h1h2s, f1s, f2s, f3s = [], [], [], [], []
    for i in idxs:
        st = int(i) * HOP_LENGTH
        seg = y[st:st + FRAME_LENGTH]
        if len(seg) < FRAME_LENGTH // 2:
            continue
        t = _spectral_tilt(seg, sr)
        if t is not None:
            tilts.append(t)
        f0 = f0_hz[i] if i < len(f0_hz) else np.nan
        if not np.isnan(f0):
            hh = _h1_h2(seg, sr, float(f0))
            if hh is not None:
                h1h2s.append(hh)
        F = _lpc_formants(seg, sr)
        if len(F) >= 1:
            f1s.append(F[0])
        if len(F) >= 2:
            f2s.append(F[1])
        if len(F) >= 3:
            f3s.append(F[2])

    def med_i(a):
        return int(round(float(np.median(a)))) if a else None

    return {
        "spectral_tilt_db_oct": round(float(np.median(tilts)), 1) if tilts else None,
        "h1h2_db": round(float(np.median(h1h2s)), 1) if h1h2s else None,
        "formant_f1_hz": med_i(f1s),
        "formant_f2_hz": med_i(f2s),
        "formant_f3_hz": med_i(f3s),
    }


# 声区推定の票しきい値。各キューは chest 側 / head 側のカット。
# tools/calibrate_register.py でラベル付き音源から再較正できる（実データが集まり次第更新）。
#
# 現行値は実録音で検証済み（低音→地声・高音→ミックスと妥当）。合成コーパス較正で
# キューの向き（傾斜・H1-H2・ロールオフが声区順に単調）は確認したが、H1-H2/傾斜の
# 「絶対値」はマイク・母音・声分離でドメイン依存のため、合成の絶対しきい値はそのまま
# 転移しない（実録音ではむしろ悪化）。よって本番は実録音検証済みの値を維持し、
# 実ラベル音源が集まり次第ハーネスで較正する運用とする。詳細は docs/15。
REGISTER_THRESHOLDS = {
    # スペクトル傾斜(dB/oct): 値が大きい(浅い)ほど地声、小さい(急)ほど裏声
    "tilt_chest_ge": -6.0,
    "tilt_head_le": -11.0,
    # H1-H2(dB): 小さい/負ほど地声、大きいほど裏声
    "h1h2_chest_le": 2.0,
    "h1h2_head_ge": 8.0,
    # ロールオフ÷f0（補助・最も転移しやすい）
    "rolloff_chest_ge": 6.0,
    "rolloff_head_lt": 4.0,
}


def _register_vote(tilt: float | None, h1h2: float | None,
                   rolloff_ratio: float | None,
                   th: dict | None = None) -> tuple[str | None, str]:
    """傾斜・H1-H2・ロールオフ比の多数決で声区を推定。戻り: (label, confidence)。

    各票 chest=+1 / head=-1 / neutral=0。score>=2→chest, <=-2→head, それ以外→mix。
    confidence は票数と一致度から high/med/low。しきい値は REGISTER_THRESHOLDS（較正可能）。
    """
    th = th or REGISTER_THRESHOLDS
    votes: list[int] = []
    if tilt is not None:
        votes.append(1 if tilt >= th["tilt_chest_ge"] else (-1 if tilt <= th["tilt_head_le"] else 0))
    if h1h2 is not None:
        votes.append(1 if h1h2 <= th["h1h2_chest_le"] else (-1 if h1h2 >= th["h1h2_head_ge"] else 0))
    if rolloff_ratio is not None:
        votes.append(1 if rolloff_ratio >= th["rolloff_chest_ge"] else (-1 if rolloff_ratio < th["rolloff_head_lt"] else 0))
    if not votes:
        return None, "low"
    score = sum(votes)
    label = "chest" if score >= 2 else ("head" if score <= -2 else "mix")
    if len(votes) >= 2 and abs(score) >= 2:
        conf = "high"
    elif len(votes) >= 2:
        conf = "med"
    else:
        conf = "low"
    return label, conf


def _singers_formant_ratio(y: np.ndarray, sr: int,
                           voiced_flag: np.ndarray | None = None) -> float | None:
    """歌手フォルマント帯(2.8–3.4kHz)のエネルギー比。高い＝前に通る・芯のある共鳴。

    無音やブレスを含めると薄まるため、有声フレームのみで集計する。
    """
    S = np.abs(librosa.stft(y, n_fft=FRAME_LENGTH, hop_length=HOP_LENGTH)) ** 2
    fr = librosa.fft_frequencies(sr=sr, n_fft=FRAME_LENGTH)
    if voiced_flag is not None and len(voiced_flag) > 0:
        m = np.zeros(S.shape[1], dtype=bool)
        n = min(len(voiced_flag), S.shape[1])
        m[:n] = voiced_flag[:n].astype(bool)
        if m.any():
            S = S[:, m]
    band = (fr >= 2800) & (fr <= 3400)
    total = float(np.sum(S)) + 1e-9
    if total <= 1e-8:
        return None
    return round(float(np.sum(S[band])) / total, 4)


def extract_timeline(y, sr, f0_hz, voiced_flag, hop_sec, window_sec=1.0, sustain_min_sec=0.6) -> dict:
    rms = librosa.feature.rms(y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
    rolloff85 = librosa.feature.spectral_rolloff(
        y=y, sr=sr, hop_length=HOP_LENGTH, roll_percent=0.85
    )[0]
    # STFTのパディング等で末尾フレームが実時間を超えうるので、秒数は録音長でクランプする
    total_dur = len(y) / sr

    per_window = []
    wf = max(1, int(window_sec / hop_sec))
    for sf in range(0, len(voiced_flag), wf):
        ef = min(sf + wf, len(voiced_flag))
        seg_voiced = voiced_flag[sf:ef]
        seg_f0 = f0_hz[sf:ef]
        seg_f0v = seg_f0[~np.isnan(seg_f0)]
        seg_rms = rms[sf:ef] if sf < len(rms) else np.array([])
        seg_cent = centroid[sf:ef] if sf < len(centroid) else np.array([])
        seg_roll = rolloff85[sf:ef] if sf < len(rolloff85) else np.array([])
        per_window.append({
            "t_sec": round(sf * hop_sec, 1),
            "voiced_ratio": round(float(np.mean(seg_voiced)), 2),
            "f0_mean_hz": round(float(np.mean(seg_f0v)), 1) if len(seg_f0v) else None,
            "rms_db": round(float(20 * np.log10(np.mean(seg_rms) + 1e-9)), 1) if len(seg_rms) else None,
            "spectral_centroid_hz": round(float(np.mean(seg_cent)), 0) if len(seg_cent) else None,
            "spectral_rolloff85_hz": round(float(np.mean(seg_roll)), 0) if len(seg_roll) else None,
        })

    # 「伸ばし」= 連続発声の中で、さらに音程が一定に保たれた区間だけを抽出する。
    # （メロディの一節を1つの伸ばしと誤認しないため）
    sustained = []
    min_frames = max(1, int(sustain_min_sec / hop_sec))
    for run_s, run_e in _voiced_runs(voiced_flag):
        for s, e in _stable_holds(f0_hz, run_s, run_e, hop_sec, min_frames):
            seg = f0_hz[s:e]
            valid = seg[~np.isnan(seg)]
            if len(valid) < min_frames:
                continue
            cents = hz_to_cents(valid)
            f0_std_cents = float(np.std(cents - np.median(cents)))
            q = max(1, len(valid) // 4)
            head_med = float(np.median(valid[:q]))
            tail_med = float(np.median(valid[-q:]))
            end_drift = round(1200 * float(np.log2(tail_med / head_med)), 1) if head_med > 0 else None
            cent_seg = centroid[s:min(e, len(centroid))]
            cent_avg = float(np.mean(cent_seg)) if len(cent_seg) else None
            roll_seg = rolloff85[s:min(e, len(rolloff85))]
            roll_avg = float(np.mean(roll_seg)) if len(roll_seg) else None
            # 伸ばし内の音量減衰（前半→後半）。息の支え判定に使う。
            rms_decay_db = None
            rseg = rms[s:min(e, len(rms))]
            if len(rseg) >= 2:
                rq = max(1, len(rseg) // 4)
                head_db = float(20 * np.log10(np.mean(rseg[:rq]) + 1e-9))
                tail_db = float(20 * np.log10(np.mean(rseg[-rq:]) + 1e-9))
                rms_decay_db = round(tail_db - head_db, 1)
            mean_f0 = float(np.mean(valid))
            ratio = roll_avg / mean_f0 if (mean_f0 > 0 and roll_avg) else None
            start_t = round(min(s * hop_sec, total_dur), 2)
            end_t = round(min(e * hop_sec, total_dur), 2)
            # 声区の精度向上: フォルマント＋スペクトル傾斜＋H1-H2 を併用して多数決
            vfeat = _segment_voice_features(y, sr, s, e, f0_hz)
            register, reg_conf = _register_vote(
                vfeat.get("spectral_tilt_db_oct"), vfeat.get("h1h2_db"), ratio
            )
            sustained.append({
                "start_sec": start_t,
                "end_sec": end_t,
                "duration_sec": round(end_t - start_t, 2),
                "mean_f0_hz": round(mean_f0, 1),
                "f0_std_cents": round(f0_std_cents, 1),
                "end_drift_cents": end_drift,
                "rms_decay_db": rms_decay_db,
                "spectral_centroid_hz": round(cent_avg, 0) if cent_avg else None,
                "spectral_rolloff85_hz": round(roll_avg, 0) if roll_avg else None,
                "rolloff_to_f0_ratio": round(ratio, 2) if ratio else None,
                "spectral_tilt_db_oct": vfeat.get("spectral_tilt_db_oct"),
                "h1h2_db": vfeat.get("h1h2_db"),
                "formant_f1_hz": vfeat.get("formant_f1_hz"),
                "formant_f2_hz": vfeat.get("formant_f2_hz"),
                "formant_f3_hz": vfeat.get("formant_f3_hz"),
                "register": register,
                "register_confidence": reg_conf,
                # 後方互換: 既存コードは voice_type_estimate を参照する
                "voice_type_estimate": register or _voice_type(ratio),
            })

    return {"window_sec": window_sec, "per_window": per_window, "sustained_segments": sustained}


def load_clip(path: str | Path, start_sec: float | None = None, end_sec: float | None = None,
              isolate_vocal: bool = False) -> tuple[np.ndarray, int]:
    """Load an audio clip (optionally vocal-isolated). Returns (y, sr)."""
    offset = start_sec if start_sec is not None else 0.0
    if end_sec is not None:
        if start_sec is not None and end_sec <= start_sec:
            raise ValueError(f"end_sec ({end_sec}) must be > start_sec ({start_sec})")
        load_duration = end_sec - offset
    else:
        load_duration = None
    # 解析時間の上限（応答10秒以内を守るため、長尺は先頭 MAX_ANALYSIS_SEC 秒に丸める）
    if load_duration is None or load_duration > MAX_ANALYSIS_SEC:
        load_duration = MAX_ANALYSIS_SEC
    y, sr = librosa.load(str(path), sr=SR, mono=True, offset=offset, duration=load_duration)
    if isolate_vocal and len(y) > sr:  # >1s のときだけ分離
        from app.audio.separation import isolate_vocal as _iso
        y = _iso(y, sr)
    return y, sr


def build_pitch_contour(f0_hz: np.ndarray, voiced_flag: np.ndarray | None,
                        hop_sec: float, max_points: int = 180) -> dict | None:
    """歌の音程の流れ（DAM風の音程バー用）。f0をMIDIノート番号に変換した時系列。

    有声フレームのみ値を持ち、無声部は None（フレーズの切れ目）。
    max_points 個までに間引いて軽量化（各バケツの中央値）。t=k*dt 秒の点列。
    """
    n = len(f0_hz)
    if n == 0:
        return None
    valid = (~np.isnan(f0_hz)) & (f0_hz > 0)
    if voiced_flag is not None and len(voiced_flag) >= n:
        valid = valid & voiced_flag[:n].astype(bool)
    if not bool(np.any(valid)):
        return None
    midi = np.full(n, np.nan)
    midi[valid] = 69.0 + 12.0 * np.log2(f0_hz[valid] / 440.0)
    step = max(1, int(np.ceil(n / max_points)))
    out: list[float | None] = []
    for k in range(0, n, step):
        seg = midi[k:k + step]
        seg = seg[~np.isnan(seg)]
        out.append(round(float(np.median(seg)), 2) if len(seg) else None)
    return {"t0": 0.0, "dt": round(step * hop_sec, 3), "midi": out}


def analyze_file(path: str | Path, start_sec: float | None = None, end_sec: float | None = None,
                 isolate_vocal: bool = False, return_signal: bool = False, light: bool = False):
    """Analyze a single audio clip and return a metrics dict (+ timeline).

    isolate_vocal: 原曲など伴奏混在音源で True にすると軽量声分離を前処理する。
    return_signal: True なら (result_dict, y, sr, f0_hz, voiced_flag) を返す（DTW用に再利用）。
    light: True で原曲(お手本)向けの軽量解析。比較に使わない重い処理
        （タイムライン/フォルマント/共鳴/装飾/音程バー）を省いて応答を速くする。
    """
    y, sr = load_clip(path, start_sec, end_sec, isolate_vocal=isolate_vocal)
    duration = float(librosa.get_duration(y=y, sr=sr))
    if duration < 0.3:
        raise ValueError("audio too short to analyze (<0.3s)")

    f0_hz, voiced_flag, _ = librosa.pyin(
        y, fmin=FMIN_HZ, fmax=FMAX_HZ, sr=sr, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH
    )
    hop_sec = HOP_LENGTH / sr
    voiced_ratio = float(np.mean(voiced_flag))

    voiced_f0 = f0_hz[voiced_flag]
    voiced_f0 = voiced_f0[~np.isnan(voiced_f0)]
    if len(voiced_f0) > 0:
        f0_median = float(np.median(voiced_f0))
        cents = hz_to_cents(voiced_f0)
        d = np.abs(np.diff(cents))
        # フレーム間隔が広いほど隣接フレーム差は大きく出るので、基準ホップへ正規化して
        # 「揺れの少なさ」の閾値（◎≤6cents 等）をホップ非依存に保つ。
        f0_jitter = (float(np.median(d)) * (JITTER_REF_HOP / HOP_LENGTH)) if len(d) > 0 else None
    else:
        f0_median = None
        f0_jitter = None

    key, mode = estimate_key(y, sr)
    tempo_arr, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP_LENGTH)
    tempo = float(tempo_arr) if np.ndim(tempo_arr) == 0 else float(tempo_arr[0])
    onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=HOP_LENGTH, units="time")
    onset_rate = len(onsets) / duration if duration > 0 else 0.0

    rms_full = librosa.feature.rms(y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)[0]
    rms = rms_full[rms_full > 1e-6]
    if len(rms) > 0:
        rms_db = 20 * np.log10(rms)
        rms_mean = float(np.mean(rms))
        rms_crest_db = float(20 * np.log10(np.max(rms) / (np.mean(rms) + 1e-9)))
        # 「強弱の幅」は“歌っている部分”の音量差。無音・ブレス（ピークより35dB以上小さい
        # フレーム）を除外しないと、無音→最大音 の差になって過大評価される。
        # 可能なら有声フレームに限定し、さらにピーク基準の床で無音を落とす。
        vmask = None
        if voiced_flag is not None and len(voiced_flag) > 0:
            n = min(len(voiced_flag), len(rms_full))
            vm = np.zeros(len(rms_full), dtype=bool)
            vm[:n] = voiced_flag[:n].astype(bool)
            vmask = vm & (rms_full > 1e-6)
        sung_db = rms_db if vmask is None or vmask.sum() < 4 else 20 * np.log10(rms_full[vmask])
        peak = float(np.percentile(sung_db, 99))
        sung_db = sung_db[sung_db > peak - 35.0]  # 無音・ブレスを除外
        if len(sung_db) >= 4:
            rms_db_range = float(np.percentile(sung_db, 95) - np.percentile(sung_db, 5))
        else:
            rms_db_range = float(np.percentile(rms_db, 95) - np.percentile(rms_db, 5))
    else:
        rms_mean = rms_db_range = rms_crest_db = 0.0

    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
    centroid_mean = float(np.mean(centroid))

    # vibrato / long-tone は f0 だけで安価に出るので light でも算出（compareで使う）
    vib_rate, vib_depth = detect_vibrato(f0_hz, hop_sec)
    lts = long_tone_stability(f0_hz, hop_sec)

    if light:
        # 原曲(お手本)向け: 比較に使わない重い処理を省略（応答時間短縮）
        harm = None
        ornaments = {"scoops": [], "falls": [], "scoop_count": 0, "fall_count": 0,
                     "kobushi": [], "kobushi_count": 0}
        timeline = {"per_window": [], "sustained_segments": []}
        formant_f1 = formant_f2 = spectral_tilt = singers_formant = None
        pitch_contour = None
    else:
        harm = harmonic_ratio(y, sr, f0_hz, voiced_flag)
        ornaments = detect_ornaments(f0_hz, voiced_flag, hop_sec)
        ornaments.update(detect_kobushi(f0_hz, voiced_flag, hop_sec))
        timeline = extract_timeline(y, sr, f0_hz, voiced_flag, hop_sec)
        # 声区/共鳴の全体集計（伸ばし区間のフォルマント・傾斜の中央値＋歌手フォルマント比）
        _segs = timeline.get("sustained_segments", [])
        def _seg_med(key):
            vals = [s[key] for s in _segs if s.get(key) is not None]
            return round(float(np.median(vals)), 1) if vals else None
        formant_f1 = _seg_med("formant_f1_hz")
        formant_f2 = _seg_med("formant_f2_hz")
        spectral_tilt = _seg_med("spectral_tilt_db_oct")
        singers_formant = _singers_formant_ratio(y, sr, voiced_flag)
        pitch_contour = build_pitch_contour(f0_hz, voiced_flag, hop_sec)

    result = {
        "duration_sec": round(duration, 2),
        "voiced_ratio": round(voiced_ratio, 3),
        "f0_median_hz": round(f0_median, 1) if f0_median else None,
        "f0_jitter_cents": round(f0_jitter, 1) if f0_jitter else None,
        "estimated_key": f"{key} {mode}",
        "estimated_mode": mode,
        "tempo_bpm": round(tempo, 1),
        "onset_rate_per_sec": round(onset_rate, 2),
        "rms_mean": round(rms_mean, 4),
        "rms_db_range": round(rms_db_range, 1),
        "rms_crest_db": round(rms_crest_db, 1),
        "spectral_centroid_hz": round(centroid_mean, 0),
        "vibrato_rate_hz": round(vib_rate, 2) if vib_rate else None,
        "vibrato_depth_cents": round(vib_depth, 1) if vib_depth else None,
        "expression_ornaments": ornaments,
        "long_tone_stability": round(lts, 1) if lts else None,
        "harmonic_ratio": round(harm, 3) if harm is not None else None,
        "formant_f1_hz": formant_f1,
        "formant_f2_hz": formant_f2,
        "spectral_tilt_db_oct": spectral_tilt,
        "singers_formant_ratio": singers_formant,
        "timeline": timeline,
        "pitch_contour": build_pitch_contour(f0_hz, voiced_flag, hop_sec),
        "vocal_isolated": bool(isolate_vocal),
    }
    if return_signal:
        # f0/voiced も返す（DTWアライメント側で pyin を再計算しないため＝高速化）
        return result, y, sr, f0_hz, voiced_flag
    return result


def warmup() -> None:
    """numba(pyin)・chroma・DTW・HPSS を起動時に一度走らせて JITコンパイルを済ませておく。

    numba の JIT はプロセス単位なので、各ワーカーで一度実行して初回リクエストの
    コールド遅延（〜+6秒）を無くす。
    """
    import logging
    import tempfile
    import time as _time
    log = logging.getLogger("uvicorn.error")
    try:
        import soundfile as sf
    except Exception as e:
        log.warning("warmup skip (soundfile不可): %s", e)
        return
    t0 = _time.time()
    try:
        dur = 2.5
        t = np.linspace(0, dur, int(SR * dur), endpoint=False)
        a = (0.5 * np.sin(2 * np.pi * 220 * t) + 0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        b = (0.5 * np.sin(2 * np.pi * 247 * t) + 0.2 * np.sin(2 * np.pi * 494 * t)).astype(np.float32)
        d = tempfile.mkdtemp(prefix="warmup_")
        pa, pb = f"{d}/a.wav", f"{d}/b.wav"
        sf.write(pa, a, SR)
        sf.write(pb, b, SR)
        analyze_file(pa)
        analyze_pair(pa, pb)
        log.info("analyzer warmup done in %.1fs", _time.time() - t0)
    except Exception as e:
        log.warning("warmup failed in %.1fs: %s", _time.time() - t0, e)


def analyze_pair(user_path, ref_path, user_range=None, ref_range=None):
    """ユーザー録音と原曲（声分離）を解析し、compare + DTWアライメントを付与して返す。

    返り値: {"user": ..., "reference": ..., "compare": ..., "alignment": ...}
    """
    from concurrent.futures import ThreadPoolExecutor

    from app.audio import alignment as _align

    u_start, u_end = user_range or (None, None)
    r_start, r_end = ref_range or (None, None)

    # ユーザーと原曲の解析は独立なので並列実行（2コアで重なり、応答時間を短縮）。
    # 原曲は light=True（比較に使わない重い処理を省略）。
    with ThreadPoolExecutor(max_workers=2) as _ex:
        fu = _ex.submit(analyze_file, user_path, u_start, u_end,
                        isolate_vocal=False, return_signal=True)
        fr = _ex.submit(analyze_file, ref_path, r_start, r_end,
                        isolate_vocal=True, return_signal=True, light=True)
        user, uy, usr, u_f0, _u_vf = fu.result()
        ref, ry, rsr, r_f0, _r_vf = fr.result()

    out = {"user": user, "reference": ref, "compare": compare(user, ref)}
    try:
        # 解析済みの f0 を渡してアライメント側の pyin 再計算を省く（応答時間短縮）
        out["alignment"] = _align.align(uy, ry, usr, user_f0=u_f0, ref_f0=r_f0)
    except Exception:
        out["alignment"] = None
    return out


def compare(user: dict, ref: dict) -> dict:
    def to_semitones(hz, ref_hz):
        if not hz or not ref_hz:
            return None
        return round(12 * float(np.log2(hz / ref_hz)), 2)

    def diff(a, b, ndigits=1):
        if a is None or b is None:
            return None
        return round(a - b, ndigits)

    return {
        "duration_diff_sec": diff(user["duration_sec"], ref["duration_sec"], 2),
        "key_match": user["estimated_key"] == ref["estimated_key"],
        "user_key": user["estimated_key"],
        "ref_key": ref["estimated_key"],
        "f0_median_diff_semitones": to_semitones(user["f0_median_hz"], ref["f0_median_hz"]),
        "tempo_diff_bpm": diff(user["tempo_bpm"], ref["tempo_bpm"]),
        "voiced_ratio_diff": diff(user["voiced_ratio"], ref["voiced_ratio"], 3),
        "rms_db_range_diff": diff(user["rms_db_range"], ref["rms_db_range"]),
        "ref_rms_db_range": ref.get("rms_db_range"),  # 原曲の抑揚量（原曲基準で抑揚を評価するため）
        "long_tone_stability_diff_cents": diff(user["long_tone_stability"], ref["long_tone_stability"]),
        "vibrato_rate_diff_hz": diff(user["vibrato_rate_hz"], ref["vibrato_rate_hz"], 2),
        "vibrato_depth_diff_cents": diff(user["vibrato_depth_cents"], ref["vibrato_depth_cents"]),
        "spectral_centroid_diff_hz": diff(user["spectral_centroid_hz"], ref["spectral_centroid_hz"], 0),
        "onset_rate_diff": diff(user["onset_rate_per_sec"], ref["onset_rate_per_sec"], 2),
        # 原曲(お手本)側の実値。ビブラート提案を「原曲にビブラートがある時だけ」にするため。
        "ref_vibrato_rate_hz": ref.get("vibrato_rate_hz"),
        "ref_vibrato_depth_cents": ref.get("vibrato_depth_cents"),
    }


def is_same_source(user: dict, ref: dict) -> bool:
    """主要指標がほぼ一致したら同一音源とみなす（簡易ヒューリスティック）。"""
    if user["f0_median_hz"] is None or ref["f0_median_hz"] is None:
        return False
    checks = [
        abs((user["f0_median_hz"] or 0) - (ref["f0_median_hz"] or 0)) < 0.6,
        user["estimated_key"] == ref["estimated_key"],
        abs((user["tempo_bpm"] or 0) - (ref["tempo_bpm"] or 0)) < 0.6,
        abs((user["voiced_ratio"] or 0) - (ref["voiced_ratio"] or 0)) < 0.02,
        abs((user["spectral_centroid_hz"] or 0) - (ref["spectral_centroid_hz"] or 0)) < 5,
    ]
    return all(checks)
