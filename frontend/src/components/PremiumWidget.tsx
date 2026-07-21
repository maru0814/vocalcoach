"use client";

import { useEffect, useState } from "react";
import { BillingMe, getBillingMe } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";
import { PREMIUM_PRICE_JPY, PREMIUM_PRICE_LABEL } from "@/lib/pricing";
import { isNativeApp } from "@/lib/appMode";

/**
 * プレミアム導線ウィジェット（ヘッダー右側に置く想定）。
 * - 無料ユーザー: 残り回数バッジ ＋「プレミアム {PREMIUM_PRICE_LABEL}」ボタン
 * - プレミアム: 「✓ プレミアム」バッジのみ
 * - billing無効 / 取得失敗: 何も出さない（ちらつき・誤表示を防ぐ）
 */
export function PremiumWidget() {
  const [me, setMe] = useState<BillingMe | null>(null);
  const [showUpgrade, setShowUpgrade] = useState(false);

  useEffect(() => {
    getBillingMe().then(setMe).catch(() => {});
  }, []);

  if (!me || !me.billing_enabled) return null;

  if (me.plan === "premium") {
    return <span className="text-xs font-semibold text-emerald-600">✓ プレミアム</span>;
  }

  const remaining =
    me.analysis_limit != null ? Math.max(0, me.analysis_limit - me.analysis_used) : null;

  const badgeClass =
    remaining === 0
      ? "text-xs font-semibold text-rose-600"
      : remaining != null && remaining <= 3
      ? "text-xs font-semibold text-rose-600"
      : "text-xs text-slate-500";

  const badgeLabel =
    remaining === null
      ? null
      : remaining === 0
      ? "今月 上限"
      : `今月 残り${remaining}回${remaining <= 3 ? "（残りわずか）" : ""}`;

  // アプリ内では購入導線を出さない（docs/78 FR-05）。残回数バッジのみ表示。
  if (isNativeApp()) {
    return badgeLabel ? (
      <span className={badgeClass} aria-label={`今月の残り解析回数: ${remaining}回`}>
        {badgeLabel}
      </span>
    ) : null;
  }

  return (
    <>
      <div className="flex items-center gap-3">
        {badgeLabel && (
          <button
            className={badgeClass}
            aria-label={`今月の残り解析回数: ${remaining}回`}
            onClick={() => setShowUpgrade(true)}
          >
            {badgeLabel}
          </button>
        )}
        <button
          className="rounded-full bg-brand-600 px-4 py-1.5 text-sm font-bold text-white shadow-[0_3px_0_#5b21b6] transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 active:translate-y-[2px] active:shadow-[0_1px_0_#5b21b6]"
          onClick={() => setShowUpgrade(true)}
          aria-label={`プレミアムプランにアップグレード（月額${PREMIUM_PRICE_JPY}円）`}
        >
          プレミアム <span className="opacity-90">{PREMIUM_PRICE_LABEL}</span>
        </button>
      </div>

      {showUpgrade && (
        <UpgradeModal source="limit" onClose={() => setShowUpgrade(false)} />
      )}
    </>
  );
}
