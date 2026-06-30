"use client";

import Link from "next/link";
import { BrandWordmark } from "@/components/brand/Brand";
import { PremiumWidget } from "@/components/PremiumWidget";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-3">
        {/* 主役は coach。ロゴ＝ホーム＝レッスンへ（docs/49 SCR-IA-1） */}
        <Link href="/coach" aria-label="レッスン一覧（ホーム）へ">
          <BrandWordmark size={36} />
        </Link>
        <PremiumWidget />
      </div>
    </header>
  );
}
