"""発声の診断ツリー（資料3章）とアンザッツ処方・エクササイズ master DB（資料4-6章）。

解析値（CPP/H1-H2/Jitter/Shimmer/HNR/声区/シンガーズフォルマント/ビブラート/ロングトーン）から
発声課題(issue)を severity つきで判定し、課題に合うアンザッツ処方とエクササイズだけを
LLM に注入（RAG）するためのデータと関数を提供する。捏造防止のため、判定根拠(evidence)は
実測値のみを持たせる。
"""

from __future__ import annotations

from typing import Optional

from app.audio.voice_lab import (
    CPP_NORMAL_DB, HNR_LOW_DB, JITTER_HIGH_PCT, SHIMMER_HIGH_PCT,
)

# ============================================================================
# エクササイズ master DB（資料6.2）。issueに合致するカテゴリだけLLMへ注入する。
# ============================================================================
EXERCISES: dict[str, dict] = {
    # A: 呼吸・体幹・声門下圧（Appoggio / MEAD）
    "A1": {"cat": "A", "name": "「フ」「ス」のロングトーン摩擦音",
           "mechanism": "歯と唇で抵抗を作り声門下圧を一定に保つ呼吸筋(アッポッジョ)を働かせる",
           "how": "上の歯と下唇で『フーー』と摩擦音を作り10秒間一定の圧力をキープ。お腹周りが張り続ける感覚を覚える"},
    "A2": {"cat": "A", "name": "スタッカート・パンティング(犬の呼吸)",
           "mechanism": "横隔膜と腹横筋の瞬発収縮で、声帯に頼らず息の圧で音の立ち上がりを作る",
           "how": "お腹のポンプで『ハッ、ハッ、ハッ』と短く息を吐き出す"},
    "A3": {"cat": "A", "name": "吸気の背中・肋骨拡張",
           "mechanism": "肺を最大拡張し受動的な呼気力(リコイル)をコントロール可能にする",
           "how": "息を吸う時、肩を上げず背中と肋骨下部が横に広がるのを感じる(浮き輪が膨らむイメージ)"},
    # B: SOVTE（半閉鎖声道）
    "B1": {"cat": "B", "name": "リップロール / タングトリル",
           "mechanism": "声道を半分塞ぎ口腔内圧を高め、声帯への背圧で無駄な力みをリセット",
           "how": "唇をブルブル震わせサイレンのように低音↔高音を行き来。少ない息で効率よく振動させる"},
    "B2": {"cat": "B", "name": "ストロー発声(LaxVox)",
           "mechanism": "細管の強いインピーダンスで声帯衝突を減らしつつストレッチ",
           "how": "細いストローをくわえ『ウー』。可能なら水入りボトルにストローを数cm沈めブクブク鳴らす"},
    "B3": {"cat": "B", "name": "ハミング(m, n, ng)",
           "mechanism": "鼻腔共鳴を開き、ソフトな声帯閉鎖と前方への響きを作る",
           "how": "軽く唇を閉じ『ンー』を鼻の奥〜眉間に集めながらスケール"},
    # C: アンザッツによる喉頭懸垂機構のチューニング
    "C1": {"cat": "C", "ansatz": "1", "name": "アンザッツ1(前斜め上・甲状舌骨筋)",
           "mechanism": "胸骨上部への当てで共鳴腔を拡張(声がこもる時)",
           "how": "胸の真ん中の骨に当てるイメージで、口角を上げて明るく『イェー』"},
    "C2": {"cat": "C", "ansatz": "2", "name": "アンザッツ2(前斜め下・胸骨甲状筋)",
           "mechanism": "喉頭を下げ声道を長く保つ(喉仏が上がりすぎ/F1が高すぎる時)",
           "how": "鎖骨のくぼみへ声を深く下ろすイメージで『ホー』"},
    "C3": {"cat": "C", "ansatz": "4", "name": "アンザッツ4(後ろ斜め上・口蓋喉頭筋)",
           "mechanism": "輪状甲状筋の伸展を補助し高音の張り上げを解く",
           "how": "頭頂・軟口蓋に当てるイメージで、声帯が後ろへ引き伸ばされる空間を作る"},
    "C4": {"cat": "C", "ansatz": "6", "name": "アンザッツ6(後ろ斜め下・輪状咽頭筋)",
           "mechanism": "喉頭を後下方に安定させ高音で声帯を限界までスムーズに伸ばす",
           "how": "後頭部・うなじへ声を引っ張るイメージで発声"},
    "C5": {"cat": "C", "name": "吸気性発声(Inspiratory Vocal Fry)",
           "mechanism": "仮声帯の力みを強制解除し声帯をリラックス(極度の緊張時)",
           "how": "息を『吸いながら』カラスのように『アー』(低めの軋み声)"},
    # D: 声区の融合・ミックス精度
    "D1": {"cat": "D", "ansatz": "3a", "name": "アンザッツ3a(ネイ Nay スケール)",
           "mechanism": "鼻根部に響きを集め声帯筋を働かせチェスト→ミックスの架け橋",
           "how": "鼻根部(目と目の間)に響きを集め、地声のまま高音へ『ネイ』でスケール"},
    "D2": {"cat": "D", "ansatz": "3b", "name": "アンザッツ3b(芯のある裏声)",
           "mechanism": "息漏れのないまろやかな芯のある裏声を作る",
           "how": "裏声のまま息漏れさせず『グ(Gu)』で低音域まで降りてくる"},
    "D3": {"cat": "D", "name": "ボーカルフライからのアタック",
           "mechanism": "極限のリラックスで分厚く合わせ(OQ低下)、声門閉鎖不全を改善",
           "how": "ガラガラ声(ボーカルフライ)を作り、息を流して『あー』と実声に繋げる"},
    # E: フォルマント・チューニング/共鳴
    "E1": {"cat": "E", "name": "母音モディフィケーション",
           "mechanism": "高音でF0がF1を追い越す抵抗を減らすため母音を曖昧化",
           "how": "高音の『ア』に『オ/ウ』を混ぜた深い母音(あくびの喉)にして抜く"},
    "E2": {"cat": "E", "name": "トゥワング(喉頭蓋管の狭窄)",
           "mechanism": "咽頭上部をメガホン状に狭め2.5-3.5kHzにシンガーズフォルマント(Ring)を生成",
           "how": "アヒルの鳴き声/魔女の笑いのように平べったく鋭い声で『抜け』を作る"},
    # F: ビブラート・ダイナミクス
    "F1": {"cat": "F", "name": "ストレートトーン→ビブラート移行",
           "mechanism": "顎/喉仏を揺らす悪癖を消し、呼気圧とCTの自然な拮抗で揺らぎ(4.0-7.5Hz)を誘発",
           "how": "真っ直ぐな声を3秒キープ→みぞおちの圧を少し緩め、自然に揺れるのに任せる"},
    "F2": {"cat": "F", "name": "半音トリル(メトロノーム)",
           "mechanism": "音程を筋肉でコントロールする力を規則的リズムに落とし込む",
           "how": "BPM80でド↔ド♯の半音トリルを『ア・ア・ア・ア』、徐々にテンポを上げる"},
}

