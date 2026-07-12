import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { BrandWordmark } from "@/components/brand/Brand";
import { VoiceTypeArt } from "@/components/voice/VoiceTypeArt";
import { VOICE_TYPE_LIST, VOICE_TYPE_META, SITE_URL } from "@/components/voice/voiceTypes";
import { VOICE_PROFILES } from "@/content/voiceProfiles";
import { Button } from "@/components/ui/Button";
import { ProfileShareButtons } from "@/components/voice/ProfileShareButtons";
import { IconChip } from "@/components/site/IconChip";
import { CoachAvatar } from "@/components/character/Coach";

// 声タイプ図鑑: タイプ別プロフィールページ（正本: docs/62）。
// 16personalities のタイプページを参考に、長文プロフィール＋有名人イラストで構成。
// 本文未制作のタイプは「準備中」フォールバック（docs/62 §14 empty state）。

export function generateStaticParams() {
  return VOICE_TYPE_LIST.map((t) => ({ typeId: t.id }));
}

export function generateMetadata({ params }: { params: { typeId: string } }): Metadata {
  const meta = VOICE_TYPE_META[params.typeId];
  if (!meta) return {};
  const profile = VOICE_PROFILES[params.typeId];
  const title = profile
    ? `${profile.nameJa}（${meta.name}）とは？歌声・話し声・性格まで徹底解説`
    : `${meta.name} とは｜声タイプ図鑑`;
  const description = profile
    ? `${profile.heroTitle}。歌声の魅力から苦手なこと、普段の話し声の印象、性格の傾向、似た声のアーティストまで。15秒歌うだけの無料声タイプ診断🎤`
    : `${meta.desc} あなたの声も15秒歌うだけで無料診断🎤`;
  const path = `/voice-type/${params.typeId}`;
  // SNSでリンクを貼ったときにタイプのイラストで開くよう、OG/Twitterカード画像を付ける
  const ogImage = `/voice-types/og/${params.typeId}.jpg`;
  return {
    metadataBase: new URL(SITE_URL),
    title,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "article",
      siteName: "AIボーカルトレーナー ソラ先生",
      locale: "ja_JP",
      url: path,
      title,
      description,
      images: [{ url: ogImage, width: 1200, height: 630, alt: title }],
    },
    twitter: { card: "summary_large_image", title, description, images: [ogImage] },
  };
}

// 本文中の **強調** を <strong> に変換する（docs/62 の原稿マークアップ）
function em(text: string): ReactNode {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return parts.map((p, i) =>
    i % 2 === 1 ? (
      <strong key={i} className="font-bold text-slate-900">
        {p}
      </strong>
    ) : (
      <span key={i}>{p}</span>
    ),
  );
}

