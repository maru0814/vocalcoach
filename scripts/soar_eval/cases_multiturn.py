"""多ターン会話コーパス（2ターン目以降の噛み合わなさ＝文脈追従の劣化を診る）。

設計意図: 「さっきの」「あれ」等の指示語、自分の過去発言への参照、進捗報告、
言い換え要求、矛盾の指摘——コーチが**自分が言ったことを覚えて一貫して**答えられるかを試す。
各ターンは前のコーチ返答に依存するため、正解は固定できない（審査で per-turn 評価する）。
"""
from __future__ import annotations

# (suffix, [user_turns...]) — 3〜5ターン
_TEMPLATES = [
    # 説明の深掘り→自分の発言の想起
    ("explain", [
        "今の歌、どうでしたか？",
        "その練習のやり方、もう少し詳しく教えて",
        "さっき言ってた課題って、どこの話でしたっけ？",
        "わかった。で、最初に言ってた一番のポイントって何だっけ？",
    ]),
    # 進捗報告→次の指示（練習の一貫性）
    ("progress", [
        "今日は何を練習すればいい？",
        "やってみました！できてるか分からないけど",
        "次は何をすればいい？",
        "明日も同じでいい？",
    ]),
    # 言い換え要求の連打（噛み砕けるか・繰り返しに逃げないか）
    ("clarify", [
        "サビが苦しいです。どうしたらいい？",
        "うーん、それってどういう意味ですか？",
        "もっと簡単に言うと？",
        "例えば具体的にどんな感じでやるの？",
    ]),
    # 指示語・省略（文脈の解決力）
    ("pronoun", [
        "高い声が出ないんです",
        "それを直すには、どれくらいかかりますか？",
        "あれ、さっきのやつもう一回言ってもらえます？",
        "結局、何から始めるんだっけ？",
    ]),
    # 脱線→復帰（話題の切り替えに追従できるか）
    ("derail-return", [
        "今日ちょっと調子悪いかも…",
        "ごめんなさい愚痴でした。で、わたしの音程どうでした？",
        "そのズレって直りますか？",
        "じゃあ今日はそれをやります",
    ]),
    # 矛盾の指摘（自分の発言と整合を取れるか・捏造しないか）
    ("contradict", [
        "ミックスボイスを練習したいです",
        "あれ？さっきは別の練習がいいって言ってませんでした？",
        "どっちが正しいんですか？",
    ]),
]

_STATES = ["st_ref_30s_mix", "st_noref_25s_chest", "st_empty_chat"]


def build_multiturn_cases() -> list[dict]:
    cases = []
    for sid in _STATES:
        for suffix, turns in _TEMPLATES:
            cases.append({
                "case_id": f"{sid}-multiturn-{suffix}",
                "state_id": sid,
                "case_type": "multiturn",
                "user_turns": turns,
            })
    return cases


if __name__ == "__main__":
    import json
    import sys
    cs = build_multiturn_cases()
    json.dump({"cases": cs}, sys.stdout, ensure_ascii=False, indent=2)
    print(f"\n# {len(cs)} multiturn cases, "
          f"{sum(len(c['user_turns']) for c in cs)} user turns", file=sys.stderr)
