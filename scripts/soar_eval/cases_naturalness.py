"""自然さ検査コーパス。ハルシネーション/逃げではなく「会話としての自然さ」を診る。

人間のコーチなら軽く・短く・自然に返す場面（雑談・感情・短い相槌・タメ口・喜び）を集め、
コーチが硬い/テンプレ臭い/説教臭い/押し付けがましい/相槌が噛み合わない返しをしないかを見る。
"""
from __future__ import annotations

# (suffix, [user_turns...]) — 短い会話中心
_TEMPLATES = [
    # 雑談・軽い一言（説教せず軽く返せるか）
    ("greeting", ["こんにちは！", "今日はいい天気ですね〜"]),
    ("mood-off", ["なんか今日は歌う気分じゃないな…", "そういう日もあるよね"]),
    ("nervous", ["歌うのちょっと緊張します", "人に聴かれると特に"]),
    ("smalltalk", ["先生っていつも褒めてくれますね", "ちょっと照れます"]),
    # 感情（共感が自然か・励ましが説教にならないか）
    ("down", ["全然上達しなくて落ち込む…もうやめようかな"]),
    ("joy", ["さっきの録音、自分でもうまく歌えた気がする！！嬉しい！"]),
    ("fail", ["本番で緊張して声が裏返っちゃった…最悪だった"]),
    ("compare-sad", ["友達の方がずっと歌うまくて、へこむ"]),
    # 短い相槌の応酬（テンポを合わせられるか・毎回長文で返さないか）
    ("aizuchi", ["うん", "そうなんだ", "へー", "なるほどね"]),
    ("yesno", ["今の、良かった？", "ほんとに？", "やった"]),
    ("short-q", ["ミックスって何？", "ふーん", "むずそう"]),
    # タメ口・カジュアル（トーンを合わせられるか・急に丁寧すぎないか）
    ("casual", ["ねえ、今の声どうだった？", "まじで？やったー", "もっかいやってみる"]),
    ("tired-casual", ["あー疲れた〜今日はもう歌えない", "また明日やる"]),
    # テンション高め（熱量に合わせられるか）
    ("excited", ["歌うの楽しい！！もっとうまくなりたい！！", "どんどん練習したい！"]),
    # 継続の雑談混じり（rapport）
    ("rapport", ["先生と話すの楽しいです", "歌以外の話もしていい？", "最近ハマってる曲があって"]),
    # 素朴な疑問（噛み砕けるか・専門用語で身構えないか）
    ("naive", ["声ってどうやって出てるんですか？", "へー、不思議"]),
]

_STATES = ["st_ref_30s_mix", "st_noref_25s_chest", "st_empty_chat"]


def build_naturalness_cases() -> list[dict]:
    cases = []
    for sid in _STATES:
        for suffix, turns in _TEMPLATES:
            cases.append({
                "case_id": f"{sid}-natural-{suffix}",
                "state_id": sid,
                "case_type": "naturalness",
                "user_turns": turns,
            })
    return cases


if __name__ == "__main__":
    import json
    import sys
    cs = build_naturalness_cases()
    json.dump({"cases": cs}, sys.stdout, ensure_ascii=False)
    print(f"\n# {len(cs)} naturalness cases, "
          f"{sum(len(c['user_turns']) for c in cs)} user turns", file=sys.stderr)
