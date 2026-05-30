import Link from "next/link";
import { BrandWordmark } from "@/components/brand/Brand";

const STEPS = [
  { n: "1", icon: "🎵", title: "曲と区間を伝える", desc: "原曲のURLと、見てほしいところ（サビなど）を入力。" },
  { n: "2", icon: "🎙", title: "歌って送る", desc: "その場で録音、または音源をアップロード。" },
  { n: "3", icon: "💬", title: "FBを受け取る", desc: "スコア・課題・基礎練・参考動画がチャットで届く。" },
];

export default function HomePage() {
  return (
    <div className="bg-studio min-h-[100dvh]">
      <header className="mx-auto flex max-w-5xl items-center justify-between p-5">
        <BrandWordmark size={42} />
        <Link
          href="/login"
          className="rounded-full bg-white/70 px-4 py-2 text-sm font-bold text-brand-700 shadow-card backdrop-blur"
        >
          ログイン
        </Link>
      </header>

      <main className="mx-auto max-w-5xl px-5 pb-20">
        <section className="relative mt-8 overflow-hidden rounded-[2rem] bg-brand-gradient p-8 text-white shadow-soft sm:p-12">
          <div className="absolute -right-10 -top-10 h-48 w-48 rounded-full bg-white/15 blur-2xl" />
          <div className="absolute -bottom-12 left-10 h-56 w-56 rounded-full bg-pink-300/20 blur-3xl" />
          <div className="relative z-10 max-w-xl">
            <p className="mb-3 inline-flex rounded-full bg-white/20 px-3 py-1 text-xs font-bold">
              🎤 AIボイストレーナー
            </p>
            <h1 className="text-4xl font-black leading-tight sm:text-5xl">
              録った歌に、
              <br />
              その場でレッスン。
            </h1>
            <p className="mt-4 max-w-md text-white/90">
              音程・リズム・表現を解析して、今日やるべき基礎練と参考動画まで。
              チャットでやり取りしながら、一緒に上達していきましょう。
            </p>
            <Link
              href="/login"
              className="mt-7 inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 font-bold text-brand-700 shadow-soft transition active:scale-95"
            >
              無料でレッスンを始める →
            </Link>
          </div>
        </section>

        <section className="mt-10 grid gap-4 sm:grid-cols-3">
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
        </section>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link href="/coach" className="rounded-full bg-brand-gradient px-6 py-3 font-bold text-white shadow-soft">
            🎤 ボイストレーナーに相談する
          </Link>
          <Link href="/recordings" className="rounded-full border border-slate-200 bg-white/70 px-6 py-3 font-medium text-slate-600">
            評価履歴一覧
          </Link>
        </div>
      </main>
    </div>
  );
}
