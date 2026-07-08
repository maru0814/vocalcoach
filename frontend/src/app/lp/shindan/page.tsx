import type { Metadata } from "next";
import { SiteHeader } from "@/components/site/SiteHeader";
import { HeroShindan } from "@/components/site/heroes";
import { LpBody, StickyCta } from "@/components/site/LpBody";

// 流入別LP（声タイプ診断訴求の広告・SNS投稿から）。広告バリアントのため noindex
// WHO=診断広告経由 / WHAT=自分の声のタイプが15秒で分かる / HOW=見出し・CTA・追従バーを診断に一本化
export const metadata: Metadata = {
  title: "あなたの声、何タイプ？",
  description:
    "15秒歌うだけ、AIが8タイプで“声診断”。登録なしで試せます（結果の保存だけ無料登録）。専用マイク不要。",
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
      <StickyCta href="/voice-type" label="登録なしで、15秒診断 →" sub="結果の保存だけ無料登録・クレカ不要" />
    </div>
  );
}