# 7アンザッツの当てるイメージ（資料4章）。LLMの説明補強に使う。
ANSATZ_MAP: dict[str, str] = {
    "1": "前斜め上(甲状舌骨筋)・胸骨上部に振動を感じる",
    "2": "前斜め下(胸骨甲状筋)・鎖骨に声を当てる",
    "3a": "地声ベースの声帯筋自律運動・鼻根部に集める",
    "3b": "裏声ベースの声帯筋自律運動・低音でも息漏れさせない",
    "4": "後ろ斜め上(口蓋喉頭筋)・頭頂/軟口蓋に当てる",
    "6": "後ろ斜め下(輪状咽頭筋)・うなじに当てる",
}

# issue → 推奨エクササイズ群（カテゴリ単位でRAG注入）
ISSUE_RX: dict[str, list[str]] = {
    "pulled_chest": ["B1", "B2", "C3", "C4", "E1"],
    "breathy": ["D3", "B3", "A1"],
    "lack_resonance": ["E2", "B3", "C1"],
    "artificial_vibrato": ["F1", "F2"],
    "unstable_support": ["A1", "A2", "A3"],
    "mix_incoordination": ["D1", "D2", "B1"],
}


def _passaggio_hz(a: dict) -> float:
    """f0中央値からおおよその換声点(高音域の張り上げ判定用)。男声≈330/女声≈415。"""
    med = a.get("f0_median_hz") or 200.0
    return 330.0 if med < 175.0 else 415.0


