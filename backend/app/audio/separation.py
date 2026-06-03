"""
軽量ボーカル分離（torch不要、librosaのみ）。

商業ミックスの原曲は伴奏（ベース・ドラム）が支配的で、pyinのf0推定が
低音に引っ張られる。HPSS + ボーカル帯域強調で伴奏を抑え、声主体の
信号に近づける。Demucs級の分離ではなく「伴奏抑制」レベル。
"""

from __future__ import annotations

import librosa
import numpy as np


def isolate_vocal(y: np.ndarray, sr: int,
                  hard_cut_hz: float = 130.0, low_hz: float = 200.0,
                  high_hz: float = 5000.0, margin: float = 3.0,
                  kernel_size: int = 17) -> np.ndarray:
    """伴奏を抑え、ボーカル帯域を強調した信号を返す。

    1. HPSS: ハーモニック成分を抽出（打楽器=ドラムのトランジェントを除く）
    2. ソフトマスク: harmonic を percussive に対して強調
    3. 帯域フィルタ:
       - hard_cut_hz 未満を実質ゼロ（ベースの基音 D2≈74Hz 等を除去）
       - hard_cut〜low_hz を緩やかに減衰
       - high_hz 超を減衰

    kernel_size: HPSS のメディアンフィルタ長。小さいほど高速（既定31→17で約半分の時間）。
    """
    n_fft = 2048
    hop = 512

    S_full, phase = librosa.magphase(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    H, P = librosa.decompose.hpss(S_full, margin=margin, kernel_size=kernel_size)
    mask_h = H / (H + P + 1e-8)
    S_harm = S_full * mask_h

    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    band = np.ones_like(freqs)
    band[freqs < hard_cut_hz] = 0.02          # ベース基音をほぼ除去
    ramp = (freqs >= hard_cut_hz) & (freqs < low_hz)
    band[ramp] = 0.02 + 0.98 * (freqs[ramp] - hard_cut_hz) / (low_hz - hard_cut_hz)
    band[freqs > high_hz] = 0.4
    S_voc = S_harm * band[:, np.newaxis]

    y_voc = librosa.istft(S_voc * phase, hop_length=hop, length=len(y))
    peak = np.max(np.abs(y_voc)) + 1e-9
    return (y_voc / peak * (np.max(np.abs(y)) + 1e-9)).astype(np.float32)
