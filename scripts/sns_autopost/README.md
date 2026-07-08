# ソラ先生 SNS投稿（X / 旧Twitter）

1日2回（昼・夜）Xに投稿する最小ツール。**Geminiが無くてもテンプレで動く**／**キーが無ければ本文表示だけ（安全）**。

> **投稿前にLINEで承認するフロー（既定）**: 自動では投稿せず、生成した下書きを
> **LINEに送って [✅承認して投稿] / [🗑却下] のボタンで確認**してから投稿します。
> 承認したものだけがXに流れます（`APPROVAL_MODE=1`、後述）。即時自動投稿に戻すなら
> `APPROVAL_MODE=0`。

## できること / 料金（正直に。詳細 docs/29）
- ✅ **Xへの自動投稿**（従量課金）。**2026年の単価: URLなし投稿 $0.015／URLあり投稿 $0.20／自分の投稿の読取 $0.001**。月額下限なし。
- ✅ **インプレ計測**: `fetch_metrics.py` が投稿のインプレ/エンゲージを取得→型別に集計→**勝ち型に寄せる**。
- ✅ 文面の自動生成（Gemini。無くてもテンプレ）。
- ✅ **ブランド画像を全投稿に自動添付**。日本語は全てコード描画＝崩れ・誤字なし。`SNS_IMAGE=0` で無効。
  - **tip / contrarian → 図解インフォグラフィック**（16:9）。`themes.py` の手順を自動構造化し `templates/infographic.html` をPlaywrightでPNG化。ソラ先生キャラ（`assets/characters/sora/`）を合成。Playwright未導入/失敗時はカードに自動フォールバック。
  - **診断導線（self_type/voice_type/visual）→ カード**（縦4:5）。背景はGemini(Imagen 4)→失敗/キー無しでPillowグラデにフォールバック（`SNS_IMAGE_AI=0` でグラデ固定）。Imagen単価 約$0.04/枚。
  - 設計: `docs/46_デザイン仕様_X投稿インフォグラフィック.md`
- 💴 **月2000円以内の方針**: ①**本文/リプにURLを入れない**（$0.20回避＆reach優先。リンクはプロフィール固定で誘導＝`POST_LINK=0` 既定）②1日2投稿（`MAX_POSTS_PER_DAY=2`）③`MONTHLY_COST_CAP_USD` で上限ガード。これでAPIは月¥450前後（投稿60件＋計測）。
- 🚀 **X Premium（Web版が安い）** に入るとインプレ約6倍。これが最大の費用対効果（docs/29）。
- ✅ **Threadsへの同時投稿（任意・無料）**: `THREADS_ENABLED=1` で承認1回でX+Threads両方に投稿（後述）。
- ⚠️ Instagram/TikTok の完全自動投稿は制限が厳しく非推奨（半自動）。

## セットアップ（5分）
```bash
cd scripts/sns_autopost
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # 値を入れる（.env はGitに入らない）
```
> 画像の日本語見出し用に**CJKフォント**が要る。mac は自動検出（ヒラギノ丸ゴ）、Docker は Noto CJK 同梱済み。
> その他の環境は `.env` の `SNS_FONT_PATH` でフォントを指定する（未設定だとカード画像は文字なしで出る）。

> **図解(tip/contrarian)はPlaywright必須**: ローカルは `python -m playwright install chromium` を実行（Dockerはビルド時に導入済み）。未導入でもカードに自動フォールバックして投稿は止まらない。
> 図解の丸ゴシックはオンライン時 Google Fonts を使う。オフライン運用は Zen Maru Gothic の TTF を `assets/fonts/` に置けばローカル`@font-face`に自動切替。

### Xのキー発行
1. https://developer.x.com で開発者登録 → アプリ作成
2. アプリの **User authentication settings** で権限を **Read and write** に
3. **API Key/Secret**（Consumer）と **Access Token/Secret** を発行し `.env` に貼る

### Threads にも同時投稿する（任意・無料。docs/63/64）
`THREADS_ENABLED=1` にすると、**LINEの承認1回で X と Threads の両方**に投稿する
（承認操作は増えない）。Threads の投稿APIは**無料**で、失敗しても X 投稿は止まらない
（LINE返信に ⚠ で明記）。既定は `0`＝完全に従来どおり。
1. https://developers.facebook.com/ でアプリ作成 → ユースケース **Threads API** を追加
2. 自分のThreadsアカウントをテスターとして連携（Threadsアプリ側で承認。自分に投稿するだけなら審査不要）
3. **長期アクセストークン**（約60日）と **ThreadsユーザーID** を `.env` に貼る
   （トークンは45日経過で投稿時に自動リフレッシュ → `{SNS_DATA_DIR}/threads_token.json` に保存。手動再発行は不要）
