import { ReactNode } from "react";
import { CoachAvatar, COACH_NAME } from "@/components/character/Coach";
import { StageDecor } from "@/components/site/Stage";
import { Marker } from "@/components/site/SectionHeading";
import { ProductSnippet } from "@/components/site/ProductSnippet";
import { Button } from "@/components/ui/Button";
import { VoiceTypeArt } from "@/components/voice/VoiceTypeArt";
import { VOICE_TYPE_LIST } from "@/components/voice/voiceTypes";

/**
 * LPヒーローの候補3案（マーケFB対応: 文字量を 見出し＋1行＋CTA に削減）。
 * /?hero=a|b|c で切り替えて比較する。方向確定後は採用案だけ残す。
 */

function HeroShell({ children }: { children: ReactNode }) {
  return (
    <section className="bg-stage grain relative mt-4 overflow-hidden rounded-[2.5rem] p-8 text-white shadow-soft sm:p-14">
      <StageDecor />
      <div className="relative z-10 grid items-center gap-10 lg:grid-cols-2">{children}</div>
    </section>
  );
}

function HeroBadge() {
  return (
    <p className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-bold">
      <span className="inline-flex"><CoachAvatar size={16} /></span>
      AIボーカルトレーナー {COACH_NAME}
    </p>
  );
}

function HeroMicrocopy() {
  return <span className="text-sm text-white/70">専用マイク不要・クレカ不要</span>;
}

/** A. 変化訴求 — コーチングの約束で押す。ビジュアルは Before→After の実チャット */
export function HeroA() {
  return (
    <HeroShell>
      <div className="max-w-xl">
        <HeroBadge />
        <h1 className="mt-4 text-5xl font-black leading-[1.15] tracking-tight sm:text-6xl lg:text-7xl">
          歌は、<Marker tone="dark">直せる。</Marker>
        </h1>
        <p className="mt-5 text-base text-white/85 sm:text-lg">
          録って送るだけ。どこを・どう直すかを、AIが言葉にします。
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Button href="/login" variant="secondary" size="lg">
            無料で始める <span className="text-sm font-normal text-slate-400">30秒</span>
          </Button>
          <HeroMicrocopy />
        </div>
      </div>
      <div className="mx-auto w-full max-w-sm">
        <p className="mb-3 text-center text-xs font-bold tracking-[0.2em] text-brand-200">BEFORE → AFTER</p>
        <ProductSnippet
          messages={[
            { from: "sora", text: "1:24の伸ばし、後半でゆれて下がっています。息の支えから直しましょう" },
            { from: "user", text: "基礎練5日やって、録り直しました！" },
            { from: "sora", text: "伸ばしがまっすぐ安定しましたね。息の支え、効いています👏" },
          ]}
        />
      </div>
    </HeroShell>
  );
}

/** B. 診断フック — 15秒の遊びで引き込む。8タイプアートがヒーローの主役 */
export function HeroB() {
  return (
    <HeroShell>
      <div className="max-w-xl">
        <HeroBadge />
        <h1 className="mt-4 text-5xl font-black leading-[1.15] tracking-tight sm:text-6xl lg:text-7xl">
          あなたの声、<br className="hidden sm:block" />
          <Marker tone="dark">何タイプ？</Marker>
        </h1>
        <p className="mt-5 text-base text-white/85 sm:text-lg">
          15秒歌うだけ、AIが8タイプで“声診断”。そのまま無料レッスンへ。
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Button href="/voice-type" variant="secondary" size="lg">
            無料で声タイプ診断 <span className="text-sm font-normal text-slate-400">15秒</span>
          </Button>
          <HeroMicrocopy />
        </div>
      </div>
      <div className="mx-auto grid w-full max-w-lg grid-cols-4 gap-2.5 sm:gap-3">
        {VOICE_TYPE_LIST.map((t, i) => (
          <div
            key={t.id}
            className={`relative aspect-square overflow-hidden rounded-2xl shadow-card ring-1 ring-white/20 transition hover:-translate-y-1 hover:ring-white/50 ${
              i % 2 === 0 ? "-rotate-2 translate-y-2" : "rotate-2"
            }`}
          >
            <VoiceTypeArt id={t.id} fallbackMascotSize={40} className="h-full w-full" />
          </div>
        ))}
      </div>
    </HeroShell>
  );
}

