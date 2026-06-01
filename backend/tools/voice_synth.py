"""
声区較正用の合成ラベル付きコーパス生成（声門源＋声道フィルタ）。

ラベル付き実音源が無い段階のブートストラップ。声門の開放率(OQ)と閉鎖の急峻さ(tilt)で
声区を物理的に制御し、地声(chest)/ミックス(mix)/裏声(head)の音源を母音・f0を変えて合成する。
実データが集まれば、同じ形式（{label}/*.wav）に置けば calibrate_register.py で再較正できる。

使い方:
    python -m tools.voice_synth --out data/register_synth --per-class 120
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import scipy.signal as sg
import soundfile as sf

SR = 22050

# 母音ごとのフォルマント (F1,F2,F3,F4) Hz と帯域幅
VOWELS = {
    "a": [(730, 90), (1090, 110), (2440, 140), (3400, 180)],
    "i": [(270, 60), (2290, 110), (3010, 140), (3400, 180)],
    "u": [(300, 60), (870, 100), (2240, 140), (3400, 180)],
    "e": [(530, 80), (1840, 110), (2480, 140), (3400, 180)],
    "o": [(570, 80), (840, 100), (2410, 140), (3400, 180)],
}

# 声区ごとの声門パラメータ: 開放率OQ, 速度商SQ, 閉鎖急峻さ=傾斜LPFカットオフfc(Hz)
REGISTER_PARAMS = {
    "chest": dict(oq=(0.40, 0.52), sq=(3.0, 4.2), fc=(4200, 6500)),
    "mix":   dict(oq=(0.55, 0.66), sq=(2.1, 2.9), fc=(2000, 3200)),
    "head":  dict(oq=(0.72, 0.85), sq=(1.4, 1.9), fc=(700, 1300)),
}

# 声区ごとの典型f0レンジ(Hz)。地声は低め、裏声は高めに寄せる（現実の使われ方）
REGISTER_F0 = {
    "chest": (130, 300),
    "mix":   (250, 480),
    "head":  (350, 700),
}


def _glottal_source(f0: float, sr: int, dur: float, oq: float, sq: float,
                    fc: float, jitter: float, vib_rate: float, vib_depth: float,
                    rng: np.random.Generator) -> np.ndarray:
    """Rosenberg型グロッタル流の微分を音源とする。OQ→H1-H2、fc→スペクトル傾斜。"""
    n = int(dur * sr)
    flow = np.zeros(n)
    i = 0
    phase = rng.uniform(0, 2 * np.pi)
    while i < n:
        # f0にビブラート＋微小ジッター
        t = i / sr
        vib = 1.0 + (vib_depth / 100.0) * np.sin(2 * np.pi * vib_rate * t + phase)
        f = f0 * vib * (1.0 + jitter * rng.standard_normal())
        T = max(8, int(sr / max(f, 1.0)))
        T0 = oq * T
        Tp = T0 * sq / (sq + 1)
        for k in range(T):
            if i + k >= n:
                break
            if k <= Tp:
                g = 0.5 * (1 - np.cos(np.pi * k / max(Tp, 1)))      # 開大
            elif k <= T0:
                g = np.cos(np.pi * (k - Tp) / max(2 * (T0 - Tp), 1))  # 閉小
            else:
                g = 0.0                                              # 閉鎖
            flow[i + k] = g
        i += T
    deriv = np.diff(flow, prepend=flow[0])
    # 閉鎖の急峻さ＝スペクトル傾斜（fc低いほど急＝裏声寄り）
    b, a = sg.butter(1, min(fc, sr / 2 * 0.99) / (sr / 2), "low")
    deriv = sg.lfilter(b, a, deriv)
    return deriv / (np.max(np.abs(deriv)) + 1e-9)


def _formant_filter(x: np.ndarray, sr: int, formants: list[tuple[float, float]]) -> np.ndarray:
    """共振器カスケードで母音フォルマントを付与。"""
    y = x.copy()
    for f, bw in formants:
        if f >= sr / 2:
            continue
        r = np.exp(-np.pi * bw / sr)
        theta = 2 * np.pi * f / sr
        b = [1 - r]
        a = [1, -2 * r * np.cos(theta), r * r]
        y = sg.lfilter(b, a, y)
    return y


def synth_sample(label: str, sr: int = SR, dur: float = 2.2,
                 seed: int = 0) -> np.ndarray:
    """1サンプル合成。声区ラベルに応じて声門・f0・母音を選ぶ。"""
    rng = np.random.default_rng(seed)
    p = REGISTER_PARAMS[label]
    oq = rng.uniform(*p["oq"])
    sq = rng.uniform(*p["sq"])
    fc = rng.uniform(*p["fc"])
    f0lo, f0hi = REGISTER_F0[label]
    f0 = rng.uniform(f0lo, f0hi)
    vowel = rng.choice(list(VOWELS.keys()))
    # 「伸ばし」として検出されるよう、ほぼ定常（ビブラート・ジッターは控えめ）にする
    vib_rate = rng.uniform(4.5, 6.5)
    vib_depth = rng.uniform(0, 12)       # cents
    jitter = rng.uniform(0.002, 0.005)

    src = _glottal_source(f0, sr, dur, oq, sq, fc, jitter, vib_rate, vib_depth, rng)
    voiced = _formant_filter(src, sr, VOWELS[vowel])
    # 気息ノイズ（裏声ほど多め）
    agg = {"chest": 0.01, "mix": 0.02, "head": 0.04}[label]
    noise = _formant_filter(rng.standard_normal(len(voiced)) * agg, sr, VOWELS[vowel])
    y = voiced / (np.max(np.abs(voiced)) + 1e-9) + noise
    # 立ち上がり/減衰のフェードと軽い振幅ゆらぎ
    env = np.ones(len(y))
    fade = int(0.05 * sr)
    env[:fade] = np.linspace(0, 1, fade)
    env[-fade:] = np.linspace(1, 0, fade)
    y = y * env
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.9
    return y.astype(np.float32)


def build_corpus(out_dir: str, per_class: int = 120, sr: int = SR) -> None:
    labels = list(REGISTER_PARAMS.keys())
    for li, label in enumerate(labels):
        d = os.path.join(out_dir, label)
        os.makedirs(d, exist_ok=True)
        for i in range(per_class):
            y = synth_sample(label, sr=sr, seed=1000 + li * 10000 + i)  # 再現可能
            sf.write(os.path.join(d, f"{label}_{i:03d}.wav"), y, sr)
    total = per_class * len(labels)
    print(f"synthesized {total} samples ({per_class}/class) -> {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/register_synth")
    ap.add_argument("--per-class", type=int, default=120)
    args = ap.parse_args()
    build_corpus(args.out, args.per_class)
