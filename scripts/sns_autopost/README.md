# ソラ先生 SNS自動投稿（X / 旧Twitter）

毎日1回、自動でXに投稿する最小ツール。**Geminiが無くてもテンプレで動く**／**キーが無ければ本文表示だけ（安全）**。

## できること / できないこと（正直に）
- ✅ **X（旧Twitter）への自動投稿**: 公式API v2を使う。無料枠でも1日数件程度は可能（枠は変動するので [developer.x.com](https://developer.x.com) で要確認）。
- ✅ **文面の自動生成**: 既存の `GEMINI_API_KEY` で、診断誘導/発声Tips/声タイプ紹介を日替わり生成。失敗時はテンプレに自動フォールバック。
- ⚠️ **Instagram / TikTok の完全自動投稿**: 個人運用ではAPI制限が厳しく非推奨。Buffer等のスケジューラ、または「下書き生成→手動投稿」の半自動が現実的。
- ⚠️ note: 公式投稿APIなし。記事の下書き生成までが自動化の限界。

## セットアップ（5分）
```bash
cd scripts/sns_autopost
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # 値を入れる（.env はGitに入らない）
```

### Xのキー発行
1. https://developer.x.com で開発者登録 → アプリ作成
2. アプリの **User authentication settings** で権限を **Read and write** に
3. **API Key/Secret**（Consumer）と **Access Token/Secret** を発行し `.env` に貼る

## 使い方
```bash
# まずは安全確認（投稿せず本文だけ表示。DRY_RUN=1 が既定）
python generate_and_post.py

# 型を指定して確認（docs/25 の「伸びる型」に対応）
python generate_and_post.py --pillar self_type   # 自己分類フック（診断誘導）
python generate_and_post.py --pillar empathy     # 共感あるある（リンクなし）
python generate_and_post.py --pillar tip         # 番号付きTips
python generate_and_post.py --pillar contrarian  # 逆張り
python generate_and_post.py --pillar question    # 問いかけ（リプ狙い）
python generate_and_post.py --pillar voice_type  # 声タイプ図鑑
python generate_and_post.py --pillar visual      # ビジュアル誘導

# 実投稿（.env で DRY_RUN=0 かつ Xキー設定済み）
DRY_RUN=0 python generate_and_post.py
```

> **リンクは本文に入れず“自己リプ”に貼ります**（docs/25 の研究：本文リンクはリーチ50–90%減）。
> empathy / question はリンクなしの純粋な会話狙い。**自動は種まき、初速の点火は手動リプで**。

## 自動化（VPSのcronで毎日投稿）
本番VPS（`/opt/vocalcoach`）にこのフォルダごと置き、毎朝9時に投稿する例:
```bash
# crontab -e
0 9 * * * cd /opt/vocalcoach/scripts/sns_autopost && /opt/vocalcoach/scripts/sns_autopost/.venv/bin/python generate_and_post.py >> /var/log/sns_autopost.log 2>&1
```
曜日ごとの型は `themes.py` の `PILLARS` で調整（既定: 月=自己分類 / 火=Tips / 水=声タイプ図鑑 / 木=共感 / 金=逆張り / 土=問いかけ / 日=ビジュアル。docs/25 のカレンダー準拠）。

## 安全装置
- `DRY_RUN` 既定=1（うっかり投稿しない）。実運用で 0 にする。
- Geminiが盛った/URL欠落の文を返したらテンプレに自動差し替え。
- キーは `.env`（Git除外）。**チャットやコミットに貼らない**。
