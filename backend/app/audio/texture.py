"""録音の「質感」計測 — 振幅変調（震え）の速さと規則性（docs/104）。

原則: このモジュールは練習名を判定しない。測定事実（毎秒何回・どれくらい規則的か）を
数字と帯域の記述で返すだけ。名前の判断はブラインド聴取（llm.listen_blind）が行う。
「震え＝リップロール」ではない（巻き舌・エッジボイス・がなり・ビブラート等でも震える）
ため、記述文には典型帯域の注釈だけを添え、断定語を含めない。
"""
from __future__ import annotations

import logging
from typing import Optional

import librosa
import numpy as np

logger = logging.getLogger(__name__)

# 自己相関ピークがこの値以上なら「規則的な震えあり」とみなす（合成信号で暫定校正。
# 線引きの見直しは eval の実測で行う＝docs/104 §4）。
STRENGTH_THRESHOLD = 0.35

# 震えの探索帯域（Hz）。下限4=ビブラートの下端、上限80=フライ/ラフネスの上端。
_MOD_LO_HZ = 4.0
_MOD_HI_HZ = 80.0


def modulation_profile(wav_path: str, sr: int = 16000) -> Optional[dict]:
    """エンベロープ（音量の輪郭）の周期的な震えを測る。

    戻り: {"mod_rate_hz": float, "mod_strength": float(0..1), "duration_sec": float}
    1秒未満・ほぼ無音・読み込み失敗は None（呼び出し側は記述なしで続行）。
    """
    try:
        y, sr = librosa.load(wav_path, sr=sr, mono=True)
    except Exception:
        logger.warning("texture: 音声の読み込みに失敗 %s", wav_path, exc_info=True)
        return None
    if len(y) < sr:  # 1秒未満は測らない
        return None
    hop = max(1, int(sr * 0.005))     # 5ms → エンベロープの実効サンプリング 200Hz
    frame = max(hop * 2, int(sr * 0.010))
    env = librosa.feature.rms(y=y, frame_length=frame, hop_length=hop)[0]
    if env.size < 32 or float(env.max()) < 1e-4:  # ほぼ無音
        return None
    env = env - float(env.mean())
    denom = float(np.dot(env, env))
    if denom <= 0.0:
        return None
    fs_env = sr / hop
    ac = np.correlate(env, env, mode="full")[env.size - 1:]
    ac = ac / denom  # ac[0] = 1.0
    lo = max(1, int(fs_env / _MOD_HI_HZ))
    hi = min(ac.size - 1, int(fs_env / _MOD_LO_HZ))
    if hi <= lo:
        return None
    seg = ac[lo:hi]
    peak = int(np.argmax(seg)) + lo
    return {
        "mod_rate_hz": float(fs_env / peak),
        "mod_strength": float(seg.max()),
        "duration_sec": float(len(y) / sr),
    }


def describe(profile: Optional[dict]) -> Optional[str]:
    """測定結果を、名前を含まない日本語の記述文にする（docs/104 §3）。"""
    if not profile:
        return None
    rate = profile["mod_rate_hz"]
    strength = profile["mod_strength"]
    if strength < STRENGTH_THRESHOLD:
        return "規則的な振幅の震えは検出されない（なめらかな発声）"
    n = round(rate)
    if 4 <= rate < 10:
        return f"毎秒約{n}回のゆったりした音量の揺れを検出（ビブラートに典型的な帯域）"
    if 15 <= rate <= 45:
        return (f"振幅の規則的な震えを毎秒約{n}回検出"
                "（唇・舌の震えやエッジボイスに典型的な帯域）")
    if rate > 45:
        return f"毎秒約{n}回の細かいパルス状の震えを検出（フライ/ラフネスに典型的な帯域）"
    # 10〜15Hz の谷間: 珍しいので帯域注釈なしの事実だけ
    return f"振幅の規則的な震えを毎秒約{n}回検出"
