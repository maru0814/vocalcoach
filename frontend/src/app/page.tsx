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
    desc: "音程・リズム・表現を数値とグラフに。「なんとなく下手」が「サビ後半で息が切れている」に変わります。",
    tag: "解析",
  },
  {
    icon: "🎯",
    title: "今日の課題と基礎練がもらえる",
    desc: "あなたの弱点に合わせた練習メニューと、お手本のYouTube動画つき。道具はいりません、声と体だけ。",
    tag: "練習",
  },
  {
    icon: "📈",
    title: "上達が記録に残る",
    desc: "レッスンごとに保存。録り直すと「前回より◯◯が良くなった」を数値で実感できます。",
    tag: "記録",
  },
];

const STEPS = [
  { n: "1", icon: "🎵", title: "曲と区間を伝える", desc: "歌いたい曲のURLと、見てほしいところ（サビなど）を入力。" },
  { n: "2", icon: "🎙", title: "歌って送る", desc: "その区間を録音、または音源をアップロード。" },
  { n: "3", icon: "💬", title: "FBを受け取る", desc: "スコア・課題・基礎練がチャットで届きます。" },
];

const FAQ = [
  { q: "本当に無料ですか？", a: "はい。メール登録だけで、すぐに始められます。" },
  { q: "機材は必要ですか？", a: "スマホ・PCのマイクだけでOK。特別な機材はいりません。" },
  { q: "音痴でも大丈夫？", a: "むしろそういう方向けです。やさしく、具体的にお伝えします。" },
  { q: "録った歌は誰かに見られる？", a: "いいえ。あなた専用に安全に保存され、他の人には見えません。" },
];

export default function HomePage() {
  return (
    <div className="bg-studio min-h-[100dvh] pb-24 sm:pb-0">
      {/* 追従ヘッダー（PC・スマホ共通、スクロールで固定） */}
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
        <section className="relative mt-4 overflow-hidden rounded-[2rem] bg-brand-gradient p-8 text-white shadow-soft sm:p-14">
          <div className="absolute -right-10 -top-10 h-56 w-56 rounded-full bg-white/15 blur-2xl" />
          <div className="absolute -bottom-16 left-10 h-64 w-64 rounded-full bg-pink-300/20 blur-3xl" />
          <div className="relative z-10 max-w-xl">
            <p className="mb-4 inline-flex items-center gap-1 rounded-full bg-white/20 px-3 py-1 text-xs font-bold">
              🎤 AIボイストレーナー
            </p>
            <h1 className="text-5xl font-black leading-[1.1] sm:text-6xl">その歌、あと一歩。</h1>
            <p className="mt-5 max-w-md text-lg text-white/90">
              録って送るだけ。AIがあなたの声を解析して、<br className="hidden sm:block" />
              今日直すところを教えます。
            </p>
            <Link
              href="/login"
              className="mt-8 inline-flex items-center gap-2 rounded-full bg-white px-7 py-3.5 font-bold text-brand-700 shadow-soft transition active:scale-95"
            >
              無料で始める <span className="text-sm font-normal text-slate-400">30秒・登録だけ</span>
            </Link>
            <p className="mt-3 text-xs text-white/70">クレジットカード不要・マイクだけでOK</p>
          </div>
        </section>

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
            ひとりの練習に、<span className="text-brand-gradient">客観的な耳</span>を。
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-slate-600">
            こえのアトリエは、あなたの録音を解析して「良かった点 → 直すところ → 今日の基礎練」まで
            チャットで伴走します。教室に通わなくても、家でスマホひとつ。
          </p>
        </section>

        {/* 機能紹介（登録するとできること） */}
        <section className="mt-14">
          <h2 className="text-center text-2xl font-bold text-slate-800">登録すると、できること</h2>
          <div className="mt-6 grid gap-5 sm:grid-cols-3">
            {FEATURES.map((f) => (
              <div key={f.title} className="glass flex flex-col rounded-3xl p-6 shadow-card">
                <div className="flex items-center justify-between">
                  <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-gradient text-2xl shadow-soft">
                    {f.icon}
                  </span>
                  <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-bold text-brand-600">{f.tag}</span>
                </div>
                <h3 className="mt-4 text-lg font-bold text-slate-800">{f.title}</h3>
                <p className="mt-2 flex-1 text-sm text-slate-500">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* 使い方 */}
        <section className="mt-14">
          <h2 className="text-center text-2xl font-bold text-slate-800">使い方は、3ステップ</h2>
          <div className="relative mt-6 grid gap-4 sm:grid-cols-3">
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
          <p className="mt-3 text-white/90">まずは1曲、歌って送ってみましょう。</p>
          <Link
            href="/login"
            className="mt-7 inline-flex items-center gap-2 rounded-full bg-white px-8 py-4 font-bold text-brand-700 shadow-soft transition active:scale-95"
          >
            無料でレッスンを始める →
          </Link>
        </section>

        <footer className="mt-10 pb-10 text-center text-xs text-slate-400">
          © こえのアトリエ — AI Vocal Trainer
        </footer>
      </main>

      {/* スマホ用 追従CTAバー（画面下固定） */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-white/40 bg-white/80 p-3 backdrop-blur sm:hidden">
        <Link
          href="/login"
          className="flex flex-col items-center rounded-2xl bg-brand-gradient py-3 font-bold text-white shadow-soft"
        >
          無料でレッスンを始める →
          <span className="text-[11px] font-normal text-white/80">登録30秒・いつでも無料</span>
        </Link>
      </div>
    </div>
  );
}
