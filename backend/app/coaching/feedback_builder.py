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


REG_JP = {"chest": "地声", "mix": "ミックス", "head": "裏声"}


_HINT_CLOSURE = "息と声のバランス（H1-H2）。息漏れ↔締めすぎの中庸が効率◎"
_HINT_RING = "前に通る芯（2.8〜3.4kHzのシンガーズフォルマント）"
_HINT_CPP = "声の芯の強さ（CPP）。高いほど倍音が立って通る"
_HINT_REG = "高音の運び方（地声/ミックス/裏声・音響からの推定）"


def _closure_item(a: dict, vc: dict) -> dict:
    """声帯の閉じ（内転＝息の効率）。原曲比較を優先、無ければ単体ラベル（docs/21）。"""
    clo = vc.get("closure")
    if clo:
        v = clo["verdict"]
        if v == "breathier":
            return {"label": "声帯の閉じ（息の効率）", "value": "息漏れ寄り（原曲より閉じがゆるい）", "level": "weak", "hint": _HINT_CLOSURE}
        if v == "pressed":
            return {"label": "声帯の閉じ（息の効率）", "value": "締めすぎ寄り（原曲より力み）", "level": "weak", "hint": _HINT_CLOSURE}
        return {"label": "声帯の閉じ（息の効率）", "value": "原曲と同じくバランス◎", "level": "good", "hint": _HINT_CLOSURE}
    cl = (a.get("voice") or {}).get("closure") or {}
    lab = cl.get("label")
    return {"label": "声帯の閉じ（息の効率）", "value": cl.get("jp") or "—",
            "level": "good" if lab == "balanced" else "ok", "hint": _HINT_CLOSURE}


def _ring_item(a: dict, vc: dict) -> dict:
    """響き（シンガーズフォルマント＝芯・通り）。"""
    ring = vc.get("ring")
    if ring:
        if ring["verdict"] == "weaker":
            return {"label": "響き（芯・通り）", "value": "原曲より弱め（前に集めたい）", "level": "weak", "hint": _HINT_RING}
        return {"label": "響き（芯・通り）", "value": "原曲と同等以上の響き", "level": "good", "hint": _HINT_RING}
    rv = (a.get("voice") or {}).get("ring") or {}
    lab = rv.get("label")
    return {"label": "響き（芯・通り）", "value": rv.get("jp") or "—",
            "level": "good" if lab == "strong" else "ok", "hint": _HINT_RING}


def _register_item(a: dict, vc: dict) -> dict:
    """高音の声区（原曲と同じ運び方か）。"""
    rh = vc.get("register_high")
    if rh:
        if rh["verdict"] == "match":
            return {"label": "高音の声区", "value": f"原曲と同じ{REG_JP.get(rh['ref'], '—')}", "level": "good", "hint": _HINT_REG}
        return {"label": "高音の声区",
                "value": f"あなた{REG_JP.get(rh['user'], '?')}／原曲{REG_JP.get(rh['ref'], '?')}", "level": "weak", "hint": _HINT_REG}
    v = (a.get("voice") or {}).get("register_high") or {}
    reg, hz = v.get("register"), v.get("hz")
    if reg:
        return {"label": "高音の声区", "value": f"{REG_JP.get(reg, '—')}（{_note_name(hz)}）", "level": "ok", "hint": _HINT_REG}
    return {"label": "高音の声区", "value": "—", "level": "ok"}


def _passaggio_item(a: dict) -> dict:
    pg = taxonomy.passaggio_estimate(a)
    return {"label": "換声点（声区の変わり目）", "value": f"{pg['note']}あたり" if pg else "—", "level": "ok"}


