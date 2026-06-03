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


def _lvl4(good: bool, ok: bool, weak: bool) -> str:
    """良し悪し4段階: good=◎ / ok=○ / weak=△ / bad=×。◎は厳しめ。"""
    return "good" if good else ("ok" if ok else ("weak" if weak else "bad"))


def build_analysis_table(a: dict, c: Optional[dict]) -> list[dict]:
    """採点カードの根拠＝この録音の出来（パフォーマンス指標）。◎○△×のlevel付き。

    声のプロフィール(音域/声区/換声点/共鳴)は採点カードの「声の特徴」に同居させる（別カードにしない）。
    ◎は厳しめ基準（◎が安売りにならないように）。
    """
    rows = []
    j = a.get("f0_jitter_cents")
    rows.append({"label": "音程の安定度", "value": f"{j:.0f}cents" if j is not None else "—",
                 "hint": "揺れの少なさ（◎は6以下）",
                 "level": "ok" if j is None else _lvl4(j <= 6, j <= 12, j <= 20)})
    rng = a.get("rms_db_range")
    rows.append({"label": "声の強弱（メリハリ）", "value": f"{rng:.0f}dB" if rng is not None else "—",
                 "hint": "大きいほどメリハリ（◎は18dB以上）",
                 "level": "ok" if rng is None else _lvl4(rng >= 18, rng >= 13, rng >= 8)})
    vr = a.get("vibrato_rate_hz")
    vd = a.get("vibrato_depth_cents")
    rows.append({"label": "ビブラート", "value": vibrato_label(vr, vd), "hint": "秒4〜7回が自然",
                 "level": "good" if (vr is not None and 4.0 <= vr <= 7.5 and (vd or 0) >= 20)
                          else ("ok" if vr is not None else "weak")})
    lts = a.get("long_tone_stability")
    rows.append({"label": "伸ばした音の安定", "value": f"{lts:.0f}cents" if lts is not None else "—",
                 "hint": "小さいほど安定（◎は20以下）",
                 "level": "ok" if lts is None else _lvl4(lts <= 20, lts <= 35, lts <= 55)})
    align = (c or {}).get("alignment") if c else None
    if align and align.get("in_tune_score") is not None:
        err = align.get("pitch_error_cents")
        it = align["in_tune_score"]
        rows.append({
            "label": "原曲との一致（音程）",
            "value": f"{it}点" + (f"（ズレ{err:.0f}c）" if err is not None else ""),
            "hint": "音を外していないか（◎は90点以上）",
            "level": _lvl4(it >= 90, it >= 78, it >= 62),
        })
        lag = align.get("mean_lag_sec")
        if lag is not None:
            al = abs(lag)
            rows.append({
                "label": "原曲とのリズム", "value": f"{al:.2f}秒{'モタり' if lag>0 else '走り'}" if al >= 0.05 else "ほぼ一致",
                "hint": "走り/モタり（◎は0.08秒未満）",
                "level": _lvl4(al < 0.08, al < 0.18, al < 0.32)})
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


def _axis_level(s: int) -> str:
    """軸スコア→◎○△×（DAM準拠で◎は厳しめ）。"""
    return "good" if s >= 90 else ("ok" if s >= 75 else ("weak" if s >= 60 else "bad"))