/**
 * キーアート・ポスターウォール（流入別LP用）。
 * 「地味・個人開発感」FBの根治策: 8枚のタイプアートをサムネイルでなく
 * 全面キーアートとして使う（Netflix/Spotify のポスターウォール型）。
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

function HeroKeyartShell({ children, card }: { children: ReactNode; card?: ReactNode }) {
  return (
    <section className="bg-stage grain relative mt-4 overflow-hidden rounded-[2.5rem] text-white shadow-soft">
      <PosterWall />
      <StageDecor notes={false} />
      <div className="relative z-10 flex min-h-[480px] flex-col justify-center p-8 sm:p-14 lg:min-h-[620px] lg:max-w-[56%]">
        {children}
      </div>
      {card && (
        <div className="relative z-10 px-8 pb-8 sm:px-14 lg:absolute lg:bottom-12 lg:right-14 lg:w-96 lg:-rotate-2 lg:p-0">
          <div className="mx-auto max-w-sm lg:max-w-none">{card}</div>
        </div>
      )}
      {/* モバイル用ミニウォール（デスクトップはPosterWallが担当） */}
      <div className="relative z-10 grid grid-cols-4 gap-2 px-8 pb-8 lg:hidden" aria-hidden>
        {VOICE_TYPE_LIST.slice(0, 4).map((t) => (
          <div key={t.id} className="aspect-square overflow-hidden rounded-xl ring-1 ring-white/15">
            <VoiceTypeArt id={t.id} className="h-full w-full" />
          </div>
        ))}
      </div>
    </section>
  );
}

/** 流入別LP: 診断訴求（/lp/shindan）— A案コピー＋診断CTA＋キーアートウォール */
export function HeroShindan() {
  return (
    <HeroKeyartShell
      card={
        <div>
          <p className="mb-2 text-center text-xs font-bold tracking-[0.2em] text-brand-200">BEFORE → AFTER</p>
          <ProductSnippet
            messages={[
              { from: "sora", text: "1:24の伸ばし、後半でゆれて下がっています。息の支えから直しましょう" },
              { from: "sora", text: "（5日後）伸ばしがまっすぐ安定しましたね。息の支え、効いています👏" },
            ]}
          />
        </div>
      }
    >
      <HeroBadge />
      <h1 className="mt-4 text-5xl font-black leading-[1.15] tracking-tight sm:text-6xl lg:text-7xl">
        歌は、<Marker tone="dark">直せる。</Marker>
      </h1>
      <p className="mt-5 max-w-md text-base text-white/85 sm:text-lg">
        まずは15秒の声タイプ診断から。どこを・どう直すかまで、AIが言葉にします。
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button href="/voice-type" variant="secondary" size="lg">
          無料で声タイプ診断 <span className="text-sm font-normal text-slate-400">15秒</span>
        </Button>
        <HeroMicrocopy />
      </div>
    </HeroKeyartShell>
  );
}

/** 流入別LP: ボイトレ訴求（/lp/voitore）— C案コピー＋キーアートウォール */
export function HeroVoitore() {
  return (
    <HeroKeyartShell
      card={
        <div>
          <p className="mb-2 text-center text-xs font-bold tracking-[0.2em] text-brand-200">秒数つきで、原因がわかる</p>
          <ProductSnippet
            messages={[
              { from: "user", text: "サビの高音がきついです…（録音を送信）" },
              { from: "sora", text: "2:10、地声のまま押し上げて裏返りかけています。“ネイネイ”で軽く当てる練習から始めましょう" },
            ]}
          />
        </div>
      }
    >
      <HeroBadge />
      <h1 className="mt-4 text-4xl font-black leading-[1.18] tracking-tight sm:text-5xl lg:text-6xl">
        その高音、<br />
        <Marker tone="dark">出るようになる。</Marker>
      </h1>
      <p className="mt-5 max-w-md text-base text-white/85 sm:text-lg">
        サビで苦しい・裏返る。原因と直し方を、AIが言葉にします。
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button href="/login" variant="secondary" size="lg">
          無料で始める <span className="text-sm font-normal text-slate-400">30秒</span>
        </Button>
        <HeroMicrocopy />
      </div>
    </HeroKeyartShell>
  );
}

/** C. 悩み直撃 — カラオケ高音の悩みに絞って刺す */
export function HeroC() {
  return (
    <HeroShell>
      <div className="max-w-xl">
        <HeroBadge />
        <h1 className="mt-4 text-5xl font-black leading-[1.15] tracking-tight sm:text-6xl lg:text-7xl">
          その高音、<br className="hidden sm:block" />
          <Marker tone="dark">出るようになる。</Marker>
        </h1>
        <p className="mt-5 text-base text-white/85 sm:text-lg">
          サビで苦しい・裏返る。原因と直し方を、AIが言葉にします。
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Button href="/login" variant="secondary" size="lg">
            無料で始める <span className="text-sm font-normal text-slate-400">30秒</span>
          </Button>
          <HeroMicrocopy />
        </div>
      </div>
      <div className="mx-auto w-full max-w-sm">
        <p className="mb-3 text-center text-xs font-bold tracking-[0.2em] text-brand-200">秒数つきで、原因がわかる</p>
        <ProductSnippet
          messages={[
            { from: "user", text: "サビの高音がきついです…（録音を送信）" },
            { from: "sora", text: "2:10、地声のまま押し上げて裏返りかけています。“ネイネイ”で軽く当てる練習から始めましょう" },
          ]}
        />
      </div>
    </HeroShell>
  );
}
