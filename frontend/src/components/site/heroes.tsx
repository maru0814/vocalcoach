import { ReactNode } from "react";
import Link from "next/link";
import { CoachAvatar, COACH_NAME } from "@/components/character/Coach";
import { StageDecor } from "@/components/site/Stage";
import { Marker } from "@/components/site/SectionHeading";
import { HeroLessonDemo } from "@/components/site/HeroLessonDemo";
import { Button } from "@/components/ui/Button";
import { VoiceTypeArt } from "@/components/voice/VoiceTypeArt";
import { VOICE_TYPE_LIST } from "@/components/voice/voiceTypes";

/**
 * LPヒーロー（監査後の確定版）。文字量は「見出し＋1行＋CTA」を上限とする。
 * - HeroTop     : `/`          WHO=上手くなりたい一般（総合入口・両導線）
 * - HeroShindan : `/lp/shindan` WHO=診断訴求の流入（診断に一本化）
 * - HeroVoitore : `/lp/voitore` WHO=高音・ミックスボイスの悩み（高音に一本化）
 * 診断オファーの文言は事実に基づく: 診断は登録なしで完走できる。
 * 結果の保存・シェアに無料登録（frontend/src/app/voice-type/page.tsx の未ログイン挙動）。
 */

function PosterWall() {
  const ids = VOICE_TYPE_LIST.map((t) => t.id);
  const tiles = [...ids, ...ids].slice(0, 12);
  return (
    <>
      <div
        className="pointer-events-none absolute -right-24 top-1/2 hidden w-[680px] -translate-y-1/2 rotate-[8deg] lg:block"
        aria-hidden
      >
        <div className="grid grid-cols-3 gap-3">
          {tiles.map((id, i) => (
            <div
              key={i}
              className={`aspect-square overflow-hidden rounded-2xl ring-1 ring-white/10 ${
                i % 3 === 1 ? "translate-y-10" : i % 3 === 2 ? "translate-y-4" : ""
              }`}
            >
              <VoiceTypeArt id={id} className="h-full w-full" />
            </div>
          ))}
        </div>
      </div>
      {/* 文字可読性のための暗幕（ウォールの上・コンテンツの下） */}
      <div
        className="pointer-events-none absolute inset-0 bg-gradient-to-r from-night-950 via-night-950/80 to-night-950/15"
        aria-hidden
      />
    </>
  );
}

function HeroKeyartShell({ children, card, cardLabel }: { children: ReactNode; card?: ReactNode; cardLabel?: string }) {
  return (
    <section className="bg-stage grain relative mt-4 overflow-hidden rounded-[2.5rem] text-white shadow-soft">
      <PosterWall />
      <StageDecor notes={false} />
      <div className="relative z-10 flex min-h-[440px] flex-col justify-center p-7 sm:p-14 lg:min-h-[620px] lg:max-w-[56%]">
        {children}
      </div>
      {card && (
        <div className="relative z-10 w-full px-7 pb-8 sm:px-14 lg:absolute lg:bottom-12 lg:right-14 lg:w-96 lg:-rotate-2 lg:px-0 lg:pb-0">
          <div className="mx-auto w-full max-w-sm lg:max-w-none">
            {cardLabel && (
              <p className="mb-2 text-center text-xs font-bold tracking-[0.2em] text-brand-200">{cardLabel}</p>
            )}
            {card}
          </div>
        </div>
      )}
      {/* モバイル用ミニウォール（デスクトップはPosterWallが担当） */}
      <div className="relative z-10 grid grid-cols-4 gap-2 px-7 pb-8 lg:hidden" aria-hidden>
        {VOICE_TYPE_LIST.slice(0, 4).map((t) => (
          <div key={t.id} className="aspect-square overflow-hidden rounded-xl ring-1 ring-white/15">
            <VoiceTypeArt id={t.id} className="h-full w-full" />
          </div>
        ))}
      </div>
    </section>
  );
}

function HeroBadge() {
  return (
    <p className="inline-flex w-fit items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-bold">
      <span className="inline-flex"><CoachAvatar size={16} /></span>
      AIボーカルトレーナー {COACH_NAME}
    </p>
  );
}

