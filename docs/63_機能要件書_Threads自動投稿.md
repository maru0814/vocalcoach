# Threads自動投稿 機能要件書

- 文書番号: 63
- 作成: PdM
- 関連: docs/24（SNS自動化）, docs/29（X有料自動化・予算）, docs/58/59（リード獲得）, docs/60（本番運用メモ）

## 1. 概要

- 既存のX(Twitter)自動投稿パイプライン（`scripts/sns_autopost/`）に、**Meta公式 Threads API** による Threads への同時自動投稿を追加する。
- 解決する課題: 現在SNS発信はXのみ。Threadsは投稿APIが**無料**で、同じ生成資産（文面・インフォグラフィック画像）を追加コストほぼゼロで二次配信でき、リーチの分散（Xアルゴリズム依存の低減）と新規流入チャネルの獲得ができる。

## 2. 想定ユーザー / ユースケース

- ペルソナ: 運用者（本会社の一人運用者）。エンドユーザーには間接的に投稿が届く。
- UC-01: cron が昼/夜に投稿を生成 → 専門家ゲート → LINE承認 → **XとThreadsの両方**へ自動投稿される。
- UC-02: Threads側の認証が切れた/失敗した場合でも X 投稿は止まらず、運用者はLINEで失敗を知る。

## 3. スコープ

### 3.1 対象（やること）
- Threads APIクライアントの新規実装（テキスト＋画像1枚、自己リプによるスレッド化）
- LINE承認フローへの統合（**承認1回でX+Threads両方に投稿**。追加の承認操作は増やさない）
- 長期アクセストークン（約60日）の自動リフレッシュ
- 投稿ログへのThreads投稿ID記録
- `.env.example` / README / セットアップ手順の更新

### 3.2 対象外（やらないこと）
- Threadsのインプレッション計測（`fetch_metrics.py` 相当）— 将来対応。投稿IDは記録しておく
- Threads向けの文面最適化・専用テンプレ（初期は X と同一文面を流用）
- Threadsでのリード獲得（lead_finder 相当）
- Threadsのみへの投稿モード（X を止めて Threads だけに出す運用）
- Instagram / TikTok 等その他SNS

## 4. ユーザーストーリー

- US-01: 運用者として、LINEで1回承認するだけでXとThreadsの両方に投稿されてほしい。なぜなら承認の手間を増やしたくないから。
- US-02: 運用者として、Threads投稿が失敗してもX投稿は成功してほしい。なぜならThreadsは追加チャネルでありXが主戦場だから。
- US-03: 運用者として、トークン期限切れで投稿が静かに止まる事態を避けたい。なぜなら気づかないまま機会損失するから。

## 5. 機能要件

### FR-01: Threads投稿クライアント
- 概要: `threads_client.py` を新設し、Threads Graph API（`https://graph.threads.net/v1.0`）で投稿する。
- 詳細仕様:
  - 投稿は2ステップ: ①メディアコンテナ作成 `POST /{user_id}/threads` → ②公開 `POST /{user_id}/threads_publish`
  - テキストのみ: `media_type=TEXT`
  - 画像付き: `media_type=IMAGE` + `image_url`（公開URL）。画像URLは既存の `GET /sns/img/{name}`（`SNS_PUBLIC_BASE_URL` ベース）を使う
  - コンテナ作成後、公開まで最大30秒程度の処理待ちが必要な場合がある（画像/動画）。ステータス確認 or 固定待機＋リトライ（最大3回・計30秒以内）を行う
  - 自己リプ: `reply_to_id={前投稿ID}` を指定してリプ本体を投稿し、Xと同じ「本投稿→リプ本体」のスレッド構造を再現する
  - 本文は **500字** に収める。超過時は末尾を「…」で切り詰める（Xの投稿は実質280字相当以下のため通常は発生しない）
  - URLリンク: X同様、既定では本文にURLを入れない（`POST_LINK` の扱いはXと共通の値を参照）
- 入出力: 入力 `(text, reply, link, post_link, image_path)` / 出力 `(ok: bool, threads_id: str, info: str)`（`post_to_x()` と同形）
- 例外ケース: キー未設定 → `(False, "", "THREADS_KEYS_MISSING")`。API失敗 → HTTPステータスと本文先頭200字を info に含める。例外は捕捉して `(False, "", "EXC: ...")`

### FR-02: 認証とトークン自動リフレッシュ
- 概要: OAuth 2.0 長期トークン（約60日有効）を自動延命し、手動再発行を不要にする。
- 詳細仕様:
  - 初期設定: 運用者が Meta 開発者アプリで長期トークンを発行し `.env` の `THREADS_ACCESS_TOKEN` に設定。`THREADS_USER_ID` も設定
  - トークンの実体は `{SNS_DATA_DIR}/threads_token.json`（`{access_token, refreshed_at}`）に保存。初回は `.env` の値をシードとして取り込む
  - 投稿実行時、`refreshed_at` から **45日** 経過していたら `GET /refresh_access_token?grant_type=th_refresh_token` で更新し、`threads_token.json` を上書きする（リフレッシュは24時間経過後から可能・期限内のみ可能）
  - リフレッシュ失敗時は既存トークンで投稿を試み、失敗したら FR-04 の失敗通知に含める
