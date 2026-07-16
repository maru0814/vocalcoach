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

### Xフォロー候補（docs/58/59。2026-07 追加、07-06に方針転換）
- **2026-07-06 方針転換**: 提案返信・専門家ゲート（`lead_reply.py`/返信用ルーブリック）を廃止し、
  「フォローすべき人だけ」を一覧で届ける形に変更。理由: Xの自動化ポリシーはフォロー/返信の
  「大量・機械的な実行」自体を禁止しており、人間操作を模した一括自動化はボタン化しても
  規約リスクが消えないため。**フォローの実行は常にXアプリで運用者本人の指**。
- **cron**: 探索=毎朝10時 / フォロバ計測=日曜22:30（ログは `/var/log/sns_leads.log`）。
  デプロイ（`remote_deploy.sh`）が冪等登録するので手作業不要。cron一覧の正は
  `setup_approval.sh --cron` と `remote_deploy.sh` の2箇所（変更時は両方揃える）。
- **毎朝の流れ**: 10時にLINEへ「🎯今日のフォロー候補」が最大15件（`MAX_FOLLOWS_PER_DAY`）
  一覧で届く（相手のプロフィール要約・元ツイート抜粋・プロフィールリンク）→
  気になる人をXアプリで自分の指でフォロー → 最後に[✅全員フォローした]を1回押すと記録される
  （**このボタンはX APIを一切呼ばない**。押し忘れてもフォロバ計測に載らないだけで実害なし）。
- **1日の安全なフォロー数（目安。公式な保証値ではない）**: 新規/小規模アカウントは
  最初の1〜2週間は**10〜15件/日**、様子を見て段階的に25件程度まで。**1日分を数分で
  一気にタップせず時間を分けて行う**（フォロー速度のスパイクが検知されやすいため）。
  既定 `MAX_FOLLOWS_PER_DAY=15` はこの経験則に基づく初期値。
- **前提（人間作業・初回のみ）**: console.x.com で**従量課金クレジット（最低$5）**をチャージ。
  未チャージだと検索/メンション取得が4xxになり「本日は該当なし」通知が続く（落ちはしない）。
- **コスト**: read課金は日次予算 `LEAD_DAILY_READ_BUDGET_USD`（既定0.60）で頭打ち。
  実績は sns コンテナ内 `/data/lead_reads_log.jsonl` に日別記録。返信生成・専門家ゲートを
  廃止したことで Gemini API 課金・処理は完全に発生しなくなった（探索readのみ）。
- **手動実行**: GitHub Actions の「SNS Ops」（workflow_dispatch）から
  `lead-finder-dry`（安全確認）/`lead-finder`（本実行）/`lead-metrics`/`healthz`/`diag` を選んで実行できる。
  SSH不要でスマホからでも回せる。
- **トラブルシュート**:
  ```bash
  tail /var/log/sns_leads.log                     # 探索の実行ログ（除外理由・read概算も出る）
  docker compose -f docker-compose.prod.yml --env-file .env \
    exec -T sns sh -c "tail -3 /data/engaged_log.jsonl"   # 提示/フォロー実施/見送りの記録
  docker compose -f docker-compose.prod.yml --env-file .env \
    exec -T sns python lead_finder.py --dry-run    # 手動で安全確認（LINE・記録に触れない）
  ```
- **事例: exit 137（SIGKILL）で探索が落ちる（2026-07-05）**: VPSは960MBで、当時の実装は
  返信生成・専門家ゲートで Gemini SDK を読み込み RSS約420MB まで膨らんでいた。デプロイ直後
  （ビルドでメモリが荒れているタイミング）に実行すると OOM キラーに殺されることがあった
  （`diag` タスクの dmesg で `Out of memory: Killed process (python)` を確認。数分待てば
  再実行は成功）。07-06の方針転換で lead_finder は Gemini SDK を一切読み込まなくなり、
  この経路のメモリ圧はそもそも解消済み（再発時は他要因を疑う）。
- **旧仕様の名残**: 07-06以前に届いた「✅返信する/⏭スキップ」ボタン付きの古いLINEカードを
  押しても、対応するpostback処理は削除済みのため「⚠️ 不明な操作です」と返るだけで実害はない。
