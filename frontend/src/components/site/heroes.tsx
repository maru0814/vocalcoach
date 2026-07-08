import { ReactNode } from "react";
import Link from "next/link";
import { CoachAvatar, COACH_NAME } from "@/components/character/Coach";
import { StageDecor } from "@/components/site/Stage";
import { Marker } from "@/components/site/SectionHeading";
import { HeroLessonDemo } from "@/components/site/HeroLessonDemo";
import { Button } from "@/components/ui/Button";
import { VoiceTypeArt } from "@/components/voice/VoiceTypeArt";
import { VoiceTypeBlock } from "@/components/voice/VoiceTypeResult";
import { VOICE_TYPE_LIST } from "@/components/voice/voiceTypes";

/**
 * LPヒーロー（監査後の確定版）。文字量は「見出し＋1行＋CTA」を上限とする。
 * Who/What/How の整合で背景を出し分ける:
 * - HeroTop     `/`          WHAT=歌を直せる    → 夜ステージ＋動的レッスンデモ
 * - HeroVoitore `/lp/voitore` WHAT=高音・ミックス → 夜ステージ＋動的レッスンデモ（高音の相談）
 * - HeroShindan `/lp/shindan` WHAT=声タイプ診断  → 診断アートウォール＋実際の診断結果カード
 * 診断オファーは事実に基づく: 診断は登録なしで完走でき、結果の保存・シェアに無料登録
 * （frontend/src/app/voice-type/page.tsx の未ログイン挙動）。
 */

function HeroBadge() {
  return (
    <p className="inline-flex w-fit items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-bold">
      <span className="inline-flex"><CoachAvatar size={16} /></span>
      AIボーカルトレーナー {COACH_NAME}
    </p>
  );
}

function CardLabel({ children }: { children: ReactNode }) {
  return <p className="mb-2 text-center text-xs font-bold tracking-[0.2em] text-brand-200">{children}</p>;
}

/**
 * 夜ステージ・ヒーロー（WHATがコーチングのページ用）。左コピー＋右カード（動的デモ）。
 * 背景に診断アートを並べない＝訴求(高音/直せる)とビジュアルを一致させる。
 */
function HeroStageShell({ children, card, cardLabel }: { children: ReactNode; card: ReactNode; cardLabel: string }) {
  return (
    <section className="bg-stage grain relative mt-4 overflow-hidden rounded-[2.5rem] p-7 text-white shadow-soft sm:p-14">
      <StageDecor />
      {/* スポットライトの光条（右カードを照らす） */}
      <div
        className="pointer-events-none absolute -top-10 right-[18%] hidden h-[560px] w-80 rotate-[10deg] bg-gradient-to-b from-neon-amber/15 via-neon-amber/5 to-transparent blur-2xl lg:block"
        aria-hidden
      />
      <div className="relative z-10 grid items-center gap-10 lg:grid-cols-2">
        <div className="max-w-xl">{children}</div>
        <div className="mx-auto w-full max-w-sm lg:mx-0 lg:ml-auto lg:-rotate-2 lg:shadow-glow-spot">
          <CardLabel>{cardLabel}</CardLabel>
          {card}
        </div>
      </div>
    </section>
  );
}

/** 診断アートのポスターウォール（WHAT=診断のページ専用） */
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
      <div
        className="pointer-events-none absolute inset-0 bg-gradient-to-r from-night-950 via-night-950/80 to-night-950/15"
        aria-hidden
      />
    </>
  );
}