def build_axis_groups(a: dict, c: Optional[dict]) -> list[dict]:
    """Live DAM風の入れ子構造: 音程 / リズム / 表現  それぞれにスコアと内訳。

    表現は 抑揚・ビブラート・しゃくり・こぶし・フォール を内包。
    """
    scores = scoring.compute_scores(a, c)
    align = (c or {}).get("alignment") if c else None
    j = a.get("f0_jitter_cents")
    rng = a.get("rms_db_range")
    vr = a.get("vibrato_rate_hz")
    vd = a.get("vibrato_depth_cents")
    orn = a.get("expression_ornaments") or {}

    # 音程
    pitch_items: list[dict] = []
    if align and align.get("in_tune_score") is not None:
        it = align["in_tune_score"]
        err = align.get("pitch_error_cents")
        pitch_items.append({"label": "原曲との一致（正確さ）",
                            "value": f"{it}点" + (f"（ズレ{err:.0f}c）" if err is not None else ""),
                            "level": _lvl4(it >= 90, it >= 78, it >= 62)})
    else:
        pitch_items.append({"label": "音程の正確さ", "value": "原曲があると判定できます", "level": "ok"})
    pitch_items.append({"label": "安定度（揺れの少なさ）", "value": f"{j:.0f}cents" if j is not None else "—",
                        "level": "ok" if j is None else _lvl4(j <= 6, j <= 12, j <= 20)})

    # リズム
    if align and align.get("mean_lag_sec") is not None:
        lag = align["mean_lag_sec"]
        al = abs(lag)
        rhythm_items = [{"label": "走り／モタり",
                         "value": f"{al:.2f}秒{'モタり' if lag > 0 else '走り'}" if al >= 0.05 else "ほぼ一致",
                         "level": _lvl4(al < 0.08, al < 0.18, al < 0.32)}]
    else:
        rhythm_items = [{"label": "走り／モタり", "value": "概算（原曲があると正確に分かる）", "level": "ok"}]

    # 表現（抑揚・ビブラート・しゃくり・こぶし・フォール）
    sc, fl = orn.get("scoop_count", 0), orn.get("fall_count", 0)
    ref_rng = (c or {}).get("ref_rms_db_range")
    yoku_val = (f"{rng:.0f}dB" if rng is not None else "—")
    if ref_rng is not None and rng is not None:
        yoku_val += f"（原曲{ref_rng:.0f}dB）"
    expr_items = [
        {"label": "抑揚（強弱）", "value": yoku_val, "level": scoring.yokuyou_level(rng, c)},
        {"label": "ビブラート", "value": vibrato_label(vr, vd),
         "level": "good" if (vr is not None and 4.0 <= vr <= 7.5 and (vd or 0) >= 20) else ("ok" if vr is not None else "weak")},
        {"label": "しゃくり", "value": f"{sc}回" if sc else "なし", "level": "good" if 1 <= sc <= 12 else "ok"},
        {"label": "こぶし", "value": "自動判定なし", "level": "ok"},
        {"label": "フォール", "value": f"{fl}回" if fl else "なし", "level": "good" if 1 <= fl <= 12 else "ok"},
    ]

    return [
        {"key": "音程", "icon": "🎵", "score": scores["pitch_score"], "level": _axis_level(scores["pitch_score"]), "items": pitch_items},
        {"key": "リズム", "icon": "🥁", "score": scores["rhythm_score"], "level": _axis_level(scores["rhythm_score"]), "items": rhythm_items},
        {"key": "表現", "icon": "🎨", "score": scores["expression_score"], "level": _axis_level(scores["expression_score"]), "items": expr_items},
    ]


def build_voice_profile(a: dict) -> list[dict]:
    """「声の特徴」をコンパクトに（音域／使っている声／換声点／響き）。採点カードに同居させる。"""
    timeline = a.get("timeline", {})
    holds = [s for s in timeline.get("sustained_segments", []) if (s.get("mean_f0_hz") or 0) >= 100]
    f0s = [w.get("f0_mean_hz") for w in timeline.get("per_window", [])
           if w.get("f0_mean_hz") and w["f0_mean_hz"] >= 100]
    out: list[dict] = []
    if f0s:
        out.append({"label": "音域", "value": f"{_note_name(min(f0s))}〜{_note_name(max(f0s))}"})
    conf = [h for h in holds if h.get("register_confidence") in ("high", "med")]
    cnt: dict[str, int] = {}
    for h in conf:
        r = h.get("register")
        if r:
            cnt[r] = cnt.get(r, 0) + 1
    if cnt:
        used = "・".join(_voice_type_jp(r).split("（")[0] for r, _ in sorted(cnt.items(), key=lambda x: -x[1]))
        out.append({"label": "使っている声", "value": used})
    pg = taxonomy.passaggio_estimate(a)
    if pg:
        out.append({"label": "換声点", "value": f"{pg['note']}あたり"})
    hr = a.get("harmonic_ratio")
    if hr is not None:
        res = "クリアで通る" if hr >= 0.55 else ("芯と柔らかさのバランス" if hr >= 0.35 else "やわらかい")
        out.append({"label": "声の響き", "value": res})
    return out


