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
- 💴 **月2000円以内の方針**: ①**本文/リプにURLを入れない**（$0.20回避＆reach優先。リンクはプロフィール固定で誘導＝`POST_LINK=0` 既定）②1日2投稿（`MAX_POSTS_PER_DAY=2`）③`MONTHLY_COST_CAP_USD` で上限ガード。これでAPIは月¥450前後（投稿60件＋計測）。
- 🚀 **X Premium（Web版が安い）** に入るとインプレ約6倍。これが最大の費用対効果（docs/29）。
- ⚠️ Instagram/TikTok の完全自動投稿は制限が厳しく非推奨（半自動）。

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

## 投稿前にLINEで承認するフロー（既定）

```
generate_and_post.py（cron）
   └─ 生成 → pending_queue.jsonl に保存 → LINEに本文＋[承認][却下]ボタンをpush
                                                   │
LINEであなたが [✅承認して投稿] を押す ──────────────┘
   └─ webhook.py が postback を受信（署名検証）→ 予算ガード → X に投稿 → LINEに結果返信
      [🗑却下] を押すと破棄（投稿しない）
```

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
