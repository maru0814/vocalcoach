import type { Metadata } from "next";
import type { ReactNode } from "react";

// 診断ページのOGP＝8タイプ全員集合の一枚絵（/lp/shindan と同一。docs/28 §11）。
// ページ本体（page.tsx）は "use client" のためメタデータはこの layout で付与する。
// 子ルート（[typeId]・share/[id]）は各自の generateMetadata で openGraph/twitter を上書きするので影響しない。
const OG_TITLE = "あなたの声、何タイプ？";
const OG_DESC =
  "15秒歌うだけ、AIが8タイプで“声診断”。登録なしで試せます（結果の保存だけ無料登録）。専用マイク不要。";
const OG_IMAGE = "/brand/og-shindan.jpg";

export const metadata: Metadata = {
  openGraph: {
    type: "website",
    locale: "ja_JP",
    url: "/voice-type",
    title: OG_TITLE,
    description: OG_DESC,
    images: [{ url: OG_IMAGE, width: 1200, height: 630, alt: OG_TITLE }],
  },
  twitter: {
    card: "summary_large_image",
    title: OG_TITLE,
    description: OG_DESC,
    images: [OG_IMAGE],
  },
};

export default function VoiceTypeLayout({ children }: { children: ReactNode }) {
  return children;
}
