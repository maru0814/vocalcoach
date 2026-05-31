import Link from "next/link";
import { SiteHeader } from "@/components/site/SiteHeader";
import { Reveal } from "@/components/site/Reveal";
import { AnimatedDemo } from "@/components/site/AnimatedDemo";

const STATS = [
  { value: "4軸", label: "音程・リズム・表現・総合をAI解析" },
  { value: "最短1分", label: "録って送れば、すぐFBが届く" },
  { value: "道具ゼロ", label: "専用マイク・機材は不要" },
  { value: "¥0", label: "登録だけで無料で始められる" },
];

const PROBLEMS = [
  { icon: "😕", text: "自分の歌の どこがダメか分からない" },
  { icon: "🔍", text: "練習法を調べても 自分に合うのか不安で続かない" },
  { icon: "📉", text: "練習してるのに 上達した実感がない" },
];

const FEATURES = [
  {
    icon: "🎙",
    tag: "AI解析",
    title: "声が、見える化される。",
    desc: "音程・リズム・表現をAIが解析して数値とグラフに。「なんとなく下手」が「サビ後半で息が切れている」に変わります。原因が分かれば、直し方も分かる。",
    bullets: ["音程の安定度を数値で表示", "声の強弱・ビブラートも可視化", "秒数つきで「どこを」直すか分かる"],
    photo: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=1000&q=80&auto=format&fit=crop",
    alt: "AIが歌声を解析しているイメージ",
  },
  {
    icon: "🎯",
    tag: "個別メニュー",
    title: "今日の課題と、基礎練。",
    desc: "あなたの弱点に合わせて、今日やるべき基礎練を1つだけ提案。お手本のYouTube動画つきだから、迷わず練習できます。道具はいりません、声と体だけ。",
    bullets: ["弱点に合わせた練習を1つに絞る", "お手本動画つきで真似しやすい", "ドッグブレス等、家でできる練習"],
    photo: "https://images.unsplash.com/photo-1454922915609-78549ad709bb?w=1000&q=80&auto=format&fit=crop",
    alt: "自宅でボイストレーニングをする人のイメージ",
  },
  {
    icon: "📈",
    tag: "成長記録",
    title: "上達が、記録に残る。",
    desc: "レッスンごとに自動で保存。録り直すと「前回よりリズムが良くなった」を数値で実感できます。見えなかった成長が、ちゃんと見える。",
    bullets: ["レッスンを自動で履歴に保存", "前回との差分を数値で表示", "良くなった点をAIが褒めてくれる"],
    photo: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=1000&q=80&auto=format&fit=crop",
    alt: "上達の記録が積み上がるイメージ",
  },
];

const STEPS = [
  { n: "1", icon: "🎵", title: "曲と区間を伝える", desc: "歌いたい曲のURLと、見てほしいところ（サビなど）を入力。" },
  { n: "2", icon: "📱", title: "歌って送る", desc: "スマホでそのまま録音、または音源をアップロード。" },
  { n: "3", icon: "💬", title: "AIから添削が届く", desc: "スコア・課題・基礎練がチャットで届きます。" },
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
  { emoji: "👩", name: "34歳・主婦", quote: "録り直すたびにスコアが上がるのが楽しい。ちゃんと褒めてくれるので続けられます。" },
];

const FAQ = [
  { q: "本当に無料ですか？", a: "はい。メール登録だけで、すぐに始められます。クレジットカードも不要です。" },
  { q: "マイクや機材は必要ですか？", a: "専用マイクは不要です。お使いのスマホやPCで録音、または手持ちの音源をアップロードするだけでOK。" },
  { q: "音痴でも大丈夫ですか？", a: "むしろそういう方向けです。AIボーカルトレーナーが、やさしく具体的にお伝えします。" },
  { q: "録った歌は誰かに見られますか？", a: "いいえ。あなた専用に安全に保存され、他の人には見えません。" },
  { q: "どんな曲でもいいですか？", a: "原曲のYouTube URLがあればOK。見てほしい区間（サビなど）を指定すると、より具体的なFBになります。" },
];

