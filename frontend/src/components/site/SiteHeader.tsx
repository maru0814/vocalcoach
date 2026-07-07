"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BrandWordmark } from "@/components/brand/Brand";
import { Button } from "@/components/ui/Button";

/** スクロールで透明→白に変化する追従ヘッダー（To C LPの定番） */
export function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-40 transition-all duration-300 ${
        scrolled ? "border-b border-white/60 bg-white/80 shadow-sm backdrop-blur" : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
        <BrandWordmark size={40} />
        <div className="hidden items-center gap-3 sm:flex">
          <Link
            href="/login"
            className="rounded text-sm font-medium text-slate-500 transition hover:text-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
          >
            ログイン
          </Link>
          <Button href="/login" size="sm">
            無料で始める
          </Button>
        </div>
        <Link href="/login" className="text-sm font-medium text-slate-500 sm:hidden">
          ログイン
        </Link>
      </div>
    </header>
  );
}
