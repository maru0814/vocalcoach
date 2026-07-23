import type { Metadata } from "next";
import { SiteHeader } from "@/components/site/SiteHeader";
import { HeroShindan } from "@/components/site/heroes";
import { LpBody, StickyCta } from "@/components/site/LpBody";

// 流入別LP（声タイプ診断訴求の広告・SNS投稿から）。広告バリアントのため noindex
// WHO=診断広告経由 / WHAT=自分の声のタイプが15秒で分かる / HOW=見出し・CTA・追従バーを診断に一本化
const LP_TITLE = "あなたの声、何タイプ？";
const LP_DESC =
  "15秒歌うだけ、AIが8タイプで“声診断”。登録なしで試せます（結果の保存だけ無料登録）。専用マイク不要。";
// OGPは8タイプ全員集合の一枚絵（再生成: 一時ImageResponseルートで作成 → docs/28 §11）
const LP_OG_IMAGE = "/brand/og-shindan.jpg";

export const metadata: Metadata = {
  title: LP_TITLE,
  description: LP_DESC,
  robots: { index: false, follow: true },
  openGraph: {
    type: "website",
    locale: "ja_JP",
    url: "/lp/shindan",
    title: LP_TITLE,
    description: LP_DESC,
    images: [{ url: LP_OG_IMAGE, width: 1200, height: 630, alt: LP_TITLE }],
  },
  twitter: {
    card: "summary_large_image",
    title: LP_TITLE,
    description: LP_DESC,
    images: [LP_OG_IMAGE],
  },
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
