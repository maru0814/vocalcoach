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

## トラブルシュート
- **`/sns/healthz` がfrontendの404になる / Caddyfileを変えても反映されない**:
  Caddyは単一ファイルbind mountを「起動時の実体」で握り続けるため、`git checkout` 等で
  Caddyfileを差し替えても古い内容を見続ける。`reload` でも直らない。**Caddyを作り直す**:
  ```bash
  cd /opt/vocalcoach/docker
  docker compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate caddy
  curl -s https://sora-vocal-ai.duckdns.org/sns/healthz   # {"status":"ok","line":true}
  ```
- **承認/却下の確認**: キューの状態は sns コンテナ内の `/data/pending_queue.jsonl`。
  ```bash
  docker compose -f docker-compose.prod.yml --env-file .env exec -T sns sh -c "tail -3 /data/pending_queue.jsonl"
  ```


## 事例: 図解画像対応のデプロイ失敗と復旧（2026-06-30）
- **症状**: PR#103 マージ後の自動デプロイ（Deploy to VPS）が失敗。`set -e` で sns ビルド段階(remote_deploy.sh L31)で停止し、backend/frontend は再ビルドされず旧 sns コンテナが稼働継続＝**本番は無停止**（`/sns/healthz` 200 のまま）。
- **原因**: sns Dockerfile の `RUN python -m playwright install --with-deps chromium` が exit 100。① `python:3.12-slim` の既定が Debian **trixie**（Playwright非対応）でOS依存解決が ubuntu20.04 にフォールバックして失敗。② 直前に `rm -rf /var/lib/apt/lists/*` 済みで apt インデックスが無く `apt-get install` が対象を見つけられない。
- **修正(PR#105)**: ベースを `python:3.12-slim-bookworm` に固定し、フォント＋`playwright install --with-deps chromium` を同一レイヤーにまとめ apt インデックスは導入後に削除。ローカル `docker build` 成功(2.6GB)＋コンテナ内で図解レンダリング・日本語表示を確認。
- **教訓**: Playwright 同梱イメージは**ベースのDebianコードネームを固定**する（slim既定はtestingに動くことがある）。`--with-deps` を使うレイヤーでは apt インデックスを残す。
- **LINE画像プレビュー有効化**: VPS `scripts/sns_autopost/.env` に `SNS_PUBLIC_BASE_URL=https://sora-vocal-ai.duckdns.org` を追記 → `docker compose ... up -d --force-recreate sns`。Caddyの `/sns/*` が `GET /sns/img/{name}` も配信（公開URLで取得 200 image/png 確認済み）。

## 事例: 声タイプ診断導線の実画像図解 デプロイ（2026-06-30）
- 変更: 診断導線(voice_type/self_type/visual)をカードから **type=diagnosis 図解**（各タイプの実画像 `assets/voice_types/{id}.jpg`）へ。`build_image` は全ピラー→infographic。Dockerに `fonts-noto-color-emoji` 追加（CTAの🎤等）。
- 検証: ローカル `docker build` 再検証OK → コンテナ内で voice_type/self_type 描画（絵文字・タイプ画像・日本語OK）。PR#108 マージ → 自動デプロイ green。
- 本番実証: 本番コンテナで voice_type 図解を生成 → `/sns/img` 公開URLで **200 image/png(1.3MB)**、Dramaticバナーの図鑑が出ることを確認。
- 教訓: 図解で絵文字を使うなら Chromium に `fonts-noto-color-emoji` が要る（無いと豆腐）。タイプ別の作り込み画像は既存frontendアセットを sns ビルドコンテキストに同梱して使い回すのが安定（AI生成不要・日本語崩れ無し）。

## DBマイグレーションのデプロイ（スキーマ変更を含むPRの段取り）
**結論: スキーマ変更は自動で適用される。手動 alembic は不要。**
- 仕組み: `backend/Dockerfile.prod` の CMD が `alembic upgrade head && uvicorn ...`。
  `remote_deploy.sh` は migration を直接叩かないが、`backend/` が変わると `up -d --build backend`
  で**コンテナ再起動時に upgrade head が走る**。本番DBは永続ボリュームの SQLite（`/data/app.db`）。
- **失敗時の挙動**: migration が失敗すると CMD が落ちて uvicorn が起動せず、backend が上がらない＝
  **サイト/API が 502**。つまり「デプロイ後に 200 が返る」こと自体が migration 成功の証拠。
- **デプロイ後の必須確認**（スキーマ変更PR時）:
  ```bash
  curl -sI https://sora-vocal-ai.duckdns.org/ | head -1              # 200
  curl -s -o /dev/null -w "%{http_code}\n" https://sora-vocal-ai.duckdns.org/api/v1/voice-type/stats  # 200 = backend起動OK=migration適用済
  ```
- **事前の備え**: migration は手元で **本番と同じ SQLite** に対し `alembic upgrade head` →
  `downgrade -1` → 再 `upgrade` の往復を通しておく（add_column＋unique index は SQLite ALTER
  制約に注意。FK列直add不可なので素のInteger＋unique indexで張る）。

## 事例: デザイン課題1〜4＋coach昇格(T-2) のデプロイ（2026-06-30）
- 変更: PR#107(課題1〜4・UI)→ green。PR#111(T-2: recordings に `source_session_id/source_message_id`
  追加＝**スキーマ変更**, migration `c7d8e9f0a1b2`)→ backend再ビルドで起動時に upgrade head 適用。
  PR#113 はドキュメントのみ（`paths-ignore` でデプロイ非対象＝正常）。
- 本番実証: マージ→自動デプロイ green。`/`=200、`/api/v1/voice-type/stats`=200（=migration成功）、
  新規 `POST /coach/sessions/{id}/promote-recording`（無認証）=**401**（404でない＝新ルート反映）、
  `POST /voice-type/analyze`（無認証）=**400**（401でない＝匿名トライアル稼働）。
- 教訓: スキーマ変更PRでも段取りは「マージ→自動デプロイ→上記curlで200を確認」で完結。手動SSHは
  502になった時だけ（その場合 `docker compose ... logs backend` で alembic のエラーを見る）。
