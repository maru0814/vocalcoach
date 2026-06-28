"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BrandWordmark } from "@/components/brand/Brand";
import { BillingMe, getBillingMe } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

export function AppHeader() {
  const [me, setMe] = useState<BillingMe | null>(null);
  const [showUpgrade, setShowUpgrade] = useState(false);

  useEffect(() => {
    getBillingMe().then(setMe).catch(() => {});
  }, []);

  const isPremium = me?.plan === "premium";
  const billingEnabled = me?.billing_enabled ?? false;

  const remaining =
    me && me.analysis_limit != null
      ? Math.max(0, me.analysis_limit - me.analysis_used)
      : null;

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
      <header className="sticky top-0 z-40 border-b bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-3">
          <Link href="/recordings">
            <BrandWordmark size={36} />
          </Link>

          <div className="flex items-center gap-3">
            {isPremium ? (
              <span className="text-xs font-semibold text-green-600">✓ プレミアム</span>
            ) : billingEnabled ? (
              <>
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
                  className="hidden rounded-full bg-brand-gradient px-4 py-1.5 text-sm font-bold text-white shadow-soft transition hover:opacity-95 active:scale-95 sm:block"
                  onClick={() => setShowUpgrade(true)}
                  aria-label="プレミアムプランにアップグレード（月額500円）"
                >
                  プレミアムにする ¥500/月
                </button>
                <button
                  className="rounded-full bg-brand-gradient px-3 py-1.5 text-sm font-bold text-white shadow-soft transition hover:opacity-95 active:scale-95 sm:hidden"
                  onClick={() => setShowUpgrade(true)}
                  aria-label="プレミアムプランにアップグレード（月額500円）"
                >
                  ¥500/月
                </button>
              </>
            ) : null}
          </div>
        </div>
      </header>

      {showUpgrade && (
        <UpgradeModal source="limit" onClose={() => setShowUpgrade(false)} />
      )}
    </>
  );
}
