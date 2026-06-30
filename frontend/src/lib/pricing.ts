/**
 * プレミアムプランの価格 — フロントエンドの単一ソース。
 *
 * ⚠️ 金額の真実の源泉は Stripe 本番モードの Price 金額（env `STRIPE_PRICE_ID_PREMIUM` が指す Price）。
 *    UI 表示は必ずその実 Price 金額に一致させること。表記と実課金額がズレると重大インシデント。
 *    要件・正本ドキュメントは docs/31。価格を変えるときは
 *    「Stripe の Price → このファイル → docs/31」の順で揃える。
 */
export const PREMIUM_PRICE_JPY = 800;

const formatted = PREMIUM_PRICE_JPY.toLocaleString("ja-JP");

/** 金額のみ（例: 「¥800」）。UpgradeModal の大きい数字表示などに使う。 */
export const PREMIUM_PRICE_YEN = `¥${formatted}`;

/** ボタン・バッジ向けの短い表記（例: 「¥800/月」）。 */
export const PREMIUM_PRICE_LABEL = `${PREMIUM_PRICE_YEN}/月`;

/** 特商法ページなどの正式表記（例: 「月額 800円（消費税込）」）。 */
export const PREMIUM_PRICE_LEGAL = `月額 ${formatted}円（消費税込）`;
