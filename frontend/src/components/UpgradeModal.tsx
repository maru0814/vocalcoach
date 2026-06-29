"use client";

import { useEffect } from "react";
import { logPaywallEvent, PaywallSource, startCheckout } from "@/lib/api";

type Props = {
  source: PaywallSource;
  onClose: () => void;
};

const HEADINGS: Record<PaywallSource, string> = {
  limit: "もっと練習したいあなたへ 🎤",
  report: "録音をもっと深く知りたいあなたへ 🎧",
  history: "過去の録音も見返したいあなたへ 📚",
};

const FEATURES: { label: string; free: string; premium: string }[] = [
  { label: "録音解析", free: "月10回", premium: "無制限" },
  { label: "詳細添削レポート", free: "—", premium: "◯" },
  { label: "原曲アップロード比較", free: "体験1回", premium: "◯" },
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
        className="w-full max-w-md space-y-4 rounded-lg bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold">{HEADINGS[source]}</h2>

        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="py-1 font-normal"> </th>
              <th className="py-1 font-normal">無料</th>
              <th className="py-1 font-medium text-blue-700">プレミアム</th>
            </tr>
          </thead>
          <tbody>
            {FEATURES.map((f) => (
              <tr key={f.label} className="border-b last:border-0">
                <td className="py-1.5">{f.label}</td>
                <td className="py-1.5 text-gray-500">{f.free}</td>
                <td className="py-1.5 font-medium text-blue-700">{f.premium}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p className="text-center text-sm">
          <span className="text-xl font-bold">¥800</span>
          <span className="text-gray-500"> / 月</span>
          <span className="ml-2 text-xs text-gray-500">（いつでも解約OK）</span>
        </p>

        <div className="flex flex-col gap-2">
          <button
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white"
            onClick={onUpgrade}
          >
            プレミアムをはじめる
          </button>
          <button className="rounded px-4 py-2 text-sm text-gray-500" onClick={onClose}>
            今はやめておく
          </button>
        </div>
      </div>
    </div>
  );
}
