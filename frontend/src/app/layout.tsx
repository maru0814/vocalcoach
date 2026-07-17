import "./globals.css";
import type { ReactNode } from "react";
import type { Metadata } from "next";
import ServiceWorkerRegister from "@/components/pwa/ServiceWorkerRegister";
import OfflineBar from "@/components/pwa/OfflineBar";
import InstallPrompt from "@/components/pwa/InstallPrompt";

const SITE_NAME = "AIボーカルトレーナー ソラ先生";
const TAGLINE = "歌をAIが解析・添削";
const DESCRIPTION =
  "AIボーカルトレーナー「ソラ先生」が、歌の録音を送るだけで音程・リズム・表現を解析し、今日直すところと基礎練メニューをチャットで教えます。スマホひとつ・専用マイク不要・無料で始められます。";

export const metadata: Metadata = {
  // OG/Twitter画像・favicon の絶対URL生成に使うサイトorigin。
  // 本番はビルド引数 NEXT_PUBLIC_SITE_URL（compose）を使い、無ければ本番ドメインにフォールバック。
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://sora-vocal-ai.duckdns.org"),
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
    // サイト共通OG。app/opengraph-image.png（ファイル規約）だと voice-type/share の
    // タイプ別OGP（generateMetadata の images 指定）まで上書きしてしまうため、
    // public 配置＋config 指定にして子ルートが上書きできるようにしている
    images: [{ url: "/brand/og-default.png", width: 1200, height: 630, alt: SITE_NAME }],
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME}｜${TAGLINE}`,
    description: DESCRIPTION,
    images: ["/brand/og-default.png"],
  },
  robots: { index: true, follow: true },
  // PWA（docs/73 FR-01）: manifest とアプリアイコン。
  manifest: "/manifest.webmanifest",
  themeColor: "#0b1020",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "ソラ先生",
  },
};

// Cloudflare Web Analytics のビーコントークン（公開値。env未設定なら計測タグを出さない）
const CF_BEACON_TOKEN = process.env.NEXT_PUBLIC_CF_BEACON_TOKEN;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700;900&family=Noto+Sans+JP:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
        {CF_BEACON_TOKEN && (
          // eslint-disable-next-line @next/next/no-sync-scripts
          <script
            defer
            src="https://static.cloudflareinsights.com/beacon.min.js"
            data-cf-beacon={`{"token": "${CF_BEACON_TOKEN}"}`}
          />
        )}
      </head>
      <body>
        <ServiceWorkerRegister />
        <OfflineBar />
        {children}
        <InstallPrompt />
        <footer className="mt-10 border-t py-6 text-center text-xs text-gray-500">
          <a className="underline hover:text-gray-700" href="/legal/tokushoho">
            特定商取引法に基づく表記
          </a>
        </footer>
      </body>
    </html>
  );
}
