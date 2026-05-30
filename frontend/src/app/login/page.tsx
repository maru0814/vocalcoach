"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/api";
import { BrandWordmark, LogoMark } from "@/components/brand/Brand";

const FEATURES = [
  { icon: "🎙", title: "録って送るだけ", desc: "ブラウザでその場録音、または音源をアップロード。" },
  { icon: "📊", title: "声を見える化", desc: "音程・リズム・表現を解析して、やさしく解説。" },
  { icon: "🎯", title: "今日の課題と基礎練", desc: "あなたに合った練習メニューと参考動画を提案。" },
  { icon: "📈", title: "上達を実感", desc: "録り直すたびに、良くなった点をちゃんと褒めます。" },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("register");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "register") await register(email, password);
      await login(email, password);
      router.push("/coach");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setError(
        mode === "register"
          ? "登録できませんでした。すでに登録済みのメールかもしれません。"
          : "ログインに失敗しました。メール・パスワードをご確認ください。",
      );
      void msg;
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-studio min-h-[100dvh] w-full">
      <div className="mx-auto grid min-h-[100dvh] max-w-6xl grid-cols-1 lg:grid-cols-2">
        {/* 左: ヒーロー */}
        <section className="relative hidden flex-col justify-between overflow-hidden p-10 lg:flex">
          <div className="absolute -left-16 top-24 h-64 w-64 rounded-full bg-brand-300/40 blur-3xl" />
          <div className="absolute -right-10 bottom-10 h-72 w-72 rounded-full bg-pink-300/30 blur-3xl" />

          <BrandWordmark size={44} />

          <div className="relative z-10 space-y-6">
            <div className="animate-floaty inline-flex h-20 w-20 items-center justify-center rounded-3xl bg-brand-gradient text-4xl shadow-soft">
              🎤
            </div>
            <h1 className="text-4xl font-black leading-tight text-slate-900">
              あなたの歌に、
              <br />
              <span className="text-brand-gradient">専属トレーナー</span>を。
            </h1>
            <p className="max-w-md text-slate-600">
              録った歌を送るだけ。音程・リズム・表現をその場で解析して、
              次にやるべき基礎練までやさしくナビゲートします。
            </p>
            <div className="grid max-w-md grid-cols-2 gap-3">
              {FEATURES.map((f) => (
                <div key={f.title} className="glass rounded-2xl p-3 shadow-card">
                  <div className="text-2xl">{f.icon}</div>
                  <div className="mt-1 text-sm font-bold text-slate-800">{f.title}</div>
                  <div className="text-xs text-slate-500">{f.desc}</div>
                </div>
              ))}
            </div>
          </div>

          <p className="relative z-10 text-xs text-slate-400">© こえのアトリエ — AI Vocal Trainer</p>
        </section>

        {/* 右: フォーム */}
        <section className="flex items-center justify-center p-6">
          <div className="w-full max-w-sm">
            <div className="mb-6 flex justify-center lg:hidden">
              <BrandWordmark size={44} />
            </div>

            <div className="glass animate-fade-in-up rounded-3xl p-7 shadow-soft">
              <div className="mb-6 flex justify-center">
                <LogoMark size={56} />
              </div>
              <h2 className="text-center text-2xl font-bold text-slate-900">
                {mode === "login" ? "おかえりなさい" : "はじめましょう"}
              </h2>
              <p className="mb-6 mt-1 text-center text-sm text-slate-500">
                {mode === "login" ? "レッスンの続きへ" : "30秒でレッスンを始められます"}
              </p>

              <form className="space-y-3" onSubmit={onSubmit}>
                <label className="block">
                  <span className="mb-1 block text-xs font-medium text-slate-500">メールアドレス</span>
                  <input
                    className="w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm outline-none transition focus:border-brand-400 focus:shadow-glow"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-medium text-slate-500">パスワード（8文字以上）</span>
                  <input
                    className="w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm outline-none transition focus:border-brand-400 focus:shadow-glow"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                  />
                </label>

                {error && (
                  <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>
                )}

                <button
                  className="group relative w-full overflow-hidden rounded-xl bg-brand-gradient px-4 py-3 font-bold text-white shadow-soft transition active:scale-[0.99] disabled:opacity-60"
                  disabled={loading}
                  type="submit"
                >
                  {loading ? "送信中…" : mode === "login" ? "ログイン" : "無料で始める"}
                </button>
              </form>

              <div className="mt-5 text-center text-sm text-slate-500">
                {mode === "login" ? "アカウントがない方は" : "すでに登録済みの方は"}{" "}
                <button
                  className="font-bold text-brand-600 underline-offset-2 hover:underline"
                  onClick={() => {
                    setMode(mode === "login" ? "register" : "login");
                    setError("");
                  }}
                  type="button"
                >
                  {mode === "login" ? "新規登録" : "ログイン"}
                </button>
              </div>
            </div>

            <p className="mt-4 text-center text-xs text-slate-400">
              録音した声はあなた専用。レッスンの記録として安全に保存されます。
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