- **事例: 「音痴」クエリのノイズ混入（2026-07-06）**: 本番実行で、あるアニメの1シーン
  （キャラクターが音痴という設定）がバズり、それに便乗する第三者コメントが「音痴」
  クエリに大量混入した（本人の悩みではない）。対策として `require` を本人の悩み語
  （直したい/治したい/克服したい/なおしたい/下手/苦手）必須に強化。併せて運用者が
  明示した3テーマ（歌全般の上達願望`sing_better`/ミックスボイス`mixvoice_want`/
  カラオケ上達`karaoke_up`）を`leads.PRIORITY_QUERY_IDS`として新設し、日替わり
  ローテーションの対象外で**毎回必ず実行**するようにした。

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
- **デプロイ直後だけ `/api/*` が 502**: backend を再ビルドするデプロイでは、旧コンテナ停止→新コンテナ起動の数十秒だけ Caddy が upstream に届かず `/api/*` が **502** になる（frontendトップは 200 のまま）。**正常な過渡状態**なので、起動完了まで待って再確認する。切り分け: `docker compose -f docker-compose.prod.yml ps`（backend が `Up` で `Restarting` でない）＋ `logs backend` に `Application startup complete`。回復後は 502 でなく 404（＝到達はしている・ルート無し）になる。数分たっても 502 のままなら起動失敗を疑い `logs backend` のトレースバックを見る。

  ```bash
  cd /opt/vocalcoach/docker
  docker compose -f docker-compose.prod.yml ps        # backend が Up か
  docker compose -f docker-compose.prod.yml logs --tail=25 backend | grep -iE "startup complete|error|traceback"
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

## アクセスログ（LP到達数の週次計測）（2026-07-08 追加 / PR#143）
- 背景: それまで Caddyfile に `log` が無く、プロフィールリンク→LP到達の**訪問数が一切取れなかった**。
  唯一の間接指標は声タイプ診断のDB記録（匿名・累計7件）のみで、ファネルが繋がっていなかった。
- 設定: `docker/Caddyfile` のサイト直下に `log`（`output file /data/access.log` / `format json` /
  `roll_size 10MiB` / `roll_keep 5` / `roll_keep_for 720h`）。ログは caddy_data volume(`/data`)に
  永続し、`--force-recreate caddy` をまたいでも残る。ディスクは最大約50MiBで頭打ち。
- 本番実証: PR#143 マージ→自動デプロイ green。`caddy` up・`/`=200 を確認後、`/data/access.log` に
  リクエストがJSON1行で記録されることを確認済み。
- **週次の集計クエリ**（growth-operator が週次レポートで使う。VPS上で実行）:
  ```bash
  # 直近ログの「ページ閲覧」到達数（静的アセット/API/sns を除外＝HTMLページ相当のみ）
  ssh root@160.251.177.227 'docker exec docker-caddy-1 sh -c "
    cat /data/access.log* 2>/dev/null | \
    grep -vE \"\\\"uri\\\":\\\"/(api|sns|_next|favicon|.*\\.(css|js|png|jpg|svg|ico|woff2?))\" | \
    wc -l"'
  # ユニーク訪問者数の目安（client_ip でユニーク化。厳密なUUではないが週次の傾向把握には十分）
  ssh root@160.251.177.227 'docker exec docker-caddy-1 sh -c "
    cat /data/access.log* 2>/dev/null | grep -oE \"\\\"client_ip\\\":\\\"[^\\\"]+\" | sort -u | wc -l"'
  ```
  注: JSON各行に `uri`・`client_ip`・`status`・`ts`（epoch秒）があるので、日付で絞るなら `jq` を
  使うのが確実（例: `jq -r 'select(.request.uri|test("^/($|\\?)")) | .ts'`）。将来リンクに UTM を
  付ければ `uri` のクエリ文字列で流入元を分離できる。

## LP到達ファネルの週次自動集計ルーチン（2026-07-08 追加 / PR#145）
- **目的**: 上記の手集計を毎週自動化。LLMを使わず（コスト0）、既存のsns計測cronと同じホストcron方式。
- **スクリプト**: `scripts/ops/access_funnel.py`。ホストで `python3` 実行し、`docker exec` で
  caddy(アクセスログ) と backend(SQLite) から集計 → `/var/log/access_funnel.jsonl` に1行追記。
  - 集計項目: 直近7日の `page_views`(HTMLページ相当のGETのみ) / `unique_ips` /
    `diagnoses_total`・`diagnoses_window` / `users_real_total`・`users_real_window`
    （`users_real` は `@example.com` のテストアカウントを除外した実会員）。
  - host実行なのは、sns コンテナ内からは兄弟コンテナ(caddy/backend)を `docker exec` できないため。
- **cron**: `45 22 * * 0`（日曜22:45。lead_metrics=22:30 の直後で、週次レポート時に数字が揃う）。
  登録は `scripts/deploy/remote_deploy.sh` と `scripts/sns_autopost/setup_approval.sh` の両方に冪等登録
  （文字列完全一致で重複判定。両ファイルの一覧は必ず揃える）。
- **growth-operator の読み方**（週次レポートで使う）:
  ```bash
  # 最新の週次スナップショット
  ssh root@160.251.177.227 'tail -1 /var/log/access_funnel.jsonl' | jq .
  # 推移（直近8週）
  ssh root@160.251.177.227 'tail -8 /var/log/access_funnel.jsonl' | jq -c '{ts,page_views,unique_ips,diagnoses_window,users_real_window}'
  ```
- **本番実証**: PR#145 デプロイ後に手動1回実行して `/var/log/access_funnel.jsonl` に初回行が入ることを確認済み
  （初回はログ蓄積前のため page_views=0。診断・実会員はDB既知値と一致）。

## 毎朝の定例メトリクスLINE通知（daily_metrics_line.py）（2026-07-09 追加）
- **目的**: 毎朝、前日(JST)の「サービスページ訪問者数(非会員含む)・新規登録者・ログインUU」を
  運用者のLINEに1通プッシュする。上の週次ファネルの日次・自動通知版。
- **スクリプト**: `scripts/ops/daily_metrics_line.py`。host で `python3` 実行。集計元は週次ファネルと同じ:
  - 訪問者(非会員含む) = Caddyアクセスログ(`/data/access.log*`)の**前日のユニーク訪問IP**（＋ページ閲覧PV）。
    静的アセット/API/sns を除外した「HTMLページ相当のGET」だけを数える（access_funnel と同一規則）。
  - 新規登録 = 本番SQLite `users`（`@example.com` のテストを除外＝実会員）の前日 `created_at` 件数。
  - ログインUU = **その日に認証必須の操作(チャット作成/更新・録音・FB)をしたユニーク実会員**。
    login を記録するテーブルが無いための代替値（＝実質デイリーアクティブ会員）。真のログイン数が要るなら
    backend にログインイベント記録を足す（backend-engineer）。
  - **メール同送**: 新規登録者と ログインUU本人の**メールアドレス**を、それぞれの見出しの下に列挙して
    LINE本文に載せる（運用者が「誰が」を追えるように）。件数0なら見出しのみ。
    PII蓄積を避けるため `/var/log/daily_metrics.jsonl` の履歴には件数のみ記録し、メールは残さない。
  - 送信は sns コンテナ内 `line_client.push_text()` を `docker exec` で叩いて再利用（LINEキーは sns の env）。
  - host実行なのは access_funnel と同じ（sns コンテナから兄弟の caddy/backend を exec できないため）。
  - 履歴は `/var/log/daily_metrics.jsonl` に1行/日で追記（推移を後から追える）。
- **cron**: `0 8 * * *`（毎朝8:00。サーバTZ=JST）。`remote_deploy.sh` と `setup_approval.sh` の両方に冪等登録。
- **注意**: Caddyログは 2026-07-08 08:40 から記録開始（PR#143）なので、7/8ぶんの訪問者数は午前欠けの部分集計。
  7/9 以降は丸1日ぶん。ユニークIPは NAT/動的IPで厳密なUUではないが、週次と定義を揃えた傾向把握用。
- **手動実行 / 動作確認**:
  ```bash
  ssh root@160.251.177.227 'DRY_RUN=1 python3 /opt/vocalcoach/scripts/ops/daily_metrics_line.py'  # 集計だけ(LINE送信なし)
  ssh root@160.251.177.227 'python3 /opt/vocalcoach/scripts/ops/daily_metrics_line.py'            # 実送信
  ```
- **本番実証**: 2026-07-09、前日(7/8)ぶんを実DB/実ログで集計→LINE実送信まで確認済み
  （訪問者16・PV79・新規登録1・ログインUU2、`[LINE] OK`）。

## 事例: VPS電源断で自動デプロイ3連続失敗 → 本番が4日間`main`から取り残される（2026-07-12〜16）
- **症状**: 声タイプ図鑑（PR#159）を main にマージしたのに、本番 `/voice-type/{id}` が **404 のまま**。
  サイト自体は 200・`/sns/healthz` も `{"status":"ok","line":true}` で、**一見「本番は正常」に見えるのが罠**。
- **原因**: 2026-07-12 のVPS電源断。この間に走った Deploy to VPS が **3連続 failure**（01:54 / 12:30 / 14:37。
  12:30 はPR#159マージ直後）。デプロイだけが落ち、VPS復帰後は Docker の restart policy でコンテナが自動起動したため、
  **旧コミットのまま無停止で稼働継続**＝ヘルスチェックは全部緑。本番の git HEAD は `527106d`(07-10) で止まり、
  origin/main `3304b73` から **数PRぶん取り残されていた**。
- **切り分け（これが最短）**: ヘルスチェックではなく **本番のコミットを直接見る**。
  ```bash
  ssh root@160.251.177.227 'cd /opt/vocalcoach && git rev-parse --short HEAD && git fetch -q origin main && git rev-parse --short origin/main'
  # HEAD != origin/main なら「デプロイされていない」。新機能が404の時は真っ先にこれ。
  gh run list --workflow deploy.yml --limit 5 --json headSha,conclusion,createdAt   # 失敗が続いていないか
  ```
- **復旧**: `gh run rerun <id>` は「workflow file may be broken」で不可、`gh workflow run`（workflow_dispatch）も
  **PATに `actions:write` が無く HTTP 403**。→ **手動デプロイ経路で復旧**:
  ```bash
  ssh root@160.251.177.227 'cd /opt/vocalcoach && bash scripts/deploy/remote_deploy.sh'
  # remote_deploy.sh が VPS 側で origin/main を pull するので、実行時点の main が出る → "Deploy done: 3304b73..."
  ```
  → 全8タイプ `/voice-type/{id}` が 200、有名人イラスト配信、`/sns/healthz` 緑を確認。
- **教訓**:
  1. **「サイトが200」は「デプロイ成功」を意味しない**。電源断・デプロイ失敗でも旧コンテナは生き続ける。
     機能が出ていない時は healthz を見ずに **HEAD vs origin/main** を比較する。
  2. **デプロイ失敗は silent に積み上がる**。長期の停電・障害のあとは `gh run list --workflow deploy.yml` を必ず見る。
  3. Actions が使えない時の**逃げ道は `remote_deploy.sh` の手動実行**（PATに actions:write が無くても復旧できる）。
  4. squash マージ後に**同じブランチの重複PRが自動で残る**ことがある（merge-base ずれで差分が「新規」に見える）。
     中身が main にあるなら **マージせずクローズ**（今回 #162/#164 をクローズ）。

## 死活監視（uptime.yml）（2026-07-17 追加・docs/62 の前提条件）

**背景**: 2026-07-11夜〜07-14 08:07 の約3日間、VPS ごと停止（電源断→カーネル 6.8.0-124→134 で再起動）していたが誰も気づかなかった。Caddy ログの 7/12・7/13 が完全にゼロ、朝8時の LINE 定例が3日届かないのが唯一の痕跡。**VPS 上の cron は VPS ごと死ぬため、死活監視は必ず外に置く**。

- **仕組み**: `.github/workflows/uptime.yml`（GitHub Actions schedule・15分毎）が外形監視:
  `/`（Caddy+frontend）・`/api/v1/voice-type/stats`（backend+DB）・`/sns/healthz`（sns webhook）の3点を curl。
  非200は20秒後に1回だけリトライしてから障害判定（誤報防止）。
- **通知は2段構え**:
  1. **GitHub Issue（主経路・追加設定なしで動く）**: 障害で `uptime` ラベルのIssueを自動作成→GitHubからメール通知が飛ぶ。復旧で自動クローズ。Issueの開閉が状態管理を兼ね、継続中の再通知は6時間毎コメントに抑制。障害履歴もIssueに残る。
  2. **LINE（任意・即時性）**: repo secrets `LINE_CHANNEL_ACCESS_TOKEN` / `LINE_OPERATOR_USER_ID` が登録されていれば併送。**PATにsecrets権限が無いためCLI登録は403**。人間が GitHub Web UI（Settings→Secrets and variables→Actions）で登録する。値は VPS `/opt/vocalcoach/scripts/sns_autopost/.env` の同名キー。ローテ時は両方更新。
- **疎通テスト**: `gh workflow run uptime.yml -f test_alert=true`（LINE設定後）→ 🔔テスト通知が届けば経路正常。Issue経路はrun成功＝正常。
- **アラートが来たら**: 本ドキュメント冒頭のプレイブック順（curl→SSH→docker compose ps）。SSH も通らなければ ConoHa コンソールで電源確認（人間作業）。**復旧後は必ず `gh run list --workflow deploy.yml` で silent なデプロイ失敗の積み上がりを確認**（上の 2026-07-12〜16 事例の教訓）。
- **限界（正直に）**: GitHub Actions の schedule は数分〜数十分遅延しうる。分単位の SLA 監視ではなく「時間単位の停止に当日気づく」ための最小構成。

## 事例: cron重複でLINE承認が毎回2通・片方が「押しても効かない」（2026-07-16 発見・解消）
- **症状**: 投稿スロットごとに **LINE承認依頼が2通**届く。片方をタップしても承認が通らない／`pending` のまま残る。
  Gemini呼び出し（生成＋専門家レビュー）も2倍かかっていた。
- **原因**: crontab に**同一時刻の重複エントリ**が残っていた。docker化前の**レガシーな host venv 版**と、現行の
  **docker exec 版**が両方生きており、12:00 / 21:00 / 23:00 に**それぞれ2回**実行されていた。
  ```
  0 12 * * * cd /opt/vocalcoach/scripts/sns_autopost && .../.venv/bin/python generate_and_post.py --slot 1   # ← レガシー(host)
  0 12 * * * cd /opt/vocalcoach/docker && docker compose ... exec -T sns python generate_and_post.py --slot 1 # ← 正(docker)
  ```
- **なぜ片方が効かないか（決定的）**: sns コンテナの `/data` は**named volume**（`docker_sns_data`）で host と共有していない。
  そのためキューが2つに分裂していた。
  - 正: `/var/lib/docker/volumes/docker_sns_data/_data/pending_queue.jsonl` ← **LINE webhook（snsコンテナ）が読む**
  - 孤児: `/opt/vocalcoach/scripts/sns_autopost/pending_queue.jsonl` ← host cron が書く
  host 版が送った承認依頼の id は**正キューに存在しない**ため、タップしても webhook が引けず失敗する。
  （実証: 重複runの id `afc4737116b3` は孤児キューに1件・正キューに0件）
- **切り分け**: 「同じ内容の承認が2通来る」「押しても通らない」時は、**まず crontab の重複を疑う**。
  ```bash
  crontab -l | grep -c generate_and_post.py            # slotごとに2行あれば重複
  grep -E "^\[$(date +%F)\] slot=" /var/log/sns_autopost.log | sort | uniq -c   # 各slotが2回走っていないか
  docker inspect docker-sns-1 --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}{{println}}{{end}}'
  find /opt /var/lib/docker/volumes -name pending_queue.jsonl   # キューが2つ出たら分裂している
  ```
- **対処**: レガシーな host venv 版の3行のみ削除し、**docker exec 版に一本化**（バックアップを取ってから）。
  ```bash
  crontab -l > /root/crontab.bak.$(date +%Y%m%d-%H%M%S)
  crontab -l | grep -v "sns_autopost/\.venv/bin/python" | crontab -
  crontab -l   # docker exec 版・lead_finder・lead_metrics・access_funnel・daily_metrics が残ることを確認
  ```
- **教訓**:
  1. **docker化した後、旧 host 実行の cron を消し忘れると二重実行になる**。移行時は必ず旧エントリを撤去する。
  2. コンテナが named volume を使う場合、**host から同じスクリプトを叩くと別のデータを触る**。
     「同じスクリプトなら同じ結果」にはならない。
  3. 承認が通らない・pending が溜まる時は、**承認UIやX APIより先に「id がどのキューに居るか」**を見る。
  4. 孤児キュー `/opt/vocalcoach/scripts/sns_autopost/pending_queue.jsonl` は writer が居なくなったので放置で無害。
     将来の調査で紛らわしいので、参照する時は**必ず docker volume 側が正**と覚えておく。
