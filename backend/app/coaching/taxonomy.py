"""
課題タクソノミー（道具不要の基礎練 + YouTube実演動画）。
SKILL.md の課題タクソノミーを構造化データに落としたもの。

各課題は:
  - id / label
  - priority: 小さいほど優先（声基礎欠損 → 音程 → ミックス → リズム → 表現）
  - diagnose(analysis, compare) -> bool: その課題に該当するか
  - reason(analysis, compare) -> str: 診断根拠（秒数・数値を含む人間向け説明）
  - practices: 道具不要の基礎練（手順 + 実演動画URL）
  - achieve(analysis) -> bool: Phase D の達成判定
  - achieve_label: 達成基準の説明
"""

from __future__ import annotations

from typing import Callable, Optional


def _g(d: Optional[dict], key: str):
    if not d:
        return None
    return d.get(key)


def _worst_sustained(analysis: dict) -> Optional[dict]:
    """最も f0 が揺れているロングトーン区間（声以外の極低音は除外）。"""
    segs = [
        s for s in analysis.get("timeline", {}).get("sustained_segments", [])
        if (s.get("mean_f0_hz") or 0) >= 150 and s.get("duration_sec", 0) >= 0.6
    ]
    if not segs:
        return None
    return max(segs, key=lambda s: s.get("f0_std_cents") or 0)


def _max_rms_decay(analysis: dict) -> Optional[tuple[float, float, float]]:
    """5秒以上の連続発声フレーズの中で最大のRMS減衰 (start, end, decay_db) を返す。"""
    pw = analysis.get("timeline", {}).get("per_window", [])
    voiced = [w for w in pw if (w.get("voiced_ratio") or 0) >= 0.8 and w.get("rms_db") is not None]
    if len(voiced) < 5:
        return None
    best = None
    run = [voiced[0]]
    for w in voiced[1:]:
        if w["t_sec"] - run[-1]["t_sec"] <= 1.5:
            run.append(w)
        else:
            run = [w]
        if len(run) >= 5:
            head = run[0]["rms_db"]
            tail = run[-1]["rms_db"]
            decay = tail - head
            if best is None or decay < best[2]:
                best = (run[0]["t_sec"], run[-1]["t_sec"], decay)
    return best


def _voiced_windows(a: dict) -> list[dict]:
    pw = a.get("timeline", {}).get("per_window", [])
    return [w for w in pw if w.get("rms_db") is not None and (w.get("voiced_ratio") or 0) >= 0.5]


def _median(xs: list[float]) -> Optional[float]:
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _segment_energy(a: dict, start: float, end: float) -> Optional[float]:
    ws = [w["rms_db"] for w in _voiced_windows(a) if start <= w["t_sec"] <= end]
    return sum(ws) / len(ws) if ws else None


def _real_holds(a: dict) -> list[dict]:
    """本物の伸ばし（音程が一定に保たれた区間。analyzer が音程で再分割済み）。

    1.2秒以上・歌声帯域(>=100Hz)のものだけ。メロディの一節は含めない。
    """
    return [
        s for s in a.get("timeline", {}).get("sustained_segments", [])
        if (s.get("duration_sec") or 0) >= 1.2 and (s.get("mean_f0_hz") or 0) >= 100
    ]


def _worst_decaying_hold(a: dict) -> Optional[dict]:
    """伸ばしの中で最も音量が落ちているものを返す。"""
    cand = [h for h in _real_holds(a) if h.get("rms_decay_db") is not None]
    if not cand:
        return None
    return min(cand, key=lambda h: h["rms_decay_db"])


def projection_point(a: dict) -> Optional[dict]:
    """張りどころ（曲の山＝最も高い伸ばし）と、そこで声を張れているかを返す。

    判定: 周囲より声量がある(strong) かつ 音程が安定(stable) かつ 裏声に逃げていない。
    """
    segs = [
        s for s in a.get("timeline", {}).get("sustained_segments", [])
        if (s.get("mean_f0_hz") or 0) >= 220 and s.get("duration_sec", 0) >= 0.5
    ]
    if not segs:
        return None
    top = max(segs, key=lambda s: s.get("mean_f0_hz") or 0)
    energy = _segment_energy(a, top["start_sec"], top["end_sec"])
    med = _median([w["rms_db"] for w in _voiced_windows(a)])
    f0_std = top.get("f0_std_cents") or 0
    vt = top.get("voice_type_estimate")
    strong = energy is not None and med is not None and energy >= med
    projected = bool(strong and f0_std <= 50 and vt in ("chest", "mix"))
    return {
        "start_sec": top["start_sec"],
        "end_sec": top["end_sec"],
        "mean_f0_hz": top["mean_f0_hz"],
        "f0_std_cents": f0_std,
        "voice_type": vt,
        "projected": projected,
    }