- 画像添付には `SNS_PUBLIC_BASE_URL` が必要（ThreadsのAPIは公開URL渡しのため。LINEプレビューと同じ `GET /sns/img/` を使う）。未設定ならテキストのみ投稿
- Threads の本文上限は500字（超過分は自動で「…」切り詰め）。予算ガードは従来どおりX費用のみを数える
- Docker / Caddy / cron の変更は不要。`.env` 編集＋コンテナ再起動だけで有効化・無効化できる

## 専門家ゲート（出稿前レビュー / skill: sns-strategist）
生成した投稿（本文＋自己リプ＋画像）は、**世界水準SNSマーケの採点ゲート**（`expert_review.py`）を
通してから承認に進む。採点は**項目別**（フック停止力・アルゴリズム適合・画像停止力 等）で行い、
合計はコード側で算出する（モデルが中間点に丸めるのを防ぐ）。
- **受かるまで再提出**: 基準（既定80点）未満なら専門家が改善版を作って再採点…を**合格するまで繰り返す**。
  暴走防止に安全上限 `EXPERT_REVIEW_MAX_ATTEMPTS`(既定6) と“スコア頭打ち”検出あり。
- **上限まで改善しても未達なら、その中の“いちばん良かった版”をLINEに送る**（⚠️未達と最高点・残る改善点を明示。
  人間が最終判断）。※ただし本文/リプにURLが残る版だけは方針違反のため送らず保留（`status=held`）。
- 通過した投稿のLINEには判定（例「✅ 合格 84/80点（3回目で通過）」＋項目別内訳）、
  未達送付なら「⚠️ 未達 最高75/80点」が先頭に表示される。
- 採点基準のSSOTは `.claude/skills/sns-strategist/SKILL.md`。
- 環境変数: `SNS_REVIEW_MODEL`(既定 gemini-2.5-flash／flash-liteは採点が雑なので非推奨。503時はpro等へ自動フォールバック)、
  `EXPERT_REVIEW_MIN_SCORE`(既定80)、`EXPERT_REVIEW_MAX_ATTEMPTS`(既定6)、`SNS_IMAGE_DIR`(審査画像の場所)。
- `GEMINI_API_KEY` 未設定や一時エラー時は「未レビュー」と明示してfail-open（運用を止めない）。
- 本文/リプにURLがあれば即失格（ハード失格）。

## 投稿前にLINEで承認するフロー（既定）

```
generate_and_post.py（cron）
   └─ 生成 → pending_queue.jsonl に保存 → LINEに【画像プレビュー＋本文】＋[承認][却下]ボタンをpush
                                                   │
LINEであなたが [✅承認して投稿] を押す ──────────────┘
   └─ webhook.py が postback を受信（署名検証）→ 予算ガード → X に投稿 → LINEに結果返信
      [🗑却下] を押すと破棄（投稿しない）
```

> **承認時に投稿画像も表示**: `.env` の `SNS_PUBLIC_BASE_URL`（例 `https://sora-vocal-ai.duckdns.org`）を設定すると、LINEの承認メッセージ先頭に生成画像のプレビューが出る。webhookの `GET /sns/img/{name}` が画像を配信する（Caddyで `/sns/*` を webhook へ通している前提）。LINEのimageメッセージは公開HTTPS URLが必須のため。未設定ならテキストの添付注記のみ（動作は止まらない）。

- **生成（cron）**と**Webhook常駐（webhook.py）**の2プロセス構成。
- 投稿は承認時に初めて実行され、`posts_log.jsonl` に記録される（計測はそのまま動く）。
- 予算ガード（`MAX_POSTS_PER_DAY` / `MONTHLY_COST_CAP_USD`）は**承認＝投稿の瞬間**に効く。

### LINE側のセットアップ（初回のみ）
1. https://developers.line.biz/ で **Messaging API チャネル**を作成
2. **チャネルアクセストークン（長期）** と **チャネルシークレット** を `.env` に貼る
   （`LINE_CHANNEL_ACCESS_TOKEN` / `LINE_CHANNEL_SECRET`）
3. **Webhook URL** に `https://<DOMAIN>/sns/line/webhook` を設定し「Webhookの利用」をON
   （本番はCaddyが `/sns/*` を webhook.py に流す。後述）
4. その公式アカウントを**自分のLINEで友だち追加** → 返信で届く `userId` を
   `.env` の `LINE_OPERATOR_USER_ID` に設定（`webhook.py` が follow 時に教える）
5. 応答メッセージ等のデフォルト自動応答はOFFにしておくと邪魔にならない

### Webhookサーバの起動
```bash
# ローカル/手動
uvicorn webhook:app --host 0.0.0.0 --port 8088
# 動作確認
curl -s http://localhost:8088/sns/healthz   # {"status":"ok","line":true}
```