- 例外ケース: `threads_token.json` が無い＆環境変数も無い → Threads投稿をスキップ（`THREADS_KEYS_MISSING`）

### FR-03: 承認フロー統合（承認1回で両チャネル投稿）
- 概要: LINEの [✅承認して投稿] 1回で X → Threads の順に投稿する。
- 詳細仕様:
  - `THREADS_ENABLED=1`（既定 `0`）のときだけ Threads へも投稿する
  - 投稿順序: X が先。X が失敗したら Threads も投稿しない（従来どおり `failed` 扱い）
  - X 成功 + Threads 失敗 → 全体は `posted` のまま。`info` に Threads の失敗理由を追記し、LINE返信にも明記する（例: 「✅ Xに投稿しました / ⚠ Threadsは失敗: HTTP 401」）
  - `--post-now`（即投稿経路）でも同じ分岐を通る
  - 専門家ゲート・DRY_RUN・APPROVAL_MODE の挙動は一切変えない（ゲート通過後の配信先が増えるだけ）
- 例外ケース: `THREADS_ENABLED=1` だがキー未設定 → Threadsのみスキップし info に `THREADS_KEYS_MISSING` を記録

### FR-04: 投稿ログと通知
- 概要: 投稿記録に Threads の結果を残し、運用者が結果を把握できるようにする。
- 詳細仕様:
  - `posts_log.jsonl` のレコードに `threads_id`（成功時のID / 失敗時は空文字）を追加。既存レコード（キー無し）は「Threads投稿なし」として扱う
  - 予算ガード（`MAX_POSTS_PER_DAY` / `MONTHLY_COST_CAP_USD`）は **X 投稿数・Xコストのみ** を対象とし続ける。Threads は無料のためコスト計上しない（レート上限は250投稿/24hで、1日2投稿運用では到達しない）
  - LINE返信に Threads の成否を含める（FR-03）

### FR-05: 設定・ドキュメント
- 概要: セットアップが README だけで完結する。
- 詳細仕様:
  - `.env.example` に追記: `THREADS_ENABLED=0` / `THREADS_ACCESS_TOKEN=` / `THREADS_USER_ID=`（取得手順のコメント付き: Meta for Developers でアプリ作成 → Threads ユースケース追加 → 自アカウント連携 → 長期トークン発行）
  - `scripts/sns_autopost/README.md` に Threads セットアップ節を追加
  - Docker/Caddy の変更は不要である旨を確認して明記（画像配信・webhookは既存のまま）

## 6. 非機能要件

- 性能: Threads投稿の追加による承認→LINE返信の遅延は+35秒以内（コンテナ処理待ち込み）。LINEのreplyToken有効期限内に返信する
- 可用性: Threads APIの障害・認証切れが X 投稿・承認フロー本体を止めない（分離失敗設計）
- セキュリティ: トークンは `.env` と `SNS_DATA_DIR` 内のみ。Gitに入れない。ログにトークンを出力しない
- 保守性: 投稿先クライアントは `post_to_x()` と同形のインターフェースで実装し、将来の配信先追加時に同じ形を踏襲できるようにする
- UX（運用者）: 承認操作は現行と完全に同一（ボタンが増えない・回数が増えない）

## 7. 受け入れ基準

- AC-01: `THREADS_ENABLED=0`（既定）では現行と完全に同一の動作をする（Threads APIを一切呼ばない）
- AC-02: `THREADS_ENABLED=1` + キー設定済みで LINE 承認すると、X と Threads の両方に本投稿＋リプ本体が投稿され、LINE返信に両方の結果が表示される
- AC-03: 画像付き投稿で、Threads の本投稿に画像が添付される（`SNS_PUBLIC_BASE_URL` 設定時）
- AC-04: Threads のキーが未設定/無効でも X 投稿は成功し、`posts_log.jsonl` に `threads_id=""`、LINE返信に Threads 失敗が明記される
- AC-05: `threads_token.json` の `refreshed_at` が45日超のとき、投稿前にトークンがリフレッシュされ、ファイルが更新される
- AC-06: 500字を超える本文を渡した場合、Threads側は500字以内に切り詰められて投稿される（X側は従来どおり）
- AC-07: DRY_RUN=1 では Threads にも一切投稿されない
- AC-08: 既存テスト（`scripts/sns_autopost/tests/`）が全て通る

## 8. 前提・制約

- Threads アカウント（Instagramアカウント連携）を保有し、Meta開発者アプリで自アカウント連携ができること（自アカウント投稿のみならアプリ審査不要）
- 画像添付には `SNS_PUBLIC_BASE_URL` の公開ドメインが必要（本番は設定済み。未設定環境ではテキストのみ投稿にフォールバック）
- Threads API 制約: 500字/投稿、画像は公開URL渡し、投稿250件/24h、長期トークン約60日（リフレッシュ可）

## 9. 未決事項 / 要確認

- Threads用の文面最適化（トピックタグ活用・Threads文化に合わせたトーン）は計測データが貯まってから判断（対象外に明記済み）
- Threadsインサイト計測の追加時期（`threads_id` は記録するため後から遡って取得可能）
