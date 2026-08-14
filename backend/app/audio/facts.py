"""ブラインド聴取へ渡す「録音自体からの測定事実」の組み立て（docs/104）。

本番（coach.py）と eval（scripts/blind_listen_eval.py）が同じ組み立てを共有する
ための単一ソース。ここがズレると「evalで測った精度」と「本番の精度」が別物になる。

原則（docs/104 §0）: 事実は名前を判定しない。練習名を含まない測定の記述だけを返す。
"""
from __future__ import annotations

import math
from typing import Optional

from app.audio import texture


def pitch_span_fact(analysis: Optional[dict]) -> Optional[str]:
    """録音の音程移動幅を、ブラインド聴取向けの測定事実にする（docs/104 改訂）。

    大きな連続移動（10半音以上）はサイレン等のグリッサンド系を消去法で支持する
    決定的な物差しになる（震えの有無だけでは似た練習を絞りきれなかった実事故対応）。
    """
    pw = ((analysis or {}).get("timeline") or {}).get("per_window") or []
    f0s = [w.get("f0_mean_hz") for w in pw if w.get("f0_mean_hz")]
    if len(f0s) < 3 or min(f0s) <= 0:
        return None
    semis = 12 * math.log2(max(f0s) / min(f0s))
    if semis >= 10:
        return (f"音程は低い音から高い音まで連続的に約{round(semis)}半音"
                f"（{round(min(f0s))}→{round(max(f0s))}Hz）移動している")
    return None


def assemble(wav_path: str, analysis: Optional[dict]) -> Optional[str]:
    """質感計測（texture）＋音程移動幅を、本番と同じ形の1文に組み立てる。

    どちらも取れなければ None（呼び出し側は記述なしで続行＝従来動作）。
    """
    parts = [
        texture.describe(texture.modulation_profile(wav_path)),
        pitch_span_fact(analysis),
    ]
    return "。".join(p for p in parts if p) or None
