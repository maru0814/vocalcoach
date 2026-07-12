"""決定論チェッカ（機械・高精度）。docs/64 §5.1。

本物の llm.py の内部正規表現・許可秒数ロジックを再利用し、基準を二重管理しない。
検査対象は「出荷される最終返答」（generate_reply が既存ガードを通した後の文字列）。
既存ガードを通り抜けて残った違反＝実際にユーザーへ届く違反を捉える。
"""
from __future__ import annotations

import re
from typing import Any

from app.coaching.llm import (  # 本物の内部ロジックを再利用
    _SCRUB_SEC_RE,
    _LYRIC_QUOTE_RE,
    _MMSS_RE,
    _URL_RE,
    _CARD_PROMISE_RE,
)
from app.coaching.tools import CATALOG_VIDEO_URLS

from . import states as S

LABELS = {
    "H1": "時刻捏造", "H2": "数値捏造", "H3": "音名捏造", "H5": "歌詞・母音断定",
    "H7": "照合なし正確さ断定", "H8": "URL捏造",
    "N3": "敬体/人称の揺れ", "N4": "冗長/長すぎ",
    "P1": "非会話出力", "P2": "カード約束",
}
SEV = {
    "H1": "S1", "H2": "S1", "H3": "S1", "H5": "S1", "H7": "S1", "H8": "S2",
    "N3": "S3", "N4": "S3", "P1": "S2", "P2": "S2",
}
RULES = {
    "H1": ["docs/12 FR-03", "docs/12 AC-04", "docs/12 AC-07"],
    "H2": ["docs/12 FR-02", "docs/12 AC-02", "docs/12 AC-06"],
    "H3": ["docs/12 FR-01", "docs/12 AC-01"],
    "H5": ["docs/12 FR-04", "docs/12 AC-08"],
    "H7": ["docs/42 §5", "docs/12 FR-01"],
    "H8": ["実装ガード _scrub_foreign_urls"],
    "N3": ["docs/42 §1"],
    "N4": ["docs/42 §2"],
    "P1": ["docs/42 §2"],
    "P2": ["docs/42 §2"],
}

_SENT_SPLIT = re.compile(r"[。！？!?\n]")

# 否定・打ち消し文脈（ユーザーの偽前提を「無い/検知されていない/混同」と否定＝正しい振る舞い）。
# この文の中に flag 候補があるなら捏造ではなく“正しく否定している”ので除外する。
_DENIAL = re.compile(
    r"(残って(?:い|お)?(?:ま?せん|ない|らず)|"
    r"(?:検知|検出|算出|特定|判別|記録)(?:は|が|に|も|されて)?(?:い?ま?せん|ない|なかった|おらず)|"
    r"出て(?:い|お)?(?:ま?せん|ない|らず)|確認でき(?:ま?せん|ない)|"
    r"ありま?せん|ないよう|ないです|混同|わかりま?せん|分かりま?せん)"
)


def _sentence_around(text: str, start: int, end: int) -> str:
    """マッチ位置を含む1文を切り出す（句点区切り）。否定文脈判定に使う。"""
    s = max(text.rfind("。", 0, start), text.rfind("\n", 0, start),
            text.rfind("！", 0, start), text.rfind("？", 0, start)) + 1
    e_candidates = [i for i in (text.find("。", end), text.find("\n", end),
                                text.find("！", end), text.find("？", end)) if i != -1]
    e = min(e_candidates) if e_candidates else len(text)
    return text[s:e]

# H2 数値: 単位つきの値を拾う（点＝スコアは撤廃済みなので最も疑わしい）
_NUM_UNIT_RES = {
    "点": re.compile(r"(\d+(?:\.\d+)?)\s*点"),
    "Hz": re.compile(r"(\d+(?:\.\d+)?)\s*Hz"),
    "cents": re.compile(r"(\d+(?:\.\d+)?)\s*(?:cents?|セント)"),
    "dB": re.compile(r"(\d+(?:\.\d+)?)\s*dB"),
    "回": re.compile(r"(\d+(?:\.\d+)?)\s*回"),
}

# H7 正確さの肯定語（原曲照合が無い state で出たら疑い）
_ACCURACY_AFFIRM = re.compile(
    r"(音程(?:は|が)?(?:とても|ばっちり|バッチリ)?(?:正確|合っ|良|いい|バッチリ))"
    r"|(ピッチ(?:は|が)?(?:正確|良|いい|安定して合))"
    r"|(音(?:を|は)?外して(?:いま|い)?せん)"
    r"|(正確に(?:歌えて|取れて))"
)
# 否定・留保があれば H7 ではない（正しい振る舞い）
_ACCURACY_HEDGE = re.compile(
    r"(できません|できない|難しい|分かりま?せん|わかりま?せん|断定でき|"
    r"照合が(?:無|な)い|原曲が(?:無|な)い|お手本が(?:無|な)い|安定度|"
    r"確認でき(?:ま?せん|ない)|とは別)"
)