def build_pitch_graph(a: dict, c: Optional[dict]) -> Optional[dict]:
    """DAM風「音程バー」(時系列の音程グラフ)のデータ。

    原曲と照合できた時は user＋ref を同一時間軸に重ねる。原曲が無い/低信頼の時は
    ユーザーの音程の流れだけを返す。どちらも MIDIノート番号の点列(None=無声)。
    """
    align = (c or {}).get("alignment") if c else None
    if align and align.get("pitch_track"):
        pt = align["pitch_track"]
        return {
            "t0": pt.get("t0", 0.0), "dt": pt["dt"],
            "user": pt["user_midi"], "ref": pt["ref_midi"], "has_ref": True,
            "off_spots": align.get("pitch_off_spots") or [],
        }
    pc = a.get("pitch_contour")
    if pc and any(v is not None for v in pc.get("midi", [])):
        return {
            "t0": pc.get("t0", 0.0), "dt": pc["dt"],
            "user": pc["midi"], "ref": None, "has_ref": False, "off_spots": [],
        }
    return None


def build_feedback_payload(a: dict, c: Optional[dict], task: Optional[dict]) -> dict:
    scores = scoring.compute_scores(a, c)
    payload = {
        "scores": scores,
        "axes": build_axis_groups(a, c),          # Live DAM風: 音程/リズム/表現 の入れ子
        "pitch": build_pitch_graph(a, c),         # Live DAM風: 音程バー(時系列グラフ)
        "good_points": build_good_points(a),
        "voice_profile": build_voice_profile(a),
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

    # 使った声区（地声/ミックス/裏声）— フォルマント＋スペクトル傾斜＋H1-H2 の多数決
    if holds:
        counts: dict[str, int] = {}
        # 信頼度の高い区間を優先して集計（low は判定材料が薄いので弱める）
        conf_w = {"high": 2, "med": 1, "low": 0}
        for h in holds:
            vt = h.get("register") or h.get("voice_type_estimate")
            if vt:
                counts[vt] = counts.get(vt, 0) + conf_w.get(h.get("register_confidence"), 1) + 1
        confident = [h for h in holds if h.get("register_confidence") in ("high", "med")]
        if counts and confident:
            used = "・".join(_voice_type_jp(vt) for vt, _ in sorted(counts.items(), key=lambda x: -x[1]))
            rows.append({
                "label": "使っている声（推定）",
                "value": used,
                "hint": "声の傾き・倍音・フォルマントから推定（目安）",
            })
        elif counts:
            # 区間が短い/材料が薄く信頼度が低い → 断定しない
            rows.append({
                "label": "使っている声（推定）",
                "value": "判定が難しい（録音が短い・情報が少ない）",
                "hint": "もう少し長く伸ばす箇所があると推定しやすくなります",
            })

    # 声の共鳴（フォルマント）— 前に通る芯のある響きか、こもり気味か（目安）
    sf_ratio = a.get("singers_formant_ratio")
    f1 = a.get("formant_f1_hz")
    f2 = a.get("formant_f2_hz")
    if sf_ratio is not None and f1 and f2:
        if sf_ratio >= 0.008:
            res = "前によく集まって通る、芯のある共鳴"
        elif sf_ratio >= 0.003:
            res = "標準的な共鳴バランス"
        else:
            res = "やわらかく親しみのある響き（前に集めるとより通りやすくなる）"
        rows.append({
            "label": "声の共鳴（フォルマント）",
            "value": res,
            "hint": f"F1≈{f1}Hz・F2≈{f2}Hz。2.8〜3.4kHzの響きが通り・張りに効く（推定・目安）",
        })

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

    # ※ 伸ばしの安定度・ビブラート・音程の安定度は「採点カード(歌の診断結果)」に集約し、
    #   ここ(声のカルテ)では声のプロフィール=音域/声区/換声点/共鳴/響き に専念する（重複回避）。
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
