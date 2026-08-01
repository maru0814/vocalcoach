# 84. 設計書 — KPI日次スプレッドシート自動記録

- 作成日: 2026-08-01
- 作成: architect（発端はオーナー指示。COO差配 → architect → backend-engineer → sre → qa-engineer）
- 関連: docs/60（本番運用メモ）, docs/62（集客全振り30日）, `scripts/ops/daily_metrics_line.py`（日次LINE通知・先行実装）

## 1. 目的

リリース以降の全日分と、以後毎日の主要KPIを Google スプレッドシートに自動記録する。
オーナーのアカウント（yumaruyama0814@gmail.com）と開発テストアカウント（`%@example.com`）は集計から除外する。

対象KPI（オーナー指定の6指標）:
1. LP遷移UU数（リンクごとに分けて出す）
2. 診断UU
3. 無料会員登録者数
4. ログインUU
5. チャット利用UU
6. 有料会員登録者数

## 2. 現状の計測ギャップと対応方針（オーナー承認済み）

| 指標 | 現状 | 対応 |
| --- | --- | --- |
| LP遷移UU（リンク別） | UTM未実装。流入リンクの識別不可。アクセスログは 2026-07-08 開始・保持30日 | **SNS投稿リンクにUTM付与**（今後分）。過去分はランディングページ別UU＋「utmなし」で記録 |
| 診断UU | `voice_type_diagnoses` が user_id/IP を持たず件数のみ | **user_id / visitor_hash（ソルト付きIPハッシュ）カラム追加**（今後分）。ログが残る期間は `POST /api/v1/voice-type/analyze` のユニークIPで推定 |
| ログインUU | ログインイベント記録なし | **`login_events` テーブル新設**（今後分）。過去分は既存の「アクティビティUU（認証操作したユニーク会員）」で代替し備考に明記 |
| 有料会員登録者数 | `subscriptions` は現在状態のみで履歴なし | 日次実行時に**プレミアム会員集合のスナップショット差分**で新規を算出（状態ファイル）。過去分は `created_at` 近似（現状ほぼ0のため影響軽微） |

## 3. 全体構成

```
[VPS host cron 08:10 JST 毎朝]
  scripts/ops/kpi_daily_sheet.py（host python3・標準ライブラリのみ）
    ├─ docker exec caddy   → /data/access.log* を読む（LP UU・リンク別UU・診断UU-IP）
    ├─ docker exec backend → SQLite /data/app.db を集計（登録/ログイン/チャット/有料）
    └─ docker exec sns     → kpi_sheets_push.py（gspread で Google Sheets に upsert）
                              認証情報は scripts/sns_autopost/.env（KPI_SHEET_ID / GOOGLE_SA_JSON_B64）
```

- 既存の `daily_metrics_line.py` / `access_funnel.py` と同じ「host cron + docker exec」方式。
  sns コンテナから兄弟コンテナを exec できないため host 実行とする（docs/60 の既定方針）。
- Sheets への書き込みだけは Google ライブラリが必要なため、sns コンテナ内の新スクリプト
  `kpi_sheets_push.py` に委譲する（LINE通知を `line_client.push_text()` に委譲するのと同じパターン）。

## 4. スプレッドシート構造

### タブ1: `日次KPI`（1日=1行、日付で upsert）

| 列 | 定義 |
| --- | --- |
| 日付 | JST の暦日 |
| LP遷移UU_合計 | HTMLページ相当GETのユニークIP。bot/監視UA除外（§6） |
| UU_トップ | ランディング `/` のユニークIP |
| UU_診断LP | `/lp/shindan` |
| UU_ボイトレLP | `/lp/voitore` |
| UU_声タイプ | `/voice-type` 配下 |
| UU_その他 | 上記以外のページ |
| 診断UU | 実装後: `distinct(user_id または visitor_hash)`。それ以前ログ有期間: analyze POST のユニークIP（推定）。ログ無し期間: 空欄 |
| 診断実行数 | `voice_type_diagnoses` の件数 |
| 無料会員登録数 | `users`（除外適用）の `created_at` 日次件数 |
| ログインUU | 実装後: `login_events` の distinct user（除外適用）。それ以前: アクティビティUU代替 |
| チャット利用UU | その日 `chat_messages` があったセッションの distinct user（除外適用） |
| 有料新規 | プレミアム集合の前日比増分（過去分は `created_at` 近似） |
| 有料会員数 | 実行時点の `status IN (active,trialing) AND current_period_end > now` 会員数（除外適用）。日次実行時のみ記録 |
| 備考 | 「ログ欠測」「VPS停止」「代替値」等を自動付与 |

