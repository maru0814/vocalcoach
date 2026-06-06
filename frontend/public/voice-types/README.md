# 声タイプのモチーフ画像

ここに各タイプの画像を置くと、ギャラリー・結果カードに自動で反映されます。
画像が無いタイプは、SVGマスコットに自動フォールバックします（壊れません）。

## ファイル名（必須）
`{id}.jpg`（小文字）。id は以下の8種。元画像はリポジトリ配置前に 1280px / JPEG へ圧縮する:

| id | 表示名 | 画像 |
| --- | --- | --- |
| rock | Rock Voice | ✅ 設置済み |
| groovy | Groovy Voice | ✅ 設置済み |
| pop | Pop Voice | ✅ 設置済み |
| mysterious | Mysterious Voice | ✅ 設置済み |
| crystal | Crystal Voice | ✅ 設置済み |
| dramatic | Dramatic Voice | ✅ 設置済み |
| whisper | Whisper Voice | ✅ 設置済み |
| moody | Moody Voice | ✅ 設置済み |

> 画像が未設置のタイプは、自動でSVGマスコットを表示します（壊れません）。

例: `frontend/public/voice-types/crystal.png`

## 推奨
- 横長（16:9 目安、例 1920×1080）。結果カードは16:9バナー、ギャラリーは中央を正方形にトリミング表示。
- キャラは中央寄せだと、正方形トリミングでも顔が切れにくい。
- 1枚 〜500KB程度に圧縮推奨（表示速度）。
