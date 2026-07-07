"use client";

import { CoachAvatar } from "@/components/character/Coach";
import { Button } from "@/components/ui/Button";

export default function BillingCancelPage() {
  return (
    <div className="bg-studio flex min-h-[100dvh] items-center justify-center p-5">
      <div className="w-full max-w-md space-y-4 rounded-2xl bg-white/90 p-8 text-center shadow-card backdrop-blur">
        {/* 励ましのポーズ（docs/61 §3-6: cheer） */}
        <div className="mx-auto">
          <CoachAvatar size={112} pose="cheer" />
        </div>
        <h1 className="text-xl font-black text-slate-800">またいつでもどうぞ</h1>
        <p className="font-body text-sm text-slate-600">
          お支払いはキャンセルされました。無料プランのままご利用いただけます。
        </p>
        <Button href="/coach" size="sm">
          ホームへ戻る
        </Button>
      </div>
    </div>
  );
}
