"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getBillingMe } from "@/lib/api";

export default function BillingSuccessPage() {
  const [ready, setReady] = useState(false);

  // webhook反映を最大60秒ポーリング（docs/32 S-07）
  useEffect(() => {
    let elapsed = 0;
    const timer = setInterval(async () => {
      elapsed += 3;
      try {
        const me = await getBillingMe();
        if (me.plan === "premium") {
          setReady(true);
          clearInterval(timer);
        }
      } catch {
        /* 一時的な失敗は無視して継続 */
      }
      if (elapsed >= 60) clearInterval(timer);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="space-y-4 rounded bg-white p-6 shadow">
      {ready ? (
        <>
          <h1 className="text-xl font-bold">ようこそプレミアムへ 🎉</h1>
          <p className="text-sm text-gray-700">
            これから録音解析が無制限になり、詳細添削レポートも使えます。
          </p>
          <div className="flex gap-3">
            <Link className="rounded bg-blue-600 px-4 py-2 text-sm text-white" href="/recordings">
              録音一覧へ
            </Link>
            <Link className="rounded border px-4 py-2 text-sm" href="/coach">
              ホームへ
            </Link>
          </div>
        </>
      ) : (
        <>
          <h1 className="text-xl font-bold">お支払いを確認しています…</h1>
          <p className="text-sm text-gray-700">
            反映まで少しかかることがあります（最大1分ほど）。このままお待ちください。
          </p>
          <div className="h-4 w-2/3 animate-pulse rounded bg-gray-200" />
        </>
      )}
    </div>
  );
}
