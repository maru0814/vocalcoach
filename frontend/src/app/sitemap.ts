import type { MetadataRoute } from "next";
import { VOICE_TYPE_LIST, SITE_URL } from "@/components/voice/voiceTypes";

// 検索エンジン向けサイトマップ（/sitemap.xml）。
// 対象は公開・index可のページのみ:
//   - /lp/* は広告バリアントで noindex のため載せない
//   - /voice-type/share/* はSNS流入用ランディングのため載せない
//   - /coach /recordings /settings /billing はログイン後画面のため載せない
export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE_URL}/voice-type`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    ...VOICE_TYPE_LIST.map((t) => ({
      url: `${SITE_URL}/voice-type/${t.id}`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.8,
    })),
    { url: `${SITE_URL}/legal/tokushoho`, lastModified: now, changeFrequency: "yearly", priority: 0.1 },
  ];
}
