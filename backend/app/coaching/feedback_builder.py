"""
解析値 → FB/カードの payload を組み立てる（ルールベース・テンプレート差し込み）。
初心者にも分かる平易な日本語。専門用語には括弧で言い換えを添える。
"""

from __future__ import annotations

from typing import Optional

from app.coaching import scoring, taxonomy


def _note_name(hz: Optional[float]) -> str:
    if not hz:
        return "—"
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    import math
    midi = round(69 + 12 * math.log2(hz / 440.0))
    return f"{names[midi % 12]}{midi // 12 - 1}"


def _voice_type_jp(vt: Optional[str]) -> str:
    return {"chest": "地声", "mix": "ミックス（地声と裏声の中間）", "head": "裏声"}.get(vt, "不明")


def vibrato_label(vr: Optional[float], vd: Optional[float] = None) -> str:
    """ビブラートと"揺れ(wobble)"を区別したラベル。

    4.0〜7.5Hz が自然なビブラート。それ未満は遅い揺れ（未確立/不安定の可能性）、
    超過は細かすぎる震え。範囲外を「ビブラートができている」と誤認させない。
    """
    if vr is None:
        return "検出なし"
    depth = f"・深さ{vd:.0f}cents" if vd is not None else ""
    if 4.0 <= vr <= 7.5:
        return f"秒{vr:.1f}回{depth}（自然なビブラート）"
    if vr < 4.0:
        return f"秒{vr:.1f}回{depth}（ゆっくりした揺れ。整ったビブラートとしては遅め）"
    return f"秒{vr:.1f}回{depth}（速め・細かい震え）"


def build_good_points(a: dict) -> list[str]:
    pts = []
    j = a.get("f0_jitter_cents")
    if j is not None and j <= 15:
        pts.append(f"音程がとても安定しています（細かい揺れが{j:.0f}cents＝半音の100分の1単位。15以下は上手な証拠）。")
    # 張りどころ（曲の山）で声を張れているか
    pp = taxonomy.projection_point(a)
    if pp and pp["projected"]:
        pts.append(
            f"{pp['start_sec']:.0f}〜{pp['end_sec']:.0f}秒の高い音（曲の山になりやすい所）で、"
            f"声をしっかり張れています。張りどころで前に出せるのは強みです。"
        )
    rng = a.get("rms_db_range")
    if rng is not None and rng >= 12:
        pts.append("声の大きさに幅（強弱・ダイナミクス）があり、表現としてメリハリをつけられています。")
    vr = a.get("vibrato_rate_hz")
    if vr is not None and 4.0 <= vr <= 7.5:
        pts.append(f"ビブラート（音をゆらす技術）が自然に出せています（秒{vr:.1f}回のゆれ）。")
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
                 "hint": "揺れの少なさ（正確さは原曲があると分かる）"})
    rng = a.get("rms_db_range")
    rows.append({"label": "声の強弱の幅", "value": f"{rng:.0f}dB" if rng is not None else "—",
                 "hint": "大きいほどメリハリがある"})
    vr = a.get("vibrato_rate_hz")
    vd = a.get("vibrato_depth_cents")
    rows.append({"label": "ビブラート／揺れ", "value": vibrato_label(vr, vd), "hint": "秒4〜7回が自然なビブラート"})
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


def build_voice_diagnosis_payload(a: dict) -> dict:
    """Voick風の「声診断」カード。既に算出済みの指標をまとめて可視化する。

    音域 / 使った声区 / いちばん長い伸ばし / 伸ばしの安定度 / ビブラート / 音程の正確さ。
    """
    timeline = a.get("timeline", {})
    holds = [s for s in timeline.get("sustained_segments", []) if (s.get("mean_f0_hz") or 0) >= 100]
    f0s = [
        w.get("f0_mean_hz") for w in timeline.get("per_window", [])
        if w.get("f0_mean_hz") and w["f0_mean_hz"] >= 100
    ]
    rows: list[dict] = []

    # 声域（この曲で出した範囲。本人の最大音域ではない点を明示）
    if f0s:
        lo, hi = min(f0s), max(f0s)
        rows.append({
            "label": "この曲で出した音域",
            "value": f"{_note_name(lo)} 〜 {_note_name(hi)}",
            "hint": "この録音で出した範囲（あなたの最大音域ではありません）",
        })

    # 使った声区（地声/ミックス/裏声）— スペクトル比からの推定で粗いことを明示
    if holds:
        counts: dict[str, int] = {}
        for h in holds:
            vt = h.get("voice_type_estimate")
            if vt:
                counts[vt] = counts.get(vt, 0) + 1
        if counts:
            used = "・".join(_voice_type_jp(vt) for vt, _ in sorted(counts.items(), key=lambda x: -x[1]))
            rows.append({"label": "使っている声（推定）", "value": used, "hint": "倍音の比からの推定。目安として"})

    # 換声点（地声→ミックス/裏声の切り替わり）の推定
    pg = taxonomy.passaggio_estimate(a)
    if pg:
        rows.append({
            "label": "換声点（推定）",
            "value": f"{pg['note']} あたり",
            "hint": "地声→ミックス/裏声に切り替わる目安。スムーズにつなぐのが目標",
        })

    # いちばん長い伸ばし
    longest = max(holds, key=lambda s: s.get("duration_sec", 0)) if holds else None
    if longest:
        rows.append({
            "label": "いちばん長い伸ばし",
            "value": f"約{longest['duration_sec']:.0f}秒（{_note_name(longest['mean_f0_hz'])}）",
            "hint": "安定して伸ばせた最長の音",
        })

    # 声の響き（整数次倍音）。クリアで通る声か、息まじりの柔らかい声か。
    hr = a.get("harmonic_ratio")
    if hr is not None:
        if hr >= 0.55:
            htxt = "豊か（クリアで芯のある・通る声）"
        elif hr >= 0.35:
            htxt = "ほどよい（芯と柔らかさのバランス）"
        else:
            htxt = "息まじり（柔らかい・ささやき寄り）"
        rows.append({
            "label": "声の響き（整数次倍音）",
            "value": htxt,
            "hint": "整数次倍音が多いほどクリアで通る声",
        })

    lts = a.get("long_tone_stability")
    rows.append({
        "label": "伸ばしの安定度",
        "value": f"{lts:.0f}cents" if lts is not None else "—",
        "hint": "小さいほど安定（30以下が目標）",
    })

    vr = a.get("vibrato_rate_hz")
    vd = a.get("vibrato_depth_cents")
    rows.append({"label": "ビブラート／揺れ", "value": vibrato_label(vr, vd), "hint": "秒4〜7回が自然なビブラート"})

    # ジッターは「音を外していないか(正確さ)」ではなく「揺れの少なさ(安定度)」。
    # in-tune の正確さは原曲(お手本)があって初めて判定できる、と明示する。
    j = a.get("f0_jitter_cents")
    rows.append({
        "label": "音程の安定度（揺れの少なさ）",
        "value": f"{j:.0f}cents" if j is not None else "—",
        "hint": "小さいほど揺れが少ない。音を外していないか(正確さ)は原曲があると分かる",
    })

    return {"rows": rows}


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
