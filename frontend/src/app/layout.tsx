import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "録音フィードバック",
  description: "録音した歌へのフィードバック",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <main className="mx-auto min-h-screen max-w-4xl p-6">{children}</main>
      </body>
    </html>
  );
}
