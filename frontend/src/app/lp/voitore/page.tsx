import type { Metadata } from "next";
import { SiteHeader } from "@/components/site/SiteHeader";
import { HeroVoitore } from "@/components/site/heroes";
import { LpBody, StickyCta } from "@/components/site/LpBody";

// 流入別LP（ボイトレ・高音・ミックスボイス訴求の広告・SNS投稿から）。広告バリアントのため noindex
// WHO=高音で悩む人 / WHAT=高音が出る＝ミックスボイスに向かえる / HOW=ヒーロー〜本体〜追従CTAまで高音一貫
export const metadata: Metadata = {
  title: "その高音、出るようになる。",
  description:
    "サビで苦しい・裏返る。原因を秒数つきで特定し、ミックスボイス習得までAIが伴走します。無料・専用マイク不要。",
  robots: { index: false, follow: true },
};

export default function LpVoitore() {
  return (
    <div className="bg-studio min-h-[100dvh] overflow-hidden pb-24 sm:pb-0">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-5">
        <HeroVoitore />
        <LpBody variant="takane" />
      </main>
      <StickyCta />
    </div>
  );
}
