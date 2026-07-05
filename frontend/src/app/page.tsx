import Link from "next/link";
import { SiteHeader } from "@/components/site/SiteHeader";
import { Reveal } from "@/components/site/Reveal";
import { AnimatedDemo } from "@/components/site/AnimatedDemo";
import { CoachAvatar, COACH_NAME } from "@/components/character/Coach";
import { CoachSpotlight } from "@/components/character/CoachSpotlight";
import { StageDecor } from "@/components/site/Stage";
import { SectionHeading, Marker } from "@/components/site/SectionHeading";
import { IconChip, IconName } from "@/components/site/IconChip";
import { ProductSnippet, SnippetMessage } from "@/components/site/ProductSnippet";
import { Button } from "@/components/ui/Button";
import { VoiceTypeArt } from "@/components/voice/VoiceTypeArt";
import { VOICE_TYPE_LIST } from "@/components/voice/voiceTypes";
import { VoiceTypeStats } from "@/components/voice/VoiceTypeStats";

const STATS = [
  { value: "会話型", label: "点数でなく、チャットでフィードバック" },
  { value: "最短1分", label: "録って送れば、すぐFBが届く" },
  { value: "道具ゼロ", label: "専用マイク・機材は不要" },
  { value: "¥0", label: "登録だけで無料で始められる" },
];

const PROBLEMS: Array<{ icon: IconName; text: string }> = [
  { icon: "frown", text: "自分の歌の どこがダメか分からない" },
  { icon: "search", text: "練習法を調べても 自分に合うのか不安で続かない" },
  { icon: "trend-down", text: "練習してるのに 上達した実感がない" },
];

const FEATURES: Array<{
  icon: IconName;
  tag: string;
  title: string;
  desc: string;
  bullets: string[];
  chat: SnippetMessage[]; // 実際の製品と同じ見た目のモック（docs/56 §3-7）
}> = [
  {
    icon: "mic",
    tag: "AI声診断",
    title: "声が、見える化される。",
    desc: "あなたの声をAIが解析して、「この曲で出した音域」「使っている声（地声・ミックス・裏声）」「換声点」「声の共鳴」まで“声診断”。「なんとなく下手」が「サビ後半で息が切れている」みたいに、言葉で分かります。",
    bullets: ["音程の安定・強弱・ビブラートまで解析", "音域・声区・換声点まで“声診断”（推定）", "秒数つきで「どこを」直すか分かる"],
    chat: [
      { from: "sora", text: "1:24の伸ばし、後半でゆれて下がっています。息の支えから整えましょう" },
      { from: "user", text: "たしかにそこ、苦しかったです…！" },
    ],
  },
  {
    icon: "headphones",
    tag: "原曲と聴き比べ",
    title: "原曲と、聴き比べる。",
    desc: "お手本の音源をアップロードすると、音を外していないか（音程の正確さ）とリズムの走り／モタりを原曲と聴き比べて実測。同じ曲を同じキーで歌うほど、ズレがぴたっと分かります。",
    bullets: ["音程の正確さを原曲と照合", "リズムの走り・モタりを秒数で指摘", "原曲なしでも、録音だけでFB"],
    chat: [
      { from: "sora", text: "原曲と比べると、Bメロで半拍はやく入っています。まずは手拍子で合わせてみましょう" },
    ],
  },
  {
    icon: "target",
    tag: "個別メニュー",
    title: "今日の課題と、基礎練。",
    desc: "あなたの弱点に合わせて、今日やるべき基礎練を1つだけ提案。お手本のYouTube動画つきだから、迷わず練習できます。道具はいりません、声と体だけ。",
    bullets: ["弱点に合わせた練習を1つに絞る", "お手本動画つきで真似しやすい", "ドッグブレス等、家でできる練習"],
    chat: [
      { from: "sora", text: "今日の基礎練は1つだけ。ドッグブレス30秒×3、お手本動画つきです" },
      { from: "user", text: "1つならできそう！" },
    ],
  },
  {
    icon: "chart",
    tag: "成長記録",
    title: "上達が、記録に残る。",
    desc: "レッスンごとに自動で保存。録り直すと「前回より伸ばしが安定した」を、ソラ先生が会話で教えてくれます。見えなかった成長が、ちゃんと分かる。",
    bullets: ["レッスンを自動で履歴に保存", "前回より良くなった点を会話で伝える", "良くなった点をソラ先生が褒めてくれる"],
    chat: [
      { from: "sora", text: "前回より伸ばしが安定しました。息の支え、効いてきていますよ" },
    ],
  },
];

