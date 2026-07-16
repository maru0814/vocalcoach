"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Recorder } from "@/components/coach/Recorder";
import { VoiceTypeBlock, ShareButtons } from "@/components/voice/VoiceTypeResult";
import { VoiceTypeArt } from "@/components/voice/VoiceTypeArt";
import { VOICE_TYPE_LIST } from "@/components/voice/voiceTypes";
import { VoiceTypeStats } from "@/components/voice/VoiceTypeStats";
import { analyzeVoiceType, getMe, VoiceTypeResult } from "@/lib/api";
import { VoiceTypeProfileArticle } from "@/components/voice/VoiceTypeProfileArticle";
import type { VoiceProfile } from "@/content/voiceProfiles";
import { BrandWordmark } from "@/components/brand/Brand";
import { CoachAvatar } from "@/components/character/Coach";
import { StageDecor } from "@/components/site/Stage";
import { Icon } from "@/components/site/IconChip";

const LOGIN_URL = "/login?next=/voice-type";

const MAX_SEC = 20;

// 未登録時の診断結果をログイン/登録のページ遷移をまたいで引き継ぐためのブリッジ（docs/67）。
// PIIは含まない（既存の匿名集計イベントと同様、type_id・score等のみ）。
const BRIDGE_KEY = "voiceTypeResultBridge";
const BRIDGE_TTL_MS = 30 * 60 * 1000;

function saveResultBridge(result: VoiceTypeResult) {
  try {
    sessionStorage.setItem(BRIDGE_KEY, JSON.stringify({ result, savedAt: Date.now() }));
  } catch {
    // sessionStorage不可の環境では引き継ぎを諦める（診断そのものは継続可能）
  }
}

function readResultBridge(): VoiceTypeResult | null {
  try {
    const raw = sessionStorage.getItem(BRIDGE_KEY);
    if (!raw) return null;
    const { result, savedAt } = JSON.parse(raw) as { result: VoiceTypeResult; savedAt: number };
    if (typeof savedAt !== "number" || Date.now() - savedAt > BRIDGE_TTL_MS) {
      sessionStorage.removeItem(BRIDGE_KEY);
      return null;
    }
    return result;
  } catch {
    return null;
  }
}

function clearResultBridge() {
  try {
    sessionStorage.removeItem(BRIDGE_KEY);
  } catch {
    // noop
  }
}

