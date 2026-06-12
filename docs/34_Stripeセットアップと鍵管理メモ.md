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

## 5. 関連

- 要件: [docs/31](31_機能要件書_有料プラン_サブスク.md) / デザイン: [docs/32](32_デザイン仕様_有料プラン.md) / 設計: [docs/33](33_設計書_有料プラン_サブスク.md)
- 実装PR: PR-A（DB＋上限ゲート・済）/ PR-C（詳細レポート・済）/ PR-B（決済・これから）/ PR-D（導線UI＋公開・これから）