# N3 人称・常体の崩れ
_PRONOUN_BAD = re.compile(r"(僕|俺|オレ|ボク)")
_PLAIN_STYLE = re.compile(r"(である。|であります|だぜ|だな。|するのだ。)")

# P1 非会話出力（Markdown見出し・表・箇条書き・記号採点）
_MD_HEADING = re.compile(r"(^|\n)#{1,6}\s")
_MD_TABLE = re.compile(r"\n\s*\|?[^\n]*\|[^\n]*\n\s*\|?\s*:?-{2,}")
_MD_BOLD = re.compile(r"\*\*[^*]+\*\*")
_BULLET = re.compile(r"(^|\n)\s*[-*・][ 　]")
_MARKSCORE = re.compile(r"[◎○△×]")


def _f(cat: str, span: str, why: str, contradicting: str,
       needs_llm_review: bool = False) -> dict[str, Any]:
    # needs_llm_review=True は「機械では確定できない候補」。verified=False にして
    # LLM審査での確認待ちにする（確定分だけ verified=True でレポート即採用）。
    return {
        "category": cat,
        "category_label": LABELS[cat],
        "severity": SEV[cat],
        "detector": "deterministic",
        "verified": not needs_llm_review,
        "verifier_verdict": "deterministic" if not needs_llm_review else "pending_llm",
        "coach_span_verbatim": span,
        "why": why,
        "contradicting_fact": contradicting,
        "violated_rule": RULES[cat],
        "needs_llm_review": needs_llm_review,
    }


