import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { VoiceTypeArt } from "@/components/voice/VoiceTypeArt";
import { VOICE_TYPE_LIST, VOICE_TYPE_META, SITE_URL, VTYPE_STYLE } from "@/components/voice/voiceTypes";

// 8タイプ分を静的生成（Xクローラが読む og/twitter メタを各タイプで出す）
export function generateStaticParams() {
  return VOICE_TYPE_LIST.map((t) => ({ id: t.id }));
}

export function generateMetadata({ params }: { params: { id: string } }): Metadata {
  const m = VOICE_TYPE_META[params.id];
  if (!m) return {};
  const title = `あなたの声タイプは【${m.name}${m.emoji}】`;
  const description = `${m.desc} あなたの声も15秒歌うだけで無料診断🎤`;
  const path = `/voice-type/share/${params.id}`;
  const ogImage = `/voice-types/og/${params.id}.jpg`;
  return {
    metadataBase: new URL(SITE_URL),
    title,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      siteName: "AIボーカルトレーナー ソラ先生",
      locale: "ja_JP",
      url: path,
      title,
      description,
      images: [{ url: ogImage, width: 1200, height: 630, alt: title }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [ogImage],
    },
  };
}

export default function VoiceTypeShareLanding({ params }: { params: { id: string } }) {
  const m = VOICE_TYPE_META[params.id];
  if (!m) notFound();
  const grad = VTYPE_STYLE[params.id] || "from-brand-500 to-pink-500";

  return (
    <div className="bg-studio min-h-[100dvh] pb-16">
      <main className="mx-auto max-w-2xl space-y-5 px-5 pt-6">
        <div className={`overflow-hidden rounded-3xl bg-gradient-to-br ${grad} text-white shadow-soft`}>
          <div className="relative aspect-[16/9] w-full">
            <VoiceTypeArt id={params.id} className="h-full w-full" />
            <div className="absolute left-3 top-3 rounded-full bg-black/35 px-2 py-0.5 text-[11px] font-bold tracking-wide backdrop-blur-sm">
              🎤 ソラ先生 声タイプ診断
            </div>
          </div>
          <div className="p-5">
            <div className="text-2xl font-black">{m.name} {m.emoji}</div>
            <p className="mt-1.5 text-sm font-medium leading-relaxed text-white/95">{m.desc}</p>
          </div>
        </div>

        <div className="rounded-3xl bg-white/90 p-6 text-center shadow-card">
          <h1 className="text-xl font-black text-slate-800">あなたの声は、どのタイプ？</h1>
          <p className="mt-2 text-sm text-slate-600">
            AIボーカルトレーナー「ソラ先生」が、15秒歌うだけであなたの声を8タイプで診断します。
            似た声質のアーティストつき。診断のあとは、その声に合った発声レッスンへ。
          </p>
          <div className="mx-auto mt-5 grid max-w-md grid-cols-4 gap-2">
            {VOICE_TYPE_LIST.map((t) => (
              <div key={t.id} className="relative aspect-square overflow-hidden rounded-xl shadow-soft">
                <VoiceTypeArt id={t.id} fallbackMascotSize={32} className="h-full w-full" />
              </div>
            ))}
          </div>
          <Link
            href="/voice-type"
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-brand-gradient px-7 py-3.5 font-bold text-white shadow-soft transition hover:scale-[1.02] active:scale-95"
          >
            無料で自分の声タイプを診断する →
          </Link>
          <p className="mt-3 text-xs text-slate-400">※ 診断・発声レッスンとも、無料登録（30秒）で使えます</p>
        </div>
      </main>
    </div>
  );
}