/** 診断ウォール・ヒーロー（/lp/shindan 専用）。左コピー＋右下に実結果カード */
function HeroKeyartShell({ children, card, cardLabel }: { children: ReactNode; card: ReactNode; cardLabel: string }) {
  return (
    <section className="bg-stage grain relative mt-4 overflow-hidden rounded-[2.5rem] text-white shadow-soft">
      <PosterWall />
      <StageDecor notes={false} />
      <div className="relative z-10 flex min-h-[440px] flex-col justify-center p-7 sm:p-14 lg:min-h-[640px] lg:max-w-[56%]">
        {children}
      </div>
      <div className="relative z-10 w-full px-7 pb-8 sm:px-14 lg:absolute lg:bottom-12 lg:right-14 lg:w-80 lg:-rotate-2 lg:px-0 lg:pb-0">
        <div className="mx-auto w-full max-w-xs lg:max-w-none">
          <CardLabel>{cardLabel}</CardLabel>
          {card}
        </div>
      </div>
      {/* モバイル用ミニウォール */}
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

/** `/` トップ — 総合入口。レッスン主導線＋診断の副導線 */
export function HeroTop() {
  return (
    <HeroStageShell cardLabel="BEFORE → AFTER（実際のレッスンの流れ）" card={<HeroLessonDemo />}>
      <HeroBadge />
      <h1 className="mt-4 text-5xl font-black leading-[1.15] tracking-tight sm:text-6xl lg:text-7xl">
        歌は、<Marker tone="dark">直せる。</Marker>
      </h1>
      <p className="mt-5 max-w-md text-base text-white/85 sm:text-lg">
        録って送るだけ。どこを・どう直すかを、AIが言葉にします。
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button href="/login" variant="secondary">
          無料で始める <span className="text-sm font-normal text-slate-400">30秒</span>
        </Button>
        <span className="text-sm text-white/70">専用マイク不要・クレカ不要</span>
      </div>
      <Link
        href="/voice-type"
        className="mt-4 block w-fit text-sm font-bold text-brand-200 underline-offset-4 hover:underline"
      >
        先に15秒の声タイプ診断だけ試す（登録なし）→
      </Link>
    </HeroStageShell>
  );
}

/**
 * shindanヒーローの主役: 実際の診断結果カード（本物の VoiceTypeBlock）。
 * 近い歌手名だけ伏せて登録誘導＝未登録は結果ぼかし→登録で開く、という実挙動と一致。
 */
const SAMPLE_RESULT = {
  id: "crystal",
  name: "Crystal Voice 💎",
  emoji: "💎",
  desc: "高く抜ける裏声成分に芯がある、きらびやかな声。",
  axes_jp: { register: "裏声成分が多め", power: "パワフル（芯がある）", color: "クリア（明るい）" },
  near: {},
  // 実データ（backend voice_coach.py）。maskArtists=true で名前はDOMに出さず伏せ字表示
  artists: { female: ["宇多田ヒカル"], male: ["藤原聡"] },
};

function ShindanResultCard() {
  return <VoiceTypeBlock vt={SAMPLE_RESULT} score={82} maskArtists />;
}

/** `/lp/shindan` — 診断訴求の流入先。見出し・CTA・遷移先を診断に一本化 */
export function HeroShindan() {
  return (
    <HeroKeyartShell cardLabel="実際の診断結果のイメージ" card={<ShindanResultCard />}>
      <HeroBadge />
      <h1 className="mt-4 text-5xl font-black leading-[1.15] tracking-tight sm:text-6xl lg:text-7xl">
        あなたの声、<br className="hidden sm:block" />
        <Marker tone="dark">何タイプ？</Marker>
      </h1>
      <p className="mt-5 max-w-md text-base text-white/85 sm:text-lg">
        15秒歌うだけ。AIが8タイプで“声診断”。近い歌手も分かります。
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button href="/voice-type" variant="secondary">
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
    <HeroStageShell cardLabel="秒数つきで原因がわかり、直るまで伴走" card={<HeroLessonDemo />}>
      <HeroBadge />
      <h1 className="mt-4 text-4xl font-black leading-[1.18] tracking-tight sm:text-5xl lg:text-6xl">
        その高音、<br />
        <Marker tone="dark">出るようになる。</Marker>
      </h1>
      <p className="mt-5 max-w-md text-base text-white/85 sm:text-lg">
        裏返る・苦しいの原因を突き止めて、ミックスボイス習得まで伴走します。
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button href="/login" variant="secondary">
          無料で始める <span className="text-sm font-normal text-slate-400">30秒</span>
        </Button>
        <span className="text-sm text-white/70">専用マイク不要・クレカ不要</span>
      </div>
    </HeroStageShell>
  );
}
