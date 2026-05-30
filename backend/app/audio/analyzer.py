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
HOP_LENGTH = 512
FRAME_LENGTH = 2048
FMIN_HZ = 65.0
FMAX_HZ = 1000.0
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


def long_tone_stability(f0_hz: np.ndarray, hop_sec: float, min_dur_sec: float = 0.6) -> float | None:
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
        stds.append(float(np.std(seg - np.median(seg))))
    return float(np.mean(stds)) if stds else None


def _voice_type(rolloff_to_f0: float | None) -> str | None:
    if rolloff_to_f0 is None:
        return None
    if rolloff_to_f0 >= 6.0:
        return "chest"
    if rolloff_to_f0 >= 4.0:
        return "mix"
    return "head"


def extract_timeline(y, sr, f0_hz, voiced_flag, hop_sec, window_sec=1.0, sustain_min_sec=0.6) -> dict:
    rms = librosa.feature.rms(y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
    rolloff85 = librosa.feature.spectral_rolloff(
        y=y, sr=sr, hop_length=HOP_LENGTH, roll_percent=0.85
    )[0]

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
        f0_std_cents = float(np.std(cents - np.median(cents)))
        q = max(1, len(valid) // 4)
        head_med = float(np.median(valid[:q]))
        tail_med = float(np.median(valid[-q:]))
        end_drift = round(1200 * float(np.log2(tail_med / head_med)), 1) if head_med > 0 else None
        cent_seg = centroid[s:min(e, len(centroid))]
        cent_avg = float(np.mean(cent_seg)) if len(cent_seg) else None
        roll_seg = rolloff85[s:min(e, len(rolloff85))]
        roll_avg = float(np.mean(roll_seg)) if len(roll_seg) else None
        mean_f0 = float(np.mean(valid))
        ratio = roll_avg / mean_f0 if (mean_f0 > 0 and roll_avg) else None
        sustained.append({
            "start_sec": round(s * hop_sec, 2),
            "end_sec": round(e * hop_sec, 2),
            "duration_sec": round((e - s) * hop_sec, 2),
            "mean_f0_hz": round(mean_f0, 1),
            "f0_std_cents": round(f0_std_cents, 1),
            "end_drift_cents": end_drift,
            "spectral_centroid_hz": round(cent_avg, 0) if cent_avg else None,
            "spectral_rolloff85_hz": round(roll_avg, 0) if roll_avg else None,
            "rolloff_to_f0_ratio": round(ratio, 2) if ratio else None,
            "voice_type_estimate": _voice_type(ratio),
        })

    return {"window_sec": window_sec, "per_window": per_window, "sustained_segments": sustained}


def analyze_file(path: str | Path, start_sec: float | None = None, end_sec: float | None = None) -> dict:
    """Analyze a single audio clip and return a metrics dict (+ timeline)."""
    offset = start_sec if start_sec is not None else 0.0
    if end_sec is not None:
        if start_sec is not None and end_sec <= start_sec:
            raise ValueError(f"end_sec ({end_sec}) must be > start_sec ({start_sec})")
        load_duration = end_sec - offset
    else:
        load_duration = None

    y, sr = librosa.load(str(path), sr=SR, mono=True, offset=offset, duration=load_duration)
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
        f0_jitter = float(np.median(d)) if len(d) > 0 else None
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
        rms_mean = rms_db_range = rms_crest_db = 0.0

    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
    centroid_mean = float(np.mean(centroid))

    vib_rate, vib_depth = detect_vibrato(f0_hz, hop_sec)
    lts = long_tone_stability(f0_hz, hop_sec)
    timeline = extract_timeline(y, sr, f0_hz, voiced_flag, hop_sec)

    return {
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
        "long_tone_stability": round(lts, 1) if lts else None,
        "timeline": timeline,
    }


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
        "long_tone_stability_diff_cents": diff(user["long_tone_stability"], ref["long_tone_stability"]),
        "vibrato_rate_diff_hz": diff(user["vibrato_rate_hz"], ref["vibrato_rate_hz"], 2),
        "vibrato_depth_diff_cents": diff(user["vibrato_depth_cents"], ref["vibrato_depth_cents"]),
        "spectral_centroid_diff_hz": diff(user["spectral_centroid_hz"], ref["spectral_centroid_hz"], 0),
        "onset_rate_diff": diff(user["onset_rate_per_sec"], ref["onset_rate_per_sec"], 2),
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