# --- 個別の diagnose / reason / achieve ---

def _diag_long_tone_decay(a: dict, c: Optional[dict]) -> bool:
    # 本物の伸ばし（音程が一定の区間）の後半で音量が大きく落ちている時だけ発火。
    # 連続発声＝メロディは「伸ばし」と数えないので、自然な強弱表現は誤検出しない。
    h = _worst_decaying_hold(a)
    return h is not None and (h.get("rms_decay_db") or 0) <= -6.0


def _reason_long_tone_decay(a: dict, c: Optional[dict]) -> str:
    h = _worst_decaying_hold(a)
    if not h:
        return "長く伸ばす音の後半で、息の支えが切れて音量が落ちる傾向があります。"
    s, e, d = h["start_sec"], h["end_sec"], (h.get("rms_decay_db") or 0)
    note = _note_label(h.get("mean_f0_hz"))
    dur = h.get("duration_sec") or (e - s)
    drift = h.get("end_drift_cents")
    extra = ""
    if drift is not None and drift <= -40:
        extra = f"音程も後半で約{abs(drift):.0f}cents（半音の100分の1単位）下がっています。"
    return (
        f"{s:.0f}〜{e:.0f}秒の{note}あたりの伸ばし（約{dur:.0f}秒）で、"
        f"音量が約{abs(d):.0f}dB下がっています。{extra}"
        f"フレーズ後半で息の支えが切れているサインです（音量を弱める表現とは別物です）。"
    )


def _achieve_long_tone_decay(a: dict) -> bool:
    h = _worst_decaying_hold(a)
    if h is None:
        # 伸ばしが無い（基礎練単音など）なら long_tone_stability で判定
        lts = a.get("long_tone_stability")
        return lts is not None and lts <= 30
    return (h.get("rms_decay_db") or 0) > -3.0


def _diag_throat_tension(a: dict, c: Optional[dict]) -> bool:
    seg = _worst_sustained(a)
    # 高めの centroid（音が硬い）かつ rolloff/f0 比が地声寄りで詰まり気味
    if not seg:
        return False
    return (seg.get("spectral_centroid_hz") or 0) >= 2700 and (seg.get("f0_std_cents") or 0) >= 80


def _reason_throat_tension(a: dict, c: Optional[dict]) -> str:
    seg = _worst_sustained(a)
    if not seg:
        return "声に詰まり（喉の力み）が感じられます。"
    return (
        f"{seg['start_sec']:.0f}〜{seg['end_sec']:.0f}秒の伸ばしで、音色が硬め"
        f"（明るさの指標が {seg['spectral_centroid_hz']:.0f}Hz と高め）です。"
        f"喉まわりに力みが入っている可能性があります。"
    )


def _achieve_throat_tension(a: dict) -> bool:
    seg = _worst_sustained(a)
    return seg is not None and (seg.get("spectral_centroid_hz") or 9999) < 2400


def _diag_no_vibrato(a: dict, c: Optional[dict]) -> bool:
    return a.get("vibrato_rate_hz") is None


def _reason_no_vibrato(a: dict, c: Optional[dict]) -> str:
    return (
        "伸ばす音に、はっきりしたビブラート（音をゆらす技術）が検出できませんでした。"
        "まっすぐ伸ばすのも良いですが、ゆらしを意図的にかけられると表現の幅が広がります。"
    )


def _achieve_no_vibrato(a: dict) -> bool:
    r = a.get("vibrato_rate_hz")
    d = a.get("vibrato_depth_cents")
    return r is not None and 4.0 <= r <= 7.5 and (d is None or d >= 30)