export default function VoiceTypeProfilePage({ params }: { params: { typeId: string } }) {
  const meta = VOICE_TYPE_META[params.typeId];
  if (!meta) notFound();
  const profile = VOICE_PROFILES[params.typeId];
  const others = VOICE_TYPE_LIST.filter((t) => t.id !== params.typeId);

  return (
    <div className="bg-studio min-h-[100dvh] pb-16">
      <header className="mx-auto flex max-w-3xl items-center justify-between p-5">
        <Link href="/">
          <BrandWordmark size={40} />
        </Link>
        <Link
          href="/voice-type"
          className="text-sm font-medium text-slate-500 hover:text-brand-600"
        >
          ← 診断ページへ
        </Link>
      </header>

      <main className="mx-auto max-w-3xl space-y-8 px-5">
        {/* ヒーロー: イラストを全幅で主役に */}
        <section className="overflow-hidden rounded-[2rem] bg-white shadow-card">
          <div className="relative aspect-[1280/698] w-full">
            <VoiceTypeArt id={params.typeId} fallbackMascotSize={120} className="h-full w-full" />
          </div>
          <div className="px-6 py-7 text-center sm:px-10 sm:py-8">
            <p className="text-xs font-bold tracking-wide text-brand-600">
              声タイプ図鑑 — {meta.name} {meta.emoji}
            </p>
            <h1 className="mt-2.5 font-rounded text-3xl font-black tracking-tight text-slate-900 sm:text-[2.6rem]">
              {profile ? profile.nameJa : meta.name}
            </h1>
            <p className="mx-auto mt-2.5 max-w-xl font-rounded text-base font-bold leading-relaxed text-slate-500 sm:text-lg">
              {profile ? profile.heroTitle : meta.desc}
            </p>
          </div>
        </section>

        {profile && (
          /* シェア導線（ヒーロー直下・診断直後に共有しやすく） */
          <section className="rounded-[2rem] bg-white/90 p-6 shadow-card sm:p-7">
            <ProfileShareButtons
              typeId={params.typeId}
              nameJa={profile.nameJa}
              heroTitle={profile.heroTitle}
            />
          </section>
        )}

        {profile ? (
          <>
            {/* 導入 */}
            <section className="rounded-[2rem] bg-white/90 p-7 shadow-card sm:p-10">
              <p className="font-body text-base leading-[2.05] tracking-[0.01em] text-slate-700">
                {em(profile.lede)}
              </p>
            </section>

            {/* 目次 */}
            <nav aria-label="このページの目次" className="flex flex-wrap gap-2 px-1">
              {profile.sections.map((s, i) => (
                <a
                  key={s.id}
                  href={`#${s.id}`}
                  className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 transition hover:border-brand-300 hover:text-brand-700"
                >
                  {String(i + 1).padStart(2, "0")} {s.nav}
                </a>
              ))}
              <a
                href="#artists"
                className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 transition hover:border-brand-300 hover:text-brand-700"
              >
                {String(profile.sections.length + 1).padStart(2, "0")} 有名人
              </a>
            </nav>

            {/* 本文セクション */}
            {profile.sections.map((s, i) => (
              <section
                key={s.id}
                id={s.id}
                aria-labelledby={`${s.id}-title`}
                className="scroll-mt-24 rounded-[2rem] bg-white/90 p-7 shadow-card sm:p-10"
              >
                <div className="flex items-center gap-4 border-b border-slate-100 pb-5">
                  <IconChip icon={s.icon} size={48} />
                  <div className="min-w-0 flex-1">
                    <span className="font-rounded text-xs font-black tracking-wide text-brand-300">
                      SECTION {String(i + 1).padStart(2, "0")}
                    </span>
                    <h2
                      id={`${s.id}-title`}
                      className="font-rounded text-xl font-black leading-tight tracking-tight text-slate-900 sm:text-2xl"
                    >
                      {s.title}
                    </h2>
                  </div>
                  {/* セクションに添えるソラ先生のポーズ（docs/61 §3-6・ポーズはページ内で一意） */}
                  <CoachAvatar pose={s.pose} size={72} />
                </div>
                {s.kind === "text" ? (
                  <div className="mt-6 space-y-6">
                    {s.paragraphs.map((p, j) => (
                      <p
                        key={j}
                        className="font-body text-base leading-[2.05] tracking-[0.01em] text-slate-700"
                      >
                        {em(p)}
                      </p>
                    ))}
                  </div>
                ) : (
                  <>
                    <ul className="mt-6 space-y-5">
                      {s.items.map((item, j) => (
                        <li key={j} className="flex gap-3.5">
                          <span
                            aria-hidden="true"
                            className="mt-3 h-2 w-2 shrink-0 rounded-full bg-brand-400"
                          />
                          <p className="font-body text-base leading-[2.05] tracking-[0.01em] text-slate-700">
                            {em(item)}
                          </p>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-7 rounded-2xl bg-brand-50/70 px-5 py-4 font-body text-base leading-[2.05] tracking-[0.01em] text-slate-600">
                      {em(s.closing)}
                    </p>
                  </>
                )}
              </section>
            ))}

            {/* 有名人ラインナップ */}
            <section
              id="artists"
              aria-labelledby="artists-title"
              className="scroll-mt-24 rounded-[2rem] bg-white/90 p-6 shadow-card sm:p-8"
            >
              <h2
                id="artists-title"
                className="text-center font-rounded text-2xl font-black tracking-tight text-slate-900"
              >
                {profile.nameJa}の有名人
              </h2>
              <div className="mt-6 grid grid-cols-2 gap-x-3 gap-y-8 sm:grid-cols-3 md:grid-cols-4">
                {profile.artists.map((a) => (
                  <figure key={a.name} className="m-0 text-center">
                    {/* 自前の静的SVG（docs/62 §5-2 承認済みイラスト）。属性がkebab-caseのため文字列描画 */}
                    <div
                      className="mx-auto max-w-[150px] [&_svg]:h-auto [&_svg]:w-full"
                      dangerouslySetInnerHTML={{ __html: a.svg }}
                    />
                    <figcaption className="mt-2 text-sm font-bold text-slate-700">
                      {a.name}
                    </figcaption>
                  </figure>
                ))}
              </div>
            </section>
          </>
        ) : (
          /* 準備中フォールバック（docs/62 §14）: 短い要約だけで成立させる */
          <section className="rounded-[2rem] bg-white/90 p-6 text-center shadow-card sm:p-10">
            <p className="font-body text-[15px] leading-relaxed text-slate-700">{meta.desc}</p>
            <p className="mt-4 text-sm font-bold text-slate-400">
              このタイプの詳しいプロフィール記事は、いま執筆中です。もう少しだけお待ちください。
            </p>
          </section>
        )}

        {/* 診断CTA */}
        <section className="rounded-[2rem] bg-white/90 p-6 text-center shadow-card sm:p-10">
          <h2 className="font-rounded text-xl font-black tracking-tight text-slate-900">
            あなたの声は、どのタイプ？
          </h2>
          <p className="mt-2 font-body text-sm leading-relaxed text-slate-600">
            15秒くらい歌うだけ。AIが発声を解析して、8つの声タイプから診断します。
          </p>
          <div className="mt-5 flex justify-center">
            <Button href="/voice-type">自分の声タイプを診断する</Button>
          </div>
          {profile && (
            <div className="mt-8 border-t border-slate-100 pt-7">
              <ProfileShareButtons
                typeId={params.typeId}
                nameJa={profile.nameJa}
                heroTitle={profile.heroTitle}
              />
            </div>
          )}
        </section>

        {/* 他のタイプへ */}
        <section aria-label="他の声タイプ">
          <p className="px-1 text-xs font-bold text-slate-500">他のタイプも見る</p>
          <div className="mt-3 grid grid-cols-4 gap-2 sm:grid-cols-7">
            {others.map((t) => (
              <Link
                key={t.id}
                href={`/voice-type/${t.id}`}
                className="group relative aspect-square overflow-hidden rounded-2xl shadow-soft transition hover:-translate-y-0.5 hover:shadow-card-2"
              >
                <VoiceTypeArt id={t.id} fallbackMascotSize={36} className="h-full w-full" />
                <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/55 to-transparent px-1 pb-1 pt-3 text-center text-[10px] font-bold text-white drop-shadow">
                  {t.name}
                </span>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