def build_voice_axes(a: dict, c: Optional[dict], ref_attempted: bool = False) -> list[dict]:
    """発声特化の入れ子構造: 音程の正確さ / 声の鳴り・効率 / 声区の運び / 支え・安定（docs/21）。

    各軸は原曲(お手本)と比較し、◎○△× とスコアで示す。リズム・表現は扱わない。
    """
    sc = scoring.voice_scores(a, c)
    align = (c or {}).get("alignment") if c else None
    vc = (c or {}).get("voice_compare") or {}
    j = a.get("f0_jitter_cents")
    lts = a.get("long_tone_stability")

    # 音程の正確さ（原曲とのin-tune ＋ 安定度）
    pitch_items: list[dict] = []
    if align and align.get("in_tune_score") is not None:
        it = align["in_tune_score"]
        err = align.get("pitch_error_cents")
        pitch_items.append({"label": "原曲との一致",
                            "value": f"{it}点" + (f"（ズレ{err:.0f}c）" if err is not None else ""),
                            "level": _lvl4(it >= 90, it >= 78, it >= 62)})
    else:
        pitch_items.append({"label": "音程の正確さ",
                            "value": "原曲とうまく重ねられず" if ref_attempted else "原曲を貼ると判定できます",
                            "level": "ok"})
    pitch_items.append({"label": "安定度（揺れの少なさ）", "value": f"{j:.0f}cents" if j is not None else "—",
                        "level": "ok" if j is None else _lvl4(j <= 6, j <= 12, j <= 20)})

    phon_items = [_closure_item(a, vc), _ring_item(a, vc)]
    cpp = a.get("cpp_db")
    if cpp is not None:
        phon_items.append({"label": "声の芯（CPP）", "value": f"{cpp:.0f}dB",
                           "level": _lvl4(cpp >= 11, cpp >= 7, cpp >= 4), "hint": _HINT_CPP})
    reg_items = [_register_item(a, vc), _passaggio_item(a)]
    sup_items = [{"label": "伸ばしの安定（息の支え）", "value": f"{lts:.0f}cents" if lts is not None else "—",
                  "level": "ok" if lts is None else _lvl4(lts <= 20, lts <= 30, lts <= 45)}]

    return [
        {"key": "音程の正確さ", "icon": "🎯", "score": sc["pitch_score"], "level": _axis_level(sc["pitch_score"]), "items": pitch_items},
        {"key": "声の鳴り・効率", "icon": "🔊", "score": sc["phonation_score"], "level": _axis_level(sc["phonation_score"]), "items": phon_items},
        {"key": "声区の運び", "icon": "🪜", "score": sc["registration_score"], "level": _axis_level(sc["registration_score"]), "items": reg_items},
        {"key": "支え・安定", "icon": "🫁", "score": sc["support_score"], "level": _axis_level(sc["support_score"]), "items": sup_items},
    ]


_HEADLINE_BY_ISSUE = {
    "pulled_chest": "高音を地声で押し上げ気味。軽く前に当ててミックスへ寄せると、楽に届きます。",
    "breathy": "息がやや漏れ気味。ストロー発声で声帯の閉じを揃えると、同じ息でもっと鳴ります。",
    "lack_resonance": "声が前に集まりきっていません。前歯〜鼻のマスクに響きを集めると芯が出ます。",
    "artificial_vibrato": "ビブラートの揺れが不自然。まっすぐ伸ばしてから自然な揺れに任せましょう。",
    "unstable_support": "伸ばしが揺れ気味。息の支え（アッポッジョ）を整えると安定します。",
    "mix_incoordination": "声区の繋ぎに段差。ネイ／リップロールでミックスを滑らかにしましょう。",
}


def build_headline(a: dict, c: Optional[dict]) -> str:
    """発声の最重要ポイントを一言で（プロトレーナーの総評）。診断と整合させる（docs/21・資料）。"""
    # 原曲比較で高音の声区差が明確なら最優先
    vc = (c or {}).get("voice_compare") or {}
    rh = vc.get("register_high")
    if rh and rh.get("verdict") != "match" and rh.get("user") == "chest" and rh.get("ref") in ("mix", "head"):
        return "高音は原曲がミックスで運んでいます。地声で押し上げず、軽く前に当てるのが近道です。"
    if rh and rh.get("verdict") != "match" and rh.get("user") == "head" and rh.get("ref") in ("mix", "chest"):
        return "原曲より薄い裏声に逃げ気味。声帯の閉じを少し足してミックスに寄せましょう。"
    # 検知された発声課題があればそれを総評にする（カードのheadlineと診断を一致させる）
    try:
        from app.coaching import voice_coach
        issues = voice_coach.diagnose(a, c)
        if issues:
            return _HEADLINE_BY_ISSUE.get(issues[0]["id"], "発声をさらに磨いていきましょう。")
    except Exception:
        pass
    if vc.get("ring", {}).get("verdict") == "weaker":
        return "原曲より響きが奥に。声を前歯〜鼻のあたりに集めると、芯が出て前に通ります。"
    return "発声の土台は良好です。響きと支えをさらに磨いていきましょう。"


