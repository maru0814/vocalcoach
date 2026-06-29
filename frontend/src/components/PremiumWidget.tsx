"use client";

import { useEffect, useState } from "react";
import { BillingMe, getBillingMe } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

/**
 * プレミアム導線ウィジェット（ヘッダー右側に置く想定）。
 * - 無料ユーザー: 残り回数バッジ ＋「プレミアム ¥500/月」ボタン
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
    return <span className="text-xs font-semibold text-green-600">✓ プレミアム</span>;
  }

  const remaining =
    me.analysis_limit != null ? Math.max(0, me.analysis_limit - me.analysis_used) : null;

  const badgeClass =
    remaining === 0
      ? "text-xs font-semibold text-red-600"
      : remaining != null && remaining <= 3
      ? "text-xs font-semibold text-amber-600"
      : "text-xs text-gray-500";

  const badgeLabel =
    remaining === null
      ? null
      : remaining === 0
      ? "今月 上限"
      : `今月 残り${remaining}回${remaining <= 3 ? " ⚠" : ""}`;

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
          className="rounded-full bg-brand-gradient px-4 py-1.5 text-sm font-bold text-white shadow-soft transition hover:opacity-95 active:scale-95"
          onClick={() => setShowUpgrade(true)}
          aria-label="プレミアムプランにアップグレード（月額500円）"
        >
          プレミアム <span className="opacity-90">¥500/月</span>
        </button>
      </div>

      {showUpgrade && (
        <UpgradeModal source="limit" onClose={() => setShowUpgrade(false)} />
      )}
    </>
  );
}
