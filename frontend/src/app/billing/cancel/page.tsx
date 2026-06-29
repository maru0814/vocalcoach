"use client";

import Link from "next/link";

export default function BillingCancelPage() {
  return (
    <div className="bg-studio flex min-h-[100dvh] items-center justify-center p-5">
      <div className="w-full max-w-md space-y-4 rounded-3xl bg-white/90 p-8 text-center shadow-card backdrop-blur">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 text-3xl">
          🙆
        </div>
        <h1 className="text-xl font-black text-slate-800">またいつでもどうぞ</h1>
        <p className="text-sm text-slate-600">
          お支払いはキャンセルされました。無料プランのままご利用いただけます。
        </p>
        <Link
          className="inline-block rounded-full bg-brand-gradient px-6 py-2.5 text-sm font-bold text-white shadow-soft transition hover:opacity-95 active:scale-95"
          href="/coach"
        >
          ホームへ戻る
        </Link>
      </div>
    </div>
  );
}
