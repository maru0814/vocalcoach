# 効果音（SFX）の置き場  ※Phase 2で使用

無音の「紙芝居」から脱する最短の一手が効果音。ここに3つ置くと、カット転換・字幕登場・CTAに音が付きます
（Phase 2 で `video_assembler` が読み込む予定）。

## 置くファイル（推奨ファイル名）
- `whoosh.mp3` … カット転換の頭に鳴らす
- `pop.mp3` … 字幕・キーワード登場に同期
- `ding.mp3` … CTA（最後の一押し）に1発

## 入手先（無料・商用OK・帰属不要）
- **Pixabay Sound Effects** … https://pixabay.com/sound-effects/ （"whoosh" "pop" "ding" で検索）
- **Mixkit Sound Effects** … https://mixkit.co/free-sound-effects/

APIは不要。手で3つダウンロードして上のファイル名で置くだけ。

## 注意
- 中身（音源ファイル）は **Git管理外**。このREADMEだけ管理されます。
- 帰属表示が必要な音源（freesoundのCC-BY等）は管理が面倒なので避け、CC0相当を使ってください。