const STEPS: Array<{ n: string; icon: IconName; title: string; desc: string }> = [
  { n: "1", icon: "mic", title: "歌って送る", desc: "スマホでそのまま録音、または音源をアップロード。原曲がなくてもOK。" },
  { n: "2", icon: "chat", title: "AIから添削が届く", desc: "良かったところ・直すところ・今日の基礎練が、会話みたいにチャットで届きます。" },
  { n: "3", icon: "headphones", title: "お手本と聴き比べ（任意）", desc: "原曲をアップロードすると、音程の正確さ・リズムをより正確に。" },
];

const FOR_YOU = [
  "カラオケでサビの高音が苦しくなる",
  "音痴かもと思って人前で歌うのが不安",
  "ボイトレ教室に通うほどではないけど上手くなりたい",
  "YouTubeの練習法が自分に合っているか分からない",
  "録音を聞いても自分のどこが悪いか分からない",
];

const VOICES = [
  { emoji: "🧑‍💼", name: "27歳・会社員", quote: "「サビで息が切れてる」って秒数で言われて納得。基礎練を続けたら、前より安定しました。" },
  { emoji: "🧑‍🎤", name: "21歳・学生", quote: "教室は緊張するけど、これなら家で気軽に。動画つきで練習法に迷わないのが助かる。" },
  { emoji: "👩", name: "34歳・主婦", quote: "録り直すたびに「ここ良くなった」って言ってくれるのが楽しい。ちゃんと褒めてくれるので続けられます。" },
];

const FAQ = [
  { q: "本当に無料ですか？", a: "はい。メール登録だけで、すぐに始められます。クレジットカードも不要です。" },
  { q: "マイクや機材は必要ですか？", a: "専用マイクは不要です。お使いのスマホやPCで録音、または手持ちの音源をアップロードするだけでOK。" },
  { q: "音痴でも大丈夫ですか？", a: "むしろそういう方向けです。AIボーカルトレーナーが、やさしく具体的にお伝えします。" },
  { q: "録った歌は誰かに見られますか？", a: "いいえ。あなた専用に安全に保存され、他の人には見えません。" },
  { q: "原曲がなくても使えますか？", a: "はい。録音だけでもフィードバックできます。お手本の音源をアップロードすると、音程の正確さやリズムを原曲と聴き比べて、より正確に見られます。" },
  { q: "プロみたいに正確に判定できますか？", a: "解析には“目安・推定”を含みます。だからこそ点数はつけず、できること・難しいことを正直に、言葉でお伝えします。音程の正確さやリズムは、原曲をアップロードするとより正確に見られます。" },
];

const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "AIボーカルトレーナー ソラ先生",
  alternateName: "ソラ先生",
  applicationCategory: "MultimediaApplication",
  operatingSystem: "Web",
  description:
    "歌の録音を送るだけでAIが音程・リズム・表現を解析し、今日直すところと基礎練メニューを教えるAIボーカルトレーナー。",
  offers: { "@type": "Offer", price: "0", priceCurrency: "JPY" },
};

