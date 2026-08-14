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

# 震えの探索帯域（Hz）。下限4=ビブラートの下端、上限45=トリル（唇・舌）の上端。
# ⚠️ 45Hz超（フライ/ラフネス帯）は測らない: 声の基本周波数（低い声で80〜110Hz）が
# エンベロープに漏れて「パルス状の震え」と誤検出した実事故があるため（2026-08-14、
# サイレン f0=94〜382Hz を『毎秒100回のパルス』と主張しブラインドをミスリード）。
_MOD_LO_HZ = 4.0
_MOD_HI_HZ = 45.0


def modulation_profile(wav_path: str, sr: int = 16000) -> Optional[dict]:
    """エンベロープ（音量の輪郭）の周期的な震えを測る。

    戻り: {"mod_rate_hz": float, "mod_strength": float(0..1), "flutter_ratio": float,
    "duration_sec": float, "windows": [{"rate_hz", "strength"}, ...]}
    windows は1秒窓ごとの自己相関ピーク（しきい値でふるう前の生値）。
    STRENGTH_THRESHOLD の較正は eval がこの生値の分布から行う（docs/104 §4）。
    1秒未満・ほぼ無音・読み込み失敗は None（呼び出し側は記述なしで続行）。
    """
    try:
        y, sr = librosa.load(wav_path, sr=sr, mono=True)
    except Exception:
        logger.warning("texture: 音声の読み込みに失敗 %s", wav_path, exc_info=True)
        return None
    if len(y) < sr:  # 1秒未満は測らない
        return None
    # エンベロープ抽出: |y| を 50Hz ローパスしてから間引く。
    # ⚠️ RMSフレーム方式は声の基本周波数（80Hz〜）のリップルが間引きで 4〜45Hz 帯へ
    # 折り返し（エイリアシング）、サイレンの声そのものを「毎秒40回の震え」と誤検出した
    # （実事故 2026-08-14）。フィルタで震え帯域(〜50Hz)以外を先に落とせば折り返しは起きない。
    from scipy.signal import butter, filtfilt
    b, a = butter(4, 50.0 / (sr / 2), btype="low")
    env_full = filtfilt(b, a, np.abs(y))
    hop = max(1, int(sr * 0.0025))    # 2.5ms → エンベロープの実効サンプリング 400Hz（帯域上限の分解能確保）
    env = env_full[::hop]
    if env.size < 32 or float(env.max()) < 1e-4:  # ほぼ無音
        return None
    fs_env = sr / hop
    # 1秒区間ごとに測る: 「冒頭のきしみだけ震えている」サイレンと「全体が震える」
    # リップロールを区別するため（実事故 2026-08-14: 冒頭クリーキーの震えを
    # クリップ全体の性質として主張し、ブラインドをミスリードした）。
    win = int(fs_env)  # 1秒
    rates, strengths, fluttered = [], [], 0
    windows: list[dict] = []
    n_win = 0
    for start in range(0, env.size - win + 1, win):
        e = env[start:start + win].astype(float)
        e = e - e.mean()
        denom = float(np.dot(e, e))
        if denom <= 0.0:
            continue
        n_win += 1
        lo = max(1, int(np.ceil(fs_env / _MOD_HI_HZ)))
        hi = min(e.size - 1, int(fs_env / _MOD_LO_HZ))
        if hi <= lo:
            continue
        ac = np.correlate(e, e, mode="full")[e.size - 1:] / denom
        seg = ac[lo:hi]
        peak = int(np.argmax(seg)) + lo
        strength = float(seg.max())
        # 境界ガード: ピークが探索下限ラグそのもの＝帯域外（45Hz超）の成分が
        # 縁に漏れている可能性が高いので「震え」と数えない
        if peak <= lo:
            continue
        windows.append({"rate_hz": float(fs_env / peak), "strength": strength})
        if strength >= STRENGTH_THRESHOLD:
            fluttered += 1
            rates.append(fs_env / peak)
            strengths.append(strength)
    if n_win == 0:
        return None
    return {
        "mod_rate_hz": float(np.median(rates)) if rates else 0.0,
        "mod_strength": float(np.median(strengths)) if strengths else 0.0,
        "flutter_ratio": fluttered / n_win,
        "duration_sec": float(len(y) / sr),
        "windows": windows,
    }


def describe(profile: Optional[dict]) -> Optional[str]:
    """測定結果を、名前を含まない日本語の記述文にする（docs/104 §3）。

    45Hz超（フライ/ラフネス帯）の主張はしない: エンベロープ計測では声の基本周波数と
    区別できず、誤った「事実」がブラインド聴取をミスリードするため（実事故 2026-08-14）。
    震えが録音の一部区間だけの場合はそのまま「一部のみ」と伝える（冒頭がきしむ
    サイレンを、全体が震えるリップロール等と混同させないため）。
    """
    if not profile:
        return None
    ratio = profile.get("flutter_ratio", 0.0)
    rate = profile["mod_rate_hz"]
    if ratio <= 0.0 or rate > _MOD_HI_HZ:
        return "規則的な振幅の震え（毎秒4〜45回の帯域）は検出されない"
    n = round(rate)
    if 4 <= rate < 10:
        band = f"毎秒約{n}回のゆったりした音量の揺れ（ビブラートに典型的な帯域）"
    elif 15 <= rate <= 45:
        band = f"毎秒約{n}回の振幅の規則的な震え（唇・舌の震えやエッジボイスに典型的な帯域）"
    else:  # 10〜15Hz の谷間: 珍しいので帯域注釈なしの事実だけ
        band = f"毎秒約{n}回の振幅の規則的な震え"
    if ratio >= 0.7:
        return f"録音のほぼ全体で{band}を検出"
    return (f"録音の一部（約{round(ratio * 10)}割）の区間でのみ{band}を検出。"
            "残りの区間はなめらか")