def _hi_hold(a: dict):
    holds = [s for s in (a.get("timeline") or {}).get("sustained_segments", [])
             if (s.get("mean_f0_hz") or 0) >= 150]
    return max(holds, key=lambda s: s.get("mean_f0_hz") or 0) if holds else None


def diagnose(a: dict, c: Optional[dict] = None) -> list[dict]:
    """発声課題を判定（資料3章の6ケース）。戻り: [{id, jp, severity, evidence}]（重い順）。"""
    issues: list[dict] = []
    cpp = a.get("cpp_db")
    h1h2 = a.get("h1h2_db")
    hnr = a.get("hnr_db")
    jit = a.get("jitter_pct")
    shim = a.get("shimmer_pct")
    sf = a.get("singers_formant_ratio")
    vr = a.get("vibrato_rate_hz")
    vd = a.get("vibrato_depth_cents") or 0
    lts = a.get("long_tone_stability")
    hi = _hi_hold(a)
    hi_reg = (hi or {}).get("register")
    hi_hz = (hi or {}).get("mean_f0_hz")

    # ケース1: 張り上げ(Pulled Chest) — 資料ケース1準拠で「力みの兆候(Jitter/Shimmer上昇)」を必須にする。
    #   安定して内転の効いた高音は健全なベルト/ミックスのこともあるので“押し上げ”と断定しない。
    if hi_hz and hi_hz > _passaggio_hz(a) and hi_reg == "chest":
        strain = (jit is not None and jit > JITTER_HIGH_PCT * 1.5) or \
                 (shim is not None and shim > SHIMMER_HIGH_PCT * 1.5)
        if strain:
            issues.append({"id": "pulled_chest", "jp": "高音の張り上げ（力みのサイン）", "severity": "high",
                           "evidence": {"high_note_hz": round(hi_hz), "register": "地声寄り",
                                        "jitter_pct": jit, "shimmer_pct": shim}})

    # ケース2: 息漏れ・声帯閉鎖不全(Breathy / Under-adduction)
    #   H1-H2(声門開放率＝内転の直接指標)が高い=閉じがゆるい、を必須条件にする。
    #   閉じの強い(pressed)声を誤って息漏れと言わないため。CPP低/HNR低 で確証を上げる。
    if h1h2 is not None and h1h2 > 7.0 and (
        (cpp is not None and cpp < 10.0) or (hnr is not None and hnr < 12.0)
    ):
        sev = "high" if (cpp is not None and cpp < 6.0) else "medium"
        issues.append({"id": "breathy", "jp": "息漏れ（声帯の閉じが弱い）", "severity": sev,
                       "evidence": {"cpp_db": cpp, "h1h2_db": h1h2, "hnr_db": hnr}})

    # ケース3: 共鳴不足(Lack of Singer's Formant) — 声は鳴っている(HNR良)が前に集まらない
    if sf is not None and sf < 0.0015 and (hnr is None or hnr >= 14.0):
        issues.append({"id": "lack_resonance", "jp": "響き不足（声が前に集まらない）", "severity": "medium",
                       "evidence": {"singers_formant_ratio": sf}})

    # ケース4: 人工的なビブラート(Wobble/Tremolo)
    if vr is not None and vd >= 15 and (vr < 4.0 or vr > 8.0):
        issues.append({"id": "artificial_vibrato",
                       "jp": "ビブラートの不自然さ（" + ("遅いウォブル" if vr < 4.0 else "速いちりめん") + "）",
                       "severity": "low", "evidence": {"vibrato_rate_hz": vr}})

    # ケース5: 支えの崩れ(Unstable Breath Support / MEAD) — ロングトーンの揺れを主指標に
    if lts is not None and lts > 45:
        issues.append({"id": "unstable_support", "jp": "息の支えの不安定さ（伸ばしが揺れる）", "severity": "high",
                       "evidence": {"long_tone_cents": lts, "shimmer_pct": shim}})

    # ケース6: ミックス精度不良(声区の段差) — 高音で薄い裏声に飛んでいる等
    segs = [s for s in (a.get("timeline") or {}).get("sustained_segments", [])
            if (s.get("mean_f0_hz") or 0) >= 150 and s.get("register_confidence") in ("high", "med")]
    if len(segs) >= 2:
        regs = [s.get("register") for s in segs]
        if "chest" in regs and "head" in regs and "mix" not in regs:
            issues.append({"id": "mix_incoordination", "jp": "声区の段差（ミックスの繋ぎが不安定）",
                           "severity": "medium", "evidence": {"registers": regs}})

    order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda x: order.get(x["severity"], 3))
    return issues


