# 動的OG画像用アセット（docs/28 §11）

`/api/og/voice-type/[id]` の `ImageResponse` が使うフォント置き場。

- `NotoSansJP-OG-Bold.subset.ttf` — Noto Sans JP を wght=700 で静的化し、
  OGカードで使うグリフ（ASCII＋かな全集合＋使用漢字）だけにサブセットしたもの（約83KB）。
  ライセンスは同梱の `OFL.txt`（SIL Open Font License 1.1）。
- **OGカードの文言を変えたら** `frontend/scripts/subset_og_font.py` を再実行してこのファイルを更新する。
  かな・ASCIIは全部入りなので、新しい**漢字**を使ったときだけ再生成が必要。
  豆腐（□）が出たらグリフ不足のサイン。手順はスクリプト先頭の docstring 参照。