/** `/` トップ — 総合入口。レッスン主導線＋診断の副導線 */
export function HeroTop() {
  return (
    <HeroKeyartShell cardLabel="BEFORE → AFTER（実際のレッスンの流れ）" card={<HeroLessonDemo />}>
      <HeroBadge />
      <h1 className="mt-4 text-5xl font-black leading-[1.15] tracking-tight sm:text-6xl lg:text-7xl">
        歌は、<Marker tone="dark">直せる。</Marker>
      </h1>
      <p className="mt-5 max-w-md text-base text-white/85 sm:text-lg">
        録って送るだけ。どこを・どう直すかを、AIが言葉にします。
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button href="/login" variant="secondary" size="lg">
          無料で始める <span className="text-sm font-normal text-slate-400">30秒</span>
        </Button>
        <span className="text-sm text-white/70">専用マイク不要・クレカ不要</span>
      </div>
      <Link
        href="/voice-type"
        className="mt-4 w-fit text-sm font-bold text-brand-200 underline-offset-4 hover:underline"
      >
        先に15秒の声タイプ診断だけ試す（登録なし）→
      </Link>
    </HeroKeyartShell>
  );
}

/** 診断結果のティザー: 近い歌手名を伏せて登録誘導（未登録は結果ぼかし→登録で開く、という実挙動と一致） */
function ShindanTeaserCard() {
  return (
    <div className="rounded-2xl bg-white p-3 shadow-card">
      <div className="flex items-center gap-2 border-b border-slate-100 px-1 pb-2">
        <CoachAvatar size={24} />
        <span className="text-xs font-bold text-slate-700">{COACH_NAME}</span>
        <span className="ml-auto inline-flex items-center gap-1 text-xs text-slate-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden />
          オンライン
        </span>
      </div>
      <div className="space-y-2 px-1 pb-1 pt-3">
        <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md bg-brand-600 px-3 py-2 text-xs leading-relaxed text-white">
          15秒だけ歌ってみました！
        </p>
        <div className="flex items-end gap-1.5">
          <CoachAvatar size={20} />
          <p className="max-w-[85%] rounded-2xl rounded-bl-md bg-slate-100 px-3 py-2 text-xs leading-relaxed text-slate-700">
            あなたは <b className="text-brand-700">Crystal Voice</b> タイプ✨ 歌手でいうと
            <span
              className="mx-1 inline-block select-none rounded bg-slate-300 px-4 align-middle text-transparent [filter:blur(4px)]"
              aria-label="（無料登録でひらく）"
            >
              ●●●●
            </span>
            さんに近い声です
          </p>
        </div>
        <p className="pt-1 text-center text-xs font-bold text-brand-600">→ 近い歌手の名前は、無料登録でひらきます</p>
      </div>
    </div>
  );
}

/** `/lp/shindan` — 診断訴求の流入先。見出し・CTA・遷移先を診断に一本化 */
export function HeroShindan() {
  return (
    <HeroKeyartShell cardLabel="診断結果のイメージ" card={<ShindanTeaserCard />}>
      <HeroBadge />
      <h1 className="mt-4 text-5xl font-black leading-[1.15] tracking-tight sm:text-6xl lg:text-7xl">
        あなたの声、<br className="hidden sm:block" />
        <Marker tone="dark">何タイプ？</Marker>
      </h1>
      <p className="mt-5 max-w-md text-base text-white/85 sm:text-lg">
        15秒歌うだけ。AIが8タイプで“声診断”します。
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button href="/voice-type" variant="secondary" size="lg">
          登録なしで、15秒診断
        </Button>
        <span className="text-sm text-white/70">結果の保存だけ無料登録・クレカ不要</span>
      </div>
    </HeroKeyartShell>
  );
}

/** `/lp/voitore` — 高音×ミックスボイス訴求の流入先 */
export function HeroVoitore() {
  return (
    <HeroKeyartShell cardLabel="秒数つきで原因がわかり、直るまで伴走" card={<HeroLessonDemo />}>
      <HeroBadge />
      <h1 className="mt-4 text-4xl font-black leading-[1.18] tracking-tight sm:text-5xl lg:text-6xl">
        その高音、<br />
        <Marker tone="dark">出るようになる。</Marker>
      </h1>
      <p className="mt-5 max-w-md text-base text-white/85 sm:text-lg">
        裏返る・苦しいの原因を突き止めて、ミックスボイス習得まで伴走します。
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button href="/login" variant="secondary" size="lg">
          無料で始める <span className="text-sm font-normal text-slate-400">30秒</span>
        </Button>
        <span className="text-sm text-white/70">専用マイク不要・クレカ不要</span>
      </div>
    </HeroKeyartShell>
  );
}