def prescriptions_for(issue_ids: list[str]) -> list[dict]:
    """課題に合うエクササイズ(打ち手)だけを返す（LLMへのRAG注入用・重複除去）。"""
    seen: set[str] = set()
    out: list[dict] = []
    for iid in issue_ids:
        for ex_id in ISSUE_RX.get(iid, []):
            if ex_id in seen or ex_id not in EXERCISES:
                continue
            seen.add(ex_id)
            ex = EXERCISES[ex_id]
            item = {"id": ex_id, "name": ex["name"], "mechanism": ex["mechanism"], "how": ex["how"]}
            if ex.get("ansatz"):
                item["ansatz"] = ex["ansatz"]
            out.append(item)
    return out[:5]   # トークン節約のため上位5件


def primary_issue(issues: list[dict]) -> Optional[dict]:
    return issues[0] if issues else None


# ============================================================================
# 声タイプ診断（3軸＝声の成分バランス／響き／音色 → 8タイプ）。シェア用の入口フック。
# 軸1 地声成分↔裏声成分: H1-H2(開放率)＋声区。 軸2 パワフル↔エアリー: CPP/HNR(芯・雑音)。
# 軸3 クリア↔ディープ: スペクトル傾斜(高域の量＝明るさ)。各軸の絶対しきい値はマイク等で
# ドメイン依存のため「近い傾向」として見せる（断定しない）。実ラベル音源で要再較正。
# ============================================================================
VOICE_TYPES: dict[tuple, dict] = {
    ("chest", "power", "clear"): {
        "id": "rock", "name": "Rock Voice", "emoji": "🔥",
        "desc": "芯のある地声成分で、明るくまっすぐ前に出るパワフルな声。",
        "artists": {"female": ["LiSA", "アイナ・ジ・エンド"], "male": ["Mrs. GREEN APPLE", "稲葉浩志(B'z)", "優里"]}},
    ("chest", "power", "deep"): {
        "id": "groovy", "name": "Groovy Voice", "emoji": "🎙",
        "desc": "太く温かい地声成分。厚みのある低音で聴かせる声。",
        "artists": {"female": ["Superfly", "あいみょん"], "male": ["玉置浩二", "鈴木雅之"]}},
    ("chest", "airy", "clear"): {
        "id": "pop", "name": "Pop Voice", "emoji": "🌤",
        "desc": "自然体で親しみやすい、軽やかで明るい地声成分の声。",
        "artists": {"female": ["aiko", "いきものがかり"], "male": ["北村匠海", "マカロニえんぴつ"]}},
    ("chest", "airy", "deep"): {
        "id": "mysterious", "name": "Mysterious Voice", "emoji": "🌒",
        "desc": "翳りのある深い地声成分。浮遊感と余韻をまとう声。",
        "artists": {"female": ["宇多田ヒカル", "MISIA"], "male": ["米津玄師", "藤井風"]}},
    ("head", "power", "clear"): {
        "id": "crystal", "name": "Crystal Voice", "emoji": "💎",
        "desc": "高く抜ける裏声成分に芯がある、きらびやかな声。",
        "artists": {"female": ["西野カナ", "ACAね(ずとまよ)"], "male": ["藤原聡(髭男)", "Taka(ONE OK ROCK)"]}},
    ("head", "power", "deep"): {
        "id": "dramatic", "name": "Dramatic Voice", "emoji": "🎭",
        "desc": "裏声成分に情感と伸びがある、切なく響くドラマチックな声。",
        "artists": {"female": ["Aimer", "ヨルシカ(suis)"], "male": ["星野源", "菅田将暉"]}},
    ("head", "airy", "clear"): {
        "id": "whisper", "name": "Whisper Voice", "emoji": "🍃",
        "desc": "やわらかく透明な裏声成分。そっと寄り添う軽やかな声。",
        "artists": {"female": ["幾田りら", "miwa"], "male": ["小田和正", "三浦大知"]}},
    ("head", "airy", "deep"): {
        "id": "moody", "name": "Moody Voice", "emoji": "🌙",
        "desc": "息まじりの深い裏声成分。しっとり包み込む大人の声。",
        "artists": {"female": ["Uru", "中島美嘉"], "male": ["平井堅", "秦基博"]}},
}