def check_reply(reply: str, context: str, state: dict,
                allowed_seconds: set[int]) -> list[dict[str, Any]]:
    """1つのコーチ返答に決定論チェックをかけ、所見のリストを返す。"""
    out: list[dict[str, Any]] = []
    if not reply:
        return out

    # H1 時刻捏造（許可秒数集合に無い位置表現の秒数）
    dur = ((state.get("last_analysis") or state.get("baseline_analysis") or {})
           .get("duration_sec"))
    for m in _SCRUB_SEC_RE.finditer(reply):
        n = int(m.group(1))
        if not any(abs(n - a) <= 1 for a in allowed_seconds):
            over = f"（録音長 約{dur:.0f}秒を超える）" if dur and n > dur else ""
            out.append(_f(
                "H1", m.group(0),
                f"許可された秒数集合に無い位置表現『{m.group(0)}』を出している{over}。",
                f"許可秒数={sorted(allowed_seconds)} / 録音長={dur}",
            ))

    # H3 音名捏造（現在のレッスン状況に無い音名）。ただし否定文脈（「C5は検知されていない」等）は除外。
    allowed_notes = S.allowed_note_names(context)
    for m in S.NOTE_RE.finditer(reply):
        note = S.normalize_note(m)
        if note in allowed_notes:
            continue
        sent = _sentence_around(reply, m.start(), m.end())
        denied = bool(_DENIAL.search(sent))
        out.append(_f(
            "H3", m.group(0),
            f"照合に無い音名『{note}』を出している（状況の音名={sorted(allowed_notes) or 'なし'}）。"
            + ("※否定文脈で言及＝正しく否定の可能性。要確認。" if denied else ""),
            f"許可音名={sorted(allowed_notes) or 'なし'}",
            needs_llm_review=denied,  # 否定文脈なら確定でなく候補（誤検出回避）
        ))

    # H2 数値捏造（文脈に無い単位つきの値）。否定文脈（「95点は残っていない」等）は正しい否定なので除外扱い。
    for unit, rex in _NUM_UNIT_RES.items():
        for m in rex.finditer(reply):
            val = m.group(1)
            if val in context:
                continue
            sent = _sentence_around(reply, m.start(), m.end())
            denied = bool(_DENIAL.search(sent))
            # 点(スコア撤廃)は肯定なら確定寄り。否定文脈 or 点以外は候補（LLM確認）。
            needs = denied or (unit != "点")
            out.append(_f(
                "H2", m.group(0),
                f"文脈に無い数値『{m.group(0)}』を断定"
                + ("（会話ではスコアを出さない方針）" if unit == "点" else "")
                + ("。※ただし否定文脈で言及＝正しく否定の可能性。要確認。" if denied else "。"),
                f"文脈に {val} は不在（単位={unit}）",
                needs_llm_review=needs,
            ))

    # H5 歌詞・母音断定
    # mm:ss 時刻参照は確定（実音声の時刻を断定＝捏造）。
    for m in _MMSS_RE.finditer(reply):
        out.append(_f("H5", m.group(0).strip(),
                      "mm:ss の時刻参照。音声認識していないため位置の断定は捏造。",
                      "音声認識なし（歌詞・母音は聞き取れない）"))
    # 英字を含む「」引用は、専門用語の補足（例「声帯の閉じ（H1-H2）」＝§1が要求する作法）を
    # 誤検出しやすい。括弧の補足を含むものは正しい作法として除外。残りは候補（LLM確認）。
    for m in _LYRIC_QUOTE_RE.finditer(reply):
        quote = m.group(0)
        if "（" in quote or "(" in quote:  # 用語＋補足＝ペルソナ要求の作法。捏造ではない
            continue
        out.append(_f("H5", quote.strip(),
                      "英字を含む「」引用。歌詞の断定なら捏造だが、専門用語の可能性もあり要確認。",
                      "音声認識なし（歌詞・母音は聞き取れない）",
                      needs_llm_review=True))

    # H7 照合なしの正確さ断定
    if not S.in_tune_available(state):
        for m in _ACCURACY_AFFIRM.finditer(reply):
            # 同一文に否定・留保があれば正しい振る舞いなので除外
            start = reply.rfind("。", 0, m.start()) + 1
            end = reply.find("。", m.end())
            sentence = reply[start: end if end != -1 else len(reply)]
            if _ACCURACY_HEDGE.search(sentence):
                continue
            out.append(_f(
                "H7", m.group(0),
                "原曲照合が無い/対応づかない state なのに音程の『正確さ』を断定している。",
                "in_tune 照合なし（安定度は語れるが正確さは断定不可）",
                needs_llm_review=True,
            ))

    # H8 URL捏造（カタログ外リンク）
    for m in _URL_RE.finditer(reply):
        cleaned = m.group(0).rstrip("。、,.！!？?")
        if cleaned not in CATALOG_VIDEO_URLS:
            out.append(_f(
                "H8", m.group(0),
                "カタログ(CATALOG_VIDEO_URLS)に無いURLを提示している（でっち上げリンクの疑い）。",
                "実在カタログに不在",
            ))

    # N3 人称・常体の崩れ
    for m in _PRONOUN_BAD.finditer(reply):
        out.append(_f("N3", m.group(0),
                      f"一人称『{m.group(0)}』。ペルソナは一人称『わたし』・やわらかい敬体。",
                      "docs/42 §1 ペルソナ"))
    for m in _PLAIN_STYLE.finditer(reply):
        out.append(_f("N3", m.group(0),
                      f"常体『{m.group(0)}』が混入（やわらかい敬体で統一すべき）。",
                      "docs/42 §1 敬体"))

    # N4 冗長・長すぎ（§2: 2〜4文/120字目安）
    nchar = len(re.sub(r"\s", "", reply))
    nsent = len([s for s in _SENT_SPLIT.split(reply) if s.strip()])
    if nchar > 200 or nsent > 6:
        out.append(_f("N4", reply[:40] + ("…" if len(reply) > 40 else ""),
                      f"返答が長すぎる（{nchar}字 / {nsent}文。目安は2〜4文・120字程度）。",
                      "docs/42 §2 チャットのテンポ"))

    # P1 非会話出力
    p1_hits = []
    if _MD_HEADING.search(reply):
        p1_hits.append("Markdown見出し")
    if _MD_TABLE.search(reply):
        p1_hits.append("表")
    if _MD_BOLD.search(reply):
        p1_hits.append("太字**")
    if _MARKSCORE.search(reply):
        p1_hits.append("◎○△×")
    if len(_BULLET.findall(reply)) >= 2:
        p1_hits.append("箇条書き")
    if p1_hits:
        out.append(_f("P1", "／".join(p1_hits),
                      f"会話チャットで使わない要素（{'／'.join(p1_hits)}）が出ている。",
                      "docs/42 §2 会話チャット完結"))

    # P2 カード約束（残存分）
    for m in _CARD_PROMISE_RE.finditer(reply):
        s = m.group(0).strip()
        if s:
            out.append(_f("P2", s, "出ないカードを約束している（チャット返信にカードは無い）。",
                          "docs/42 §2"))

    return out
