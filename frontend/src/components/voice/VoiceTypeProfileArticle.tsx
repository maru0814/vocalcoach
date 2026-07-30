import type { ReactNode } from "react";
import type { VoiceProfile } from "@/content/voiceProfiles";
import { IconChip } from "@/components/site/IconChip";
import { CoachAvatar } from "@/components/character/Coach";
import { VoiceAxisBars, VTYPE_AXES } from "./VoiceAxisBars";

// 声タイプ図鑑のプロフィール記事本体（正本: docs/62。共有化: docs/70 §3-2）。
// 詳細ページ（/voice-type/[typeId]）と診断結果ビュー（/voice-type）の両方で使う。
// hooksなし・サーバー/クライアント両用。ヒーロー・診断CTA・他タイプグリッドは含まない。

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

export function VoiceTypeProfileArticle({ profile }: { profile: VoiceProfile }) {
  return (
    <>
      {/* 導入 ＋ このタイプの3軸位置（docs/83） */}
      <section className="rounded-[2rem] bg-white/90 p-7 shadow-card sm:p-10">
        <p className="font-body text-base leading-[2.05] tracking-[0.01em] text-slate-700">
          {em(profile.lede)}
        </p>
        {VTYPE_AXES[profile.id] && (
          <div className="mt-7 border-t border-slate-100 pt-6">
            <p className="mb-3 text-xs font-bold tracking-wide text-slate-500">このタイプの位置</p>
            <VoiceAxisBars
              pos={VTYPE_AXES[profile.id]}
              caption="※ 声の傾向からの推定です（優劣ではありません）"
              className="max-w-md"
            />
          </div>
        )}
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
            {/* セクションに添えるソラ先生のポーズ（docs/61 §3-6・ポーズはページ内で一意）。
                poseSrc があるタイプはタイプ専用のシーン絵を優先表示する */}
            <CoachAvatar pose={s.pose} poseSrc={s.poseSrc} size={72} />
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
  );
}
