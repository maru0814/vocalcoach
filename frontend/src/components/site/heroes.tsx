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
