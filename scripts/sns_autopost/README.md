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

# 柱を指定して確認
python generate_and_post.py --pillar diagnosis   # 診断誘導
python generate_and_post.py --pillar tip         # 発声Tips
python generate_and_post.py --pillar type        # 声タイプ紹介

# 実投稿（.env で DRY_RUN=0 かつ Xキー設定済み）
DRY_RUN=0 python generate_and_post.py
```

## 自動化（VPSのcronで毎日投稿）
本番VPS（`/opt/vocalcoach`）にこのフォルダごと置き、毎朝9時に投稿する例:
```bash
# crontab -e
0 9 * * * cd /opt/vocalcoach/scripts/sns_autopost && /opt/vocalcoach/scripts/sns_autopost/.venv/bin/python generate_and_post.py >> /var/log/sns_autopost.log 2>&1
```
曜日ごとの柱は `themes.py` の `PILLARS` で調整（既定: 月金=診断誘導 / 火木日=Tips / 水土=声タイプ紹介）。

## 安全装置
- `DRY_RUN` 既定=1（うっかり投稿しない）。実運用で 0 にする。
- Geminiが盛った/URL欠落の文を返したらテンプレに自動差し替え。
- キーは `.env`（Git除外）。**チャットやコミットに貼らない**。