## 使い方
```bash
# まずは安全確認（生成して本文だけ表示。キューにもLINEにも送らない。DRY_RUN=1 が既定）
python generate_and_post.py

# 型を指定して確認
python generate_and_post.py --pillar tip         # 実践Tips（2部構成: フック→手順はリプ）
python generate_and_post.py --pillar contrarian  # 逆張り（2部構成: 誤解→根拠はリプ）
python generate_and_post.py --pillar self_type   # 自己分類フック（診断導線・単発）
python generate_and_post.py --pillar voice_type  # 声タイプ図鑑（診断導線・単発）
python generate_and_post.py --pillar visual      # ビジュアル誘導（診断導線・単発）

# 承認フローに乗せる（DRY_RUN=0。生成→キュー→LINE通知。投稿は承認後）
DRY_RUN=0 python generate_and_post.py

# 承認を挟まず即投稿（手動・緊急用。--force で日次上限も無視＝月間コスト上限は維持）
DRY_RUN=0 python generate_and_post.py --pillar tip --post-now --force
```

### 投稿は2部構成（リプに本体を置く）
`tip` / `contrarian` は **本投稿＝好奇心フックで寸止め／リプ（自己返信）＝手順・根拠の本体** の2部構成で投稿する。読者にリプを促す“リプ乞い”ではなく、**自分の自己返信に続きを置いて「リプを開きたくなる」導線**にする設計。診断導線型（self_type/voice_type/visual）は単発。
`generate_post()` が `{text, reply, link}` を返し、承認キュー（`enqueue`）→ LINEプレビュー（本投稿＋リプ本体を表示）→ `webhook.py` が承認時に **本投稿→リプ本体→(任意)URL** の順でスレッド投稿する。

> **本文にもリプにもURLを入れない**のが既定（`POST_LINK=0`）。リンクは**プロフィール固定**で誘導（reach減＆$0.20課金を回避）。リプ本体はURLなしの中身なので $0.015。

## インプレ計測（改善ループ）
```bash
python fetch_metrics.py            # 直近投稿のインプレ/エンゲージ取得＋型別サマリ
```
- 投稿IDは `posts_log.jsonl`、メトリクスは `metrics_log.jsonl` に記録（Git除外）。
- 出力の「平均imp / eng率」が高い型を `themes.py` の `PILLARS` で増やす。

## 自動化（VPSのcron。夜20–22時が最良）

cronは**生成して承認待ちに送るだけ**になる（投稿はLINE承認時）。Webhook常駐が必要。

```bash
# crontab -e（JST）
# 昼12時に1本目（slot1=情報/診断導線）→ 生成してLINEに承認依頼
0 12 * * * cd /opt/vocalcoach/scripts/sns_autopost && ./.venv/bin/python generate_and_post.py --slot 1 >> /var/log/sns_autopost.log 2>&1
# 夜21時に2本目（slot2=会話/リプ型。ゴールデンタイム）
0 21 * * * cd /opt/vocalcoach/scripts/sns_autopost && ./.venv/bin/python generate_and_post.py --slot 2 >> /var/log/sns_autopost.log 2>&1
# 毎日23時にインプレ計測（承認済み＝投稿済みの分を集計）
0 23 * * * cd /opt/vocalcoach/scripts/sns_autopost && ./.venv/bin/python fetch_metrics.py >> /var/log/sns_metrics.log 2>&1
```

### 本番（Docker Compose）
`docker/docker-compose.prod.yml` に **`sns` サービス（Webhook常駐）** を追加済み。
Caddyが `https://<DOMAIN>/sns/*` を `sns:8088` に流す。投稿の生成はこのコンテナ内で叩く
（承認キュー・投稿ログをコンテナの永続volume `sns_data`(/data) で共有するため）。

> **かんたんセットアップ**: `.env` を埋めたら以下を1回叩くだけ（起動＋疎通確認＋Webhook URL表示）。
> ```bash
> bash scripts/sns_autopost/setup_approval.sh          # 起動＋疎通確認
> # LINEコンソールでWebhook URL設定＆友だち追加 → userId を .env に入れたら:
> bash scripts/sns_autopost/setup_approval.sh --test --cron   # テスト送信＋cron登録
> ```