def build_voice_good_points(a: dict, c: Optional[dict]) -> list[str]:
    """発声の良い点（原曲一致・閉じのバランス・響き・支え・音域）。"""
    pts: list[str] = []
    align = (c or {}).get("alignment") or {}
    voice = a.get("voice") or {}
    if align.get("in_tune_score") and align["in_tune_score"] >= 85:
        pts.append(f"原曲のメロディによく沿えています（一致 {align['in_tune_score']}点）。")
    if (voice.get("closure") or {}).get("label") == "balanced":
        pts.append("声帯の閉じが効率的で、息と声のバランスが取れています（flow phonation）。")
    if (voice.get("ring") or {}).get("label") == "strong":
        pts.append("前に通る芯のある響き（シンガーズフォルマント）が出せています。")
    if (voice.get("support") or {}).get("label") == "steady":
        pts.append("伸ばした音が安定していて、息の支えがしっかりしています。")
    f0s = [w.get("f0_mean_hz") for w in (a.get("timeline") or {}).get("per_window", [])
           if w.get("f0_mean_hz") and w["f0_mean_hz"] >= 100]
    if f0s and len(pts) < 3:
        pts.append(f"この録音で {_note_name(min(f0s))}〜{_note_name(max(f0s))} の音域を出せています。")
    if not pts:
        pts.append("最後まで歌い切れています。発声の土台はここからです。")
    return pts[:3]


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


def build_pitch_mistakes(c: Optional[dict]) -> list[dict]:
    """明確に音を外した箇所だけを「秒数つき」で返す（原曲と照合できた時のみ）。

    原曲との一致が確実に測れた区間で、40〜150centずれた所を方向つきで列挙。
    照合できない（原曲なし/低信頼）時は空＝何も出さない（憶測で外しを作らない）。
    """
    align = (c or {}).get("alignment") if c else None
    spots = (align or {}).get("pitch_off_spots") or []
    return [
        {
            "sec": s["user_sec"],
            "cents": s["cents"],
            "direction": s["direction"],
            "dir_jp": "高め" if s["direction"] == "sharp" else "低め",
        }
        for s in spots
    ]


