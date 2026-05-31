import "./globals.css";
import type { ReactNode } from "react";
import type { Metadata } from "next";

const SITE_NAME = "AIボーカルトレーナー ソラ先生";
const TAGLINE = "歌をAIが解析・添削";
const DESCRIPTION =
  "AIボーカルトレーナー「ソラ先生」が、歌の録音を送るだけで音程・リズム・表現を解析し、今日直すところと基礎練メニューをチャットで教えます。スマホひとつ・専用マイク不要・無料で始められます。";

export const metadata: Metadata = {
  metadataBase: new URL("http://localhost:3000"),
  title: {
    default: `${SITE_NAME} - ${TAGLINE}`,
    template: `%s｜${SITE_NAME}`,
  },
  description: DESCRIPTION,
  applicationName: SITE_NAME,
  keywords: [
    "AIボーカルトレーナー",
    "AIボイストレーナー",
    "ボイトレ",
    "ボイストレーニング",
    "歌 練習 アプリ",
    "歌 上達",
    "音程 改善",
    "ミックスボイス",
    "歌 添削 AI",
    "ソラ先生",
  ],
  authors: [{ name: SITE_NAME }],
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: `${SITE_NAME}｜${TAGLINE}`,
    description: DESCRIPTION,
    locale: "ja_JP",
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME}｜${TAGLINE}`,
    description: DESCRIPTION,
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
