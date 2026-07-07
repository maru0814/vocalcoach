import type { Metadata } from "next";
import { SiteHeader } from "@/components/site/SiteHeader";
import { HeroShindan } from "@/components/site/heroes";
import { LpBody, StickyCta } from "@/components/site/LpBody";

// 流入別LP（声タイプ診断訴求の広告・SNS投稿から）。広告バリアントのため noindex
export const metadata: Metadata = {
  title: "歌は、直せる。",
  description:
    "まずは15秒の声タイプ診断から。AIボーカルトレーナーが、どこを・どう直すかまで言葉にします。無料・専用マイク不要。",
  robots: { index: false, follow: true },
};

export default function LpShindan() {
  return (
    <div className="bg-studio min-h-[100dvh] overflow-hidden pb-24 sm:pb-0">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-5">
        <HeroShindan />
        <LpBody />
      </main>
      <StickyCta />
    </div>
  );
}