### タブ2: `リンク別LP流入`（1日×リンク=1行、該当日の行を洗い替え）

| 列 | 定義 |
| --- | --- |
| 日付 | JST |
| utm_source / utm_medium / utm_campaign | クエリから取得。無ければ `(utmなし)` |
| ランディングパス | `/`, `/lp/shindan` など |
| UU | その組のユニークIP |

- 「リンクごと」の識別は UTM 3点で行う。SNS投稿リンクは §7 の規約で自動付与。
- X プロフィール固定リンクは手動設定のため、オーナーが
  `https://sora-vocal-ai.duckdns.org/?utm_source=x&utm_medium=profile&utm_campaign=profile`
  に張り替える（セットアップ手順に含める）。

## 5. 除外規則（実会員定義の拡張）

- 既存の実会員定義: `email NOT LIKE '%@example.com'`（daily/weekly と共通）
- 本件でオーナー本人 `yumaruyama0814@gmail.com` を追加除外。
- 実装: `kpi_daily_sheet.py` 内の定数 `EXCLUDE_EMAILS`（環境変数 `KPI_EXCLUDE_EMAILS` で上書き可、カンマ区切り）。
- 適用範囲: 登録数・ログインUU・チャットUU・有料系・診断UU（user_id が取れた分のみ）。
- **IP除外（2026-08-01 追加）**: `KPI_EXCLUDE_IPS`（カンマ区切り。環境変数優先、無ければ
  `scripts/sns_autopost/.env` から読む）に登録した固定IPは、LP遷移UU・リンク別UU・
  診断UU(IP推定) の全IPベース指標から除外する。さらに backend コンテナ内で
  `sha256("JWT_SECRET:ip")` を再現照合し、除外IPからの**匿名診断（visitor_hash）も除外**する。
- **残る限界**: IPが変わる回線（モバイル等）からのオーナーのアクセスは除外できない。
  固定IPが変わったら `KPI_EXCLUDE_IPS` を更新する。

## 6. アクセスログ集計の規則

- 既存規則を踏襲: 静的アセット・`/api`・`/sns`・`/healthz`・`/_next`・`/favicon` を除いた GET のみ。
- **bot/監視除外（新規）**: User-Agent が
  `bot|crawl|spider|slurp|curl|wget|python-requests|httpx|monitor|uptime|headless|facebookexternalhit|preview|scan`
  にマッチする行は除外する。死活監視（uptime.yml が15分毎に `/` を curl）や SNS のリンクプレビュー
  クローラで UU が水増しされるのを防ぐ。既存 daily/weekly の数字とはこの分だけズレる（正確側に寄る）。
- 診断UU-IP 推定: `POST /api/v1/voice-type/analyze` のユニーク client_ip（bot除外後）。

## 7. 計測強化の実装

### 7.1 `login_events` テーブル（backend）

```
login_events: id PK / user_id FK(users.id) index / created_at DateTime index (UTC naive)
```
- `POST /api/v1/auth/login` 成功時に1行 INSERT（best-effort。失敗してもログインは成功させる）。
- Alembic マイグレーション追加。

### 7.2 `voice_type_diagnoses` 拡張（backend）

```
+ user_id     Integer nullable index   … ログイン診断時のみ
+ visitor_hash String(64) nullable index … sha256(JWT_SECRET + client_ip)。生IPは保存しない
```
- PII方針の変更: 生IPやメールは引き続き保存しない。ソルト付き一方向ハッシュのみ
  （UU算出のための仮名化識別子）。docstring を更新する。