def _diag_pitch_wobble(a: dict, c: Optional[dict]) -> bool:
    j = a.get("f0_jitter_cents")
    return j is not None and j > 20


def _reason_pitch_wobble(a: dict, c: Optional[dict]) -> str:
    j = a.get("f0_jitter_cents")
    return (
        f"音程の細かい揺れ（ジッター）が {j:.0f}cents（セント＝半音の100分の1）あります。"
        f"15cents以下だと安定して聞こえます。少しだけ音程が定まりにくい状態です。"
    )


def _achieve_pitch_wobble(a: dict) -> bool:
    j = a.get("f0_jitter_cents")
    return j is not None and j <= 15


def _high_segment(a: dict) -> Optional[dict]:
    """高めの音（おおむねE4=330Hz以上）の伸ばし区間で、最も不安定なものを返す。"""
    segs = [
        s for s in a.get("timeline", {}).get("sustained_segments", [])
        if (s.get("mean_f0_hz") or 0) >= 330 and s.get("duration_sec", 0) >= 0.6
    ]
    if not segs:
        return None
    return max(segs, key=lambda s: s.get("f0_std_cents") or 0)


def _diag_mixed_voice(a: dict, c: Optional[dict]) -> bool:
    """換声点付近の高音が崩れている＝ミックスボイスの課題。

    高音の伸ばしが揺れている(地声で押して苦しい/裏返る)、または
    高音区間が地声(chest)で f0 が大きく揺れているケースを拾う。
    """
    seg = _high_segment(a)
    if not seg:
        return False
    unstable = (seg.get("f0_std_cents") or 0) >= 50
    chest_strain = seg.get("voice_type_estimate") == "chest" and (seg.get("f0_std_cents") or 0) >= 40
    return unstable or chest_strain


def _reason_mixed_voice(a: dict, c: Optional[dict]) -> str:
    seg = _high_segment(a)
    if not seg:
        return "高い音をミックスボイスで楽に出せると、サビがぐっと安定します。"
    vt = {"chest": "地声で押している", "head": "裏声に逃げている", "mix": "ミックス気味"}.get(
        seg.get("voice_type_estimate"), "力みがある"
    )
    return (
        f"{seg['start_sec']:.0f}〜{seg['end_sec']:.0f}秒の高い音（{_note_label(seg['mean_f0_hz'])}あたり）で、"
        f"{vt}ようで、音が揺れています（{seg['f0_std_cents']:.0f}cents＝半音の100分の1）。"
        f"ここをミックスボイス（地声と裏声の中間）で出すと、力まず安定しますよ。"
    )


def _achieve_mixed_voice(a: dict) -> bool:
    seg = _high_segment(a)
    if seg is not None:
        return (seg.get("f0_std_cents") or 999) <= 30
    # 高音区間が無い基礎練単体なら、ジッターの安定で代替判定
    j = a.get("f0_jitter_cents")
    return j is not None and j <= 18


def _note_label(hz: Optional[float]) -> str:
    if not hz:
        return "—"
    import math
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    midi = round(69 + 12 * math.log2(hz / 440.0))
    return f"{names[midi % 12]}{midi // 12 - 1}"


def _diag_rhythm_lag(a: dict, c: Optional[dict]) -> bool:
    align = (c or {}).get("alignment") if c else None
    if align and align.get("mean_lag_sec") is not None:
        return abs(align["mean_lag_sec"]) >= 0.25
    # アライメントが無ければテンポ差で代替（half/double誤判定は除外）
    if c and c.get("tempo_diff_bpm") is not None:
        td = abs(c["tempo_diff_bpm"])
        return 6 < td < 40
    return False


def _reason_rhythm_lag(a: dict, c: Optional[dict]) -> str:
    align = (c or {}).get("alignment") if c else None
    if align and align.get("mean_lag_sec") is not None:
        lag = align["mean_lag_sec"]
        dir_ = "遅れ気味（モタり）" if lag > 0 else "早め（走り）"
        spots = align.get("worst_segments") or []
        extra = ""
        if spots:
            extra = "特に " + "、".join(f"{w['user_sec']:.0f}秒あたり" for w in spots[:2]) + " でズレています。"
        return f"原曲と比べてリズムが約{abs(lag):.2f}秒{dir_}です。{extra}"
    return "原曲とテンポがずれ気味です。拍に合わせる練習をしましょう。"


