"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Recorder } from "@/components/coach/Recorder";
import { VoiceTypeBlock, ShareButtons } from "@/components/voice/VoiceTypeResult";
import { VoiceTypeArt } from "@/components/voice/VoiceTypeArt";
import { VOICE_TYPE_LIST } from "@/components/voice/voiceTypes";
import { VoiceTypeStats } from "@/components/voice/VoiceTypeStats";
import { analyzeVoiceType, getMe, VoiceTypeResult } from "@/lib/api";
import { BrandWordmark } from "@/components/brand/Brand";

const LOGIN_URL = "/login?next=/voice-type";

const MAX_SEC = 20;

export default function VoiceTypePage() {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VoiceTypeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [needLogin, setNeedLogin] = useState(false);
  // 認証ゲート: 未ログインなら録音させず、登録に誘導する
  const [auth, setAuth] = useState<"checking" | "in" | "out">("checking");

  const recorderRef = useRef<Recorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const shareRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    getMe()
      .then(() => setAuth("in"))
      .catch(() => setAuth("out"));
  }, []);

  async function runAnalyze(blob: Blob, filename: string) {
    setError(null);
    setNeedLogin(false);
    setResult(null);
    setLoading(true);
    try {
      const res = await analyzeVoiceType(blob, filename);
      setResult(res);
    } catch (e: unknown) {
      const err = e as Error & { status?: number };
      if (err.status === 401) {
        setNeedLogin(true);
      } else {
        setError(err.message || "診断に失敗しました。もう一度お試しください。");
      }
    } finally {
      setLoading(false);
    }
  }

  async function startRecording() {
    setError(null);
    try {
      const rec = new Recorder();
      await rec.start();
      recorderRef.current = rec;
      setRecording(true);
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed((s) => {
          if (s + 1 >= MAX_SEC) {
            stopRecording();
            return MAX_SEC;
          }
          return s + 1;
        });
      }, 1000);
    } catch {
      setError("マイクの使用を許可してください🎤");
    }
  }

  async function stopRecording() {
    if (timerRef.current) clearInterval(timerRef.current);
    const rec = recorderRef.current;
    if (!rec) return;
    setRecording(false);
    try {
      const { blob, ext } = await rec.stop();
      await runAnalyze(blob, `voice.${ext}`);
    } catch {
      setError("録音に失敗しました。もう一度お試しください。");
    }
    recorderRef.current = null;
  }

  function cancelRecording() {
    if (timerRef.current) clearInterval(timerRef.current);
    recorderRef.current?.cancel();
    recorderRef.current = null;
    setRecording(false);
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) runAnalyze(f, f.name);
    if (fileRef.current) fileRef.current.value = "";
  }

  const mm = String(Math.floor(elapsed / 60));
  const ss = String(elapsed % 60).padStart(2, "0");

  return (
    <div className="bg-studio min-h-[100dvh] pb-16">
      <header className="mx-auto flex max-w-2xl items-center justify-between p-5">
        <Link href={auth === "in" ? "/coach" : "/"}><BrandWordmark size={40} /></Link>
        <Link href={auth === "in" ? "/coach" : "/"} className="text-sm font-medium text-slate-500 hover:text-brand-600">
          {auth === "in" ? "← レッスンへ" : "← トップへ"}
        </Link>
      </header>

      <main className="mx-auto max-w-2xl space-y-5 px-5">
        {/* ヒーロー */}
        <section className="relative overflow-hidden rounded-3xl bg-brand-gradient p-6 text-white shadow-soft">
          <div className="absolute -right-8 -top-10 h-36 w-36 rounded-full bg-white/15 blur-2xl" />
          <div className="relative z-10">
            <span className="inline-flex rounded-full bg-white/20 px-3 py-1 text-xs font-bold">🎤 声タイプ診断</span>
            <h1 className="mt-3 text-2xl font-black leading-snug sm:text-3xl">
              あなたの声は、どのタイプ？
            </h1>
            <p className="mt-2 text-sm text-white/90">
              15秒くらい歌うだけ。AIが発声を解析して、8つの声タイプから診断します。
              似た声質のアーティストつき。結果はそのままシェアできます😊
            </p>
          </div>
        </section>

        {/* 8タイプギャラリー */}
        <VoiceTypeStats />

        <section className="rounded-3xl bg-white/85 p-4 shadow-card">
          <div className="px-1 text-xs font-bold text-slate-500">あなたはどれ？ — 8つの声タイプ</div>
          <div className="mt-3 grid grid-cols-4 gap-2">
            {VOICE_TYPE_LIST.map((t) => (
              <div key={t.id} className="relative aspect-square overflow-hidden rounded-2xl shadow-soft">
                <VoiceTypeArt id={t.id} fallbackMascotSize={40} className="h-full w-full" />
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/55 to-transparent px-1 pb-1 pt-3 text-center">
                  <span className="text-[10px] font-bold text-white drop-shadow">{t.name}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 診断アクション or 結果 */}
        {!result && (
          <section className="rounded-3xl bg-white/90 p-5 shadow-card">
            {auth === "checking" ? (
              <div className="flex flex-col items-center gap-3 py-6">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand-200 border-t-brand-500" />
                <p className="text-sm font-bold text-slate-600">準備しています…</p>
              </div>
            ) : auth === "out" || needLogin ? (
              <div className="space-y-3 text-center">
                <p className="text-sm font-bold text-slate-700">まずは無料登録（30秒）から🎤</p>
                <p className="text-xs leading-relaxed text-slate-500">
                  声タイプ診断は、AIボイストレーナー「ソラ先生」の入口です。
                  登録すると、診断も・声に合わせた発声レッスンも、ぜんぶ無料。
                  録音はあなた専用に安全に扱われます。
                </p>
                <Link
                  href={LOGIN_URL}
                  className="inline-flex items-center justify-center rounded-full bg-brand-gradient px-6 py-3 font-bold text-white shadow-soft transition active:scale-95"
                >
                  無料登録して診断する →
                </Link>
                <p className="text-[11px] text-slate-400">登録済みの方は、そのまま診断に進めます</p>
              </div>
            ) : loading ? (
              <div className="flex flex-col items-center gap-3 py-6">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand-200 border-t-brand-500" />
                <p className="text-sm font-bold text-slate-600">声を解析しています…🎧</p>
                <p className="text-xs text-slate-400">10秒ほどで結果が出ます</p>
              </div>
            ) : recording ? (
              <div className="flex items-center gap-3 rounded-2xl bg-rose-50 px-4 py-3">
                <span className="relative flex h-3 w-3">
                  <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-rose-400" />
                  <span className="relative inline-flex h-3 w-3 rounded-full bg-rose-500" />
                </span>
                <span className="font-bold text-rose-600">録音中</span>
                <span className="font-mono text-sm text-rose-500">{mm}:{ss} / 0:{String(MAX_SEC).padStart(2, "0")}</span>
                <div className="ml-auto flex gap-2">
                  <button onClick={cancelRecording} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500">✕</button>
                  <button onClick={stopRecording} className="rounded-xl bg-brand-gradient px-4 py-2 text-sm font-bold text-white shadow-soft">■ 診断する</button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <button
                  onClick={startRecording}
                  className="flex w-full items-center justify-center gap-2 rounded-2xl bg-brand-gradient px-6 py-4 text-base font-bold text-white shadow-soft transition active:scale-95"
                >
                  🎙 録音して診断する
                </button>
                <button
                  onClick={() => fileRef.current?.click()}
                  className="flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-6 py-3 text-sm font-bold text-slate-600 transition active:scale-95"
                >
                  📎 音源をアップロードして診断
                </button>
                <input ref={fileRef} type="file" accept="audio/*" onChange={onFile} className="hidden" />
                <p className="px-1 text-center text-[11px] text-slate-400">
                  サビなど、しっかり声を出している部分を15秒ほど歌うのがおすすめです🎤
                </p>
              </div>
            )}
            {error && <div className="mt-3 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
          </section>
        )}

        {/* 結果カード */}
        {result && (
          <section className="space-y-3">
            <div className="rounded-3xl bg-white/90 p-4 shadow-card">
              <div ref={shareRef} className="space-y-0">
                <VoiceTypeBlock vt={result.voice_type} score={result.score} />
              </div>
              <div className="mt-3">
                <ShareButtons vt={result.voice_type} score={result.score} shareRef={shareRef} />
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => { setResult(null); setError(null); }}
                className="flex-1 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-600 transition active:scale-95"
              >
                🔁 もう一度診断
              </button>
              <Link
                href="/coach"
                className="flex-1 rounded-full bg-brand-gradient px-4 py-3 text-center text-sm font-bold text-white shadow-soft transition active:scale-95"
              >
                🎤 レッスンを受ける
              </Link>
            </div>
            <p className="px-1 text-center text-[11px] text-slate-400">
              声タイプは「傾向」の推定です。録音の歌い方や録音環境で変わることがあります。
            </p>
          </section>
        )}
      </main>
    </div>
  );
}
