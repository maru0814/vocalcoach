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


# 震えと音程移動が同時に測れた時に添える注記。片方の事実がもう片方を打ち消す
# 材料だと誤読され、モデルの正しい聴覚を上書きした実事故への較正
# （2026-08-14 較正第1号: リップロールをサイレン音形でやった録音 → サイレンと誤認。
#  この注記の有無で 0/5 → 5/5 に反転。docs/106 §4）
_COEXIST_NOTE = "（注: 震えと音程移動は同時に成立し得る。大きな音程移動は震えを伴う練習でも起こる）"


def assemble(wav_path: str, analysis: Optional[dict]) -> Optional[str]:
    """質感計測（texture）＋音程移動幅を、本番と同じ形の1文に組み立てる。

    どちらも取れなければ None（呼び出し側は記述なしで続行＝従来動作）。
    """
    profile = texture.modulation_profile(wav_path)
    tex = texture.describe(profile)
    span = pitch_span_fact(analysis)
    joined = "。".join(p for p in (tex, span) if p)
    if not joined:
        return None
    if span and texture.has_modulation(profile):
        joined += _COEXIST_NOTE
    return joined