- `analyze` エンドポイントで記録。UU = `distinct(coalesce('u:'||user_id, 'v:'||visitor_hash))`。

### 7.3 SNS投稿リンクの UTM 付与（sns）

- `generate_and_post.py` で投稿直前に `link` へ `utm_source=x&utm_medium=post&utm_campaign=<pillar>` を付与。
- Caddy ログの `request.uri` にクエリごと残るため、フロント側の実装は不要。

## 8. Sheets 認証と push（sns コンテナ）

- `scripts/sns_autopost/requirements.txt` に `gspread` を追加。
- `kpi_sheets_push.py`（新規）: stdin で `{"daily": [...], "links": [...]}` を受け取り、
  - `日次KPI`: 日付一致行を上書き、無ければ追記（ヘッダ無ければ自動作成）
  - `リンク別LP流入`: 対象日の既存行を削除してから追記（洗い替え）
- 認証情報は `scripts/sns_autopost/.env`（VPS上・git管理外）:
  - `KPI_SHEET_ID` … スプレッドシートのID
  - `GOOGLE_SA_JSON_B64` … サービスアカウントJSONの base64
- オーナー側の1回作業: GCPでサービスアカウント作成 → Sheets API 有効化 → シートをSAメールに編集者共有。

## 9. 集計スクリプト `scripts/ops/kpi_daily_sheet.py`

- 実行モード:
  - 引数なし: 前日(JST)1日分を集計して upsert（cron用）
  - `--since 2026-06-06 [--until 2026-07-31]`: 期間バックフィル（初回の全日分記録用）
  - `DRY_RUN=1`: シートに書かず集計結果をJSONで表示
- 有料新規の状態ファイル: `/var/log/kpi_premium_state.json`（前回実行時のプレミアム会員emailリスト）。
- データ可用性の注記（備考欄に自動付与）:
  - 2026-07-08 より前: アクセスログ由来の列は空欄（「ログ欠測」）
  - 2026-07-08: ログ開始日（08:40〜）のため部分集計
  - 2026-07-11〜14: VPS電源断で停止（docs/60）。ゼロは実ゼロだが「VPS停止」注記
- リリース日（バックフィル起点）: **2026-06-06**（本番ドメイン切替・診断機能公開）。

## 10. cron（sre）

- `10 8 * * * python3 $REPO/scripts/ops/kpi_daily_sheet.py >> /var/log/kpi_sheet.log 2>&1`
  （LINE通知の 08:00 と分離して 08:10）
- `scripts/deploy/remote_deploy.sh` と `scripts/sns_autopost/setup_approval.sh` の両方の一覧に追加し、
  `CRON_MARKER` に `kpi_daily_sheet\.py` を追加（再同期の対象にする）。

## 11. テスト観点（qa-engineer が実施）

- TC-KPI-01: Alembic マイグレーションが空DBと既存DBの両方で通る（SQLite）
- TC-KPI-02: login 成功で `login_events` に1行、失敗で0行
- TC-KPI-03: analyze 実行で `user_id`（ログイン時）/`visitor_hash` が保存される
- TC-KPI-04: ログパーサ — bot UA 除外、日跨ぎ境界(JST)、utm抽出、パス分類をフィクスチャで検証
- TC-KPI-05: DB集計 — 除外メール（オーナー・@example.com）が全指標から落ちる
- TC-KPI-06: upsert — 同日2回実行で行が重複しない（DRY_RUNとモックで確認）
- TC-KPI-07: UTM付与 — 既存クエリがあるリンクにも `&` で正しく連結される

## 12. 制約・既知の限界（オーナー向けサマリ）

- IPベースの指標はオーナー自身の閲覧を除外できない（§5）。
- アクセスログの保持は30日。**7/8以前のLP遷移UUは永遠に取得不能**、それ以降も古い分は
  ローテーションで消えるため、バックフィルは実装直後に1回だけ確実に実行する。
- 「診断UU」「ログインUU」の過去分は代替値（推定IP UU／アクティビティUU）。真値は計測実装デプロイ日以降。
- 有料会員は現状 Stripe テスト運用のため、実質0が続く想定。スナップショット差分方式は初回実行日から有効。
