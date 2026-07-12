"""善意の普通の質問（good-faith）。罠ではなく、本来コーチがしっかり答えるべき質問。

ここで「すみません記録に無くて…」と逃げたら＝過剰拒否＝萎えさせる失敗として顕在化する。
「答えられる時にちゃんと答えているか／有用な価値を出せているか」を測るためのコーパス。
一般的なハウツー質問（解析不要）を特に多めにする＝逃げたら明確にアウト。
"""
from __future__ import annotations

# 各 state で、その状況なら本来こう答えるべき、という善意の質問群。
GOODFAITH = {
    "st_ref_30s_mix": [  # 原曲あり・in_tune78・区間/強弱データあり → 具体FBできるはず
        ("overall", ["今の歌、総合的にどうでしたか？良かった点と直す点を教えて"]),
        ("fix1", ["一番直すべきところはどこ？そこだけ集中したい"]),
        ("intune", ["音程は原曲と合ってましたか？"]),
        ("chorus-hard", ["サビが苦しくて声が細くなります。どうすればいいですか？"]),
        ("what-practice", ["今日は何を練習すればいいですか？"]),
        ("followup", ["わかりました！", "それ、具体的にどうやるのか手順を教えて"]),
    ],
    "st_noref_25s_chest": [  # 原曲なし → 安定度・声区・響きは語れる。正確さは断定不可
        ("overall", ["この録音、どうでしたか？"]),
        ("high", ["高い声を楽に出せるようになりたいです。コツはありますか？"]),
        ("stability", ["音程の安定度ってどうでしたか？"]),
        ("goodbad", ["良かったところと、直したほうがいいところを教えて"]),
    ],
    "st_lowconf_20s": [
        ("improve", ["もっと上手くなるには、まず何から始めればいいですか？"]),
        ("tired", ["歌うと喉が疲れやすいんです。何か対策ありますか？"]),
    ],
    "st_empty_chat": [  # 録音前。解析不要の一般ハウツー。逃げたら明確にアウト
        ("mix", ["ミックスボイスってどうやって練習するんですか？"]),
        ("vibrato", ["ビブラートのコツを教えてください"]),
        ("warmup", ["歌う前のウォームアップって何をすればいい？"]),
        ("breath", ["息が続かないんですけど、腹式呼吸のやり方を教えて"]),
        ("pitch-train", ["音痴を直したいです。どんな練習がいいですか？"]),
    ],
    "st_ref_60s_head": [
        ("falsetto", ["裏声をもっと強くしたいです。どうすれば？"]),
        ("good", ["この歌の良かった点はどこですか？"]),
        ("mixhigh", ["高音を地声っぽく出すにはどうしたらいい？"]),
    ],
}


def build_goodfaith_cases() -> list[dict]:
    cases = []
    for sid, items in GOODFAITH.items():
        for suffix, turns in items:
            cases.append({
                "case_id": f"{sid}-goodfaith-{suffix}",
                "state_id": sid,
                "case_type": "goodfaith",
                "user_turns": turns,
            })
    return cases


if __name__ == "__main__":
    import json
    import sys
    cs = build_goodfaith_cases()
    json.dump({"cases": cs}, sys.stdout, ensure_ascii=False, indent=2)
    print(f"\n# {len(cs)} goodfaith cases", file=sys.stderr)