def build_feedback_payload(a: dict, c: Optional[dict], task: Optional[dict],
                           ref_attempted: bool = False, include_voice_type: bool = False) -> dict:
    """発声特化の採点カード payload（docs/21）。原曲と比較した発声FBを1枚に集約。

    include_voice_type: 声タイプ診断（シェア用フック）を載せるか。初回録音の時だけ True。
    """
    scores = scoring.voice_scores(a, c)
    align = (c or {}).get("alignment") if c else None
    compared = bool(align and align.get("in_tune_score") is not None)
    voice_type = None
    if include_voice_type:
        try:
            from app.coaching import voice_coach
            voice_type = voice_coach.classify_voice_type(a)
        except Exception:
            voice_type = None
    payload = {
        "scores": scores,
        "focus": "voice",                                  # 発声特化カードであることの目印
        "voice_type": voice_type,                          # 声タイプ診断（シェア用フック）
        "headline": build_headline(a, c),                  # 発声の一言総評（原曲比較）
        "axes": build_voice_axes(a, c, ref_attempted),     # 音程/鳴り・効率/声区/支え
        "pitch_mistakes": build_pitch_mistakes(c),         # 明確に外した箇所（秒数つき）
        "good_points": build_voice_good_points(a, c),
        "voice_profile": build_voice_profile(a),
        "today_task": None,
        "compare_note": (
            "原曲は受け取りましたが、今回はうまく重ね合わせられませんでした。"
            "サビなど同じ区間を、歌い出しのタイミングを合わせてもう一度録ると、"
            "発声や音程を原曲と比べられます🎤"
            if (ref_attempted and not compared) else None
        ),
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


# 前回→今回で比べる音響指標（docs/91: 同一課題フォーカス＋微改善の励まし）。
# direction: +1=増加が良い / -1=減少が良い / 0=目標帯へ近づくのが良い(H1-H2)。
# floor: これ未満の変化は測定ゆらぎとして拾わない（嘘の励ましをしない）。
# nd: 表示の小数桁数。
# spoken: ユーザーに口に出す体感語（docs/42 §6: 生の数値・単位は文面に出さない。
#         「40→34cents」は生徒に何も伝わらないため、数値は内部根拠にとどめ体感に翻訳する）。
_MICRO_METRICS: list[tuple[str, str, str, int, float, int, str]] = [
    ("f0_jitter_cents", "音程の細かな揺れ", "cents", -1, 1.0, 0,
     "声の揺れが落ち着いて、ピッチがまっすぐ保てるようになってきました"),
    ("long_tone_stability", "伸ばした音の安定度", "cents", -1, 2.0, 0,
     "伸ばした音が最後までまっすぐ安定するようになってきました"),
    ("cpp_db", "声の芯（CPP）", "dB", +1, 0.3, 1,
     "声に芯が出て、張りのある響きになってきました"),
    ("hnr_db", "声のクリアさ（HNR）", "dB", +1, 0.5, 1,
     "声の雑味が減って、クリアに通るようになってきました"),
    ("h1h2_db", "声帯の閉じ（H1-H2）", "dB", 0, 0.5, 1,
     "息と声のバランスがちょうど良い閉じ具合に近づいています"),
    ("singers_formant_ratio", "響き（シンガーズフォルマント比）", "", +1, 0.0005, 4,
     "声の響きが前に飛ぶようになってきました"),
    ("shimmer_pct", "声量の細かな揺れ（Shimmer）", "%", -1, 0.3, 1,
     "声量のムラが減って、音がなめらかにつながるようになってきました"),
    ("jitter_pct", "声の周期の揺れ（Jitter）", "%", -1, 0.05, 2,
     "声のざらつきにつながる細かな揺れが減ってきました"),
    ("rms_db_range", "強弱の幅（ダイナミクス）", "dB", +1, 1.0, 0,
     "強弱の表現の幅が広がってきました"),
]

# flow phonation（息漏れ⇔締めすぎの中庸）の目安。H1-H2 はこの値へ近づけば「方向性が合っている」
H1H2_TARGET_DB = 4.5


def build_micro_progress(baseline: dict, current: dict) -> dict:
    """前回と今回の音響指標を比べ、「わずかでも良くなった点」を実測で拾う（docs/91）。

    同じ課題にフォーカスし続けてもユーザーが萎えないよう、ノイズ床を超えた微改善を
    具体的な数値つきで検知し、励まし（「少しずつ良くなっていますよ」）の根拠にする。
    改善が無ければ無いと正直に返す（捏造の励ましをしない＝docs/42 §5。gains が空なら
    呼び出し側は取り組み自体を認める文面に切り替える）。
    戻り: {"gains": [数値つき内部根拠1行, ...最大3件],
          "spoken": [gains と同順の体感語（ユーザーに口に出す文）],
          "any_gain": bool}
    gains は判定根拠・LLMへの事実供給用で、そのままユーザーに見せない（docs/42 §6:
    生の数値比較は生徒に伝わらないため、口に出すのは spoken の体感語）。
    """
    gains: list[str] = []
    spoken: list[str] = []
    for key, label, unit, direction, floor, nd, speak in _MICRO_METRICS:
        b, cur = (baseline or {}).get(key), (current or {}).get(key)
        if b is None or cur is None:
            continue
        if direction == 0:
            # 目標帯へ近づいたか（H1-H2: 息漏れ⇔締めすぎ の中庸に寄れば改善）
            improvement = abs(b - H1H2_TARGET_DB) - abs(cur - H1H2_TARGET_DB)
            note = "ちょうど良い閉じのバランスに近づいた"
        else:
            improvement = (cur - b) * direction
            note = "良くなっている"
        if improvement < floor:
            continue
        fmt = f"{{:.{nd}f}}"
        gains.append(f"{label}: 前回{fmt.format(b)}{unit}→今回{fmt.format(cur)}{unit}（{note}）")
        spoken.append(speak)
    return {"gains": gains[:3], "spoken": spoken[:3], "any_gain": bool(gains)}


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
