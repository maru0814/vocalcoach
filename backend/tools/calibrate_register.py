"""
声区しきい値の較正ハーネス。

ラベル付き音源ディレクトリ（{chest,mix,head}/*.wav）から声区特徴（スペクトル傾斜・
H1-H2・ロールオフ比）を抽出し、多数決分類器のしきい値を当てはめて混同行列を出す。

- 合成コーパス（tools/voice_synth.py）でブートストラップ較正。
- 実データが集まったら同じ形式で置けばそのまま再較正できる。

使い方:
    python -m tools.voice_synth --out data/register_synth --per-class 120
    python -m tools.calibrate_register --data data/register_synth
"""
from __future__ import annotations

import argparse
import glob
import os

import librosa
import numpy as np

from app.audio import analyzer

LABELS = ["chest", "mix", "head"]


def _clip_features(path: str) -> dict | None:
    """1クリップ（=1つの伸ばし音）を本番と同じ測定コードで特徴抽出する。

    合成クリップは1音なので、有声フレーム全体を1区間として
    analyzer._segment_voice_features に通す（本番の伸ばし区間と同一処理）。
    """
    y, sr = librosa.load(path, sr=analyzer.SR, mono=True)
    f0, vflag, _ = librosa.pyin(
        y, fmin=analyzer.FMIN_HZ, fmax=analyzer.FMAX_HZ, sr=sr,
        frame_length=analyzer.FRAME_LENGTH, hop_length=analyzer.HOP_LENGTH,
    )
    voiced = np.where(~np.isnan(f0))[0]
    if len(voiced) < 8:
        return None
    s_frame, e_frame = int(voiced[0]), int(voiced[-1]) + 1
    feat = analyzer._segment_voice_features(y, sr, s_frame, e_frame, f0)
    # ロールオフ÷f0（補助キュー）
    roll = librosa.feature.spectral_rolloff(
        y=y, sr=sr, hop_length=analyzer.HOP_LENGTH, roll_percent=0.85)[0]
    f0v = f0[~np.isnan(f0)]
    mean_f0 = float(np.mean(f0v)) if len(f0v) else 0.0
    ratio = (float(np.median(roll)) / mean_f0) if mean_f0 > 0 else None
    return {
        "tilt": feat.get("spectral_tilt_db_oct"),
        "h1h2": feat.get("h1h2_db"),
        "rolloff": round(ratio, 2) if ratio else None,
    }


def collect_features(data_dir: str) -> list[dict]:
    """各ファイル（=1音）の (tilt,h1h2,rolloff,label) を集める。"""
    rows: list[dict] = []
    for label in LABELS:
        for path in sorted(glob.glob(os.path.join(data_dir, label, "*.wav"))):
            try:
                f = _clip_features(path)
            except Exception:
                f = None
            if f and (f["tilt"] is not None or f["h1h2"] is not None):
                rows.append({"label": label, **f})
    return rows


def _vote_label(row: dict, th: dict) -> str:
    lbl, _ = analyzer._register_vote(row["tilt"], row["h1h2"], row["rolloff"], th)
    return lbl or "mix"