export default function VoiceTypePage() {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VoiceTypeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  // 認証状態。未ログインでも診断は1回完走できる（docs/35 課題1: アハ→登録）。
  // 結果は未ログインだとぼかして提示し、シェア/保存の瞬間に登録へ誘導する。
  const [auth, setAuth] = useState<"checking" | "in" | "out">("checking");
  // 診断されたタイプの詳細プロフィール記事（docs/69 FR-01）。
  // 本文は約300KBあるため初期バンドルに含めず、結果が出てから動的importする。
  const [profile, setProfile] = useState<VoiceProfile | null>(null);

  const resultRef = useRef<HTMLElement | null>(null);
  const recorderRef = useRef<Recorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const shareRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    getMe()
      .then(() => setAuth("in"))
      .catch(() => setAuth("out"));
  }, []);

  // ログイン/登録画面への遷移でアンマウントされても、戻ってきたときに結果を復元する（docs/67）。
  useEffect(() => {
    if (result) return;
    const restored = readResultBridge();
    if (restored) setResult(restored);
  }, [result]);

  // フル結果を実際に見られた時点でブリッジは消費済みとし、使い回されないようにする。
  useEffect(() => {
    if (result && auth === "in") clearResultBridge();
  }, [result, auth]);

  // 結果が決まったらそのタイプの記事を読み込む（docs/69 FR-01）。
  // 本文は約300KBあるため初期バンドルに含めず動的importする。診断直後だけでなく
  // ブリッジからの復元（docs/67）でも result が入るため、runAnalyze ではなく result 起点で読む。
  useEffect(() => {
    const id = result?.voice_type?.id;
    if (!id) {
      setProfile(null);
      return;
    }
    let cancelled = false;
    // 記事の読み込み失敗は診断結果に影響させない（記事ブロックが出ないだけ）
    import("@/content/voiceProfiles")
      .then((m) => {
        if (!cancelled) setProfile(m.VOICE_PROFILES[id] ?? null);
      })
      .catch(() => {
        if (!cancelled) setProfile(null);
      });
    return () => {
      cancelled = true;
    };
  }, [result]);

  // 診断が出たら結果カードを画面上部へ運ぶ（docs/69 FR-04）。
  // 自動スクロールが無いと、結果もその下の記事もユーザーの視界に入らないまま終わる。
  useEffect(() => {
    if (!result || auth === "checking") return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    resultRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }, [result, auth]);

  async function runAnalyze(blob: Blob, filename: string) {
    setError(null);
    setResult(null);
    setProfile(null);
    setLoading(true);
    try {
      const res = await analyzeVoiceType(blob, filename);
      setResult(res);
      saveResultBridge(res);
      // 記事は result 起点の useEffect が読み込む（復元経路と共通化するため）
    } catch (e: unknown) {
      const err = e as Error & { status?: number };
      setError(err.message || "診断に失敗しました。もう一度お試しください。");
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
      setError("マイクの使用を許可してください");
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
        {/* ヒーロー（夜のステージ docs/55 Phase 3） */}
        <section className="bg-stage grain relative overflow-hidden rounded-2xl p-6 text-white shadow-soft">
          <StageDecor notes={false} />
          <div className="relative z-10">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-bold">
              <span className="inline-flex"><CoachAvatar size={16} /></span>
              声タイプ診断
            </span>
            <h1 className="mt-3 text-2xl font-black leading-snug sm:text-3xl">
              あなたの声は、どのタイプ？
            </h1>
            <p className="mt-2 text-sm text-white/90">
              15秒くらい歌うだけ。AIが発声を解析して、8つの声タイプから診断します。
              似た声質のアーティストつき。結果はそのままシェアできます。
            </p>
          </div>
        </section>

        {/* 8タイプギャラリー */}
        <VoiceTypeStats />

        <section className="rounded-2xl bg-white/85 p-4 shadow-card">
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
          <section className="rounded-2xl bg-white/90 p-5 shadow-card">
            {auth === "checking" ? (
              <div className="flex flex-col items-center gap-3 py-6">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand-200 border-t-brand-500" />
                <p className="text-sm font-bold text-slate-600">準備しています…</p>
              </div>
            ) : loading ? (
              <div className="flex flex-col items-center gap-3 py-6">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand-200 border-t-brand-500" />
                <p className="text-sm font-bold text-slate-600">声を解析しています…</p>
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
                  <button onClick={cancelRecording} aria-label="録音をやめる" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"><Icon name="x" size={14} /></button>
                  <button onClick={stopRecording} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white shadow-[0_3px_0_#5b21b6] transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 active:translate-y-[2px] active:shadow-[0_1px_0_#5b21b6]">■ 診断する</button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <button
                  onClick={startRecording}
                  className="flex w-full items-center justify-center gap-2 rounded-full bg-brand-600 px-6 py-4 text-base font-bold text-white shadow-[0_4px_0_#5b21b6] transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 active:translate-y-[3px] active:shadow-[0_1px_0_#5b21b6]"
                >
                  <Icon name="mic" size={18} /> 録音して診断する
                </button>
                <button
                  onClick={() => fileRef.current?.click()}
                  className="flex w-full items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-bold text-slate-600 shadow-[0_4px_0_#cbd5e1] transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 active:translate-y-[3px] active:shadow-[0_1px_0_#cbd5e1]"
                >
                  <Icon name="paperclip" size={16} /> 音源をアップロードして診断
                </button>
                <input ref={fileRef} type="file" accept="audio/*" onChange={onFile} className="hidden" />
                <p className="px-1 text-center text-[11px] text-slate-400">
                  サビなど、しっかり声を出している部分を15秒ほど歌うのがおすすめです
                </p>
              </div>
            )}
            {error && <div className="mt-3 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
          </section>
        )}

        {/* 結果カード */}
        {result && auth === "in" && (
          <section ref={resultRef} className="scroll-mt-4 space-y-3">
            <div className="rounded-2xl bg-white/90 p-4 shadow-card">
              <div ref={shareRef} className="space-y-0">
                <VoiceTypeBlock vt={result.voice_type} score={result.score} />
              </div>
              <div className="mt-3">
                <ShareButtons vt={result.voice_type} score={result.score} shareRef={shareRef} />
              </div>
            </div>

            {/* 下に記事が続くことを明示する誘導（docs/69 FR-05）。shareRef の外＝シェア画像には写らない */}
            {profile && (
              <p className="text-center">
                <a
                  href="#profile"
                  className="text-xs font-bold text-brand-600 underline decoration-brand-200 underline-offset-2 transition hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                >
                  ↓ {profile.nameJa}のプロフィールを読む
                </a>
              </p>
            )}

            <div className="flex gap-2">
              {/* profile は result 起点の useEffect が null に戻すため、ここでは触らない */}
              <button
                onClick={() => { setResult(null); setError(null); clearResultBridge(); }}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-600 shadow-[0_4px_0_#cbd5e1] transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 active:translate-y-[3px] active:shadow-[0_1px_0_#cbd5e1]"
              >
                <Icon name="refresh" size={15} /> もう一度診断
              </button>
              <Link
                href="/coach"
                className="flex-1 rounded-full bg-brand-600 px-4 py-3 text-center text-sm font-bold text-white shadow-[0_4px_0_#5b21b6] transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 active:translate-y-[3px] active:shadow-[0_1px_0_#5b21b6]"
              >
                レッスンを受ける →
              </Link>
            </div>
            <p className="px-1 text-center text-[11px] text-slate-400">
              声タイプは「傾向」の推定です。録音の歌い方や録音環境で変わることがあります。
            </p>

            {/* 診断されたタイプの詳細プロフィール記事（docs/69 FR-01・docs/70 §3-2）。
                MBTIのように診断完了と同時に全文を読める。記事本体は詳細ページと共有。 */}
            {profile && (
              <div className="space-y-8 pt-4">
                <h2
                  id="profile"
                  className="scroll-mt-4 text-center font-rounded text-xl font-black tracking-tight text-slate-900"
                >
                  {profile.nameJa}のプロフィール
                </h2>
                <VoiceTypeProfileArticle profile={profile} />

                {/* 読了直後にレッスンへ橋を架ける（docs/69 FR-06・docs/70）。
                    夜のステージ調でヒーローと呼応させ、読み物の終わり＝行動の始まりを示す。 */}
                <section className="bg-stage grain relative overflow-hidden rounded-2xl p-6 text-center text-white shadow-soft">
                  <StageDecor notes={false} />
                  <div className="relative z-10">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-bold">
                      <span className="inline-flex"><CoachAvatar size={16} /></span>
                      ここまで読んでくれたあなたへ
                    </span>
                    <h2 className="mt-3 font-rounded text-2xl font-black tracking-tight">
                      その声を、磨きにいこう
                    </h2>
                    <p className="mx-auto mt-3 max-w-md font-body text-sm leading-relaxed text-white/90">
                      {profile.nameJa}の武器も、苦手も、もう分かりました。あとは、実際に歌ってみるだけです。
                      あなたが歌った一曲をソラ先生が聴いて、{profile.nameJa}の良さがいちばん出た瞬間と、
                      もう一歩だったところを、具体的な言葉でお返しします。
                    </p>
                    <Link
                      href="/coach"
                      className="mt-5 inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-bold text-brand-700 shadow-[0_4px_0_rgba(255,255,255,0.35)] transition hover:brightness-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white active:translate-y-[3px] active:shadow-[0_1px_0_rgba(255,255,255,0.35)]"
                    >
                      ソラ先生のレッスンを受ける →
                    </Link>
                  </div>
                </section>

                {/* 単独ページへの補助リンク（FR-03: あとで読み返す・URL共有用） */}
                <p className="text-center">
                  <Link
                    href={`/voice-type/${result.voice_type.id}`}
                    className="text-xs font-bold text-brand-600 underline decoration-brand-200 underline-offset-2 transition hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                  >
                    この記事を単独ページで開く →
                  </Link>
                </p>
              </div>
            )}
          </section>
        )}

        {/* 未登録の結果: アハ→登録（docs/35 課題1）。結果をぼかして提示し、
            「見る・シェアする」瞬間に無料登録へ誘導する。 */}
        {result && auth !== "in" && (
          <section ref={resultRef} className="scroll-mt-4 space-y-3">
            <div className="relative overflow-hidden rounded-2xl bg-white/90 p-4 shadow-card">
              <div className="pointer-events-none select-none blur-[7px]" aria-hidden="true">
                <VoiceTypeBlock vt={result.voice_type} score={result.score} />
              </div>
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-white/45 px-6 text-center backdrop-blur-[2px]">
                <CoachAvatar size={72} pose="clap" />
                <p className="text-base font-black text-slate-800">あなたの声タイプが出ました！</p>
                <p className="text-xs leading-relaxed text-slate-600">
                  無料登録すると、結果カード（似た声のアーティスト・スコア）が見られて、
                  そのままシェアもできます。声に合わせた発声レッスンもぜんぶ無料です。
                </p>
                <Link
                  href={LOGIN_URL}
                  className="inline-flex items-center justify-center rounded-full bg-brand-600 px-6 py-3 font-bold text-white shadow-[0_4px_0_#5b21b6] transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 active:translate-y-[3px] active:shadow-[0_1px_0_#5b21b6]"
                >
                  無料登録して結果を見る →
                </Link>
                <p className="text-[11px] text-slate-400">登録済みの方は、ログインすると結果が開きます</p>
              </div>
            </div>

            <button
              onClick={() => { setResult(null); setError(null); clearResultBridge(); }}
              className="w-full rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-600 transition active:scale-95"
            >
              <Icon name="refresh" size={15} /> もう一度ためす
            </button>
            <p className="px-1 text-center text-[11px] text-slate-400">
              声タイプは「傾向」の推定です。録音の歌い方や録音環境で変わることがあります。
            </p>
          </section>
        )}
      </main>
    </div>
  );
}