/** Before → After の変化（点数でなく、ソラ先生の会話で示す） */
function BeforeAfter() {
  return (
    <div className="mx-auto flex max-w-md flex-col gap-3 text-left">
      <div className="flex items-end gap-2">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-rose-50 text-sm">🎤</span>
        <div className="rounded-2xl rounded-bl-md bg-white px-4 py-2.5 text-sm text-slate-600 shadow-card">
          最初の録音：サビの伸ばしが、後半でゆれて下がりがちですね。
        </div>
      </div>
      <div className="text-center text-xs font-bold text-brand-600">基礎練5日 → 録り直し ↓</div>
      <div className="flex items-end gap-2">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-sm">🌤</span>
        <div className="rounded-2xl rounded-bl-md bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-800 shadow-card">
          伸ばしがまっすぐ安定しましたね！息の支えが効いています✨
        </div>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="bg-studio min-h-[100dvh] overflow-hidden pb-24 sm:pb-0">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />

      <SiteHeader />

      <main className="mx-auto max-w-6xl px-5">
        {/* Hero（夜のステージ・開演 docs/55 §7 パイロット） */}
        <section className="bg-stage grain relative mt-4 overflow-hidden rounded-[2.5rem] p-8 text-white shadow-soft sm:p-14">
          <StageDecor />
          <div className="relative z-10 grid items-center gap-10 lg:grid-cols-2">
            <div className="max-w-xl">
              <p className="mb-4 inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-bold">
                <span className="inline-flex"><CoachAvatar size={18} /></span>
                AIボーカルトレーナー {COACH_NAME}が担当
              </p>
              <h1 className="text-4xl font-black leading-[1.12] tracking-tight sm:text-6xl lg:text-7xl">
                その歌、<br className="hidden sm:block" />
                <Marker tone="dark">あと一歩。</Marker>
              </h1>
              <p className="mt-4 text-lg font-bold text-white/95 sm:text-xl">
                録って送るだけ。{COACH_NAME}が、今日直すところを教えます。
              </p>
              <p className="mt-4 max-w-md text-white/85">
                音程・リズム・表現を解析して、あなた専用の基礎練メニューまで
                チャットでお届け。原曲を入れれば、音を外していないかも聴き比べ。
                教室に通わなくても、家でスマホひとつ。
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <Button href="/login" variant="secondary" size="lg">
                  無料で始める <span className="text-sm font-normal text-slate-400">30秒</span>
                </Button>
                <span className="text-sm text-white/80">専用マイク不要・クレカ不要</span>
              </div>
            </div>
            <div className="flex flex-col items-center gap-10">
              <CoachSpotlight size={140} bubble="今日はどこを直す？" />
              <div className="hidden lg:block">
                <AnimatedDemo />
              </div>
            </div>
          </div>
        </section>

        <div className="mt-12 lg:hidden">
          <AnimatedDemo />
        </div>

        {/* 信頼バッジ帯（factualな数字） */}
        <Reveal className="mt-12 sm:mt-16">
          <div className="grid grid-cols-2 gap-3 rounded-3xl bg-white/80 p-5 shadow-card sm:grid-cols-4 sm:p-6">
            {STATS.map((s) => (
              <div key={s.value} className="text-center">
                <div className="text-2xl font-black text-brand-gradient sm:text-3xl">{s.value}</div>
                <div className="mt-1 text-xs text-slate-500">{s.label}</div>
              </div>
            ))}
          </div>
        </Reveal>

        {/* 声タイプ診断 = AIボイトレの入口（図鑑アートと同じ夜ステージの世界） */}
        <Reveal className="mt-20">
          <div className="bg-stage grain relative overflow-hidden rounded-[2rem] p-8 text-center shadow-card sm:p-12">
            <StageDecor />
            <div className="relative z-10">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/90 px-3 py-1 text-xs font-bold text-brand-600">
                <span className="inline-flex"><CoachAvatar size={16} /></span>
                STEP 1 ・ まずはここから
              </span>
              <h2 className="mt-3 text-2xl font-black text-white sm:text-4xl">
                まずは、<span className="bg-gradient-to-r from-brand-200 to-pink-200 bg-clip-text text-transparent">声タイプ診断</span>から。
              </h2>
              <p className="mx-auto mt-3 max-w-xl text-white/80">
                AIボーカルトレーナー{COACH_NAME}は、はじめにあなたの声を8タイプで“見立て”ます。
                15秒ほど歌うだけ。似た声質のアーティストつきで、結果はそのままシェアできます。
              </p>
              <p className="mx-auto mt-2 max-w-xl text-sm font-bold text-brand-200">
                診断のあとは、その声に合った発声レッスンへ。だから“いまの自分”から始められます。
              </p>
              <div className="mx-auto mt-8 grid max-w-2xl grid-cols-4 gap-2.5 sm:gap-3">
                {VOICE_TYPE_LIST.map((t) => (
                  <div key={t.id} className="relative aspect-square overflow-hidden rounded-2xl shadow-soft ring-1 ring-white/15 transition hover:-translate-y-0.5 hover:ring-white/40">
                    <VoiceTypeArt id={t.id} fallbackMascotSize={42} className="h-full w-full" />
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/55 to-transparent px-1 pb-1 pt-3 text-center">
                      <span className="text-[10px] font-bold text-white drop-shadow">{t.name}</span>
                    </div>
                  </div>
                ))}
              </div>
              <Link
                href="/voice-type"
                className="mt-8 inline-flex items-center gap-2 rounded-full bg-brand-gradient px-7 py-3.5 font-bold text-white shadow-soft transition hover:scale-[1.02] hover:shadow-glow-neon active:scale-95"
              >
                無料登録して、声タイプ診断 →
              </Link>
              <p className="mt-3 text-xs text-white/50">※ 診断・発声レッスンとも、無料登録（30秒）で使えます</p>
              <VoiceTypeStats className="mt-3" tone="dark" />
            </div>
          </div>
        </Reveal>

        {/* 課題提起 */}
        <Reveal className="mt-20 text-center">
          <SectionHeading eyebrow="PROBLEM" title={<>こんな悩み、<Marker>ありませんか？</Marker></>} />
          <div className="mt-7 grid gap-4 sm:grid-cols-3">
            {PROBLEMS.map((p) => (
              <div key={p.text} className="rounded-2xl bg-white/90 p-6 shadow-card transition hover:-translate-y-0.5 hover:shadow-card-2">
                <IconChip icon={p.icon} size={48} />
                <p className="mt-3 text-sm font-medium text-slate-600">{p.text}</p>
              </div>
            ))}
          </div>
        </Reveal>

        {/* ソリューション */}
        <Reveal className="mt-20">
          <div className="rounded-[2rem] bg-white/80 p-8 text-center shadow-card sm:p-12">
            <p className="text-sm font-bold tracking-wide text-brand-600">SOLUTION</p>
            <h2 className="mt-2 text-2xl font-black text-slate-800 sm:text-4xl">
              ひとりの練習に、<span className="text-brand-gradient">AIの耳</span>を。
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-slate-600">
              AIボーカルトレーナーのソラ先生が、あなたの録音を解析して
              「良かった点 → 直すところ → 今日の基礎練」までチャットで伴走します。
            </p>
            <p className="mx-auto mt-3 max-w-2xl text-sm font-medium text-brand-600">
              しかも、点数はつけません。友だちのコーチみたいに、できる・難しいを会話で正直にお伝えします。
            </p>
          </div>
        </Reveal>

        {/* 使い方 3ステップ */}
        <Reveal className="mt-20">
          <SectionHeading eyebrow="HOW IT WORKS" title={<>使い方は、<Marker>3ステップ</Marker></>} />
          <div className="mt-7 grid gap-4 sm:grid-cols-3">
            {STEPS.map((s, i) => (
              <Reveal key={s.n} delay={i * 120}>
                <div className="h-full rounded-2xl bg-white/90 p-6 shadow-card transition hover:-translate-y-0.5 hover:shadow-card-2">
                  <div className="flex items-center gap-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-gradient text-sm font-bold text-white">
                      {s.n}
                    </span>
                    <IconChip icon={s.icon} size={40} />
                  </div>
                  <div className="mt-3 font-bold text-slate-800">{s.title}</div>
                  <div className="mt-1 text-sm text-slate-500">{s.desc}</div>
                </div>
              </Reveal>
            ))}
          </div>
        </Reveal>

        {/* 機能紹介（ジグザグ・パネルは実写でなくブランドの夜ステージ） */}
        <section className="mt-24 space-y-16">
          <SectionHeading eyebrow="FEATURES" title={<>登録すると、<Marker>できること</Marker></>} />
          {FEATURES.map((f, i) => (
            <Reveal key={f.title}>
              <div className={`grid items-center gap-8 lg:grid-cols-2 ${i % 2 === 1 ? "lg:[&>div:first-child]:order-2" : ""}`}>
                <div className="bg-stage grain relative flex items-center justify-center overflow-hidden rounded-[2rem] p-6 shadow-card sm:p-10">
                  <StageDecor notes={false} />
                  <ProductSnippet messages={f.chat} className="relative z-10 w-full max-w-sm" />
                  <span className="absolute left-4 top-4 z-10 rounded-full bg-white/90 px-3 py-1 text-xs font-bold text-brand-600">
                    {f.tag}
                  </span>
                </div>
                <div>
                  <IconChip icon={f.icon} size={48} />
                  <h3 className="mt-4 text-2xl font-black text-slate-800">{f.title}</h3>
                  <p className="mt-3 text-slate-600">{f.desc}</p>
                  <ul className="mt-4 space-y-2">
                    {f.bullets.map((b) => (
                      <li key={b} className="flex items-center gap-2 text-sm text-slate-600">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-xs text-emerald-600">✓</span>
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </Reveal>
          ))}
        </section>

        {/* Before → After */}
        <Reveal className="mt-24">
          <div className="overflow-hidden rounded-[2rem] bg-gradient-to-br from-brand-50 to-pink-50 p-8 text-center shadow-card sm:p-12">
            <p className="text-sm font-bold tracking-wide text-brand-600">BEFORE → AFTER</p>
            <h2 className="mt-2 text-2xl font-black text-slate-800 sm:text-3xl">
              録り直すたび、変化が分かる。
            </h2>
            <p className="mx-auto mt-3 max-w-md text-sm text-slate-600">
              課題に合った基礎練をこなして再録音すると、ソラ先生が「ここが良くなった」と会話で教えてくれます。
            </p>
            <div className="mt-8">
              <BeforeAfter />
            </div>
            <p className="mt-6 text-xs text-slate-400">※ 体験イメージです。</p>
          </div>
        </Reveal>

        {/* こんな人におすすめ */}
        <Reveal className="mt-24">
          <div className="grid items-center gap-8 rounded-[2rem] bg-white/85 p-8 shadow-card sm:p-12 lg:grid-cols-2">
            <div>
              <h2 className="text-2xl font-black text-slate-800 sm:text-3xl">
                こんな人に、<span className="text-brand-gradient">ぴったり</span>。
              </h2>
              <p className="mt-3 text-sm text-slate-500">ひとつでも当てはまったら、まず1曲ためしてみてください。</p>
            </div>
            <ul className="space-y-3">
              {FOR_YOU.map((t) => (
                <li key={t} className="flex items-start gap-3 rounded-2xl bg-brand-50/60 px-4 py-3 text-sm font-medium text-slate-700">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-xs text-white">✓</span>
                  {t}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>

        {/* 利用者の声 */}
        <Reveal className="mt-24">
          <SectionHeading eyebrow="VOICES" title="使った人の声" />
          <div className="mt-7 grid gap-4 sm:grid-cols-3">
            {VOICES.map((v, i) => (
              <Reveal key={v.name} delay={i * 120}>
                <div className="h-full rounded-2xl bg-white/90 p-6 shadow-card transition hover:-translate-y-0.5 hover:shadow-card-2">
                  <div className="text-amber-400">★★★★★</div>
                  <p className="mt-3 text-sm text-slate-700">{v.quote}</p>
                  <div className="mt-4 flex items-center gap-2">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 text-lg">{v.emoji}</span>
                    <span className="text-xs font-bold text-slate-500">{v.name}</span>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
          <p className="mt-4 text-center text-xs text-slate-400">※ 体験イメージです。</p>
        </Reveal>

        {/* 料金 */}
        <Reveal className="mt-24">
          <div className="mx-auto max-w-md overflow-hidden rounded-[2rem] bg-white/90 p-8 text-center shadow-card">
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">いまなら</span>
            <h2 className="mt-3 text-2xl font-black text-slate-800">ずっと無料で始められる</h2>
            <div className="mt-4 text-5xl font-black text-brand-gradient">¥0</div>
            <ul className="mx-auto mt-6 max-w-xs space-y-2 text-left text-sm text-slate-600">
              {["登録はメールだけ・30秒", "クレジットカード不要", "専用マイク・機材いらず", "レッスン履歴も保存"].map((t) => (
                <li key={t} className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-xs text-emerald-600">✓</span>
                  {t}
                </li>
              ))}
            </ul>
            <Link href="/login" className="mt-7 inline-flex w-full items-center justify-center rounded-full bg-brand-gradient px-6 py-3.5 font-bold text-white shadow-soft transition active:scale-95">
              無料で始める →
            </Link>
          </div>
        </Reveal>

        {/* FAQ（アコーディオン） */}
        <Reveal className="mt-24">
          <SectionHeading eyebrow="FAQ" title="よくある質問" />
          <div className="mx-auto mt-7 max-w-2xl space-y-3">
            {FAQ.map((f) => (
              <details key={f.q} className="group rounded-2xl bg-white/90 px-5 py-4 shadow-card">
                <summary className="flex cursor-pointer list-none items-center justify-between font-bold text-slate-800">
                  <span>Q. {f.q}</span>
                  <span className="text-brand-400 transition group-open:rotate-45">＋</span>
                </summary>
                <p className="mt-3 text-sm text-slate-600">A. {f.a}</p>
              </details>
            ))}
          </div>
        </Reveal>

        {/* 最後のCTA（夜のステージ・終演＝開演と首尾を揃える） */}
        <Reveal className="mt-24">
          <div className="bg-stage grain relative overflow-hidden rounded-[2.5rem] p-10 text-center text-white shadow-soft sm:p-16">
            <StageDecor />
            <h2 className="relative z-10 text-3xl font-black sm:text-4xl">
              上達は、<Marker tone="dark">今日の一歩</Marker>から。
            </h2>
            <p className="relative z-10 mt-3 text-white/90">まずは1曲、歌って送ってみましょう。AIボーカルトレーナーが待っています。</p>
            <Link href="/login" className="relative z-10 mt-8 inline-flex items-center gap-2 rounded-full bg-white px-8 py-4 font-bold text-brand-700 shadow-soft transition hover:scale-[1.02] hover:shadow-glow-neon active:scale-95">
              無料でレッスンを始める →
            </Link>
            <p className="relative z-10 mt-3 text-xs text-white/70">専用マイク不要・登録30秒・クレジットカード不要</p>
          </div>
        </Reveal>

        {/* フッター */}
        <footer className="mt-16 border-t border-slate-200 py-10 text-center">
          <p className="text-sm font-bold text-slate-600">AIボーカルトレーナー ソラ先生</p>
          <p className="mt-1 text-xs text-slate-400">歌をAIが解析・添削するボイトレアプリ</p>
          <div className="mt-4 flex justify-center gap-5 text-xs text-slate-400">
            <Link href="/login" className="hover:text-brand-600">ログイン</Link>
            <Link href="/login" className="hover:text-brand-600">無料で始める</Link>
          </div>
          <p className="mt-6 text-[11px] text-slate-300">© AIボーカルトレーナー ソラ先生</p>
        </footer>
      </main>

      {/* スマホ用 追従CTAバー */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-white/40 bg-white/85 p-3 backdrop-blur sm:hidden">
        <Link href="/login" className="flex flex-col items-center rounded-2xl bg-brand-gradient py-3 font-bold text-white shadow-soft">
          無料でレッスンを始める →
          <span className="text-[11px] font-normal text-white/80">専用マイク不要・登録30秒・無料</span>
        </Link>
      </div>
    </div>
  );
}
