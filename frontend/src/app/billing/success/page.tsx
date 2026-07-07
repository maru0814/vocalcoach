"use client";

import { useEffect, useState } from "react";
import { getBillingMe } from "@/lib/api";
import { CoachAvatar } from "@/components/character/Coach";
import { Button } from "@/components/ui/Button";

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
    <div className="bg-studio flex min-h-[100dvh] items-center justify-center p-5">
      <div className="w-full max-w-md space-y-4 rounded-2xl bg-white/90 p-8 text-center shadow-card backdrop-blur">
        {ready ? (
          <>
            {/* 成功＝よろこびのポーズ（docs/61 §3-6: clap） */}
            <div className="mx-auto">
              <CoachAvatar size={112} pose="clap" />
            </div>
            <h1 className="text-xl font-black text-slate-800">ようこそプレミアムへ</h1>
            <p className="font-body text-sm text-slate-600">
              これから録音解析が無制限になり、詳細添削レポートも使えます。
            </p>
            <Button href="/coach" size="sm">
              ホームへ戻る
            </Button>
          </>
        ) : (
          <>
            {/* 確認中＝考えるポーズ（docs/61 §3-6: thinking） */}
            <div className="mx-auto">
              <CoachAvatar size={112} pose="thinking" />
            </div>
            <h1 className="text-xl font-black text-slate-800">お支払いを確認しています…</h1>
            <p className="font-body text-sm text-slate-600">
              反映まで少しかかることがあります（最大1分ほど）。このままお待ちください。
            </p>
            <div className="mx-auto h-3 w-2/3 animate-pulse rounded-full bg-slate-200" />
          </>
        )}
      </div>
    </div>
  );
}
