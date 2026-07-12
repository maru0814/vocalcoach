"""会話の「テンプレ臭さ・不自然さ」を決定論で計測（Claude不要）。

同一コーパス横断で、AIコーチ特有の定型句・毎回同じ書き出し/締め・長さのミスマッチ・
絵文字などを数える。頻度そのものが「機械的で不自然」の証拠になる。
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter

# AIコーチ特有の常套句（“らしさ”のテル）。出現会話数/総ターンで頻度化する。
STOCK_PHRASES = {
    "もしよろしければ": re.compile(r"もしよろしけれ?ば"),
    "〜していきましょう": re.compile(r"していきましょう|していきましょ"),
    "〜てみませんか": re.compile(r"てみませんか|てみましょうか"),
    "〜てくださいね": re.compile(r"てくださいね|てみてくださいね"),
    "素晴らしい/素敵": re.compile(r"素晴らしい|素敵ですね"),
    "全体として/全体的に": re.compile(r"全体(として|的に)"),
    "一緒に": re.compile(r"一緒に"),
    "近道": re.compile(r"近道"),
    "参考になる実演動画": re.compile(r"参考になる実演動画|実演動画を出しましょうか"),
    "〜が大切/大事": re.compile(r"が(とても)?大切|が大事"),
    "ありがとうございます": re.compile(r"ありがとうございま"),
    "コツは/ポイントは": re.compile(r"コツは|ポイントは"),
}

# 「書き出しの定型化」= 各コーチ返答の冒頭12文字を集計（同じ入りが多い＝テンプレ）
_LEAD = 12
_SENT = re.compile(r"[。！？!?\n]")
_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")


def coach_turns(tr):
    return [e["text"] for e in tr if e["role"] == "coach"]


def analyze(results: list[dict]) -> dict:
    turns = [t for r in results for t in coach_turns(r["transcript"])]
    n = len(turns) or 1
    # 常套句の出現ターン率
    phrase_rate = {}
    for name, rex in STOCK_PHRASES.items():
        hits = sum(1 for t in turns if rex.search(t))
        phrase_rate[name] = (hits, round(100 * hits / n))
    # 書き出しの定型度（上位の冒頭パターン）
    leads = Counter(re.sub(r"\s", "", t)[:_LEAD] for t in turns if t)
    # 締めの定型度（末尾の1文の語尾パターン: 最後の文の末尾10文字）
    tails = Counter()
    for t in turns:
        sents = [s for s in _SENT.split(t) if s.strip()]
        if sents:
            tails[re.sub(r"\s", "", sents[-1])[-12:]] += 1
    # 質問・オファーで終わる率（毎回問い返す押し付けがましさ）
    q_end = sum(1 for t in turns if t.rstrip().rstrip("😊🎤✨").endswith(("？", "?")))
    # 長さ（自然な短さか）
    lens = [len(re.sub(r"\s", "", t)) for t in turns if t]
    over120 = sum(1 for L in lens if L > 120)
    emoji_turns = sum(1 for t in turns if _EMOJI.search(t))
    return {
        "convs": len(results), "coach_turns": n,
        "phrase_rate": phrase_rate,
        "top_leads": leads.most_common(8),
        "top_tails": tails.most_common(8),
        "question_end_rate": (q_end, round(100 * q_end / n)),
        "over_120_chars": (over120, round(100 * over120 / n)),
        "avg_chars": round(sum(lens) / n, 1),
        "emoji_turn_rate": (emoji_turns, round(100 * emoji_turns / n)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, nargs="+")
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    results = []
    for p in a.inp:
        d = json.load(open(p))
        results += d["results"] if isinstance(d, dict) else d
    m = analyze(results)
    json.dump(m, open(a.out_json, "w"), ensure_ascii=False, indent=2)

    print(f"== {m['convs']}会話 / コーチ{m['coach_turns']}ターン ==")
    print(f"平均{m['avg_chars']}字 / 120字超 {m['over_120_chars'][1]}% / "
          f"疑問で締める {m['question_end_rate'][1]}% / 絵文字 {m['emoji_turn_rate'][1]}%")
    print("\n常套句の出現ターン率（多いほどテンプレ臭い）:")
    for name, (h, r) in sorted(m["phrase_rate"].items(), key=lambda x: -x[1][1]):
        bar = "█" * (r // 3)
        print(f"  {name:22s} {r:3d}% ({h:3d}) {bar}")
    print("\n書き出しの定型TOP（同じ入りの多さ）:")
    for lead, c in m["top_leads"]:
        print(f"  {c:3d}回  「{lead}…」")
    print("\n締めの定型TOP:")
    for tail, c in m["top_tails"]:
        print(f"  {c:3d}回  「…{tail}」")


if __name__ == "__main__":
    main()