def macro_f1(rows: list[dict], th: dict) -> float:
    preds = [_vote_label(r, th) for r in rows]
    gts = [r["label"] for r in rows]
    f1s = []
    for c in LABELS:
        tp = sum(1 for p, g in zip(preds, gts) if p == c and g == c)
        fp = sum(1 for p, g in zip(preds, gts) if p == c and g != c)
        fn = sum(1 for p, g in zip(preds, gts) if p != c and g == c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return float(np.mean(f1s))


def confusion(rows: list[dict], th: dict) -> None:
    idx = {c: i for i, c in enumerate(LABELS)}
    M = np.zeros((3, 3), dtype=int)
    for r in rows:
        M[idx[r["label"]], idx[_vote_label(r, th)]] += 1
    print("\n混同行列（行=正解, 列=推定）:")
    print("            " + "  ".join(f"{c:>6}" for c in LABELS))
    for i, c in enumerate(LABELS):
        row = "  ".join(f"{M[i, j]:6d}" for j in range(3))
        acc = M[i, i] / max(M[i].sum(), 1)
        print(f"  {c:>6}    {row}   (recall {acc:.2f})")
    print(f"  全体正解率: {np.trace(M) / max(M.sum(),1):.3f}")


def _fit_cue(rows: list[dict], key: str, chest_high: bool) -> tuple[float, float]:
    """1キューだけで3クラスを当てる2しきい値(hi,lo)を独立に最適化（縮退回避・解釈可能）。

    chest_high=True: 値が大きいほど chest（tilt, rolloff）。False: 大きいほど head（h1h2）。
    戻り: (chest側カット, head側カット)。
    """
    vals = [(r[key], r["label"]) for r in rows if r.get(key) is not None]
    if len(vals) < 6:
        return None, None
    xs = sorted(v for v, _ in vals)
    cands = sorted(set(round(float(np.percentile([v for v, _ in vals], q)), 1)
                       for q in np.linspace(5, 95, 19)))

    def acc(hi, lo):
        ok = 0
        for v, lab in vals:
            if chest_high:
                pred = "chest" if v >= hi else ("head" if v <= lo else "mix")
            else:
                pred = "chest" if v <= lo else ("head" if v >= hi else "mix")
                # ここでは hi=head側, lo=chest側 として扱う
            ok += (pred == lab)
        return ok

    best, bhi, blo = -1, None, None
    for a in cands:
        for b in cands:
            if a <= b:
                continue
            # chest_high: hi=a(chest), lo=b(head)。h1h2: hi=a(head), lo=b(chest)
            s = acc(a, b)
            if s > best:
                best, bhi, blo = s, a, b
    if chest_high:
        return bhi, blo          # (chest_ge, head_le)
    return blo, bhi              # (chest_le, head_ge)


def fit_thresholds(rows: list[dict]) -> dict:
    """各キューを独立に較正（縮退しにくく転移しやすい）。"""
    th = dict(analyzer.REGISTER_THRESHOLDS)
    t_chest, t_head = _fit_cue(rows, "tilt", chest_high=True)
    if t_chest is not None:
        th["tilt_chest_ge"], th["tilt_head_le"] = t_chest, t_head
    h_chest, h_head = _fit_cue(rows, "h1h2", chest_high=False)
    if h_chest is not None:
        th["h1h2_chest_le"], th["h1h2_head_ge"] = h_chest, h_head
    r_chest, r_head = _fit_cue(rows, "rolloff", chest_high=True)
    if r_chest is not None:
        th["rolloff_chest_ge"], th["rolloff_head_lt"] = r_chest, r_head
    return th


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/register_synth")
    ap.add_argument("--no-fit", action="store_true", help="現行しきい値の評価のみ")
    args = ap.parse_args()

    rows = collect_features(args.data)
    n_by = {c: sum(1 for r in rows if r["label"] == c) for c in LABELS}
    print(f"サンプル区間数: {len(rows)}  内訳 {n_by}")
    if not rows:
        print("データがありません。先に tools.voice_synth でコーパスを作ってください。")
        return

    print(f"\n[現行しきい値] macro-F1 = {macro_f1(rows, analyzer.REGISTER_THRESHOLDS):.3f}")
    confusion(rows, analyzer.REGISTER_THRESHOLDS)

    if not args.no_fit:
        fitted = fit_thresholds(rows)
        print(f"\n[較正後しきい値] macro-F1 = {macro_f1(rows, fitted):.3f}")
        confusion(rows, fitted)
        print("\n推奨 REGISTER_THRESHOLDS:")
        for k in ["tilt_chest_ge", "tilt_head_le", "h1h2_chest_le", "h1h2_head_ge",
                  "rolloff_chest_ge", "rolloff_head_lt"]:
            print(f'    "{k}": {fitted[k]},')


if __name__ == "__main__":
    main()