def _achieve_rhythm_lag(a: dict) -> bool:
    # 単体録音では判定材料が乏しいので、ジッターが安定していれば良しとする簡易判定
    j = a.get("f0_jitter_cents")
    return j is not None and j <= 20


def _diag_expression_flat(a: dict, c: Optional[dict]) -> bool:
    if c and c.get("rms_db_range_diff") is not None:
        return c["rms_db_range_diff"] < -8  # 原曲より強弱が小さい
    rng = a.get("rms_db_range")
    return rng is not None and rng < 8


def _reason_expression_flat(a: dict, c: Optional[dict]) -> str:
    return (
        "声の大きさの幅（強弱・ダイナミクス）が小さめで、平らに聞こえやすい状態です。"
        "サビと静かな部分で音量の差をつけると、感情が伝わりやすくなります。"
    )


def _achieve_expression_flat(a: dict) -> bool:
    rng = a.get("rms_db_range")
    return rng is not None and rng >= 12


TASKS: list[dict] = [
    {
        "id": "throat_tension",
        "label": "喉の力み（詰まり）をとる",
        "priority": 1,
        "diagnose": _diag_throat_tension,
        "reason": _reason_throat_tension,
        "achieve": _achieve_throat_tension,
        "achieve_label": "伸ばした音の硬さ（明るさ指標）が下がる",
        "practices": [
            {
                "name": "あくび → ロングトーン",
                "steps": [
                    "本気のあくびを1回する（フリではなく本物）。",
                    "あくびの瞬間の『喉の奥が縦に広がる感覚』を覚える。",
                    "あくびの形のまま、口を閉じずに『ハーー』と8秒伸ばす。",
                    "喉が締まったら、すぐ『ハハハ』と笑って喉を開き直して再挑戦。",
                ],
                "checkpoint": "『ハーー』が太く丸く響き、喉仏が下がっていれば成功。",
                "video": {"title": "喉がどんどん開くトレーニング（道具なし）", "url": "https://www.youtube.com/watch?v=H43qzWSYWuE"},
            },
            {
                "name": "笑い → 発声",
                "steps": [
                    "『ハハハ！』と本気で笑った時の喉のゆるみを覚える。",
                    "その喉のまま『ハー』と4〜8秒伸ばす。",
                ],
                "checkpoint": "喉に力みが入らず、ラクに声が出ていれば成功。",
                "video": {"title": "響く声になるあくび声トレ", "url": "https://www.youtube.com/watch?v=tE_JxKjWka4"},
            },
        ],
    },
    {
        "id": "long_tone_decay",
        "label": "ロングトーンの後半安定（息の支え）",
        "priority": 2,
        "diagnose": _diag_long_tone_decay,
        "reason": _reason_long_tone_decay,
        "achieve": _achieve_long_tone_decay,
        "achieve_label": "長いフレーズ中の音量の落ち込みが3dB以内",
        "practices": [
            {
                "name": "スーッ呼吸（ロングブレス）",
                "steps": [
                    "お腹（おへその少し上）に手を当てて立つ。肩は上げない。",
                    "鼻から3秒で吸い、お腹を前にふくらませる。",
                    "上下の前歯を軽くつけ、その隙間から『スーー』と細く一定に吐く。",
                    "最初は15秒 → 慣れたら30秒 → 45秒を目標に伸ばす。",
                ],
                "checkpoint": "『スー』の太さが最後まで一定で、終わった時お腹の横が温かければ成功。",
                "video": {"title": "ロングブレスをGETしよう（声楽式）", "url": "https://www.youtube.com/watch?v=Hp8C8NsvPdc"},
            },
            {
                "name": "ドッグブレス",
                "steps": [
                    "口を半開きにして、お腹に手を当てる。",
                    "『ハッハッハッ』と速く浅く吐く（1秒に2〜3回）。",
                    "吸うのは意識しない。お腹が小刻みに動くのを感じる。",
                    "15秒続けて5秒休む。3セット。",
                ],
                "checkpoint": "肩が動かず、お腹（みぞおち下）だけが動いていれば成功。",
                "video": {"title": "ボーカリストのための超基本！ドッグブレス", "url": "https://www.youtube.com/watch?v=FDIGjxdQLwI"},
            },
            {
                "name": "バ行スタッカート → ロングトーン",
                "steps": [
                    "中音域で『バッ バッ バッ バッ』と短く4回（1拍ずつ）。",
                    "その直後に同じ音で『バーーーー』と8拍伸ばす。",
                    "半音ずつ上げて無理ない範囲で5音くり返す。",
                ],
                "checkpoint": "『バーー』の音量が8拍最後まで一定なら成功。",
                "video": {"title": "スタッカートで呼吸練習（小野正利）", "url": "https://www.youtube.com/watch?v=dH1Ouz1gMXI"},
            },
        ],
    },
    {
        "id": "mixed_voice",
        "label": "ミックスボイスで高音を楽に出す",
        "priority": 3,
        "diagnose": _diag_mixed_voice,
        "reason": _reason_mixed_voice,
        "achieve": _achieve_mixed_voice,
        "achieve_label": "高音の伸ばしの揺れが30cents以下（地声で押さず安定）",
        "practices": [
            {
                "name": "① ハミング（鼻に響かせる）",
                "steps": [
                    "口を閉じて「ンー」と軽く鼻に響かせる。下の前歯の裏がムズムズ振動する位置を探す。",
                    "その響きを保ったまま、低めの音から少しずつ高くしていく。",
                    "力まず、響きが鼻に集まる感覚をつかむ。",
                ],
                "checkpoint": "鼻のあたりがムズムズ振動していれば、共鳴の入口に乗れています。",
                "video": {"title": "ミックスボイスの基礎・ハミング", "url": "https://www.youtube.com/watch?v=H43qzWSYWuE"},
            },
            {
                "name": "② ネイネイ（細い声で換声点をつなぐ）",
                "steps": [
                    "ちょっと意地悪な魔女の声で「ねぃ、ねぃ、ねぃ」と言う（鼻にかかった細い声）。",
                    "その細い声のまま、1音ずつ半音上げていく。",
                    "地声から裏声に切り替わる『換声点』で、裏返らずスッと細くつなぐのが目標。",
                ],
                "checkpoint": "高くしても急に裏返らず、細いまま音がつながれば成功です。",
                "video": {"title": "ネイネイで換声点をつなぐ練習", "url": "https://www.youtube.com/watch?v=dH1Ouz1gMXI"},
            },
            {
                "name": "③ ナンナン（口の響きで厚みを足す）",
                "steps": [
                    "②ができたら「なん、なん、なん」と、口の中を少し広げて言う。",
                    "鼻の響き（①）を保ったまま、口の響きを足して声に厚みを出す。",
                    "細さと厚みのバランスがとれた声が、ミックスボイスです。",
                ],
                "checkpoint": "細いけれど芯がある声になっていれば、ミックスに近づいています。",
                "video": {"title": "ミックスボイスの出し方・まとめ", "url": "https://www.youtube.com/watch?v=xpV4GO4kpds"},
            },
        ],
    },
    {
        "id": "pitch_wobble",
        "label": "音程の細かい揺れをおさえる",
        "priority": 4,
        "diagnose": _diag_pitch_wobble,
        "reason": _reason_pitch_wobble,
        "achieve": _achieve_pitch_wobble,
        "achieve_label": "音程の揺れ（ジッター）が15cents以下",
        "practices": [
            {
                "name": "リップロール → 母音ロングトーン",
                "steps": [
                    "唇を軽く閉じて『ブルルル』と息で唇を震わせる（リップロール）。",
                    "10秒できたら、同じ息の流れで『アーー』に切り替える。",
                    "音程を一定に保つことだけ意識する。",
                ],
                "checkpoint": "リップロールが途切れず続き、母音に移っても音程が動かなければ成功。",
                "video": {"title": "喉を開く発声のコツ", "url": "https://www.youtube.com/watch?v=H43qzWSYWuE"},
            },
        ],
    },
    {
        "id": "no_vibrato",
        "label": "ビブラート（音のゆらし）を身につける",
        "priority": 5,
        "diagnose": _diag_no_vibrato,
        "reason": _reason_no_vibrato,
        "achieve": _achieve_no_vibrato,
        "achieve_label": "ビブラートが秒4〜7回・適度な深さで出る",
        "practices": [
            {
                "name": "お腹ゆらしビブラート",
                "steps": [
                    "中音域で『アーー』と伸ばす。",
                    "お腹を『ハッハッ』と軽く押す感じで、音を上下にゆらす。",
                    "最初はゆっくり、慣れたら秒4〜6回のペースへ。",
                ],
                "checkpoint": "音が一定の速さで規則正しくゆれていれば成功。",
                "video": {"title": "ビブラートのかけ方と練習方法", "url": "https://www.youtube.com/watch?v=dH1Ouz1gMXI"},
            },
        ],
    },
    {
        "id": "rhythm_lag",
        "label": "リズム（拍の合わせ方）を整える",
        "priority": 6,
        "diagnose": _diag_rhythm_lag,
        "reason": _reason_rhythm_lag,
        "achieve": _achieve_rhythm_lag,
        "achieve_label": "拍に合わせて安定して歌える",
        "practices": [
            {
                "name": "メトロノーム手拍子 → 歌",
                "steps": [
                    "スマホのメトロノームを60BPMに設定する（無料アプリでOK）。",
                    "まず拍に合わせて手拍子だけを30秒。",
                    "次に、歌詞の頭の音を手拍子のタイミングにぴったり合わせて歌う。",
                    "走りやすい人は『拍より少し後ろ』、モタる人は『拍ぴったり』を意識。",
                ],
                "checkpoint": "歌い出しの音が、毎回同じタイミングで拍に乗っていれば成功。",
                "video": {"title": "リズム感を鍛える練習（スタッカート発声法）", "url": "https://www.youtube.com/watch?v=xpV4GO4kpds"},
            },
        ],
    },
    {
        "id": "expression_flat",
        "label": "強弱（ダイナミクス）をつける",
        "priority": 7,
        "diagnose": _diag_expression_flat,
        "reason": _reason_expression_flat,
        "achieve": _achieve_expression_flat,
        "achieve_label": "声の大きさの幅（強弱）が広がる",
        "practices": [
            {
                "name": "弱→強→弱クレッシェンド",
                "steps": [
                    "1つの音『アーー』を、小さく始めて → だんだん大きく → また小さく。",
                    "8拍かけて山なりに音量を変える。",
                    "音程は変えず、音量だけを動かす。",
                ],
                "checkpoint": "音量がなめらかに大きく・小さく変化できれば成功。",
                "video": {"title": "スタッカートとレガートの発声練習", "url": "https://www.youtube.com/watch?v=xpV4GO4kpds"},
            },
        ],
    },
]


