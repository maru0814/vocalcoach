import Link from "next/link";
import { BrandWordmark } from "@/components/brand/Brand";

const PROBLEMS = [
  { icon: "😕", text: "自分の歌の どこがダメか分からない" },
  { icon: "🔍", text: "練習法を調べても 自分に合うのか不安で続かない" },
  { icon: "📉", text: "練習してるのに 上達した実感がない" },
];

const FEATURES = [
  {
    icon: "🎙",
    title: "声が見える化される",
    desc: "音程・リズム・表現をAIが解析して数値とグラフに。「なんとなく下手」が「サビ後半で息が切れている」に変わります。",
    tag: "AI解析",
    photo:
      "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=900&q=80&auto=format&fit=crop",
    alt: "AIが歌声を解析しているイメージ",
  },
  {
    icon: "🎯",
    title: "今日の課題と基礎練がもらえる",
    desc: "あなたの弱点に合わせた練習メニューと、お手本のYouTube動画つき。道具はいりません、声と体だけ。",
    tag: "個別メニュー",
    photo:
      "https://images.unsplash.com/photo-1454922915609-78549ad709bb?w=900&q=80&auto=format&fit=crop",
    alt: "自宅でボイストレーニングをする人のイメージ",
  },
  {
    icon: "📈",
    title: "上達が記録に残る",
    desc: "レッスンごとに保存。録り直すと「前回より◯◯が良くなった」を数値で実感できます。",
    tag: "成長記録",
    photo:
      "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=900&q=80&auto=format&fit=crop",
    alt: "上達の記録が積み上がるイメージ",
  },
];

const STEPS = [
  { n: "1", icon: "🎵", title: "曲と区間を伝える", desc: "歌いたい曲のURLと、見てほしいところ（サビなど）を入力。" },
  { n: "2", icon: "📱", title: "歌って送る", desc: "スマホでそのまま録音、または音源をアップロード。" },
  { n: "3", icon: "💬", title: "AIから添削が届く", desc: "スコア・課題・基礎練がチャットで届きます。" },
];

