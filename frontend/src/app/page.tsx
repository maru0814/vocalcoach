import { SiteHeader } from "@/components/site/SiteHeader";
import { HeroTop } from "@/components/site/heroes";
import { LpBody, StickyCta } from "@/components/site/LpBody";

const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "AIボーカルトレーナー ソラ先生",
  alternateName: "ソラ先生",
  applicationCategory: "MultimediaApplication",
  operatingSystem: "Web",
  description:
    "歌の録音を送るだけでAIが音程・リズム・表現を解析し、今日直すところと基礎練メニューを教えるAIボーカルトレーナー。",
  offers: { "@type": "Offer", price: "0", priceCurrency: "JPY" },
};

// WHO=歌が上手くなりたい一般 / WHAT=録って送れば直すところが分かる / HOW=レッスン主導線＋診断の副導線
export default function HomePage() {
  return (
    <div className="bg-studio min-h-[100dvh] overflow-hidden pb-24 sm:pb-0">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />

      <SiteHeader />

      <main className="mx-auto max-w-6xl px-5">
        <HeroTop />
        <LpBody />
      </main>

      <StickyCta />
    </div>
  );
}
