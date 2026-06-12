"use client";

import Link from "next/link";

export default function BillingCancelPage() {
  return (
    <div className="space-y-4 rounded bg-white p-6 shadow">
      <h1 className="text-xl font-bold">またいつでもどうぞ 🙆</h1>
      <p className="text-sm text-gray-700">
        お支払いはキャンセルされました。無料プランのままご利用いただけます。
      </p>
      <Link className="rounded bg-blue-600 px-4 py-2 text-sm text-white" href="/recordings">
        録音一覧へ戻る
      </Link>
    </div>
  );
}