const FAQ = [
  { q: "本当に無料ですか？", a: "はい。メール登録だけで、すぐに始められます。" },
  { q: "マイクや機材は必要ですか？", a: "専用マイクは不要です。お使いのスマホやPCで録音、または手持ちの音源をアップロードするだけでOK。" },
  { q: "音痴でも大丈夫？", a: "むしろそういう方向けです。AIボーカルトレーナーが、やさしく具体的にお伝えします。" },
  { q: "録った歌は誰かに見られる？", a: "いいえ。あなた専用に安全に保存され、他の人には見えません。" },
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

/** 製品の雰囲気を伝えるミニ・チャットモックアップ（実画面の再現） */
function ProductMockup() {
  return (
    <div className="relative mx-auto w-full max-w-[300px]">
      <div className="rounded-[2rem] border-4 border-white/70 bg-white/95 p-3 shadow-2xl">
        <div className="mb-2 flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-gradient text-xs text-white">🎤</span>
          <div className="leading-none">
            <div className="text-xs font-bold text-slate-700">トレーナー</div>
            <div className="text-[9px] text-brand-600">オンライン</div>
          </div>
        </div>
        <div className="space-y-2">
          <div className="max-w-[80%] rounded-2xl rounded-bl-md bg-slate-100 px-3 py-2 text-[11px] text-slate-700">
            8〜13秒で声が小さくなっています。息の支えを作りましょう🎯
          </div>
          <div className="rounded-xl bg-white p-2.5 shadow ring-1 ring-slate-100">
            <div className="flex items-center gap-3">
              <div className="relative flex h-14 w-14 items-center justify-center">
                <svg viewBox="0 0 80 80" className="h-14 w-14 -rotate-90">
                  <circle cx="40" cy="40" r="34" fill="none" stroke="#eef2f7" strokeWidth="8" />
                  <circle cx="40" cy="40" r="34" fill="none" stroke="#f59e0b" strokeWidth="8" strokeLinecap="round" strokeDasharray="167 214" />
                </svg>
                <span className="absolute text-sm font-black text-slate-800">77</span>
              </div>
              <div className="flex-1 space-y-1">
                {[["音程", 85, "#10b981"], ["リズム", 55, "#f43f5e"], ["表現", 88, "#10b981"]].map(([l, v, c]) => (
                  <div key={l as string} className="flex items-center gap-1.5 text-[9px]">
                    <span className="w-6 text-slate-500">{l}</span>
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                      <span className="block h-1.5 rounded-full" style={{ width: `${v}%`, background: c as string }} />
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="ml-auto max-w-[70%] rounded-2xl rounded-br-md bg-brand-gradient px-3 py-2 text-[11px] text-white">
            ありがとう！やってみる🔥
          </div>
        </div>
      </div>
      <div className="absolute -right-3 -top-3 animate-floaty rounded-2xl bg-white px-3 py-2 text-xs font-bold text-brand-600 shadow-soft">
        🎙 録音するだけ
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="bg-studio min-h-[100dvh] pb-24 sm:pb-0">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />

      {/* 追従ヘッダー */}
      <header className="sticky top-0 z-30 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3">
          <BrandWordmark size={40} />
          <div className="hidden items-center gap-3 sm:flex">
            <Link href="/login" className="text-sm font-medium text-slate-500 hover:text-brand-600">
              ログイン
            </Link>
            <Link
              href="/login"
              className="rounded-full bg-brand-gradient px-5 py-2 text-sm font-bold text-white shadow-soft transition active:scale-95"
            >
              無料で始める
            </Link>
          </div>
          <Link href="/login" className="text-sm font-medium text-slate-500 hover:text-brand-600 sm:hidden">
            ログイン
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5">
        {/* Hero */}
        <section className="relative mt-4 overflow-hidden rounded-[2rem] bg-brand-gradient p-8 text-white shadow-soft sm:p-12">
          <div className="absolute -right-10 -top-10 h-56 w-56 rounded-full bg-white/15 blur-2xl" />
          <div className="absolute -bottom-16 left-10 h-64 w-64 rounded-full bg-pink-300/20 blur-3xl" />
          <div className="relative z-10 grid items-center gap-8 lg:grid-cols-2">
            <div className="max-w-xl">
              <p className="mb-4 inline-flex items-center gap-1 rounded-full bg-white/20 px-3 py-1 text-xs font-bold">
                🎤 AIボーカルトレーナー
              </p>
              <h1 className="text-4xl font-black leading-[1.1] sm:text-5xl">
                その歌、あと一歩。
                <span className="mt-2 block text-lg font-bold text-white/90 sm:text-xl">
                  AIボーカルトレーナーが、今日直すところを教えます。
                </span>
              </h1>
              <p className="mt-5 max-w-md text-white/90">
                歌の録音を送るだけ。AIが音程・リズム・表現を解析して、
                あなた専用の基礎練メニューまでチャットでお届けします。
              </p>
              <Link
                href="/login"
                className="mt-7 inline-flex items-center gap-2 rounded-full bg-white px-7 py-3.5 font-bold text-brand-700 shadow-soft transition active:scale-95"
              >
                無料で始める <span className="text-sm font-normal text-slate-400">30秒・登録だけ</span>
              </Link>
              <p className="mt-3 text-xs text-white/70">専用マイク不要・スマホひとつでOK・クレジットカード不要</p>
            </div>
            <div className="hidden lg:block">
              <ProductMockup />
            </div>
          </div>
        </section>

        {/* スマホ用モックアップ */}
        <div className="mt-8 lg:hidden">
          <ProductMockup />
        </div>

        {/* 課題提起 */}
        <section className="mt-14 text-center">
          <h2 className="text-2xl font-bold text-slate-800">こんな悩み、ありませんか？</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {PROBLEMS.map((p) => (
              <div key={p.text} className="glass rounded-2xl p-5 shadow-card">
                <div className="text-3xl">{p.icon}</div>
                <p className="mt-2 text-sm font-medium text-slate-600">{p.text}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ソリューション */}
        <section className="mt-14 rounded-3xl bg-white/70 p-8 text-center shadow-card backdrop-blur sm:p-10">
          <p className="text-sm font-bold text-brand-600">SOLUTION</p>
          <h2 className="mt-2 text-2xl font-black text-slate-800 sm:text-3xl">
            ひとりの練習に、<span className="text-brand-gradient">AIの耳</span>を。
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-slate-600">
            こえのアトリエは、あなたの録音をAIボーカルトレーナーが解析して
            「良かった点 → 直すところ → 今日の基礎練」までチャットで伴走します。
            教室に通わなくても、家でスマホひとつ。
          </p>
        </section>

        {/* 機能紹介（写真つき） */}
        <section className="mt-14">
          <h2 className="text-center text-2xl font-bold text-slate-800">登録すると、できること</h2>
          <div className="mt-6 grid gap-5 sm:grid-cols-3">
            {FEATURES.map((f) => (
              <div key={f.title} className="glass flex flex-col overflow-hidden rounded-3xl shadow-card">
                <div
                  className="relative h-36 bg-brand-gradient bg-cover bg-center"
                  style={{ backgroundImage: `url(${f.photo}), linear-gradient(135deg,#7c3aed,#ec4899)` }}
                  role="img"
                  aria-label={f.alt}
                >
                  <span className="absolute left-3 top-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-white/90 text-2xl shadow-soft">
                    {f.icon}
                  </span>
                  <span className="absolute right-3 top-3 rounded-full bg-white/90 px-2.5 py-1 text-xs font-bold text-brand-600">
                    {f.tag}
                  </span>
                </div>
                <div className="flex flex-1 flex-col p-5">
                  <h3 className="text-lg font-bold text-slate-800">{f.title}</h3>
                  <p className="mt-2 flex-1 text-sm text-slate-500">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 使い方 */}
        <section className="mt-14">
          <h2 className="text-center text-2xl font-bold text-slate-800">使い方は、3ステップ</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {STEPS.map((s) => (
              <div key={s.n} className="glass rounded-2xl p-5 shadow-card">
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-gradient text-sm font-bold text-white">
                    {s.n}
                  </span>
                  <span className="text-2xl">{s.icon}</span>
                </div>
                <div className="mt-3 font-bold text-slate-800">{s.title}</div>
                <div className="mt-1 text-sm text-slate-500">{s.desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section className="mt-14">
          <h2 className="text-center text-2xl font-bold text-slate-800">よくある質問</h2>
          <div className="mx-auto mt-6 max-w-2xl space-y-3">
            {FAQ.map((f) => (
              <div key={f.q} className="glass rounded-2xl p-5 shadow-card">
                <div className="font-bold text-slate-800">Q. {f.q}</div>
                <div className="mt-1 text-sm text-slate-600">A. {f.a}</div>
              </div>
            ))}
          </div>
        </section>

        {/* 最後のCTA */}
        <section className="mt-14 overflow-hidden rounded-[2rem] bg-brand-gradient p-10 text-center text-white shadow-soft">
          <h2 className="text-3xl font-black">上達は、今日の一歩から。</h2>
          <p className="mt-3 text-white/90">まずは1曲、歌って送ってみましょう。AIボーカルトレーナーが待っています。</p>
          <Link
            href="/login"
            className="mt-7 inline-flex items-center gap-2 rounded-full bg-white px-8 py-4 font-bold text-brand-700 shadow-soft transition active:scale-95"
          >
            無料でレッスンを始める →
          </Link>
        </section>

        <footer className="mt-10 pb-10 text-center text-xs text-slate-400">
          こえのアトリエ — AIボーカルトレーナー（歌をAIが解析・添削するボイトレアプリ）
        </footer>
      </main>

      {/* スマホ用 追従CTAバー */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-white/40 bg-white/80 p-3 backdrop-blur sm:hidden">
        <Link
          href="/login"
          className="flex flex-col items-center rounded-2xl bg-brand-gradient py-3 font-bold text-white shadow-soft"
        >
          無料でレッスンを始める →
          <span className="text-[11px] font-normal text-white/80">専用マイク不要・登録30秒・無料</span>
        </Link>
      </div>
    </div>
  );
}
