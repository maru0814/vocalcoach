"use client";

import { useEffect } from "react";
import { logPaywallEvent, PaywallSource, startCheckout } from "@/lib/api";
import { PREMIUM_PRICE_YEN } from "@/lib/pricing";
import { Button } from "@/components/ui/Button";

type Props = {
  source: PaywallSource;
  onClose: () => void;
};

const HEADINGS: Record<PaywallSource, string> = {
  limit: "もっと練習したいあなたへ",
  report: "録音をもっと深く知りたいあなたへ",
  history: "過去の録音も見返したいあなたへ",
};

const FEATURES: { label: string; free: string; premium: string }[] = [
  { label: "録音解析", free: "月10回", premium: "無制限" },
  { label: "詳細添削レポート", free: "—", premium: "◯" },
  { label: "原曲アップロード比較", free: "◯", premium: "◯" },
  { label: "履歴保存", free: "直近10件", premium: "無制限" },
];

export default function UpgradeModal({ source, onClose }: Props) {
  useEffect(() => {
    logPaywallEvent("paywall_view", source);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [source, onClose]);

  const onUpgrade = async () => {
    logPaywallEvent("paywall_click", source);
    try {
      logPaywallEvent("checkout_start", source);
      const { url } = await startCheckout();
      window.location.href = url;
    } catch {
      // 鍵未設定など。閉じてフォールバック（設定画面から再試行可）。
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold">{HEADINGS[source]}</h2>

        <table className="font-body w-full text-sm">
          <thead>
            <tr className="border-b text-left text-slate-500">
              <th className="py-1 font-normal"> </th>
              <th className="py-1 font-normal">無料</th>
              <th className="py-1 font-medium text-brand-700">プレミアム</th>
            </tr>
          </thead>
          <tbody>
            {FEATURES.map((f) => (
              <tr key={f.label} className="border-b last:border-0">
                <td className="py-1.5">{f.label}</td>
                <td className="py-1.5 text-slate-500">{f.free}</td>
                <td className="py-1.5 font-medium text-brand-700">{f.premium}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p className="text-center text-sm">
          <span className="text-xl font-bold">{PREMIUM_PRICE_YEN}</span>
          <span className="text-slate-500"> / 月</span>
          <span className="ml-2 text-xs text-slate-500">（いつでも解約OK）</span>
        </p>

        <div className="flex flex-col gap-2">
          <Button onClick={onUpgrade} className="w-full">
            プレミアムをはじめる
          </Button>
          <Button variant="ghost" onClick={onClose} className="w-full text-slate-500">
            今はやめておく
          </Button>
        </div>
      </div>
    </div>
  );
}