const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "こえのアトリエ",
  alternateName: "こえのアトリエ AIボーカルトレーナー",
  applicationCategory: "MultimediaApplication",
  operatingSystem: "Web",
  description:
    "歌の録音を送るだけでAIが音程・リズム・表現を解析し、今日直すところと基礎練メニューを教えるAIボーカルトレーナー。",
  offers: { "@type": "Offer", price: "0", priceCurrency: "JPY" },
};

/** Before → After の声の変化ビジュアル */
function BeforeAfter() {
  const Gauge = ({ v, color }: { v: number; color: string }) => (
    <div className="relative flex h-20 w-20 items-center justify-center">
      <svg viewBox="0 0 80 80" className="h-20 w-20 -rotate-90">
        <circle cx="40" cy="40" r="34" fill="none" stroke="#eef2f7" strokeWidth="8" />
        <circle cx="40" cy="40" r="34" fill="none" stroke={color} strokeWidth="8" strokeLinecap="round" strokeDasharray={`${(v / 100) * 214} 214`} />
      </svg>
      <span className="absolute text-xl font-black text-slate-800">{v}</span>
    </div>
  );
  return (
    <div className="flex items-center justify-center gap-4 sm:gap-8">
      <div className="text-center">
        <Gauge v={55} color="#f43f5e" />
        <div className="mt-2 text-xs font-bold text-slate-400">最初の録音</div>
      </div>
      <div className="text-center">
        <div className="text-3xl">→</div>
        <div className="text-xs font-bold text-brand-600">基礎練5日</div>
      </div>
      <div className="text-center">
        <Gauge v={78} color="#10b981" />
        <div className="mt-2 text-xs font-bold text-emerald-600">録り直し</div>
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
        {/* Hero */}
        <section className="relative mt-4 overflow-hidden rounded-[2.5rem] bg-brand-gradient p-8 text-white shadow-soft sm:p-14">
          <div className="absolute -right-16 -top-16 h-72 w-72 rounded-full bg-white/15 blur-3xl" />
          <div className="absolute -bottom-20 left-1/4 h-80 w-80 rounded-full bg-pink-300/25 blur-3xl" />
          <div className="relative z-10 grid items-center gap-10 lg:grid-cols-2">
            <div className="max-w-xl">
              <p className="mb-4 inline-flex items-center gap-1 rounded-full bg-white/20 px-3 py-1 text-xs font-bold">
                🎤 AIボーカルトレーナー
              </p>
              <h1 className="text-4xl font-black leading-[1.12] sm:text-6xl">
                その歌、<br className="hidden sm:block" />あと一歩。
              </h1>
              <p className="mt-4 text-lg font-bold text-white/95 sm:text-xl">
                録って送るだけ。AIが、今日直すところを教えます。
              </p>
              <p className="mt-4 max-w-md text-white/85">
                音程・リズム・表現を解析して、あなた専用の基礎練メニューまで
                チャットでお届け。教室に通わなくても、家でスマホひとつ。
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 rounded-full bg-white px-7 py-3.5 font-bold text-brand-700 shadow-soft transition hover:scale-[1.02] active:scale-95"
                >
                  無料で始める <span className="text-sm font-normal text-slate-400">30秒</span>
                </Link>
                <span className="text-sm text-white/80">★ 専用マイク不要・クレカ不要</span>
              </div>
            </div>
            <div className="hidden lg:block">
              <AnimatedDemo />
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

        {/* 課題提起 */}
        <Reveal className="mt-20 text-center">
          <h2 className="text-2xl font-bold text-slate-800 sm:text-3xl">こんな悩み、ありませんか？</h2>
          <div className="mt-7 grid gap-4 sm:grid-cols-3">
            {PROBLEMS.map((p) => (
              <div key={p.text} className="rounded-2xl bg-white/90 p-6 shadow-card">
                <div className="text-4xl">{p.icon}</div>
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
              こえのアトリエは、あなたの録音をAIボーカルトレーナーが解析して
              「良かった点 → 直すところ → 今日の基礎練」までチャットで伴走します。
            </p>
          </div>
        </Reveal>

        {/* 使い方 3ステップ */}
        <Reveal className="mt-20">
          <h2 className="text-center text-2xl font-bold text-slate-800 sm:text-3xl">使い方は、3ステップ</h2>
          <div className="mt-7 grid gap-4 sm:grid-cols-3">
            {STEPS.map((s, i) => (
              <Reveal key={s.n} delay={i * 120}>
                <div className="h-full rounded-2xl bg-white/90 p-6 shadow-card">
                  <div className="flex items-center gap-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-gradient text-sm font-bold text-white">
                      {s.n}
                    </span>
                    <span className="text-2xl">{s.icon}</span>
                  </div>
                  <div className="mt-3 font-bold text-slate-800">{s.title}</div>
                  <div className="mt-1 text-sm text-slate-500">{s.desc}</div>
                </div>
              </Reveal>
            ))}
          </div>
        </Reveal>

        {/* 機能紹介（ジグザグ） */}
        <section className="mt-24 space-y-16">
          <h2 className="text-center text-2xl font-bold text-slate-800 sm:text-3xl">
            登録すると、できること
          </h2>
          {FEATURES.map((f, i) => (
            <Reveal key={f.title}>
              <div className={`grid items-center gap-8 lg:grid-cols-2 ${i % 2 === 1 ? "lg:[&>div:first-child]:order-2" : ""}`}>
                <div
                  className="relative h-60 overflow-hidden rounded-3xl bg-brand-gradient bg-cover bg-center shadow-card sm:h-72"
                  style={{ backgroundImage: `url(${f.photo}), linear-gradient(135deg,#7c3aed,#ec4899)` }}
                  role="img"
                  aria-label={f.alt}
                >
                  <span className="absolute left-4 top-4 rounded-full bg-white/90 px-3 py-1 text-xs font-bold text-brand-600">
                    {f.tag}
                  </span>
                </div>
                <div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-gradient text-2xl shadow-soft">
                    {f.icon}
                  </div>
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
              録り直すたび、数字で伸びる。
            </h2>
            <p className="mx-auto mt-3 max-w-md text-sm text-slate-600">
              課題に合った基礎練をこなして再録音すると、スコアの変化がひと目で分かります。
            </p>
            <div className="mt-8">
              <BeforeAfter />
            </div>
            <p className="mt-6 text-xs text-slate-400">※ スコアは「リズム」の一例です。実際の数値は歌唱により異なります。</p>
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
          <h2 className="text-center text-2xl font-bold text-slate-800 sm:text-3xl">使った人の声</h2>
          <div className="mt-7 grid gap-4 sm:grid-cols-3">
            {VOICES.map((v, i) => (
              <Reveal key={v.name} delay={i * 120}>
                <div className="h-full rounded-2xl bg-white/90 p-6 shadow-card">
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
          <h2 className="text-center text-2xl font-bold text-slate-800 sm:text-3xl">よくある質問</h2>
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

        {/* 最後のCTA */}
        <Reveal className="mt-24">
          <div className="relative overflow-hidden rounded-[2.5rem] bg-brand-gradient p-10 text-center text-white shadow-soft sm:p-16">
            <div className="absolute -right-10 -top-10 h-48 w-48 rounded-full bg-white/15 blur-2xl" />
            <h2 className="relative z-10 text-3xl font-black sm:text-4xl">上達は、今日の一歩から。</h2>
            <p className="relative z-10 mt-3 text-white/90">まずは1曲、歌って送ってみましょう。AIボーカルトレーナーが待っています。</p>
            <Link href="/login" className="relative z-10 mt-8 inline-flex items-center gap-2 rounded-full bg-white px-8 py-4 font-bold text-brand-700 shadow-soft transition hover:scale-[1.02] active:scale-95">
              無料でレッスンを始める →
            </Link>
            <p className="relative z-10 mt-3 text-xs text-white/70">専用マイク不要・登録30秒・クレジットカード不要</p>
          </div>
        </Reveal>

        {/* フッター */}
        <footer className="mt-16 border-t border-slate-200 py-10 text-center">
          <p className="text-sm font-bold text-slate-600">こえのアトリエ</p>
          <p className="mt-1 text-xs text-slate-400">AIボーカルトレーナー｜歌をAIが解析・添削するボイトレアプリ</p>
          <div className="mt-4 flex justify-center gap-5 text-xs text-slate-400">
            <Link href="/login" className="hover:text-brand-600">ログイン</Link>
            <Link href="/login" className="hover:text-brand-600">無料で始める</Link>
          </div>
          <p className="mt-6 text-[11px] text-slate-300">© こえのアトリエ</p>
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
