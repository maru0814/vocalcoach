# 本番運用メモ（VPS / SNS承認フロー）

このプロジェクトの本番環境と、ツイートのLINE承認フローのデプロイ手順を記録する運用メモ。
（次回以降のセッションでも参照できるように残す。）

## 本番環境
- **公開サイト**: https://sora-vocal-ai.duckdns.org
- **稼働場所**: ConoHa VPS（自分のMacではない。Macは編集用）
- **SSH**: `ssh root@160.251.177.227`
- **構成**: Docker Compose（`docker/docker-compose.prod.yml`）+ Caddy(自動HTTPS) → frontend / backend / sns。DBはSQLite（volume）。
- リポジトリはVPS上にもクローンしてある（場所は下記コマンドで特定）。

```bash
# VPS上でリポジトリのルートを特定する
D=$(dirname "$(find / -maxdepth 6 -name docker-compose.prod.yml 2>/dev/null | head -1)")
cd "$D/.." && pwd
```

## SNS投稿のLINE承認フロー（投稿前に承認）
ツイートは自動投稿せず、生成 → LINEで [✅承認][🗑却下] → 承認したものだけX投稿。
実装は `scripts/sns_autopost/`（本体バックエンドとは独立）。詳細は同ディレクトリの README。

### デプロイ手順（VPS上で実行）
```bash
ssh root@160.251.177.227
D=$(dirname "$(find / -maxdepth 6 -name docker-compose.prod.yml 2>/dev/null | head -1)")
cd "$D/.."
git pull

# 1) キーを対話入力（画面非表示で .env に書き込む。X4つ＋LINE2つ＋任意Gemini）
bash scripts/sns_autopost/setup_approval.sh --init
#   → 起動・疎通確認のあと、設定すべき Webhook URL が表示される

# 2) LINE Developers コンソール（手作業）
#   - Webhook URL に https://sora-vocal-ai.duckdns.org/sns/line/webhook を設定し「Webhookの利用」ON
#   - 公式アカウントを自分のスマホで友だち追加 → Botが返す userId を控える

# 3) テスト送信＋cron登録（userId はここで入力）
bash scripts/sns_autopost/setup_approval.sh --test --cron
```

### 運用
- 生成cron（昼12時/夜21時）と計測cron（23時）は `--cron` で登録済み。
- 毎日その時刻に下書きがLINEに届く → 承認したものだけ投稿される。
- 即投稿したいとき（緊急）: `docker compose -f docker-compose.prod.yml exec -T sns python generate_and_post.py --pillar tip --post-now --force`

## 注意
- キー類（X / LINE / Gemini）は `.env`（Git除外）にのみ置く。**チャットやスクショに出さない**。
- 漏れたら必ず再生成（X: 開発者ポータルで再生成 / Gemini: AI Studioで再発行）。
