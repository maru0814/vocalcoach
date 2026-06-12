# Stripe セットアップ＆鍵管理メモ

> 将来の自分用。有料プラン（プレミアム ¥500/月）の決済まわり。docs/31〜33・PR-A/Cの続き（PR-B）で使う。
> ⚠️ 鍵の実値はこのファイルにもチャットにも書かない。実値は `backend/.env`（gitignore済み）だけに置く。

## 1. `.env` に入れる鍵（backend/.env）

| env名 | 形式 | 取得元 | 用途 |
| --- | --- | --- | --- |
| `STRIPE_SECRET_KEY` | `sk_test_...` / `sk_live_...` | 開発者 → APIキー | サーバからStripe APIを叩く |
| `STRIPE_PRICE_ID_PREMIUM` | `price_...` | 商品 → ¥500/月の価格 | サブスク作成時のプラン指定 |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | `stripe listen`（ローカル）/ ダッシュボードのWebhook設定（本番） | webhook署名検証 |

- これらは `app/core/config.py` の `stripe_secret_key` / `stripe_price_id_premium` / `stripe_webhook_secret` に対応（PR-Aで枠だけ用意済み）。
- ゲートの有効化は別スイッチ `BILLING_ENABLED=1`（既定0）。鍵を入れても0の間は課金UIは出ない。

## 2. テスト ⇄ 本番の対応

| | テスト | 本番 |
| --- | --- | --- |
| ダッシュボード | 右上「テスト環境」ON | OFFに切替（要 本人確認・銀行口座審査） |
| シークレットキー | `sk_test_...` | `sk_live_...` |
| Price ID | テストモードで作った `price_...` | **本番モードで作り直した別の** `price_...` |
| カード | `4242 4242 4242 4242`（任意の未来日/CVC） | 実カード |
| Webhook secret | `stripe listen` が表示する `whsec_...` | ダッシュボードでendpoint登録時に発行される `whsec_...` |

> 注意: **テストと本番でキーもPrice IDもWebhook secretも別物**。本番切替時は3つとも差し替える。

## 3. ローカル開発でwebhookを受ける手順

```bash
# Stripe CLI（未導入なら）
brew install stripe/stripe-cli/stripe
stripe login                       # ブラウザで承認

# ローカルのFastAPIへwebhookを転送（起動しっぱなしにする）
stripe listen --forward-to localhost:8000/api/v1/billing/webhook
# → 表示される whsec_... を backend/.env の STRIPE_WEBHOOK_SECRET に入れる

# 別ターミナルでイベントを手動発火して確認
stripe trigger checkout.session.completed
```

テストカード: `4242 4242 4242 4242` / 有効期限=未来の任意 / CVC=任意3桁。

## 4. 本番リリース時のチェックリスト

- [ ] 本番モードでビジネス情報・本人確認・銀行口座を登録し審査通過
- [ ] 本番モードで ¥500/月 の商品を**作り直す**（テストのPrice IDは本番で使えない）
- [ ] 本番の `sk_live_...` / `price_...` をサーバ（VPS）の `.env` に設定
- [ ] 本番Webhook endpoint を登録（URL: `https://sora-vocal-ai.duckdns.org/api/v1/billing/webhook`）→ 発行された `whsec_...` を設定
- [ ] 購読イベント: `checkout.session.completed` / `customer.subscription.updated` / `customer.subscription.deleted` / `invoice.payment_failed`
- [ ] 特定商取引法に基づく表記ページを公開（販売者・価格・**解約方法**・提供時期。サブスクは解約方法の明記が必須）
- [ ] `BILLING_ENABLED=1` に切替（= 課金UI・上限ゲートを有効化）
- [ ] 緊急時は `BILLING_ENABLED=0` に戻せば全機能無料に即ロールバック（コード変更不要）

## 5. 本番セットアップ手順（ダッシュボード操作）

> 本番モードでの作業。所要30〜60分＋審査（最短即日〜数営業日）。
> ⚠️ テストモードのキー・Price ID・Webhookは本番では使えない。すべて本番モードで作り直す。

