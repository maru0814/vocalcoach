# 声タイプのモチーフ画像

ここに各タイプの画像を置くと、ギャラリー・結果カードに自動で反映されます。
画像が無いタイプは、SVGマスコットに自動フォールバックします（壊れません）。

## ファイル名（必須）
`{id}.png`。id は以下の8種:

| id | 表示名 | 画像 |
| --- | --- | --- |
| groovy | Groovy Voice | これから設置（1枚目） |
| crystal | Crystal Voice | これから設置（2枚目） |
| whisper | Whisper Voice | これから設置（3枚目） |
| moody | Moody Voice | これから設置（4枚目） |
| dramatic | Dramatic Voice | これから設置（5枚目） |
| rock | Rock Voice | 後日（残り3枚） |
| pop | Pop Voice | 後日（残り3枚） |
| mysterious | Mysterious Voice | 後日（残り3枚） |

> 画像が未設置のタイプは、自動でSVGマスコットを表示します（壊れません）。

例: `frontend/public/voice-types/crystal.png`

## 推奨
- 横長（16:9 目安、例 1920×1080）。結果カードは16:9バナー、ギャラリーは中央を正方形にトリミング表示。
- キャラは中央寄せだと、正方形トリミングでも顔が切れにくい。
- 1枚 〜500KB程度に圧縮推奨（表示速度）。
