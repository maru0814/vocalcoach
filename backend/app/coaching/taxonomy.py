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


# --- 個別の diagnose / reason / achieve ---

def _diag_long_tone_decay(a: dict, c: Optional[dict]) -> bool:
    decay = _max_rms_decay(a)
    return decay is not None and decay[2] <= -6.0


def _reason_long_tone_decay(a: dict, c: Optional[dict]) -> str:
    decay = _max_rms_decay(a)
    if not decay:
        return "長いフレーズで声が小さくなっていく傾向があります。"
    s, e, d = decay
    return (
        f"{s:.0f}〜{e:.0f}秒の長いフレーズで、声の大きさが {abs(d):.0f}dB"
        f"（けっこう大きい差）下がっています。フレーズの後半で息の支えが切れているサインです。"
    )


def _achieve_long_tone_decay(a: dict) -> bool:
    decay = _max_rms_decay(a)
    if decay is None:
        # 長いフレーズが無い＝基礎練単音なら long_tone_stability で判定
        lts = a.get("long_tone_stability")
        return lts is not None and lts <= 30
    return decay[2] > -3.0


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
        "id": "pitch_wobble",
        "label": "音程の細かい揺れをおさえる",
        "priority": 3,
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
        "priority": 4,
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
        "id": "expression_flat",
        "label": "強弱（ダイナミクス）をつける",
        "priority": 5,
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


def diagnose_task(analysis: dict, compare_data: Optional[dict]) -> Optional[dict]:
    """優先度順に診断し、最初に該当した課題を1つ返す。なければ None。"""
    for task in sorted(TASKS, key=lambda t: t["priority"]):
        try:
            if task["diagnose"](analysis, compare_data):
                return task
        except Exception:
            continue
    return None


def get_task(task_id: str) -> Optional[dict]:
    for t in TASKS:
        if t["id"] == task_id:
            return t
    return None