### 5.1 本番モードに切替
- [dashboard.stripe.com](https://dashboard.stripe.com) 右上トグルを「テスト環境」→**本番**に。

### 5.2 事業者情報・本人確認・銀行口座（審査）
「ビジネスを有効化」から順に入力:
- **事業形態**: 個人 / 個人事業主（Individual）
- **本人情報**: 氏名（丸山ゆう）・生年月日・住所・電話（Stripe登録用。特商法の「請求時開示」とは別）
- **本人確認書類**: 運転免許証（表裏）/ マイナンバーカード（表面のみ）/ パスポート のいずれか
- **事業内容**: 業種=ソフトウェア/SaaS or 教育。説明=「歌唱録音をAIが解析しFBを提供する月額サブスク」。URL=`https://sora-vocal-ai.duckdns.org`（特商法ページ公開済みだと審査が通りやすい）
- **銀行口座**: 名義（カナ）はStripe登録氏名と一致させる（屋号口座は弾かれやすい→個人名義が無難）
- 送信 → 審査。最短即日、書類確認が入ると数営業日。

### 5.3 本番の商品（¥500/月）を作成
- 商品カタログ → 商品 → 「+ 商品を追加」
- 名前=`ソラ先生 プレミアム`、料金=**500 JPY**、**継続（月次）**
- 発行された `price_...`（本番）を控える。

### 5.4 本番Webhookエンドポイント登録
- 開発者 → Webhook → 「+ エンドポイントを追加」
- URL: `https://sora-vocal-ai.duckdns.org/api/v1/billing/webhook`
- イベント: `checkout.session.completed` / `customer.subscription.created` / `customer.subscription.updated` / `customer.subscription.deleted`（任意で `invoice.payment_failed`）
- 作成後の「署名シークレット」`whsec_...`（本番）を控える。

### 5.5 VPSに反映して公開
- VPSの `.env` に `STRIPE_SECRET_KEY=sk_live_...` / `STRIPE_PRICE_ID_PREMIUM=price_...`（本番）/ `STRIPE_WEBHOOK_SECRET=whsec_...`（本番）/ `FRONTEND_BASE_URL=https://sora-vocal-ai.duckdns.org` / `BILLING_ENABLED=1`
- `requirements.txt` に `stripe` 入り（PR-Bで追加済み）→ `pip install -r`
- `alembic upgrade head` → アプリ再起動。

### よくあるつまずき
- **キー取り違え**: 本番モードで `sk_live_`（`sk_test_` ではない）。モードトグルを再確認。
- **口座名義不一致**: Stripe登録氏名と銀行名義（カナ）を揃える。
- **審査保留**: サイトに料金・解約方法・特商法が無いと保留されやすい（→対応済み）。
- **審査前でも開発可**: キーは先に取れるのでVPS設定だけ先行できる（`BILLING_ENABLED=1`は審査通過後に）。

## 6. アカウントを作り直す場合（事業転換・審査落ち等）

**コード変更は不要**（Stripe識別子は全て `.env`。ハードコード無し）。やることは:

1. 新アカウントで **5.3 商品** と **5.4 Webhook** を作成。
2. `.env` の3鍵（`STRIPE_SECRET_KEY` / `STRIPE_PRICE_ID_PREMIUM` / `STRIPE_WEBHOOK_SECRET`）を新アカウントの値に差し替え。
3. **DBの旧IDを掃除**: `subscriptions` の `stripe_customer_id` / `stripe_subscription_id` は旧アカウントのもので新アカウントには存在しない。実課金ユーザーがいなければ全削除でよい:
   ```sql
   DELETE FROM subscriptions;
   ```
   （実課金者がいる移行では、顧客の作り直し・案内が必要。本番公開前なら不要）
4. アプリ再起動。

> 審査落ち対策（事業情報の更新）は Stripeダッシュボード側の作業で、コード/DBとは独立。

## 7. 関連

- 要件: [docs/31](31_機能要件書_有料プラン_サブスク.md) / デザイン: [docs/32](32_デザイン仕様_有料プラン.md) / 設計: [docs/33](33_設計書_有料プラン_サブスク.md)
- 特商法ページ: `frontend/src/app/legal/tokushoho/page.tsx`（`SELLER` に実値設定済み）
- 実装PR: PR-A #74（DB＋上限ゲート）/ PR-C #75（詳細レポート）/ PR-B #77（決済・ライブ確認済）/ PR-D #79（導線UI＋計測） いずれも済
