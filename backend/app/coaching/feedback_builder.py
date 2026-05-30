"""
解析値 → FB/カードの payload を組み立てる（ルールベース・テンプレート差し込み）。
初心者にも分かる平易な日本語。専門用語には括弧で言い換えを添える。
"""

from __future__ import annotations

from typing import Optional

from app.coaching import scoring


def _note_name(hz: Optional[float]) -> str:
    if not hz:
        return "—"
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    import math
    midi = round(69 + 12 * math.log2(hz / 440.0))
    return f"{names[midi % 12]}{midi // 12 - 1}"


def _voice_type_jp(vt: Optional[str]) -> str:
    return {"chest": "地声", "mix": "ミックス（地声と裏声の中間）", "head": "裏声"}.get(vt, "不明")


def build_good_points(a: dict) -> list[str]:
    pts = []
    j = a.get("f0_jitter_cents")
    if j is not None and j <= 15:
        pts.append(f"音程がとても安定しています（細かい揺れが{j:.0f}cents＝半音の100分の1単位。15以下は上手な証拠）。")
    vr = a.get("vibrato_rate_hz")
    if vr is not None and 4.0 <= vr <= 7.5:
        pts.append(f"ビブラート（音をゆらす技術）が自然に出せています（秒{vr:.1f}回のゆれ）。")
    rng = a.get("rms_db_range")
    if rng is not None and rng >= 12:
        pts.append(f"声の大きさに幅があり、メリハリのある歌い方ができています。")
    # 声種への言及
    segs = [s for s in a.get("timeline", {}).get("sustained_segments", []) if (s.get("mean_f0_hz") or 0) >= 150]
    if segs:
        longest = max(segs, key=lambda s: s["duration_sec"])
        vt = _voice_type_jp(longest.get("voice_type_estimate"))
        pts.append(
            f"{longest['start_sec']:.0f}〜{longest['end_sec']:.0f}秒で約{longest['duration_sec']:.0f}秒、"
            f"{_note_name(longest['mean_f0_hz'])}あたりの音を{vt}で伸ばせています。"
        )
    if not pts:
        pts.append("最後まで歌い切れています。まずはここが第一歩です。")
    return pts[:3]


def build_analysis_table(a: dict, c: Optional[dict]) -> list[dict]:
    """FBカードの実測値テーブル（行: label, value, hint）。"""
    rows = []
    rows.append({"label": "あなたの声の高さ（中心）", "value": f"{_note_name(a.get('f0_median_hz'))}", "hint": "中心となる音の高さ"})
    j = a.get("f0_jitter_cents")
    rows.append({"label": "音程の安定度", "value": f"{j:.0f}cents" if j is not None else "—",
                 "hint": "小さいほど安定（15以下で上手）"})
    rng = a.get("rms_db_range")
    rows.append({"label": "声の強弱の幅", "value": f"{rng:.0f}dB" if rng is not None else "—",
                 "hint": "大きいほどメリハリがある"})
    vr = a.get("vibrato_rate_hz")
    rows.append({"label": "ビブラート", "value": f"秒{vr:.1f}回" if vr is not None else "検出なし",
                 "hint": "秒4〜7回が自然"})
    lts = a.get("long_tone_stability")
    rows.append({"label": "伸ばした音の安定度", "value": f"{lts:.0f}cents" if lts is not None else "—",
                 "hint": "小さいほど安定（30以下が目標）"})
    if c:
        rows.append({"label": "原曲とのテンポ差", "value": f"{c.get('tempo_diff_bpm')}BPM" if c.get("tempo_diff_bpm") is not None else "—",
                     "hint": "0に近いほどリズムが合っている"})
    return rows


def build_rhythm_note(c: Optional[dict]) -> Optional[str]:
    """DTWアライメントからリズムの走り/モタりを秒数つきで説明。"""
    align = (c or {}).get("alignment")
    if not align:
        return None
    lag = align.get("mean_lag_sec")
    notes = []
    if lag is not None and abs(lag) >= 0.1:
        if lag > 0:
            notes.append(f"原曲より全体的に約{abs(lag):.2f}秒遅れ気味（モタり）です。")
        else:
            notes.append(f"原曲より全体的に約{abs(lag):.2f}秒早め（走り）です。")
    worst = align.get("worst_segments") or []
    if worst:
        spots = "、".join(f"{w['user_sec']:.0f}秒あたり（{'遅れ' if w['lag_sec']>0 else '走り'}{abs(w['lag_sec']):.2f}秒）" for w in worst[:3])
        notes.append(f"特にズレが大きいのは {spots} です。")
    return " ".join(notes) if notes else None


def build_feedback_payload(a: dict, c: Optional[dict], task: Optional[dict]) -> dict:
    scores = scoring.compute_scores(a, c)
    payload = {
        "scores": scores,
        "analysis_table": build_analysis_table(a, c),
        "good_points": build_good_points(a),
        "today_task": None,
        "rhythm_note": build_rhythm_note(c),
    }
    if task:
        payload["today_task"] = {
            "id": task["id"],
            "label": task["label"],
            "reason": task["reason"](a, c),
        }
    return payload


def build_practice_payload(task: dict) -> dict:
    return {
        "task_id": task["id"],
        "task_label": task["label"],
        "practices": [
            {
                "name": p["name"],
                "steps": p["steps"],
                "checkpoint": p.get("checkpoint"),
                "video": p.get("video"),
            }
            for p in task["practices"]
        ],
        "achieve_label": task["achieve_label"],
    }


def build_judge_payload(task: dict, a: dict) -> dict:
    achieved = False
    try:
        achieved = task["achieve"](a)
    except Exception:
        achieved = False
    return {
        "task_id": task["id"],
        "task_label": task["label"],
        "achieve_label": task["achieve_label"],
        "result": "pass" if achieved else "retry",
        "metrics": build_analysis_table(a, None),
    }


def build_progress_payload(baseline: dict, current: dict, task: Optional[dict]) -> dict:
    """初回(baseline)と今回(current)の差分。改善していれば praise を埋める。"""
    def metric(d, key):
        return d.get(key)

    rows = []
    improvements = []

    pairs = [
        ("f0_jitter_cents", "音程の安定度（小さいほど良い）", "cents", -1),
        ("long_tone_stability", "伸ばした音の安定度（小さいほど良い）", "cents", -1),
        ("rms_db_range", "声の強弱の幅（大きいほど良い）", "dB", +1),
    ]
    for key, label, unit, direction in pairs:
        b, cur = metric(baseline, key), metric(current, key)
        if b is None or cur is None:
            continue
        delta = round(cur - b, 1)
        improved = (delta < 0 and direction < 0) or (delta > 0 and direction > 0)
        rows.append({
            "label": label,
            "before": f"{b}{unit}",
            "after": f"{cur}{unit}",
            "delta": f"{delta:+}{unit}",
            "improved": improved,
        })
        if improved and abs(delta) >= 1:
            improvements.append((label, abs(delta), unit))

    praise = None
    if improvements:
        label, amt, unit = max(improvements, key=lambda x: x[1])
        praise = f"「{label}」が {amt}{unit} 良くなりました！この調子です👏"

    return {
        "rows": rows,
        "praise": praise,
        "improved": bool(improvements),
        "next_task_label": task["label"] if task else None,
    }