def diagnose_task(
    analysis: dict, compare_data: Optional[dict], exclude: Optional[list[str]] = None
) -> Optional[dict]:
    """優先度順に診断し、最初に該当した課題を1つ返す。なければ None。

    exclude: 除外する課題ID（「別の課題に変える」で直前の課題を避けるため）。
    """
    exclude = exclude or []
    for task in sorted(TASKS, key=lambda t: t["priority"]):
        if task["id"] in exclude:
            continue
        try:
            if task["diagnose"](analysis, compare_data):
                return task
        except Exception:
            continue
    return None


def list_weaknesses(
    analysis: dict,
    compare_data: Optional[dict] = None,
    limit: int = 3,
    exclude: Optional[list[str]] = None,
) -> list[dict]:
    """該当する弱点を優先度順に最大 limit 件返す。

    「他に気になるところは？」への回答や、LLM文脈への候補注入に使う。
    各要素: {"id", "label", "reason"}。reason は秒数・数値を含む人間向け説明。
    """
    exclude = exclude or []
    out: list[dict] = []
    for task in sorted(TASKS, key=lambda t: t["priority"]):
        if task["id"] in exclude:
            continue
        try:
            if not task["diagnose"](analysis, compare_data):
                continue
            reason = task["reason"](analysis, compare_data)
        except Exception:
            continue
        out.append({"id": task["id"], "label": task["label"], "reason": reason})
        if len(out) >= limit:
            break
    return out


def get_task(task_id: str) -> Optional[dict]:
    for t in TASKS:
        if t["id"] == task_id:
            return t
    return None