_AXIS_JP = {
    "chest": "地声寄り", "head": "裏声寄り",
    "power": "パワフル", "airy": "ソフト",
    "clear": "明るめ", "deep": "暗め",
}


def classify_voice_type(a: dict) -> Optional[dict]:
    """声の成分バランス/響き/音色の3軸から8つの声タイプを判定（シェア用フック）。

    断定しないため、各軸が境界に近い時は near=True を返す（コピーで「やや〜」と表現）。
    """
    h1h2 = a.get("h1h2_db")
    reg = ((a.get("voice") or {}).get("register_high") or {}).get("register")
    cpp = a.get("cpp_db")
    hnr = a.get("hnr_db")
    tilt = a.get("spectral_tilt_db_oct")
    sf = a.get("singers_formant_ratio")
    if h1h2 is None and tilt is None and cpp is None:
        return None  # 発声指標が無い（解析不足）

    # 軸1: 地声成分(chest) vs 裏声成分(head) ← H1-H2(声門開放率)＋声区
    s1 = 0.0
    if h1h2 is not None:
        s1 += -(h1h2 - 4.0) / 4.0          # H1-H2 小→地声(+) / 大→裏声(-)
    if reg == "chest":
        s1 += 0.7
    elif reg == "head":
        s1 -= 0.7
    a1 = "chest" if s1 >= 0 else "head"

    # 軸2: パワフル(power) vs エアリー(airy) ← CPP/HNR(声の芯・雑音の少なさ)
    s2 = 0.0
    if cpp is not None:
        s2 += (cpp - 8.0) / 4.0
    if hnr is not None:
        s2 += (hnr - 14.0) / 10.0
    if sf is not None:
        s2 += (sf - 0.004) / 0.008
    a2 = "power" if s2 >= 0 else "airy"

    # 軸3: クリア(明るい) vs ディープ(深い) ← スペクトル傾斜(高域の量)
    s3 = 0.0
    if tilt is not None:
        s3 += (tilt + 9.0) / 4.0           # 傾斜が浅い(>-9)→明るい(+) / 急→暗い(-)
    if sf is not None:
        s3 += (sf - 0.004) / 0.010
    a3 = "clear" if s3 >= 0 else "deep"

    t = VOICE_TYPES[(a1, a2, a3)]

    def _near(s: float) -> bool:
        return abs(s) < 0.4

    def _pos(s: float) -> float:
        """スコアを 0〜1 の位置に写す（docs/83 §4）。

        0=左ラベル側の極 / 0.5=どちらとも言えない / 1=右ラベル側の極。
        s は + が左ラベル側（地声寄り・パワフル・明るめ）なので符号を反転させる。
        """
        return round(0.5 - max(-1.5, min(1.5, s)) / 3, 3)

    return {
        **t,
        "axes": {"register": a1, "power": a2, "color": a3},
        "axes_jp": {"register": _AXIS_JP[a1], "power": _AXIS_JP[a2], "color": _AXIS_JP[a3]},
        "near": {"register": _near(s1), "power": _near(s2), "color": _near(s3)},
        "axes_pos": {"register": _pos(s1), "power": _pos(s2), "color": _pos(s3)},
    }


