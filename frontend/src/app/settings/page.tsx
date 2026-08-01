"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BillingMe,
  getBillingMe,
  getMe,
  openPortal,
  setNewsletterOptIn as apiSetNewsletterOptIn,
  startCheckout,
} from "@/lib/api";
import { PREMIUM_PRICE_LABEL } from "@/lib/pricing";
import { redirectToLoginIfAuthError } from "@/lib/authRedirect";
import NotificationToggle from "@/components/pwa/NotificationToggle";
import { isNativeApp } from "@/lib/appMode";

export default function SettingsPage() {
  const router = useRouter();
  const [me, setMe] = useState<BillingMe | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  // お知らせメール同意（docs/88 FR-03）。null=読み込み中
  const [newsletter, setNewsletter] = useState<boolean | null>(null);
  const [newsletterBusy, setNewsletterBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setMe(await getBillingMe());
        setNewsletter((await getMe()).newsletter_opt_in);
      } catch (err) {
        if (redirectToLoginIfAuthError(err, router)) return;
        setError(err instanceof Error ? err.message : "取得に失敗しました");
      }
    })();
  }, [router]);

  const toggleNewsletter = async () => {
    if (newsletter === null) return;
    setNewsletterBusy(true);
    try {
      const { opt_in } = await apiSetNewsletterOptIn(!newsletter);
      setNewsletter(opt_in);
    } catch {
      setError("お知らせメール設定を変更できませんでした。時間をおいてお試しください。");
    } finally {
      setNewsletterBusy(false);
    }
  };

  const goCheckout = async () => {
    setBusy(true);
    try {
      const { url } = await startCheckout();
      window.location.href = url;
    } catch {
      setError("お申し込みページを開けませんでした。時間をおいてお試しください。");
      setBusy(false);
    }
  };

  const goPortal = async () => {
    setBusy(true);
    try {
      const { url } = await openPortal();
      window.location.href = url;
    } catch {
      setError("お支払い管理ページを開けませんでした。");
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">設定</h1>
        <Link className="text-blue-700 underline" href="/coach">
          ホームへ
        </Link>
      </div>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <section className="space-y-3 rounded bg-white p-5 shadow">
        <h2 className="font-semibold">プラン管理</h2>
        {!me ? (
          <p className="text-sm text-gray-500">読み込み中…</p>
        ) : me.plan === "premium" ? (
          <>
            <p className="text-sm text-gray-700">
              現在のプラン: <span className="font-medium">プレミアム</span>
              {me.period_end
                ? `（次回更新: ${new Date(me.period_end).toLocaleDateString("ja-JP")}）`
                : null}
            </p>
            <button
              className="rounded border px-4 py-2 text-sm disabled:opacity-50"
              onClick={goPortal}
              disabled={busy}
            >
              お支払い・解約の管理
            </button>
          </>
        ) : isNativeApp() ? (
          // アプリ内では購入導線を出さない（docs/78 FR-05）
          <p className="text-sm text-gray-700">現在のプラン: 無料プラン</p>
        ) : (
          <>
            <p className="text-sm text-gray-700">現在のプラン: 無料プラン</p>
            <p className="text-xs text-gray-500">
              プレミアム {PREMIUM_PRICE_LABEL} で録音解析が無制限・詳細添削レポートが使えます（いつでも解約OK）。
            </p>
            <button
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
              onClick={goCheckout}
              disabled={busy || !me.billing_enabled}
            >
              プレミアムをはじめる
            </button>
            {!me.billing_enabled ? (
              <p className="text-xs text-gray-400">（現在この環境では申し込みを受け付けていません）</p>
            ) : null}
          </>
        )}
      </section>

      <NotificationToggle />

      <section className="space-y-3 rounded bg-white p-5 shadow">
        <h2 className="font-semibold">お知らせメール</h2>
        <p className="text-sm text-gray-700">
          新機能やアップデートのお知らせをメールで受け取ります（いつでも停止できます）。
        </p>
        {newsletter === null ? (
          <p className="text-sm text-gray-500">読み込み中…</p>
        ) : (
          <button
            className={`rounded px-4 py-2 text-sm disabled:opacity-50 ${
              newsletter ? "border" : "bg-blue-600 text-white"
            }`}
            onClick={toggleNewsletter}
            disabled={newsletterBusy}
          >
            {newsletter ? "受け取りをやめる（現在: ON）" : "受け取る（現在: OFF）"}
          </button>
        )}
      </section>
    </div>
  );
}
