import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "こえのアトリエ｜AIボイストレーナー",
  description: "録音した歌に、ボイストレーナーがその場でフィードバック",
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