def build_llm_block(a: dict, c: Optional[dict] = None) -> str:
    """LLMに渡す『発声の事実＋検知課題＋処方候補(RAG)』テキスト。捏造防止のため実測のみ。"""
    lines: list[str] = []
    metric_bits: list[str] = []
    for k, label, unit in [
        ("cpp_db", "声の芯CPP", "dB"), ("h1h2_db", "声帯の閉じH1-H2", "dB"),
        ("hnr_db", "クリアさHNR", "dB"), ("jitter_pct", "ゆらぎJitter", "%"),
        ("singers_formant_ratio", "響き(シンガーズF比)", ""),
    ]:
        v = a.get(k)
        if v is not None:
            metric_bits.append(f"{label}={v}{unit}")
    if metric_bits:
        lines.append("- 発声指標(実測): " + " / ".join(metric_bits))
    rh = (a.get("voice") or {}).get("register_high")
    if rh and rh.get("register"):
        jp = {"chest": "地声", "mix": "ミックス", "head": "裏声"}.get(rh["register"], rh["register"])
        note = "（倍音構成からの推定。換声点付近は曖昧なので、本人が裏声/ミックスの感覚を述べたら断定せずそれを尊重する）"
        lines.append(f"- 高音の声区(推定): {jp}（{rh.get('hz')}Hz付近）{note}")
    vc = (c or {}).get("voice_compare") if c else None
    if vc:
        bits = []
        if vc.get("ring", {}).get("verdict") == "weaker":
            bits.append("響きが原曲より弱い")
        if vc.get("closure", {}).get("verdict") == "breathier":
            bits.append("原曲より息漏れ寄り")
        if vc.get("closure", {}).get("verdict") == "pressed":
            bits.append("原曲より締めすぎ寄り")
        rhc = vc.get("register_high")
        if rhc and rhc.get("verdict") == "differ":
            jp = {"chest": "地声", "mix": "ミックス", "head": "裏声"}
            uhz = f"≈{rhc['user_hz']}Hz" if rhc.get("user_hz") else ""
            rhz = f"≈{rhc['ref_hz']}Hz" if rhc.get("ref_hz") else ""
            bits.append(f"高音の声区が原曲と違う・推定(あなた{jp.get(rhc['user'],'?')}{uhz}/原曲{jp.get(rhc['ref'],'?')}{rhz})")
        if bits:
            lines.append("- 原曲との発声比較: " + "／".join(bits))
    issues = diagnose(a, c)
    if issues:
        prim = issues[0]
        extra = ("／他: " + "・".join(i["jp"] for i in issues[1:3])) if len(issues) > 1 else ""
        lines.append(f"- 検知された発声課題: {prim['jp']}（重要度 {prim['severity']}）{extra}")
        rx = prescriptions_for([i["id"] for i in issues])
        if rx:
            lines.append("- 処方候補（この課題に効くエクササイズ。必ずこの中から選ぶ。"
                         "★が第一推奨。会話では基本これを続け、ユーザーが『うまくいかない/できない』と言った時だけ次の候補へ移る）:")
            for k, x in enumerate(rx):
                mark = "★推奨 " if k == 0 else ""
                an = f"（アンザッツ{x['ansatz']}）" if x.get("ansatz") else ""
                lines.append(f"  ・{mark}{x['name']}{an}: 効く理由={x['mechanism']} / やり方={x['how']}")
    else:
        lines.append("- 発声の大きな課題は検知されていない（良い土台。響き・支えをさらに磨く方向で励ます）")
    return "\n".join(lines)
