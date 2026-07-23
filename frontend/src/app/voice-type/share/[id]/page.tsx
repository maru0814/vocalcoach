import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { VoiceTypeArt } from "@/components/voice/VoiceTypeArt";
import { VOICE_TYPE_LIST, VOICE_TYPE_META, SITE_URL, VTYPE_STYLE } from "@/components/voice/voiceTypes";

type SP = { [k: string]: string | string[] | undefined };
function parseScore(searchParams?: SP): number | null {
  const raw = searchParams?.s;
  const s = Array.isArray(raw) ? raw[0] : raw;
  return s && /^\d{1,3}$/.test(s) ? Number(s) : null;
}

// 8タイプ分を静的生成（Xクローラが読む og/twitter メタを各タイプで出す）
export function generateStaticParams() {
  return VOICE_TYPE_LIST.map((t) => ({ id: t.id }));
}

export function generateMetadata(
  { params, searchParams }: { params: { id: string }; searchParams?: SP },
): Metadata {
  const m = VOICE_TYPE_META[params.id];
  if (!m) return {};
  const score = parseScore(searchParams);
  const scoreSuffix = score != null ? ` 総合${score}点` : "";
  const title = `あなたの声タイプは【${m.name}${m.emoji}】${scoreSuffix}`;
  const description = `${m.desc} あなたの声も15秒歌うだけで無料診断🎤`;
  const path = `/voice-type/share/${params.id}`;
  // 診断結果の一枚絵（スコア入りカード）を動的生成。失敗時はルート側で静的OGへフォールバック
  // 注: /api/* は本番Caddyがbackendへ振るため、Next側ルートは /og/ 配下に置く（docs/28 §11）
  const ogImage = `/og/voice-type/${params.id}${score != null ? `?s=${score}` : ""}`;
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

export default function VoiceTypeShareLanding(
  { params, searchParams }: { params: { id: string }; searchParams?: SP },
) {
  const m = VOICE_TYPE_META[params.id];
  if (!m) notFound();
  const grad = VTYPE_STYLE[params.id] || "from-brand-500 to-pink-500";
  const score = parseScore(searchParams);

  return (
    <div className="bg-studio min-h-[100dvh] pb-16">
      <main className="mx-auto max-w-2xl space-y-5 px-5 pt-6">
        <div className={`overflow-hidden rounded-2xl bg-gradient-to-br ${grad} text-white shadow-soft`}>
          <div className="relative aspect-[16/9] w-full">
            <VoiceTypeArt id={params.id} className="h-full w-full" />
            <div className="absolute left-3 top-3 rounded-full bg-black/35 px-2 py-0.5 text-[11px] font-bold tracking-wide backdrop-blur-sm">
              ソラ先生 声タイプ診断
            </div>
          </div>
          <div className="p-5">
            <div className="flex items-center gap-2">
              <div className="text-2xl font-black">{m.name} {m.emoji}</div>
              {score != null && (
                <span className="ml-auto text-right text-xs text-white/85">総合<br /><b className="text-lg">{score}</b></span>
              )}
            </div>
            <p className="mt-1.5 text-sm font-medium leading-relaxed text-white/95">{m.desc}</p>
          </div>
        </div>

        <div className="rounded-2xl bg-white/90 p-6 text-center shadow-card">
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
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-brand-600 px-7 py-3.5 font-bold text-white shadow-[0_4px_0_#5b21b6] transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 active:translate-y-[3px] active:shadow-[0_1px_0_#5b21b6]"
          >
            無料で自分の声タイプを診断する →
          </Link>
          <p className="mt-3 text-xs text-slate-400">※ 診断・発声レッスンとも、無料登録（30秒）で使えます</p>
        </div>
      </main>
    </div>
  );
}