手動でやる場合は以下。
```bash
# .env を用意（scripts/sns_autopost/.env。LINE/X/Geminiキー等。compose が読み込む）
cd docker && docker compose -f docker-compose.prod.yml --env-file .env up -d --build sns caddy

# 生成cron（host側）はコンテナ内で実行する形にする
0 12 * * * cd /opt/vocalcoach/docker && docker compose -f docker-compose.prod.yml exec -T sns python generate_and_post.py --slot 1 >> /var/log/sns_autopost.log 2>&1
0 21 * * * cd /opt/vocalcoach/docker && docker compose -f docker-compose.prod.yml exec -T sns python generate_and_post.py --slot 2 >> /var/log/sns_autopost.log 2>&1
0 23 * * * cd /opt/vocalcoach/docker && docker compose -f docker-compose.prod.yml exec -T sns python fetch_metrics.py >> /var/log/sns_metrics.log 2>&1
```
- 昼枠(slot1)の型は `themes.py` の `PILLARS`（Tips中心＋診断導線・逆張り）。
- 夜枠(slot2)は `PILLARS_2ND`。同日の昼とは必ず別の型になる。
- 1日2投稿なので `.env` の `MAX_POSTS_PER_DAY=2` を忘れず設定する。

## 安全装置 / 予算ガード
- `APPROVAL_MODE` 既定=1（**投稿前に必ずLINEで人間が承認**。誤爆・炎上を防ぐ最重要ガード）。
- `DRY_RUN` 既定=1（生成のみ。キューにもLINEにも送らない）。承認フローを動かすには `DRY_RUN=0`。
- `POST_LINK=0`（URL投稿しない＝$0.20回避）／`MAX_POSTS_PER_DAY`／`MONTHLY_COST_CAP_USD` で**月額を物理的に制限**。
- `--force` は手動投稿用に**日次上限のみ**を無視する（cronの自動投稿には付けない）。`MONTHLY_COST_CAP_USD` の月間上限は `--force` でも常に有効＝本当の安全弁は維持。
- 本文にURLが混入した生成文はテンプレに自動差し替え。
- キーは `.env`（Git除外）。**チャットやコミットに貼らない**。

## 安全装置
- `DRY_RUN` 既定=1（うっかり投稿しない）。実運用で 0 にする。
- Geminiが盛った/URL欠落の文を返したらテンプレに自動差し替え。
- キーは `.env`（Git除外）。**チャットやコミットに貼らない**。

## Xフォロー候補（半自動。docs/58/59）

「歌の悩みを実況している人」を見つけて選別し、**フォローすべき人だけ**を毎日
LINEに一覧で届ける（返信文は生成しない＝2026-07-06方針転換）。
**フォローの実行は常にあなたの指**（write自動化は実装として存在しない＝バン安全性の不変条件）。

自動フォローを実装しない理由: Xの自動化ポリシーはフォロー/アンフォローの
「大量・機械的な実行」自体を禁止行為として明記しており、ボタン1つでAPIが
複数フォローする設計にしても規約上のリスクは消えない（人間が押したかどうかは関係ない）。
LINEの [✅全員フォローした] ボタンは「Xアプリで自分の指でフォローした」という
自己申告を記録するだけで、X APIへのfollow呼び出しはコードのどこにも存在しない。

```bash
python lead_finder.py --dry-run                 # まず安全に確認（既定DRY_RUN=1）
python lead_finder.py                           # メンション＋API検索（要Xキー）
python lead_finder.py --input leads_input.jsonl # Xアプリで見つけたURLを渡す（¥0）
python lead_metrics.py                          # クエリ別フォロバ率（週次）
```

- 候補ソースは安い順に ①ペースト入力(oEmbed・¥0) ②自投稿へのメンション(owned read≒$0.001)
  ③従量API検索(post read $0.005)。検索は**優先3テーマ**（歌全般の上達願望/ミックスボイス/
  カラオケ上達＝`leads.PRIORITY_QUERY_IDS`）を毎回必ず実行し、残り枠を他クエリで日替わりローテ。
- フォロワー数/bio は本文選別を**通過した候補だけ** user read($0.010)で取得（遅延lookup）。
- read課金は `LEAD_DAILY_READ_BUDGET_USD`(既定0.60)の日次予算ガード内。概算は
  `lead_reads_log.jsonl` に記録。
- 選別: 日本語/悩み文脈/相互狙い除外/対応済み除外/フォロワー30〜3000（`.env`で変更可）。
  「音痴」クエリは第三者・キャラクターの話題便乗を除外するため、本人の悩み語（直したい/
  苦手/下手 等）を必須にしている（2026-07-06追加絞り込み）。
- 1日の提示上限 `MAX_FOLLOWS_PER_DAY`(既定15)。**公式な「安全な人数」は存在しない**が、
  フォロー速度のスパイクを避ける経験則として、最初の1〜2週間は10〜15、様子を見て
  段階的に25程度まで。1日分を一気にタップせず時間を分けて行うことを推奨（docs/60参照）。
- LINEには相手のプロフィール要約・元ツイートの抜粋・プロフィールへのリンクが並ぶ。
  気になる人のリンクをタップ→Xアプリで自分の指でフォロー→最後に [✅全員フォローした] を
  1回押すと、フォロバ計測用に記録される（**Xへの書込みは発生しない**）。
- テスト: `python tests/qa_leads.py`（外部API/キー不要）。
