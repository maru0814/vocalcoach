"""
Audio analyzer for vocal-trainer skill.

ユーザー録音と原曲（リファレンス）の wav を入力に取り、
発声・リズム・音感・表現の4軸で解析・比較する JSON を出力する。

使い方:
    python tools/audio_analyzer.py <user.wav> [<reference.wav>] \
        [--user-start 0:15] [--user-end 0:45] \
        [--ref-start 1:30] [--ref-end 2:00] \
        [--isolate-vocal-ref]

時間指定は "mm:ss" または秒数（"15", "1.5"）のいずれかを受け付ける。
指定しない場合はトラック全体を解析する。
--isolate-vocal-ref を付けると原曲に軽量声分離(HPSS+帯域)を適用し、
伴奏(ベース)由来の f0/キー誤判定を緩和。2音源指定時は DTW アライメントも出力。

依存:
    librosa, numpy, scipy, soundfile
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import librosa
import numpy as np


SR = 22050
HOP_LENGTH = 512
FRAME_LENGTH = 2048
FMIN_HZ = 65.0    # ~C2
FMAX_HZ = 1000.0  # ~B5
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class TrackAnalysis:
    duration_sec: float
    voiced_ratio: float                # voiced frames / total frames
    f0_median_hz: float | None         # median of voiced f0
    f0_jitter_cents: float | None      # frame-to-frame std of f0 (cents) within voiced
    estimated_key: str                 # e.g. "C major" via chroma argmax
    estimated_mode: str                # "major" or "minor"
    tempo_bpm: float
    onset_rate_per_sec: float          # onsets per second
    rms_mean: float                    # mean loudness
    rms_db_range: float                # 95th - 5th percentile, in dB
    rms_crest_db: float                # peak / mean in dB
    spectral_centroid_hz: float        # brightness proxy
    vibrato_rate_hz: float | None      # detected oscillation rate in f0
    vibrato_depth_cents: float | None  # depth of f0 oscillation
    long_tone_stability: float | None  # avg f0 std within sustained notes (cents)


def hz_to_cents(hz: np.ndarray, ref_hz: float = 440.0) -> np.ndarray:
    """Convert Hz to cents above ref."""
    pos = hz > 0
    out = np.full_like(hz, np.nan, dtype=float)
    out[pos] = 1200.0 * np.log2(hz[pos] / ref_hz)
    return out


def estimate_key(y: np.ndarray, sr: int) -> tuple[str, str]:
    """Estimate musical key via chroma + Krumhansl-Schmuckler-style template."""
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP_LENGTH)
    mean_chroma = chroma.mean(axis=1)

    # Krumhansl key profiles (normalized)
    major_profile = np.array(
        [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    )
    minor_profile = np.array(
        [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    )

    best_score = -np.inf
    best_key = "C"
    best_mode = "major"
    for shift in range(12):
        rotated_major = np.roll(major_profile, shift)
        rotated_minor = np.roll(minor_profile, shift)
        s_major = np.corrcoef(mean_chroma, rotated_major)[0, 1]
        s_minor = np.corrcoef(mean_chroma, rotated_minor)[0, 1]
        if s_major > best_score:
            best_score = s_major
            best_key = PITCH_CLASSES[shift]
            best_mode = "major"
        if s_minor > best_score:
            best_score = s_minor
            best_key = PITCH_CLASSES[shift]
            best_mode = "minor"
    return best_key, best_mode


def detect_vibrato(f0_hz: np.ndarray, hop_sec: float) -> tuple[float | None, float | None]:
    """Detect vibrato rate (Hz) and depth (cents) in voiced regions.

    Returns (rate_hz, depth_cents). None if no clear vibrato.
    """
    voiced_mask = ~np.isnan(f0_hz) & (f0_hz > 0)
    if voiced_mask.sum() < 50:
        return None, None

    # Convert to cents (relative to running median, to remove pitch drift)
    f0_cents = hz_to_cents(f0_hz)

    # Take longest contiguous voiced segment
    diffs = np.diff(voiced_mask.astype(int))
    starts = np.where(diffs == 1)[0] + 1
    ends = np.where(diffs == -1)[0] + 1
    if voiced_mask[0]:
        starts = np.insert(starts, 0, 0)
    if voiced_mask[-1]:
        ends = np.append(ends, len(voiced_mask))
    if len(starts) == 0 or len(ends) == 0:
        return None, None
    seg_lengths = ends - starts
    longest_idx = int(np.argmax(seg_lengths))
    seg = f0_cents[starts[longest_idx] : ends[longest_idx]]
    seg = seg[~np.isnan(seg)]
    if len(seg) < 50:
        return None, None

    # Remove slow drift (running median 0.5s window)
    win = max(3, int(0.5 / hop_sec))
    if win % 2 == 0:
        win += 1
    drift = np.array(
        [np.median(seg[max(0, i - win // 2) : i + win // 2 + 1]) for i in range(len(seg))]
    )
    centered = seg - drift

    # FFT for dominant oscillation
    fs = 1.0 / hop_sec
    spectrum = np.abs(np.fft.rfft(centered - centered.mean()))
    freqs = np.fft.rfftfreq(len(centered), d=hop_sec)
    # vibrato typically 4-8 Hz
    mask = (freqs >= 3.0) & (freqs <= 10.0)
    if not mask.any() or spectrum[mask].size == 0:
        return None, None
    peak_idx_in_mask = int(np.argmax(spectrum[mask]))
    peak_freq = float(freqs[mask][peak_idx_in_mask])
    peak_power = float(spectrum[mask][peak_idx_in_mask])

    # Check if peak is significant (>2x neighborhood median)
    median_power = float(np.median(spectrum[mask]))
    if median_power == 0 or peak_power < median_power * 2.0:
        return None, None

    depth_cents = float(np.std(centered))
    return peak_freq, depth_cents


def long_tone_stability(f0_hz: np.ndarray, hop_sec: float, min_dur_sec: float = 0.6) -> float | None:
    """Avg f0 std (cents) within sustained voiced segments of >= min_dur_sec.

    Lower = more stable.
    """
    voiced_mask = ~np.isnan(f0_hz) & (f0_hz > 0)
    f0_cents = hz_to_cents(f0_hz)

    diffs = np.diff(voiced_mask.astype(int))
    starts = np.where(diffs == 1)[0] + 1
    ends = np.where(diffs == -1)[0] + 1
    if voiced_mask[0]:
        starts = np.insert(starts, 0, 0)
    if voiced_mask[-1]:
        ends = np.append(ends, len(voiced_mask))

    min_frames = int(min_dur_sec / hop_sec)
    stds = []
    for s, e in zip(starts, ends):
        if e - s < min_frames:
            continue
        seg = f0_cents[s:e]
        seg = seg[~np.isnan(seg)]
        if len(seg) < min_frames:
            continue
        # detrend
        seg = seg - np.median(seg)
        stds.append(float(np.std(seg)))
    if not stds:
        return None
    return float(np.mean(stds))


def parse_time(value: str | None) -> float | None:
    """Parse 'mm:ss', 'm:ss', or a numeric string as seconds. Returns None for None/empty."""
    if value is None or value == "":
        return None
    if ":" in value:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError(f"invalid time format: {value!r}, expected mm:ss")
        m, s = parts
        return int(m) * 60 + float(s)
    return float(value)


def isolate_vocal(y: np.ndarray, sr: int, hard_cut_hz: float = 130.0,
                  low_hz: float = 200.0, high_hz: float = 5000.0, margin: float = 3.0) -> np.ndarray:
    """HPSS + ボーカル帯域強調で伴奏を抑える（torch不要の軽量分離）。"""
    n_fft, hop = 2048, 512
    S_full, phase = librosa.magphase(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    H, P = librosa.decompose.hpss(S_full, margin=margin)
    S_harm = S_full * (H / (H + P + 1e-8))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    band = np.ones_like(freqs)
    band[freqs < hard_cut_hz] = 0.02
    ramp = (freqs >= hard_cut_hz) & (freqs < low_hz)
    band[ramp] = 0.02 + 0.98 * (freqs[ramp] - hard_cut_hz) / (low_hz - hard_cut_hz)
    band[freqs > high_hz] = 0.4
    y_voc = librosa.istft(S_harm * band[:, np.newaxis] * phase, hop_length=hop, length=len(y))
    peak = np.max(np.abs(y_voc)) + 1e-9
    return (y_voc / peak * (np.max(np.abs(y)) + 1e-9)).astype(np.float32)


def align_dtw(user_y, ref_y, sr, lag_threshold_sec=0.25, max_segments=3):
    """ユーザーと原曲のクロマ系列を DTW で対応付け、フレーズずれを秒数で抽出。"""
    hop_sec = HOP_LENGTH / sr
    if len(user_y) / sr < 3 or len(ref_y) / sr < 3:
        return None
    ratio = (len(user_y) / sr) / (len(ref_y) / sr)
    if ratio < 0.5 or ratio > 2.0:
        return None
    cu = librosa.feature.chroma_cqt(y=user_y, sr=sr, hop_length=HOP_LENGTH)
    cr = librosa.feature.chroma_cqt(y=ref_y, sr=sr, hop_length=HOP_LENGTH)
    if cu.shape[1] < 8 or cr.shape[1] < 8:
        return None
    try:
        _, wp = librosa.sequence.dtw(X=cu, Y=cr, metric="cosine")
    except Exception:
        return None
    wp = wp[::-1]
    n = len(wp)
    if n < 10:
        return None
    lo, hi = int(n * 0.1), int(n * 0.9)
    user_t = wp[lo:hi, 0] * hop_sec
    ref_t = wp[lo:hi, 1] * hop_sec
    rel_lag = (user_t - ref_t) - np.median(user_t - ref_t)
    worst, seen = [], set()
    for idx in np.argsort(-np.abs(rel_lag)):
        l = float(rel_lag[idx])
        if abs(l) < lag_threshold_sec:
            break
        b = int(user_t[idx])
        if b in seen:
            continue
        seen.add(b)
        worst.append({"user_sec": round(float(user_t[idx]), 1),
                      "ref_sec": round(float(ref_t[idx]), 1), "lag_sec": round(l, 2)})
        if len(worst) >= max_segments:
            break
    worst.sort(key=lambda w: w["user_sec"])
    return {"mean_lag_sec": round(float(np.mean(rel_lag)), 2), "worst_segments": worst}


def extract_timeline(
    y: np.ndarray,
    sr: int,
    f0_hz: np.ndarray,
    voiced_flag: np.ndarray,
    hop_sec: float,
    window_sec: float = 1.0,
    sustain_min_sec: float = 0.6,
) -> dict:
    """Per-second metrics and sustained-note segments (with start/end seconds).

    All seconds are clip-relative (i.e. 0 = first frame of the loaded clip).
    Callers can add the analysis offset back to get absolute song timestamps.
    """
    rms = librosa.feature.rms(y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
    rolloff85 = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=HOP_LENGTH, roll_percent=0.85)[0]

    per_window = []
    window_frames = max(1, int(window_sec / hop_sec))
    for start_frame in range(0, len(voiced_flag), window_frames):
        end_frame = min(start_frame + window_frames, len(voiced_flag))
        seg_voiced = voiced_flag[start_frame:end_frame]
        seg_f0 = f0_hz[start_frame:end_frame]
        seg_f0_valid = seg_f0[~np.isnan(seg_f0)]
        seg_rms = rms[start_frame:end_frame] if start_frame < len(rms) else np.array([])
        seg_centroid = centroid[start_frame:end_frame] if start_frame < len(centroid) else np.array([])
        seg_rolloff = rolloff85[start_frame:end_frame] if start_frame < len(rolloff85) else np.array([])
        per_window.append({
            "t_sec": round(start_frame * hop_sec, 1),
            "voiced_ratio": round(float(np.mean(seg_voiced)), 2),
            "f0_mean_hz": round(float(np.mean(seg_f0_valid)), 1) if len(seg_f0_valid) else None,
            "rms_db": (
                round(float(20 * np.log10(np.mean(seg_rms) + 1e-9)), 1)
                if len(seg_rms) else None
            ),
            "spectral_centroid_hz": (
                round(float(np.mean(seg_centroid)), 0) if len(seg_centroid) else None
            ),
            "spectral_rolloff85_hz": (
                round(float(np.mean(seg_rolloff)), 0) if len(seg_rolloff) else None
            ),
        })

    # Sustained voiced segments (≥ sustain_min_sec)
    sustained = []
    diffs = np.diff(voiced_flag.astype(int))
    starts = np.where(diffs == 1)[0] + 1
    ends = np.where(diffs == -1)[0] + 1
    if voiced_flag[0]:
        starts = np.insert(starts, 0, 0)
    if voiced_flag[-1]:
        ends = np.append(ends, len(voiced_flag))
    min_frames = max(1, int(sustain_min_sec / hop_sec))
    for s, e in zip(starts, ends):
        if e - s < min_frames:
            continue
        seg = f0_hz[s:e]
        valid = seg[~np.isnan(seg)]
        if len(valid) < min_frames:
            continue
        cents = hz_to_cents(valid)
        cents_detrended = cents - np.median(cents)
        f0_std_cents = float(np.std(cents_detrended))
        # End drift: median of last 25% vs first 25% (in cents)
        q = max(1, len(valid) // 4)
        head_med = float(np.median(valid[:q]))
        tail_med = float(np.median(valid[-q:]))
        end_drift_cents = (
            round(1200 * float(np.log2(tail_med / head_med)), 1) if head_med > 0 else None
        )
        # Spectral centroid / rolloff over this segment
        cent_seg = centroid[s : min(e, len(centroid))]
        cent_avg = float(np.mean(cent_seg)) if len(cent_seg) > 0 else None
        roll_seg = rolloff85[s : min(e, len(rolloff85))]
        roll_avg = float(np.mean(roll_seg)) if len(roll_seg) > 0 else None

        # Voice type heuristic: rolloff85 / mean_f0 ratio
        # 純粋地声(chest): 6-10倍 / ミックス(mix): 4-6倍 / 純粋裏声(head): 2-4倍
        mean_f0 = float(np.mean(valid))
        voice_type = None
        rolloff_to_f0 = None
        if mean_f0 > 0 and roll_avg:
            rolloff_to_f0 = roll_avg / mean_f0
            if rolloff_to_f0 >= 6.0:
                voice_type = "chest"
            elif rolloff_to_f0 >= 4.0:
                voice_type = "mix"
            else:
                voice_type = "head"

        sustained.append({
            "start_sec": round(s * hop_sec, 2),
            "end_sec": round(e * hop_sec, 2),
            "duration_sec": round((e - s) * hop_sec, 2),
            "mean_f0_hz": round(mean_f0, 1),
            "f0_std_cents": round(f0_std_cents, 1),
            "end_drift_cents": end_drift_cents,
            "spectral_centroid_hz": round(cent_avg, 0) if cent_avg else None,
            "spectral_rolloff85_hz": round(roll_avg, 0) if roll_avg else None,
            "rolloff_to_f0_ratio": round(rolloff_to_f0, 2) if rolloff_to_f0 else None,
            "voice_type_estimate": voice_type,
        })

    return {
        "window_sec": window_sec,
        "per_window": per_window,
        "sustained_segments": sustained,
    }


def analyze_track(path: Path, start_sec: float | None = None, end_sec: float | None = None,
                  isolate: bool = False, return_signal: bool = False):
    # librosa.load supports offset & duration for partial loading
    offset = start_sec if start_sec is not None else 0.0
    if end_sec is not None:
        if start_sec is not None and end_sec <= start_sec:
            raise ValueError(f"end_sec ({end_sec}) must be > start_sec ({start_sec})")
        load_duration = end_sec - offset
    else:
        load_duration = None
    y, sr = librosa.load(str(path), sr=SR, mono=True, offset=offset, duration=load_duration)
    if isolate and len(y) > sr:
        y = isolate_vocal(y, sr)
    duration = float(librosa.get_duration(y=y, sr=sr))

    # f0 via pyin (probabilistic YIN)
    f0_hz, voiced_flag, _ = librosa.pyin(
        y,
        fmin=FMIN_HZ,
        fmax=FMAX_HZ,
        sr=sr,
        frame_length=FRAME_LENGTH,
        hop_length=HOP_LENGTH,
    )
    hop_sec = HOP_LENGTH / sr
    voiced_ratio = float(np.mean(voiced_flag))

    voiced_f0 = f0_hz[voiced_flag]
    voiced_f0 = voiced_f0[~np.isnan(voiced_f0)]
    if len(voiced_f0) > 0:
        f0_median = float(np.median(voiced_f0))
        # frame-to-frame difference in cents
        cents = hz_to_cents(voiced_f0)
        diffs = np.abs(np.diff(cents))
        f0_jitter = float(np.median(diffs)) if len(diffs) > 0 else None
    else:
        f0_median = None
        f0_jitter = None

    key, mode = estimate_key(y, sr)

    tempo_arr, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP_LENGTH)
    tempo = float(tempo_arr) if np.ndim(tempo_arr) == 0 else float(tempo_arr[0])

    onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=HOP_LENGTH, units="time")
    onset_rate = len(onsets) / duration if duration > 0 else 0.0

    rms = librosa.feature.rms(y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)[0]
    rms = rms[rms > 1e-6]
    if len(rms) > 0:
        rms_db = 20 * np.log10(rms)
        rms_mean = float(np.mean(rms))
        rms_db_range = float(np.percentile(rms_db, 95) - np.percentile(rms_db, 5))
        rms_crest_db = float(20 * np.log10(np.max(rms) / (np.mean(rms) + 1e-9)))
    else:
        rms_mean = 0.0
        rms_db_range = 0.0
        rms_crest_db = 0.0

    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
    centroid_mean = float(np.mean(centroid))

    vib_rate, vib_depth = detect_vibrato(f0_hz, hop_sec)
    lts = long_tone_stability(f0_hz, hop_sec)

    timeline = extract_timeline(y, sr, f0_hz, voiced_flag, hop_sec)

    analysis = TrackAnalysis(
        duration_sec=round(duration, 2),
        voiced_ratio=round(voiced_ratio, 3),
        f0_median_hz=round(f0_median, 1) if f0_median else None,
        f0_jitter_cents=round(f0_jitter, 1) if f0_jitter else None,
        estimated_key=f"{key} {mode}",
        estimated_mode=mode,
        tempo_bpm=round(tempo, 1),
        onset_rate_per_sec=round(onset_rate, 2),
        rms_mean=round(rms_mean, 4),
        rms_db_range=round(rms_db_range, 1),
        rms_crest_db=round(rms_crest_db, 1),
        spectral_centroid_hz=round(centroid_mean, 0),
        vibrato_rate_hz=round(vib_rate, 2) if vib_rate else None,
        vibrato_depth_cents=round(vib_depth, 1) if vib_depth else None,
        long_tone_stability=round(lts, 1) if lts else None,
    )
    if return_signal:
        return analysis, timeline, y, sr
    return analysis, timeline


def compare(user: TrackAnalysis, ref: TrackAnalysis) -> dict:
    """Compute differences relevant to the 4-axis FB."""
    def f0_to_semitones(hz: float | None, ref_hz: float | None) -> float | None:
        if not hz or not ref_hz:
            return None
        return round(12 * np.log2(hz / ref_hz), 2)

    key_match = user.estimated_key == ref.estimated_key
    return {
        "duration_diff_sec": round(user.duration_sec - ref.duration_sec, 2),
        "key_match": key_match,
        "user_key": user.estimated_key,
        "ref_key": ref.estimated_key,
        "f0_median_diff_semitones": f0_to_semitones(user.f0_median_hz, ref.f0_median_hz),
        "tempo_diff_bpm": round(user.tempo_bpm - ref.tempo_bpm, 1),
        "voiced_ratio_diff": round(user.voiced_ratio - ref.voiced_ratio, 3),
        "rms_db_range_diff": round(user.rms_db_range - ref.rms_db_range, 1),
        "long_tone_stability_diff_cents": (
            round(user.long_tone_stability - ref.long_tone_stability, 1)
            if user.long_tone_stability is not None and ref.long_tone_stability is not None
            else None
        ),
        "vibrato_rate_diff_hz": (
            round(user.vibrato_rate_hz - ref.vibrato_rate_hz, 2)
            if user.vibrato_rate_hz is not None and ref.vibrato_rate_hz is not None
            else None
        ),
        "vibrato_depth_diff_cents": (
            round(user.vibrato_depth_cents - ref.vibrato_depth_cents, 1)
            if user.vibrato_depth_cents is not None and ref.vibrato_depth_cents is not None
            else None
        ),
        "spectral_centroid_diff_hz": round(
            user.spectral_centroid_hz - ref.spectral_centroid_hz, 0
        ),
        "onset_rate_diff": round(user.onset_rate_per_sec - ref.onset_rate_per_sec, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a user recording (and optional reference) for vocal coaching."
    )
    parser.add_argument("user", help="Path to user recording (wav recommended; mp3/m4a auto-decoded)")
    parser.add_argument("reference", nargs="?", help="Path to original/reference audio")
    parser.add_argument("--user-start", help="Start time of user clip (mm:ss or seconds)")
    parser.add_argument("--user-end", help="End time of user clip (mm:ss or seconds)")
    parser.add_argument("--ref-start", help="Start time of reference clip (mm:ss or seconds)")
    parser.add_argument("--ref-end", help="End time of reference clip (mm:ss or seconds)")
    parser.add_argument("--isolate-vocal-ref", action="store_true",
                        help="原曲に軽量声分離を適用し、伴奏由来の誤判定を緩和する")
    args = parser.parse_args()

    user_path = Path(args.user)
    ref_path = Path(args.reference) if args.reference else None

    try:
        u_start = parse_time(args.user_start)
        u_end = parse_time(args.user_end)
        r_start = parse_time(args.ref_start)
        r_end = parse_time(args.ref_end)
    except ValueError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2

    range_label_user = f"[{args.user_start or '0:00'}–{args.user_end or 'EOF'}]"
    print(f"[analyzing] user: {user_path.name} {range_label_user}", file=sys.stderr)
    user, user_timeline, user_y, sr = analyze_track(
        user_path, start_sec=u_start, end_sec=u_end, return_signal=True
    )

    result: dict = {
        "user": asdict(user),
        "user_range": {"start_sec": u_start, "end_sec": u_end},
        "user_timeline": user_timeline,
    }

    if ref_path:
        range_label_ref = f"[{args.ref_start or '0:00'}–{args.ref_end or 'EOF'}]"
        iso = " (vocal-isolated)" if args.isolate_vocal_ref else ""
        print(f"[analyzing] ref:  {ref_path.name} {range_label_ref}{iso}", file=sys.stderr)
        ref, ref_timeline, ref_y, _ = analyze_track(
            ref_path, start_sec=r_start, end_sec=r_end,
            isolate=args.isolate_vocal_ref, return_signal=True
        )
        result["reference"] = asdict(ref)
        result["reference_range"] = {"start_sec": r_start, "end_sec": r_end}
        result["reference_timeline"] = ref_timeline
        result["compare"] = compare(user, ref)
        try:
            result["alignment"] = align_dtw(user_y, ref_y, sr)
        except Exception:
            result["alignment"] = None

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
